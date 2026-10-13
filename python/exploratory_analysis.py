"""
explore_data.py  (Stage D - exploratory analysis; Power BI remains the reporting layer)
Applies the agreed Stage A/B definitions to the LATEST week and writes summary tables to documentation/eda/.
Run from the project root:   python python/explore_data.py

All thresholds below are PROPOSED management policy settings, not evidence-derived values.
"""

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "documentation" / "eda"
OUT.mkdir(parents=True, exist_ok=True)

# ---- policy parameters (configurable management policy)
DEMAND_WINDOW_WEEKS = 8  # trailing weeks used for average daily demand
SLOW_WINDOW_WEEKS = 12  # slow-moving: look-back window (M)
SLOW_MAX_ACTIVE_WEEKS = 4  # slow-moving: demand in <= N of the last M weeks (N)

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 30)
pd.set_option("display.float_format", lambda v: f"{v:,.1f}")


def inr(v):
    return f"INR {v:,.0f}"


def main():
    item = pd.read_csv(RAW / "dim_item.csv")
    wh = pd.read_csv(RAW / "dim_warehouse.csv")
    loc = pd.read_csv(RAW / "dim_item_location.csv")
    wk = pd.read_csv(RAW / "fact_inventory_weekly.csv", parse_dates=["week_start_date"])
    orders = pd.read_csv(
        RAW / "fact_replenishment_orders.csv",
        parse_dates=["order_date", "expected_date"],
    )
    rec = pd.read_csv(RAW / "fact_order_receipts.csv", parse_dates=["receipt_date"])

    master = loc.merge(item, on="item_id").merge(wh, on="warehouse_id")
    wk = wk.merge(master[["item_location_key", "unit_cost"]], on="item_location_key")
    wk["closing_value"] = wk["closing_stock"] * wk["unit_cost"]
    wk["consumption_value"] = wk["fulfilled_qty"] * wk["unit_cost"]

    weeks = sorted(wk["week_start_date"].unique())
    last_week = weeks[-1]

    # ------------------------------------------------------------------ snapshot at latest week
    last = wk[wk["week_start_date"] == last_week].set_index("item_location_key")
    tail8 = (
        wk[wk["week_start_date"].isin(weeks[-DEMAND_WINDOW_WEEKS:])]
        .groupby("item_location_key")["demand_qty"]
        .sum()
    )
    tail12 = wk[wk["week_start_date"].isin(weeks[-SLOW_WINDOW_WEEKS:])]
    active12 = (
        tail12.assign(a=tail12["demand_qty"] > 0)
        .groupby("item_location_key")["a"]
        .sum()
    )

    s = master.set_index("item_location_key").copy()
    s["on_hand"] = last["closing_stock"]
    s["on_order"] = last["on_order_qty"]
    s["add"] = tail8 / (7 * DEMAND_WINDOW_WEEKS)
    s["active_weeks_12"] = active12
    s["inv_position"] = s["on_hand"] + s["on_order"]
    s["safety_stock"] = s["safety_stock_days"] * s["add"]
    s["rop"] = s["add"] * s["planned_lead_time_days"] + s["safety_stock"]
    s["doi"] = np.where(
        s["add"] > 0, s["on_hand"] / s["add"].replace(0, np.nan), np.nan
    )
    s["on_hand_value"] = s["on_hand"] * s["unit_cost"]
    s["excess_qty"] = np.where(
        s["add"] > 0, np.maximum(0, s["on_hand"] - s["add"] * s["max_cover_days"]), 0
    )
    s["excess_value"] = s["excess_qty"] * s["unit_cost"]
    order_up_to = np.minimum(
        s["rop"] + s["add"] * s["order_cycle_days"],
        s["add"] * (s["planned_lead_time_days"] + s["max_cover_days"]),
    )
    s["suggested_qty"] = np.where(
        (s["add"] > 0) & (s["inv_position"] <= s["rop"]),
        np.ceil(np.maximum(0, order_up_to - s["inv_position"])),
        0,
    ).astype(int)
    s["suggested_value"] = s["suggested_qty"] * s["unit_cost"]

    def status(r):
        if r["add"] == 0:
            return "No Demand"
        if r["on_hand"] == 0:
            return "Stocked Out"
        if r["inv_position"] <= r["rop"]:
            if (
                r["doi"] < r["planned_lead_time_days"]
                or r["inv_position"] < r["safety_stock"]
            ):
                return "Critical Risk"
            return "Reorder Now"
        if r["excess_qty"] > 0:
            return "Excess"
        if r["active_weeks_12"] <= SLOW_MAX_ACTIVE_WEEKS:
            return "Slow-Moving"
        return "Healthy"

    s["status"] = s.apply(status, axis=1)
    order = [
        "Stocked Out",
        "Critical Risk",
        "Reorder Now",
        "Excess",
        "Slow-Moving",
        "No Demand",
        "Healthy",
    ]
    s["status"] = pd.Categorical(s["status"], categories=order, ordered=True)

    snap = s.reset_index()[
        [
            "item_location_key",
            "item_id",
            "item_name",
            "item_type",
            "category",
            "criticality",
            "abc_class",
            "warehouse_id",
            "unit_cost",
            "on_hand",
            "on_order",
            "inv_position",
            "add",
            "doi",
            "planned_lead_time_days",
            "safety_stock",
            "rop",
            "erp_reorder_point_qty",
            "max_cover_days",
            "excess_qty",
            "excess_value",
            "suggested_qty",
            "suggested_value",
            "on_hand_value",
            "active_weeks_12",
            "status",
        ]
    ]
    snap.to_csv(OUT / "snapshot_latest_week.csv", index=False)

    print(f"LATEST WEEK: {pd.Timestamp(last_week).date()}   (item-locations: {len(s)})")
    print("\n1. INVENTORY VALUE & POSITION")
    print(
        f"  On-hand value: {inr(s['on_hand_value'].sum())}   On-hand units: {int(s['on_hand'].sum()):,}"
    )
    print(s.groupby("warehouse_id")["on_hand_value"].sum().map(inr).to_string())
    print(s.groupby("item_type")["on_hand_value"].sum().map(inr).to_string())

    print("\n2. STATUS DISTRIBUTION (item-locations, on-hand value)")
    st = s.groupby("status", observed=False).agg(
        item_locations=("on_hand", "size"), on_hand_value=("on_hand_value", "sum")
    )
    print(st)
    st.to_csv(OUT / "status_summary.csv")
    print("\n   Status x criticality (counts)")
    print(pd.crosstab(s["status"], s["criticality"]))
    print("\n   Status x warehouse (counts)")
    print(pd.crosstab(s["status"], s["warehouse_id"]))

    print("\n3. STOCKOUT / SHORTAGE (observed over 26 weeks)")
    sh = wk[wk["shortage_qty"] > 0].merge(
        master[
            [
                "item_location_key",
                "criticality",
                "warehouse_id",
                "category",
                "item_type",
            ]
        ],
        on="item_location_key",
    )
    print(
        f"  Shortage item-weeks: {len(sh)} of {len(wk)} ({len(sh) / len(wk):.1%}); item-locations affected: {sh['item_location_key'].nunique()}"
    )
    fill = wk.merge(
        master[["item_location_key", "criticality", "warehouse_id", "item_type"]],
        on="item_location_key",
    )
    for col in ["criticality", "warehouse_id", "item_type"]:
        g = fill.groupby(col).agg(
            demand=("demand_qty", "sum"),
            fulfilled=("fulfilled_qty", "sum"),
            shortage_weeks=("shortage_qty", lambda x: int((x > 0).sum())),
        )
        g["fill_rate_%"] = 100 * g["fulfilled"] / g["demand"]
        print(f"\n  By {col}:\n{g[['shortage_weeks', 'fill_rate_%']]}")
    top_short = (
        wk.assign(short_value=wk["shortage_qty"] * wk["unit_cost"])
        .groupby("item_location_key")
        .agg(
            shortage_weeks=("shortage_qty", lambda x: int((x > 0).sum())),
            short_value=("short_value", "sum"),
        )
        .sort_values("short_value", ascending=False)
        .head(8)
        .merge(
            master[["item_location_key", "item_name", "criticality"]],
            on="item_location_key",
        )
    )
    print(
        "\n  Top 8 item-locations by unmet demand value (standard cost):\n",
        top_short.to_string(index=False),
    )
    wkly = wk.groupby("week_start_date").agg(
        shortage_item_locs=("shortage_qty", lambda x: int((x > 0).sum()))
    )
    wkly.to_csv(OUT / "weekly_shortage_count.csv")
    print(
        "\n  Weekly shortage item-locations (first/last 4 weeks):",
        wkly["shortage_item_locs"].tolist()[:4],
        "...",
        wkly["shortage_item_locs"].tolist()[-4:],
    )

    print("\n4. REPLENISHMENT ACTIONS (Stocked Out / Critical / Reorder Now)")
    act = snap[
        snap["status"].isin(["Stocked Out", "Critical Risk", "Reorder Now"])
    ].copy()
    act["crit_rank"] = (act["criticality"] == "Critical").map({True: 0, False: 1})
    act = act.sort_values(["status", "crit_rank", "doi"])
    print(
        f"  Actionable item-locations: {len(act)}   Total suggested order value: {inr(act['suggested_value'].sum())}"
    )
    print(
        act[
            [
                "item_location_key",
                "item_name",
                "criticality",
                "status",
                "on_hand",
                "on_order",
                "doi",
                "planned_lead_time_days",
                "rop",
                "suggested_qty",
            ]
        ]
        .head(15)
        .to_string(index=False)
    )
    act.drop(columns="crit_rank").to_csv(OUT / "replenishment_actions.csv", index=False)

    print("\n5. EXCESS, SLOW-MOVING, NO DEMAND")
    ex = s[s["excess_qty"] > 0]
    print(
        f"  Excess item-locations: {len(ex)}   Excess value (policy-based): {inr(ex['excess_value'].sum())}  "
        f"= {ex['excess_value'].sum() / s['on_hand_value'].sum():.1%} of on-hand value"
    )
    print(
        ex.groupby("category")["excess_value"]
        .sum()
        .sort_values(ascending=False)
        .map(inr)
        .to_string()
    )
    print("  Top 8 excess items:")
    print(
        ex.sort_values("excess_value", ascending=False)
        .head(8)[["item_name", "warehouse_id", "doi", "max_cover_days", "excess_value"]]
        .to_string()
    )
    slow = s[s["status"] == "Slow-Moving"]
    nd = s[s["status"] == "No Demand"]
    print(
        f"\n  Slow-moving (status): {len(slow)} item-locations, on-hand value {inr(slow['on_hand_value'].sum())}"
    )
    print(
        f"  No Demand (8 wks): {len(nd)} item-locations, non-moving stock value {inr(nd['on_hand_value'].sum())}"
    )
    print(
        f"  Slow-moving by pure demand pattern (any status, ADD>0, <= {SLOW_MAX_ACTIVE_WEEKS} active weeks of {SLOW_WINDOW_WEEKS}): "
        f"{int(((s['add'] > 0) & (s['active_weeks_12'] <= SLOW_MAX_ACTIVE_WEEKS)).sum())}"
    )
    print(
        f"  DOI distribution (ADD>0): median {s['doi'].median():.0f} d, p75 {s['doi'].quantile(.75):.0f} d, max {s['doi'].max():.0f} d"
    )

    print(
        "\n6. ERP SETTING vs POLICY ROP (is the current static reorder point adequate?)"
    )
    chk = s[s["add"] > 0].copy()
    chk["erp_vs_rop"] = chk["erp_reorder_point_qty"] / chk["rop"]
    print(
        f"  ERP ROP below calculated ROP by >25%: {int((chk['erp_vs_rop'] < 0.75).sum())}   "
        f"above by >50%: {int((chk['erp_vs_rop'] > 1.5).sum())}   within band: {int(chk['erp_vs_rop'].between(0.75, 1.5).sum())}"
    )
    short_locs = set(sh["item_location_key"])
    chk["had_shortage"] = chk.index.isin(short_locs)
    print("  Shortage incidence when ERP ROP < 75% of policy ROP vs otherwise:")
    print(
        chk.groupby(chk["erp_vs_rop"] < 0.75)["had_shortage"]
        .agg(["sum", "size"])
        .rename(columns={"sum": "with_shortage", "size": "item_locations"})
    )

    print("\n7. LEAD TIME: ACTUAL vs PLANNED (first receipt per order)")
    first = rec.sort_values("receipt_date").groupby("order_id").first().reset_index()
    first = first.merge(
        orders[["order_id", "item_location_key", "order_date"]], on="order_id"
    ).merge(
        master[
            ["item_location_key", "planned_lead_time_days", "category", "item_type"]
        ],
        on="item_location_key",
    )
    first["actual_lt"] = (first["receipt_date"] - first["order_date"]).dt.days
    first["delay"] = first["actual_lt"] - first["planned_lead_time_days"]
    lt = first.groupby("category").agg(
        orders=("delay", "size"),
        planned=("planned_lead_time_days", "mean"),
        actual=("actual_lt", "mean"),
        avg_delay=("delay", "mean"),
        pct_late=("delay", lambda x: 100 * (x > 0).mean()),
    )
    print(lt)
    lt.to_csv(OUT / "lead_time_by_category.csv")
    print(
        f"  Overall: planned {first['planned_lead_time_days'].mean():.1f} d, actual {first['actual_lt'].mean():.1f} d, "
        f"{(first['delay'] > 0).mean():.0%} of orders later than planned"
    )
    print(
        f"  Open orders at data end: {int((orders['order_status'] == 'Open').sum())}, partially received: "
        f"{int((orders['order_status'] == 'Partially Received').sum())}"
    )

    print(
        "\n8. TURNOVER (consumption-based at standard cost, annualized; NOT accounting COGS)"
    )
    days = len(weeks) * 7
    tot = wk.groupby("week_start_date")["closing_value"].sum().mean()
    cons = wk["consumption_value"].sum()
    print(
        f"  Overall: consumption {inr(cons)} over {days} days; avg weekly inventory {inr(tot)}; turnover {cons * 365 / days / tot:.1f}x"
    )
    for col in ["item_type", "warehouse_id"]:
        g = wk.merge(master[["item_location_key", col]], on="item_location_key")
        c = g.groupby(col)["consumption_value"].sum()
        a = (
            g.groupby([col, "week_start_date"])["closing_value"]
            .sum()
            .groupby(col)
            .mean()
        )
        print(
            "  By",
            col,
            ":",
            {k: round(float(c[k] * 365 / days / a[k]), 1) for k in c.index},
        )

    print(f"\nFiles written to {OUT}")


if __name__ == "__main__":
    main()
