"""
validate_data.py
Independent validation of the generated CSVs (reads files only; does not import the generator).
Run from the project root:   python python/validate_data.py
Writes documentation/validation_report.txt and exits with code 1 if any check FAILS.
"""

from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "documentation"
OUT.mkdir(exist_ok=True)

START, END = pd.Timestamp("2026-01-05"), pd.Timestamp("2026-07-05")
N_WEEKS = 26

SCHEMA = {  # column -> kind (int | float | str | date)
    "dim_item": {
        "item_id": "str",
        "item_name": "str",
        "item_type": "str",
        "category": "str",
        "uom": "str",
        "unit_cost": "float",
        "abc_class": "str",
        "criticality": "str",
    },
    "dim_warehouse": {
        "warehouse_id": "str",
        "warehouse_name": "str",
        "city": "str",
        "region": "str",
        "warehouse_role": "str",
    },
    "dim_item_location": {
        "item_location_key": "str",
        "item_id": "str",
        "warehouse_id": "str",
        "planned_lead_time_days": "int",
        "safety_stock_days": "int",
        "order_cycle_days": "int",
        "max_cover_days": "int",
        "erp_reorder_point_qty": "int",
        "erp_order_qty": "int",
    },
    "fact_inventory_weekly": {
        "item_location_key": "str",
        "week_start_date": "date",
        "opening_stock": "int",
        "receipts_qty": "int",
        "demand_qty": "int",
        "fulfilled_qty": "int",
        "shortage_qty": "int",
        "closing_stock": "int",
        "on_order_qty": "int",
    },
    "fact_replenishment_orders": {
        "order_id": "str",
        "item_location_key": "str",
        "order_type": "str",
        "order_date": "date",
        "expected_date": "date",
        "order_qty": "int",
        "order_status": "str",
    },
    "fact_order_receipts": {
        "receipt_id": "str",
        "order_id": "str",
        "receipt_date": "date",
        "received_qty": "int",
    },
}

results, lines = [], []


def log(text=""):
    print(text)
    lines.append(text)


def check(name, ok, detail=""):
    ok = bool(ok)
    results.append((name, ok))
    log(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  -> {detail}" if detail else ""))
    return ok


def main():
    log("INVENTORY ANALYTICS - DATA VALIDATION REPORT")
    log("=" * 60)

    # ---- 1. files, columns, data types
    log("\n1. FILES, COLUMNS, DATA TYPES")
    t = {}
    for name, cols in SCHEMA.items():
        path = RAW / f"{name}.csv"
        if not check(f"{name}.csv exists", path.exists()):
            continue
        df = pd.read_csv(path)
        check(
            f"{name}: columns match spec (names and order)",
            list(df.columns) == list(cols),
            "" if list(df.columns) == list(cols) else f"found {list(df.columns)}",
        )
        ok_types = True
        for c, kind in cols.items():
            if c not in df.columns:
                ok_types = False
                continue
            if kind == "int":
                ok_types &= pd.api.types.is_integer_dtype(df[c])
            elif kind == "float":
                ok_types &= pd.api.types.is_numeric_dtype(df[c])
            elif kind == "str":
                ok_types &= pd.api.types.is_string_dtype(df[c]) or df[c].dtype == object
            elif kind == "date":
                parsed = pd.to_datetime(df[c], format="%Y-%m-%d", errors="coerce")
                ok_types &= parsed.notna().all()
                df[c] = parsed
        check(f"{name}: data types as expected", ok_types)
        t[name] = df
    if len(t) < len(SCHEMA):
        log("\nCannot continue: missing files. Run python/generate_data.py first.")
        return finish()

    item, wh, loc = t["dim_item"], t["dim_warehouse"], t["dim_item_location"]
    wk, orders, rec = (
        t["fact_inventory_weekly"],
        t["fact_replenishment_orders"],
        t["fact_order_receipts"],
    )

    # ---- 2. missing values
    log("\n2. MISSING VALUES")
    for name, df in t.items():
        check(
            f"{name}: no missing values",
            df.isna().sum().sum() == 0,
            f"{int(df.isna().sum().sum())} nulls",
        )

    # ---- 3. duplicate primary keys
    log("\n3. PRIMARY KEYS")
    check("dim_item.item_id unique", item["item_id"].is_unique)
    check("dim_warehouse.warehouse_id unique", wh["warehouse_id"].is_unique)
    check(
        "dim_item_location.item_location_key unique", loc["item_location_key"].is_unique
    )
    check(
        "dim_item_location (item_id, warehouse_id) unique",
        not loc.duplicated(["item_id", "warehouse_id"]).any(),
    )
    check(
        "fact_inventory_weekly (key, week) unique",
        not wk.duplicated(["item_location_key", "week_start_date"]).any(),
    )
    check("fact_replenishment_orders.order_id unique", orders["order_id"].is_unique)
    check("fact_order_receipts.receipt_id unique", rec["receipt_id"].is_unique)
    check(
        "item_location_key = item_id|warehouse_id",
        (loc["item_location_key"] == loc["item_id"] + "|" + loc["warehouse_id"]).all(),
    )

    # ---- 4. foreign keys
    log("\n4. FOREIGN KEYS / ORPHANS")
    check(
        "dim_item_location.item_id in dim_item",
        loc["item_id"].isin(item["item_id"]).all(),
    )
    check(
        "dim_item_location.warehouse_id in dim_warehouse",
        loc["warehouse_id"].isin(wh["warehouse_id"]).all(),
    )
    check(
        "fact_inventory_weekly keys in dim_item_location",
        wk["item_location_key"].isin(loc["item_location_key"]).all(),
    )
    check(
        "fact_replenishment_orders keys in dim_item_location",
        orders["item_location_key"].isin(loc["item_location_key"]).all(),
    )
    check(
        "fact_order_receipts.order_id in orders",
        rec["order_id"].isin(orders["order_id"]).all(),
    )
    check(
        "every item-location has weekly rows",
        set(loc["item_location_key"]) == set(wk["item_location_key"]),
    )
    check(
        "every item is stocked somewhere", set(item["item_id"]) == set(loc["item_id"])
    )

    # ---- 5. dates
    log("\n5. DATE VALIDITY")
    weeks_expected = pd.date_range(START, periods=N_WEEKS, freq="7D")
    check(
        "week_start_date are all Mondays",
        (wk["week_start_date"].dt.dayofweek == 0).all(),
    )
    per_key = wk.groupby("item_location_key")["week_start_date"].apply(
        lambda s: list(sorted(s))
    )
    check(
        "each item-location has exactly 26 contiguous weeks (5 Jan - 29 Jun 2026)",
        all(v == list(weeks_expected) for v in per_key),
    )
    check(
        "order_date within [4 Jan 2026, 5 Jul 2026]",
        orders["order_date"].between(START - pd.Timedelta(days=1), END).all(),
    )
    check("receipt_date <= data end (5 Jul 2026)", (rec["receipt_date"] <= END).all())
    o_idx = orders.set_index("order_id")
    rec = rec.assign(order_date=rec["order_id"].map(o_idx["order_date"]))
    check("receipt_date > order_date", (rec["receipt_date"] > rec["order_date"]).all())
    pl = loc.set_index("item_location_key")["planned_lead_time_days"]
    exp_calc = orders["order_date"] + pd.to_timedelta(
        orders["item_location_key"].map(pl), unit="D"
    )
    check(
        "expected_date = order_date + planned lead time",
        (orders["expected_date"] == exp_calc).all(),
    )

    # ---- 6. numeric ranges
    log("\n6. NUMERIC RANGES")
    check("unit_cost > 0", (item["unit_cost"] > 0).all())
    check(
        "lead time between 1 and 60 days",
        loc["planned_lead_time_days"].between(1, 60).all(),
    )
    check(
        "safety stock, cycle, max cover days > 0",
        (loc[["safety_stock_days", "order_cycle_days", "max_cover_days"]] > 0)
        .all()
        .all(),
    )
    check(
        "max_cover_days >= safety_stock_days + order_cycle_days",
        (
            loc["max_cover_days"] >= loc["safety_stock_days"] + loc["order_cycle_days"]
        ).all(),
    )
    check(
        "ERP reorder point and order qty >= 1",
        ((loc["erp_reorder_point_qty"] >= 1) & (loc["erp_order_qty"] >= 1)).all(),
    )
    qty_cols = [
        "opening_stock",
        "receipts_qty",
        "demand_qty",
        "fulfilled_qty",
        "shortage_qty",
        "closing_stock",
        "on_order_qty",
    ]
    check(
        "weekly quantities all >= 0 (no negative stock)",
        (wk[qty_cols] >= 0).all().all(),
    )
    check(
        "order_qty >= 1 and received_qty >= 1",
        (orders["order_qty"] >= 1).all() and (rec["received_qty"] >= 1).all(),
    )

    # ---- 7. stock reconciliation
    log("\n7. STOCK RECONCILIATION (weekly)")
    wk = wk.sort_values(["item_location_key", "week_start_date"]).reset_index(drop=True)
    avail = wk["opening_stock"] + wk["receipts_qty"]
    check(
        "closing = opening + receipts - fulfilled",
        (wk["closing_stock"] == avail - wk["fulfilled_qty"]).all(),
    )
    check(
        "fulfilled = min(demand, opening + receipts)",
        (wk["fulfilled_qty"] == np.minimum(wk["demand_qty"], avail)).all(),
    )
    check(
        "shortage = demand - fulfilled",
        (wk["shortage_qty"] == wk["demand_qty"] - wk["fulfilled_qty"]).all(),
    )
    nxt = wk.groupby("item_location_key")["opening_stock"].shift(-1)
    mask = nxt.notna()
    check(
        "opening(week t+1) = closing(week t)",
        (nxt[mask] == wk.loc[mask, "closing_stock"]).all(),
    )

    # ---- 8. receipts and on-order reconciliation
    log("\n8. RECEIPTS & ON-ORDER RECONCILIATION")
    rec["item_location_key"] = rec["order_id"].map(o_idx["item_location_key"])
    rec["week_start_date"] = rec["receipt_date"] - pd.to_timedelta(
        rec["receipt_date"].dt.dayofweek, unit="D"
    )
    rec_week = (
        rec.groupby(["item_location_key", "week_start_date"])["received_qty"]
        .sum()
        .rename("rec_from_orders")
    )
    chk = wk.merge(
        rec_week,
        how="left",
        left_on=["item_location_key", "week_start_date"],
        right_index=True,
    )
    chk["rec_from_orders"] = chk["rec_from_orders"].fillna(0).astype(int)
    check(
        "weekly receipts_qty = SUM(order receipts) for that item-location-week (exact)",
        (chk["receipts_qty"] == chk["rec_from_orders"]).all(),
        f"{int((chk['receipts_qty'] != chk['rec_from_orders']).sum())} mismatches",
    )
    check(
        "total weekly receipts = total order receipts (no double counting)",
        wk["receipts_qty"].sum() == rec["received_qty"].sum(),
        f"{int(wk['receipts_qty'].sum()):,} vs {int(rec['received_qty'].sum()):,}",
    )
    check(
        "every receipt falls in a modelled week",
        rec["week_start_date"].isin(weeks_expected).all(),
    )

    got = (
        rec.groupby("order_id")["received_qty"]
        .sum()
        .reindex(orders["order_id"])
        .fillna(0)
        .astype(int)
        .values
    )
    check(
        "received total per order <= order_qty",
        (got <= orders["order_qty"].values).all(),
    )
    status_calc = np.where(
        got == 0,
        "Open",
        np.where(got < orders["order_qty"].values, "Partially Received", "Closed"),
    )
    check(
        "order_status consistent with receipts",
        (orders["order_status"].values == status_calc).all(),
    )
    check(
        "order_type consistent (RM=Purchase, FG=Production)",
        (
            orders["order_type"].values
            == np.where(
                orders["item_location_key"].str.startswith("RM"),
                "Purchase",
                "Production",
            )
        ).all(),
    )

    # recompute week-end on-order independently
    bad = 0
    for key, g in wk.groupby("item_location_key"):
        o = orders[orders["item_location_key"] == key]
        r = rec[rec["item_location_key"] == key]
        for _, row in g.iterrows():
            we = row["week_start_date"] + pd.Timedelta(days=6)
            expected = (
                o.loc[o["order_date"] <= we, "order_qty"].sum()
                - r.loc[r["receipt_date"] <= we, "received_qty"].sum()
            )
            if expected != row["on_order_qty"]:
                bad += 1
    check(
        "on_order_qty (week end) = cumulative order_qty - cumulative received_qty (exact)",
        bad == 0,
        f"{bad} mismatches",
    )

    # ---- 9. classification consistency
    log("\n9. CLASSIFICATION & UNIT CONSISTENCY")
    check(
        "item_type in {RM, FG} and matches id prefix",
        item["item_type"].isin(["RM", "FG"]).all()
        and (item["item_id"].str[:2] == item["item_type"]).all(),
    )
    check("single unit of measure (pcs)", (item["uom"] == "pcs").all())
    check(
        "abc_class in {A,B,C}; criticality in {Critical,Standard}",
        item["abc_class"].isin(list("ABC")).all()
        and item["criticality"].isin(["Critical", "Standard"]).all(),
    )
    m = loc.merge(item, on="item_id")
    check(
        "safety_stock_days follows criticality (Critical=14, Standard=7)",
        (
            m["safety_stock_days"] == np.where(m["criticality"] == "Critical", 14, 7)
        ).all(),
    )
    check(
        "order_cycle_days follows ABC (A=14, B=21, C=28)",
        (
            m["order_cycle_days"] == m["abc_class"].map({"A": 14, "B": 21, "C": 28})
        ).all(),
    )
    check(
        "max_cover_days = round-half-up(1.5 x (safety + cycle))",
        (
            m["max_cover_days"]
            == (3 * (m["safety_stock_days"] + m["order_cycle_days"]) + 1) // 2
        ).all(),
    )
    check(
        "every warehouse stocks RM and FG items",
        all(
            set(m.loc[m["warehouse_id"] == w, "item_type"]) == {"RM", "FG"}
            for w in wh["warehouse_id"]
        ),
    )

    # ---- 10. dataset size
    log("\n10. DATASET SIZE")
    total_tx = len(wk) + len(orders) + len(rec)
    check(
        "transaction records within 1,000-5,000",
        1000 <= total_tx <= 5000,
        f"{total_tx:,}",
    )

    # ---- informational profile (NOT pass/fail)
    log("\nINFORMATIONAL DATA PROFILE (not pass/fail)")
    log(f"  Items: {len(item)}  Warehouses: {len(wh)}  Item-locations: {len(loc)}")
    log(f"  Weekly rows: {len(wk):,}  Orders: {len(orders):,}  Receipts: {len(rec):,}")
    log(f"  Order status counts: {orders['order_status'].value_counts().to_dict()}")
    so = wk[wk["shortage_qty"] > 0]
    log(
        f"  Item-weeks with shortage: {len(so)} ({len(so) / len(wk):.1%}); item-locations affected: {so['item_location_key'].nunique()}"
    )
    log(
        f"  Overall fill rate: {wk['fulfilled_qty'].sum() / max(1, wk['demand_qty'].sum()):.2%}"
    )
    last = wk[wk["week_start_date"] == wk["week_start_date"].max()]
    log(
        f"  Item-locations with zero closing stock in final week: {int((last['closing_stock'] == 0).sum())}"
    )
    d8 = (
        wk[wk["week_start_date"] >= weeks_expected[-8]]
        .groupby("item_location_key")["demand_qty"]
        .sum()
    )
    log(
        f"  Item-locations with zero demand in the last 8 weeks: {int((d8 == 0).sum())}"
    )
    cost = m.set_index("item_location_key")["unit_cost"]
    inv_val = (
        last["closing_stock"].values * last["item_location_key"].map(cost).values
    ).sum()
    log(f"  Closing inventory value, final week (INR): {inv_val:,.0f}")
    lt = rec.sort_values("receipt_date").groupby("order_id").first()
    lt["actual_lt"] = (lt["receipt_date"] - lt["order_date"]).dt.days
    lt["planned_lt"] = lt["item_location_key"].map(pl)
    log(
        f"  Avg first-receipt lead time: actual {lt['actual_lt'].mean():.1f} d vs planned {lt['planned_lt'].mean():.1f} d"
    )
    return finish()


def finish():
    n_fail = sum(1 for _, ok in results if not ok)
    log("\n" + "=" * 60)
    log(
        f"SUMMARY: {len(results) - n_fail} passed, {n_fail} failed, {len(results)} checks total"
    )
    (OUT / "validation_report.txt").write_text("\n".join(lines), encoding="utf-8")
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
