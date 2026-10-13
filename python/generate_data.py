"""
generate_data.py
Inventory Optimization & Stockout Risk Analytics - Apex Electronics Manufacturing Pvt. Ltd. (FICTIONAL)

Generates a small, internally consistent, SYNTHETIC dataset (fixed seed) as CSV files in data/raw/.
Run from the project root:   python python/generate_data.py

Simulation logic (one source of truth for stock movement):
  * Weekly grain, 26 weeks (Mon 2026-01-05 .. Sun 2026-07-05).
  * Receipts are generated at the replenishment-order level (fact_order_receipts); weekly receipts_qty is the
    SUM of those receipts for the week -> exact reconciliation, no double counting.
  * on_order_qty (week end) = SUM(order_qty of orders placed on/before week end)
                              - SUM(received_qty of receipts dated on/before week end).
  * Receipts are assumed available at the start of the week they arrive in (simplifying assumption).
  * Unmet demand is recorded as shortage (lost / not back-ordered).
  * The simulated planner follows a STALE static (s, Q) ERP rule. These settings differ deliberately from the
    analytical policy (safety stock days, cycle days, max cover) so the dashboard has exceptions to find.
"""

from datetime import date, timedelta
from pathlib import Path
import math

import numpy as np
import pandas as pd

# ----------------------------------------------------------------------------- configuration
SEED = 20260105
START_DATE = date(2026, 1, 5)  # Monday
N_WEEKS = 26
END_DATE = START_DATE + timedelta(days=N_WEEKS * 7 - 1)  # Sunday 2026-07-05
OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

# Analytical policy (proposed management settings, stored per item-location)
SS_DAYS = {"Critical": 14, "Standard": 7}  # safety stock, days of average demand
CYCLE_DAYS = {
    "A": 14,
    "B": 21,
    "C": 28,
}  # order cycle, days of demand covered by one replenishment


def max_cover(ss, cycle):  # integer arithmetic: round-half-up of 1.5*(ss+cycle)
    return (3 * (ss + cycle) + 1) // 2


# Item master: id, name, type, category, unit_cost (INR), ABC, criticality, base weekly demand (Pune), LT low, LT high (days)
ITEMS = [
    (
        "RM001",
        "32-bit Microcontroller",
        "RM",
        "Semiconductors",
        185.0,
        "A",
        "Critical",
        450,
        28,
        42,
    ),
    (
        "RM002",
        "Metering IC",
        "RM",
        "Semiconductors",
        210.0,
        "A",
        "Critical",
        420,
        28,
        42,
    ),
    (
        "RM003",
        "Power MOSFET",
        "RM",
        "Semiconductors",
        28.0,
        "B",
        "Critical",
        1600,
        21,
        35,
    ),
    (
        "RM004",
        "Voltage Regulator IC",
        "RM",
        "Semiconductors",
        14.0,
        "B",
        "Standard",
        1800,
        21,
        35,
    ),
    (
        "RM005",
        "GSM/Wi-Fi Communication Module",
        "RM",
        "Semiconductors",
        420.0,
        "A",
        "Critical",
        300,
        28,
        42,
    ),
    (
        "RM006",
        "Main PCB - Smart Meter",
        "RM",
        "PCBs",
        95.0,
        "A",
        "Critical",
        450,
        21,
        28,
    ),
    ("RM007", "PCB - LED Driver", "RM", "PCBs", 42.0, "B", "Standard", 800, 21, 28),
    ("RM008", "PCB - Power Adapter", "RM", "PCBs", 38.0, "B", "Standard", 900, 21, 28),
    (
        "RM009",
        "Electrolytic Capacitor 470uF",
        "RM",
        "Passive Components",
        6.5,
        "C",
        "Standard",
        6000,
        14,
        21,
    ),
    (
        "RM010",
        "MLCC Capacitor 100nF",
        "RM",
        "Passive Components",
        0.8,
        "C",
        "Standard",
        40000,
        14,
        21,
    ),
    (
        "RM011",
        "SMD Resistor 10k",
        "RM",
        "Passive Components",
        0.3,
        "C",
        "Standard",
        50000,
        14,
        21,
    ),
    (
        "RM012",
        "Power Inductor",
        "RM",
        "Passive Components",
        12.0,
        "B",
        "Standard",
        2500,
        14,
        21,
    ),
    (
        "RM013",
        "EE-core Transformer",
        "RM",
        "Passive Components",
        55.0,
        "B",
        "Critical",
        1000,
        21,
        28,
    ),
    (
        "RM014",
        "Terminal Block",
        "RM",
        "Connectors & Cables",
        9.0,
        "C",
        "Standard",
        3000,
        10,
        18,
    ),
    (
        "RM015",
        "DC Power Jack",
        "RM",
        "Connectors & Cables",
        4.5,
        "C",
        "Standard",
        3500,
        10,
        18,
    ),
    (
        "RM016",
        "Wiring Harness",
        "RM",
        "Connectors & Cables",
        22.0,
        "B",
        "Standard",
        1200,
        10,
        18,
    ),
    (
        "RM017",
        "USB-C Connector",
        "RM",
        "Connectors & Cables",
        7.0,
        "C",
        "Standard",
        2500,
        10,
        18,
    ),
    (
        "RM018",
        "Meter Housing",
        "RM",
        "Enclosures & Displays",
        48.0,
        "B",
        "Standard",
        450,
        14,
        21,
    ),
    (
        "RM019",
        "LED Driver Casing",
        "RM",
        "Enclosures & Displays",
        25.0,
        "B",
        "Standard",
        800,
        14,
        21,
    ),
    (
        "RM020",
        "Adapter Shell",
        "RM",
        "Enclosures & Displays",
        15.0,
        "C",
        "Standard",
        900,
        14,
        21,
    ),
    (
        "RM021",
        "LCD Display Module",
        "RM",
        "Enclosures & Displays",
        130.0,
        "A",
        "Critical",
        450,
        21,
        35,
    ),
    ("RM022", "Carton Box", "RM", "Packaging", 11.0, "C", "Standard", 2500, 7, 10),
    ("RM023", "Anti-static Bag", "RM", "Packaging", 1.2, "C", "Standard", 6000, 7, 10),
    (
        "RM024",
        "Label & Manual Kit",
        "RM",
        "Packaging",
        2.5,
        "C",
        "Standard",
        4500,
        7,
        10,
    ),
    (
        "FG001",
        "1-Phase Smart Meter",
        "FG",
        "Smart Energy Meters",
        1450.0,
        "A",
        "Critical",
        220,
        5,
        12,
    ),
    (
        "FG002",
        "3-Phase Smart Meter",
        "FG",
        "Smart Energy Meters",
        3200.0,
        "A",
        "Critical",
        110,
        5,
        12,
    ),
    (
        "FG003",
        "Prepaid Smart Meter",
        "FG",
        "Smart Energy Meters",
        1650.0,
        "A",
        "Critical",
        140,
        5,
        12,
    ),
    (
        "FG004",
        "CT-Operated Meter",
        "FG",
        "Smart Energy Meters",
        3800.0,
        "B",
        "Standard",
        45,
        5,
        12,
    ),
    (
        "FG005",
        "Meter Data Gateway",
        "FG",
        "Smart Energy Meters",
        2900.0,
        "B",
        "Standard",
        35,
        5,
        12,
    ),
    (
        "FG006",
        "LED Driver 18W",
        "FG",
        "LED Drivers",
        320.0,
        "B",
        "Standard",
        400,
        5,
        12,
    ),
    (
        "FG007",
        "LED Driver 36W",
        "FG",
        "LED Drivers",
        480.0,
        "A",
        "Standard",
        380,
        5,
        12,
    ),
    (
        "FG008",
        "LED Driver 60W",
        "FG",
        "LED Drivers",
        690.0,
        "B",
        "Standard",
        200,
        5,
        12,
    ),
    (
        "FG009",
        "Dimmable LED Driver 40W",
        "FG",
        "LED Drivers",
        760.0,
        "B",
        "Standard",
        120,
        5,
        12,
    ),
    (
        "FG010",
        "Street Light Driver 120W",
        "FG",
        "LED Drivers",
        1250.0,
        "A",
        "Critical",
        90,
        5,
        12,
    ),
    (
        "FG011",
        "Adapter 12V 2A",
        "FG",
        "Power Adapters",
        210.0,
        "B",
        "Standard",
        600,
        5,
        12,
    ),
    (
        "FG012",
        "Laptop Adapter 19V",
        "FG",
        "Power Adapters",
        540.0,
        "A",
        "Standard",
        320,
        5,
        12,
    ),
    (
        "FG013",
        "Adapter 24V 5A",
        "FG",
        "Power Adapters",
        620.0,
        "B",
        "Standard",
        150,
        5,
        12,
    ),
    (
        "FG014",
        "USB-C PD 65W Adapter",
        "FG",
        "Power Adapters",
        780.0,
        "A",
        "Critical",
        260,
        5,
        12,
    ),
    (
        "FG015",
        "Industrial Adapter 48V",
        "FG",
        "Power Adapters",
        1150.0,
        "B",
        "Standard",
        60,
        5,
        12,
    ),
    (
        "FG016",
        "Adapter 5V 1A",
        "FG",
        "Power Adapters",
        95.0,
        "C",
        "Standard",
        900,
        5,
        12,
    ),
]

WAREHOUSES = [
    ("PUN", "Pune Main Plant Warehouse", "Pune", "West", "Main plant"),
    ("CHE", "Chennai Regional Warehouse", "Chennai", "South", "Regional"),
    ("GUR", "Gurugram Regional Warehouse", "Gurugram", "North", "Regional"),
]
# number of RM / FG items stocked at each warehouse (Pune stocks everything)
HOLDINGS = {"PUN": (24, 16), "CHE": (12, 14), "GUR": (10, 14)}

DELAY_VALUES_NORMAL = np.array([-1, 0, 1, 2, 3, 5, 8, 12])
DELAY_P_NORMAL = np.array([0.05, 0.50, 0.15, 0.12, 0.08, 0.05, 0.03, 0.02])
DELAY_VALUES_LATE = np.array([0, 2, 4, 6, 8, 10, 14])
DELAY_P_LATE = np.array([0.10, 0.10, 0.20, 0.20, 0.20, 0.10, 0.10])


# ----------------------------------------------------------------------------- build dimensions
def build_dimensions(rng):
    dim_item = pd.DataFrame(
        [(i[0], i[1], i[2], i[3], "pcs", i[4], i[5], i[6]) for i in ITEMS],
        columns=[
            "item_id",
            "item_name",
            "item_type",
            "category",
            "uom",
            "unit_cost",
            "abc_class",
            "criticality",
        ],
    )
    dim_wh = pd.DataFrame(
        WAREHOUSES,
        columns=["warehouse_id", "warehouse_name", "city", "region", "warehouse_role"],
    )

    item_by_id = {i[0]: i for i in ITEMS}
    rm_ids = [i[0] for i in ITEMS if i[2] == "RM"]
    fg_ids = [i[0] for i in ITEMS if i[2] == "FG"]

    locs = []
    for wh_id, (n_rm, n_fg) in HOLDINGS.items():
        rm_sel = sorted(rng.choice(rm_ids, n_rm, replace=False).tolist())
        fg_sel = sorted(rng.choice(fg_ids, n_fg, replace=False).tolist())
        for item_id in rm_sel + fg_sel:
            it = item_by_id[item_id]
            regional = wh_id != "PUN"
            demand_mult = 1.0 if not regional else float(rng.uniform(0.30, 0.60))
            lt = int(rng.integers(it[8], it[9] + 1)) + (
                int(rng.integers(2, 5)) if (regional and it[2] == "FG") else 0
            )
            ss = SS_DAYS[it[6]]
            cycle = CYCLE_DAYS[it[5]]
            locs.append(
                dict(
                    item_id=item_id,
                    warehouse_id=wh_id,
                    item_type=it[2],
                    abc=it[5],
                    crit=it[6],
                    base_weekly=it[7] * demand_mult,
                    planned_lt=lt,
                    ss_days=ss,
                    cycle_days=cycle,
                    max_cover_days=max_cover(ss, cycle),
                    unit_cost=it[4],
                )
            )
    return dim_item, dim_wh, locs


def assign_profiles(rng, locs):
    """Seed deliberate patterns: dead stock, slow movers, demand spikes, under-/over-set ERP rules, late-prone lanes."""
    n = len(locs)
    eligible = [
        k for k in range(n) if locs[k]["abc"] != "A" and locs[k]["crit"] == "Standard"
    ]
    perm = [int(x) for x in rng.permutation(eligible)]
    dead, slow = perm[:3], perm[3:9]
    taken = set(dead) | set(slow)
    others = [k for k in range(n) if k not in taken]
    crit_others = [k for k in others if locs[k]["crit"] == "Critical"]
    std_others = [k for k in others if locs[k]["crit"] == "Standard"]

    spike = [int(x) for x in rng.choice(crit_others, 5, replace=False)]
    under = [int(x) for x in rng.choice(crit_others, 6, replace=False)] + [
        int(x) for x in rng.choice(std_others, 8, replace=False)
    ]
    under = list(dict.fromkeys(under))
    remaining = [k for k in others if k not in set(under)]
    over = [int(x) for x in rng.choice(remaining, 14, replace=False)]
    late_prone = [
        int(x)
        for x in rng.choice(
            [k for k in range(n) if locs[k]["item_type"] == "RM"], 8, replace=False
        )
    ]

    dead_start = {
        dead[0]: 0,
        dead[1]: 9,
        dead[2]: 12,
    }  # week index from which demand is zero
    for k, loc in enumerate(locs):
        loc["profile"] = "normal"
        if k in under:
            loc["profile"] = "under"
        if k in over:
            loc["profile"] = "over"
        if k in dead:
            loc["profile"] = "dead"
        if k in slow:
            loc["profile"] = "slow"
        loc["spike"] = k in spike
        loc["late_prone"] = k in late_prone
        loc["dead_start"] = dead_start.get(k)


def set_erp_parameters(rng, locs):
    """Stale static ERP rule per item-location: reorder point (s) and fixed order quantity (Q)."""
    for loc in locs:
        base_daily = loc["base_weekly"] / 7.0
        rop_ideal = base_daily * (loc["planned_lt"] + loc["ss_days"])
        p = loc["profile"]
        if p == "under":
            f_rop, f_q = rng.uniform(0.45, 0.75), rng.uniform(0.7, 1.0)
        elif p in ("over", "dead", "slow"):
            f_rop, f_q = rng.uniform(1.4, 2.0), rng.uniform(2.2, 3.5)
        else:
            f_rop, f_q = rng.uniform(0.9, 1.2), rng.uniform(0.8, 1.3)
        rop = max(1, int(round(rop_ideal * f_rop)))
        q = base_daily * loc["cycle_days"] * f_q
        q = int(round(q / 10.0) * 10) if q >= 50 else int(round(q))
        q = max(1, q)
        loc["erp_rop"], loc["erp_q"] = rop, q
        # opening stock
        if p == "under":
            stock = (rop + q / 2.0) * rng.uniform(0.6, 1.2)
        elif p == "over":
            stock = (rop + q) * rng.uniform(1.2, 1.8)
        elif p in ("dead", "slow"):
            stock = (rop + q) * rng.uniform(1.5, 2.5)
        else:
            stock = (rop + q / 2.0) * rng.uniform(0.9, 1.5)
        loc["opening_stock"] = max(1, int(round(stock)))


# ----------------------------------------------------------------------------- simulation
def gen_demand(rng, loc):
    weeks = np.arange(N_WEEKS)
    season = 1 + 0.10 * np.sin(2 * np.pi * (weeks - 4) / 26)
    sigma = 0.22
    noise = rng.lognormal(mean=-(sigma**2) / 2, sigma=sigma, size=N_WEEKS)
    mean = loc["base_weekly"] * season * noise
    if loc["spike"]:
        mean = np.where((weeks >= 17) & (weeks <= 22), mean * 1.7, mean)
    if loc["profile"] == "slow":
        occurs = rng.random(N_WEEKS) < 0.20
        mean = np.where(occurs, mean / 0.20, 0.0)
    demand = np.rint(mean).astype(int)
    if loc["dead_start"] is not None:
        demand[loc["dead_start"] :] = 0
    return np.maximum(demand, 0)


def draw_receipts(rng, loc, order_date, qty):
    """Return list of (receipt_date, qty) for one order, including delay and optional partial delivery."""
    if loc["late_prone"]:
        delay = int(rng.choice(DELAY_VALUES_LATE, p=DELAY_P_LATE))
    else:
        delay = int(rng.choice(DELAY_VALUES_NORMAL, p=DELAY_P_NORMAL))
    lt = max(1, loc["planned_lt"] + delay)
    first_date = order_date + timedelta(days=lt)
    p_partial = 0.15 if loc["item_type"] == "RM" else 0.07
    if qty >= 2 and rng.random() < p_partial:
        q1 = min(qty - 1, max(1, int(math.floor(qty * rng.uniform(0.4, 0.8)))))
        second_date = first_date + timedelta(days=int(rng.integers(4, 15)))
        return [(first_date, q1), (second_date, qty - q1)]
    return [(first_date, qty)]


def simulate(rng, locs):
    weekly_rows, orders, receipts = [], [], []
    for loc in locs:
        key = f"{loc['item_id']}|{loc['warehouse_id']}"
        loc["key"] = key
        demand = gen_demand(rng, loc)
        stock = loc["opening_stock"]
        on_order = 0
        events = []  # (receipt_date, qty) still to be applied
        order_seq = 0

        def maybe_order(closing, on_ord, review_date):
            """Stale ERP rule: if inventory position <= s, order enough multiples of Q to exceed s."""
            nonlocal order_seq
            ip = closing + on_ord
            if ip <= loc["erp_rop"]:
                n_batches = int(math.ceil((loc["erp_rop"] - ip + 1) / loc["erp_q"]))
                qty = n_batches * loc["erp_q"]
                tmp = (key, order_seq)
                order_seq += 1
                orders.append(
                    dict(
                        tmp=tmp,
                        item_location_key=key,
                        order_type=(
                            "Purchase" if loc["item_type"] == "RM" else "Production"
                        ),
                        order_date=review_date,
                        expected_date=review_date + timedelta(days=loc["planned_lt"]),
                        order_qty=qty,
                    )
                )
                for rdate, rqty in draw_receipts(rng, loc, review_date, qty):
                    if (
                        rdate <= END_DATE
                    ):  # receipts after the data end are not yet observed
                        events.append((rdate, rqty))
                        receipts.append(
                            dict(tmp=tmp, receipt_date=rdate, received_qty=rqty)
                        )
                return qty
            return 0

        # planning run on the day before the window starts (creates a few pre-window open orders)
        on_order += maybe_order(stock, on_order, START_DATE - timedelta(days=1))

        for w in range(N_WEEKS):
            ws = START_DATE + timedelta(days=7 * w)
            we = ws + timedelta(days=6)
            rec_w = sum(q for d, q in events if ws <= d <= we)
            opening = stock
            avail = opening + rec_w
            fulfilled = min(int(demand[w]), avail)
            shortage = int(demand[w]) - fulfilled
            closing = avail - fulfilled
            on_order -= rec_w
            on_order += maybe_order(
                closing, on_order, we
            )  # weekly planning run on the week-end date
            weekly_rows.append(
                dict(
                    item_location_key=key,
                    week_start_date=ws,
                    opening_stock=opening,
                    receipts_qty=rec_w,
                    demand_qty=int(demand[w]),
                    fulfilled_qty=fulfilled,
                    shortage_qty=shortage,
                    closing_stock=closing,
                    on_order_qty=on_order,
                )
            )
            stock = closing
    return weekly_rows, orders, receipts


# ----------------------------------------------------------------------------- main
def main():
    rng = np.random.default_rng(SEED)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    dim_item, dim_wh, locs = build_dimensions(rng)
    assign_profiles(rng, locs)
    set_erp_parameters(rng, locs)
    weekly_rows, orders, receipts = simulate(rng, locs)

    dim_item_location = pd.DataFrame(
        [
            dict(
                item_location_key=l["key"],
                item_id=l["item_id"],
                warehouse_id=l["warehouse_id"],
                planned_lead_time_days=l["planned_lt"],
                safety_stock_days=l["ss_days"],
                order_cycle_days=l["cycle_days"],
                max_cover_days=l["max_cover_days"],
                erp_reorder_point_qty=l["erp_rop"],
                erp_order_qty=l["erp_q"],
            )
            for l in locs
        ]
    )

    fact_weekly = pd.DataFrame(weekly_rows)

    ord_df = (
        pd.DataFrame(orders)
        .sort_values(["order_date", "item_location_key"])
        .reset_index(drop=True)
    )
    ord_df["order_id"] = [f"RO-{i + 1:05d}" for i in range(len(ord_df))]
    tmp_to_id = dict(zip(ord_df["tmp"], ord_df["order_id"]))

    rec_df = pd.DataFrame(receipts)
    rec_df["order_id"] = rec_df["tmp"].map(tmp_to_id)
    rec_df = rec_df.sort_values(["receipt_date", "order_id"]).reset_index(drop=True)
    rec_df["receipt_id"] = [f"RC-{i + 1:05d}" for i in range(len(rec_df))]

    received = rec_df.groupby("order_id")["received_qty"].sum()
    ord_df["received_total"] = ord_df["order_id"].map(received).fillna(0).astype(int)
    ord_df["order_status"] = np.where(
        ord_df["received_total"] == 0,
        "Open",
        np.where(
            ord_df["received_total"] < ord_df["order_qty"],
            "Partially Received",
            "Closed",
        ),
    )

    fact_orders = ord_df[
        [
            "order_id",
            "item_location_key",
            "order_type",
            "order_date",
            "expected_date",
            "order_qty",
            "order_status",
        ]
    ]
    fact_receipts = rec_df[["receipt_id", "order_id", "receipt_date", "received_qty"]]

    tables = {
        "dim_item": dim_item,
        "dim_warehouse": dim_wh,
        "dim_item_location": dim_item_location,
        "fact_inventory_weekly": fact_weekly,
        "fact_replenishment_orders": fact_orders,
        "fact_order_receipts": fact_receipts,
    }
    for name, df in tables.items():
        df.to_csv(OUT_DIR / f"{name}.csv", index=False, date_format="%Y-%m-%d")
        print(f"{name}.csv: {len(df):,} rows")
    total_tx = len(fact_weekly) + len(fact_orders) + len(fact_receipts)
    print(f"\nTransaction records (weekly + orders + receipts): {total_tx:,}")
    print(f"Output folder: {OUT_DIR}")


if __name__ == "__main__":
    main()
