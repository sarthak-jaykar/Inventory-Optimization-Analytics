# DAX Measures Reference

All measures live in the `_Measures` table, organised by display folder. Stock columns (`opening_stock`, `closing_stock`, `on_order_qty`) are **snapshots** and are never summed across weeks; stock measures read the **report week** (the latest week in the current filter context). Flow columns (`demand_qty`, `fulfilled_qty`, `shortage_qty`, `receipts_qty`) are summed over the selected period.

**Item-level vs aggregate.** Quantity measures are written as `SUMX` over `dim_item_location`, so they work at any level. Status logic (`Item Status`) and the single-value helpers (`Planned Lead Time (days)`, `Max Cover (days)`) are meaningful only at item-location level; the count and value measures that aggregate status iterate item-locations explicitly.

**Policy-dependent measures** (safety stock, reorder point, excess, suggested order, slow-moving) use proposed management settings stored in `dim_item_location` and the What-If parameters; they are not derived from evidence.

---

## 01 Inventory

### Report Week
```dax
Report Week = MAX ( fact_inventory_weekly[week_start_date] )
```
Latest week in the current filter context. *Format:* Date `dd mmm yyyy`. *Assumption:* with no date filter, this is 29 Jun 2026.

### On-Hand Qty
```dax
On-Hand Qty =
VAR w = [Report Week]
RETURN CALCULATE ( SUM ( fact_inventory_weekly[closing_stock] ), fact_inventory_weekly[week_start_date] = w )
```
Closing stock for the report week. *Format:* whole number.

### On-Order Qty
```dax
On-Order Qty =
VAR w = [Report Week]
RETURN CALCULATE ( SUM ( fact_inventory_weekly[on_order_qty] ), fact_inventory_weekly[week_start_date] = w )
```
Quantity ordered but not yet received at the end of the report week. *Format:* whole number.

### Inventory Position
```dax
Inventory Position = [On-Hand Qty] + [On-Order Qty]
```
On-hand plus on-order. *Limitation:* no backorders in this dataset, so none are subtracted.

### On-Hand Value
```dax
On-Hand Value =
VAR w = [Report Week]
RETURN
    SUMX (
        FILTER ( fact_inventory_weekly, fact_inventory_weekly[week_start_date] = w ),
        fact_inventory_weekly[closing_stock] * RELATED ( dim_item[unit_cost] )
    )
```
On-hand stock at standard cost. *Format:* ₹, 0 decimals.

### On-Order Value
```dax
On-Order Value =
VAR w = [Report Week]
RETURN
    SUMX (
        FILTER ( fact_inventory_weekly, fact_inventory_weekly[week_start_date] = w ),
        fact_inventory_weekly[on_order_qty] * RELATED ( dim_item[unit_cost] )
    )
```
On-order stock at standard cost. *Format:* ₹, 0 decimals.

---

## 02 Demand & Cover

### Total Demand / Fulfilled Qty / Shortage Qty / Receipts Qty
```dax
Total Demand = SUM ( fact_inventory_weekly[demand_qty] )
Fulfilled Qty = SUM ( fact_inventory_weekly[fulfilled_qty] )
Shortage Qty = SUM ( fact_inventory_weekly[shortage_qty] )
Receipts Qty = SUM ( fact_inventory_weekly[receipts_qty] )
```
Flow totals over the selected period. *Format:* whole number.

### Fill Rate
```dax
Fill Rate = DIVIDE ( [Fulfilled Qty], [Total Demand] )
```
Share of demand met from stock. *Format:* % with 1 decimal.

### Shortage Item-Weeks
```dax
Shortage Item-Weeks = CALCULATE ( COUNTROWS ( fact_inventory_weekly ), fact_inventory_weekly[shortage_qty] > 0 )
```
Count of item-location weeks with unmet demand (observed). *Format:* whole number.

### Shortage Item-Locations
```dax
Shortage Item-Locations =
CALCULATE ( DISTINCTCOUNT ( fact_inventory_weekly[item_location_key] ), fact_inventory_weekly[shortage_qty] > 0 )
```
Number of distinct item-locations with at least one shortage week. *Format:* whole number.

### Unmet Demand Value
```dax
Unmet Demand Value = SUMX ( fact_inventory_weekly, fact_inventory_weekly[shortage_qty] * RELATED ( dim_item[unit_cost] ) )
```
Shortage quantity at **standard cost**. *Limitation:* not lost revenue or margin. *Format:* ₹, 0 decimals.

### Avg Daily Demand
```dax
Avg Daily Demand =
VAR w = [Report Week]
VAR n = [ADD Window Value]
VAR d =
    CALCULATE (
        SUM ( fact_inventory_weekly[demand_qty] ),
        REMOVEFILTERS ( dim_date ),
        fact_inventory_weekly[week_start_date] > w - 7 * n,
        fact_inventory_weekly[week_start_date] <= w
    )
VAR k =
    CALCULATE (
        DISTINCTCOUNT ( fact_inventory_weekly[week_start_date] ),
        REMOVEFILTERS ( dim_date ),
        fact_inventory_weekly[week_start_date] > w - 7 * n,
        fact_inventory_weekly[week_start_date] <= w
    )
RETURN DIVIDE ( d, 7 * k )
```
Demand over the trailing `ADD Window` weeks (default 8) divided by days in the weeks available. *Format:* 1 decimal. *Assumption:* the window may extend before the selected date range. *Limitation:* the 8-week window includes the seeded demand spike for some items.

### Total Avg Daily Demand
```dax
Total Avg Daily Demand = SUMX ( dim_item_location, [Avg Daily Demand] )
```
Sum of average daily demand across item-locations in context. *Format:* 1 decimal.

### Days of Inventory
```dax
Days of Inventory =
DIVIDE (
    SUMX ( FILTER ( dim_item_location, [Avg Daily Demand] > 0 ), [On-Hand Qty] ),
    SUMX ( dim_item_location, [Avg Daily Demand] )
)
```
On-hand ÷ average daily demand, calculated only over demand-active item-locations, so no-demand stock does not distort the figure. Blank where demand is zero. *Format:* 1 decimal.

---

## 03 Policy (Safety Stock, Reorder Point)

### Planned Lead Time (days)
```dax
Planned Lead Time (days) = SELECTEDVALUE ( dim_item_location[planned_lead_time_days] )
```
Item-location level only; blank when several item-locations are selected.

### Safety Stock Qty
```dax
Safety Stock Qty = SUMX ( dim_item_location, dim_item_location[safety_stock_days] * [Avg Daily Demand] )
```
Safety-stock days × average daily demand. *Limitation:* a simplified days-of-cover policy, not a statistical safety-stock model.

### Reorder Point Qty
```dax
Reorder Point Qty =
SUMX (
    dim_item_location,
    ( dim_item_location[planned_lead_time_days] + dim_item_location[safety_stock_days] ) * [Avg Daily Demand]
)
```
Average daily demand × planned lead time + safety stock. *Format:* whole number.

### ERP Reorder Point Qty / ERP Order Qty
```dax
ERP Reorder Point Qty = SUM ( dim_item_location[erp_reorder_point_qty] )
ERP Order Qty = SUM ( dim_item_location[erp_order_qty] )
```
Current static ERP settings (observed). Meaningful at item-location level.

### ERP ROP Too Low (<75% of Policy)
```dax
ERP ROP Too Low (<75% of Policy) =
COUNTROWS (
    FILTER (
        dim_item_location,
        [Avg Daily Demand] > 0 && dim_item_location[erp_reorder_point_qty] < 0.75 * [Reorder Point Qty]
    )
)
```
Demand-active item-locations whose ERP reorder point is more than 25% below the policy reorder point.

### ERP ROP Too High (>150% of Policy)
```dax
ERP ROP Too High (>150% of Policy) =
COUNTROWS (
    FILTER (
        dim_item_location,
        [Avg Daily Demand] > 0 && dim_item_location[erp_reorder_point_qty] > 1.5 * [Reorder Point Qty]
    )
)
```
Demand-active item-locations whose ERP reorder point is more than 50% above the policy reorder point.

---

## 04 Status & Risk

### Excess Qty
```dax
Excess Qty =
SUMX (
    dim_item_location,
    VAR a = [Avg Daily Demand]
    RETURN IF ( a > 0, MAX ( 0, [On-Hand Qty] - a * dim_item_location[max_cover_days] ), 0 )
)
```
On-hand above `max_cover_days` of demand, for demand-active items only. No-demand items are excluded (reported as non-moving stock).

### Active Weeks (Lookback)
```dax
Active Weeks (Lookback) =
VAR w = [Report Week]
VAR m = [Slow Lookback Value]
RETURN
    CALCULATE (
        COUNTROWS ( fact_inventory_weekly ),
        REMOVEFILTERS ( dim_date ),
        fact_inventory_weekly[week_start_date] > w - 7 * m,
        fact_inventory_weekly[week_start_date] <= w,
        fact_inventory_weekly[demand_qty] > 0
    )
```
Number of weeks with demand in the last `Slow Lookback` weeks (default 12).

### Item Status
```dax
Item Status =
VAR a = [Avg Daily Demand]
VAR oh = [On-Hand Qty]
VAR ip = [Inventory Position]
VAR lt = [Planned Lead Time (days)]
VAR ss = [Safety Stock Qty]
VAR rp = [Reorder Point Qty]
VAR doi = [Days of Inventory]
RETURN
    SWITCH (
        TRUE (),
        a = 0, "No Demand",
        oh = 0, "Stocked Out",
        ip <= rp && ( doi < lt || ip < ss ), "Critical Risk",
        ip <= rp, "Reorder Now",
        [Excess Qty] > 0, "Excess",
        [Active Weeks (Lookback)] <= [Slow Max Active Value], "Slow-Moving",
        "Healthy"
    )
```
First-match rule at item-location level. **Stocked Out** (on-hand = 0 with demand) is observed. **Critical Risk** and **Reorder Now** are *indicators*, not confirmed stockouts. *Limitation:* thresholds are proposed policy.

### Status counts
```dax
Item-Locations = COUNTROWS ( dim_item_location )
Stocked Out Items = COUNTROWS ( FILTER ( dim_item_location, [Item Status] = "Stocked Out" ) )
Critical Risk Items = COUNTROWS ( FILTER ( dim_item_location, [Item Status] = "Critical Risk" ) )
Reorder Now Items = COUNTROWS ( FILTER ( dim_item_location, [Item Status] = "Reorder Now" ) )
Excess Items = COUNTROWS ( FILTER ( dim_item_location, [Item Status] = "Excess" ) )
Slow-Moving Items (status) = COUNTROWS ( FILTER ( dim_item_location, [Item Status] = "Slow-Moving" ) )
No Demand Items = COUNTROWS ( FILTER ( dim_item_location, [Item Status] = "No Demand" ) )
Healthy Items = COUNTROWS ( FILTER ( dim_item_location, [Item Status] = "Healthy" ) )
```
Item-location counts per status. *Format:* whole number.

### Items at Risk / % Items at Risk
```dax
Items at Risk = [Stocked Out Items] + [Critical Risk Items] + [Reorder Now Items]
% Items at Risk = DIVIDE ( [Items at Risk], [Item-Locations] )
```
Item-locations needing replenishment attention, and the share of all item-locations. *Format:* whole number; % with 1 decimal.

### Critical-Class Items at Risk
```dax
Critical-Class Items at Risk =
COUNTROWS (
    FILTER (
        dim_item_location,
        [Item Status] IN { "Stocked Out", "Critical Risk", "Reorder Now" }
            && RELATED ( dim_item[criticality] ) = "Critical"
    )
)
```
At-risk item-locations whose item is classed Critical.

### Items by Status / On-Hand Value by Status
```dax
Items by Status =
VAR s = SELECTEDVALUE ( dim_status[Status] )
RETURN IF ( ISBLANK ( s ), [Item-Locations], COUNTROWS ( FILTER ( dim_item_location, [Item Status] = s ) ) )

On-Hand Value by Status =
VAR s = SELECTEDVALUE ( dim_status[Status] )
RETURN IF ( ISBLANK ( s ), [On-Hand Value], SUMX ( FILTER ( dim_item_location, [Item Status] = s ), [On-Hand Value] ) )
```
Count and value by status for charts, using the unrelated `dim_status` table.

---

## 05 Excess & Slow-Moving

### Excess Value
```dax
Excess Value =
SUMX (
    dim_item_location,
    VAR a = [Avg Daily Demand]
    RETURN
        IF ( a > 0, MAX ( 0, [On-Hand Qty] - a * dim_item_location[max_cover_days] ) * RELATED ( dim_item[unit_cost] ), 0 )
)
```
Excess quantity at standard cost: capital held above the stated maximum-cover policy. *Not a savings estimate.* *Format:* ₹, 0 decimals.

### Excess % of On-Hand Value
```dax
Excess % of On-Hand Value = DIVIDE ( [Excess Value], [On-Hand Value] )
```
*Format:* % with 1 decimal.

### Excess Item-Locations
```dax
Excess Item-Locations = COUNTROWS ( FILTER ( dim_item_location, [Excess Qty] > 0 ) )
```
Item-locations holding any quantity above maximum cover (includes items whose status is a higher-priority one such as Reorder Now).

### Non-Moving Stock Value
```dax
Non-Moving Stock Value = SUMX ( FILTER ( dim_item_location, [Avg Daily Demand] = 0 ), [On-Hand Value] )
```
On-hand value of item-locations with zero demand in the trailing window. Mutually exclusive with Excess Value.

### Slow-Moving Item-Locations (pattern) / Slow-Moving Value (pattern)
```dax
Slow-Moving Item-Locations (pattern) =
COUNTROWS ( FILTER ( dim_item_location, [Avg Daily Demand] > 0 && [Active Weeks (Lookback)] <= [Slow Max Active Value] ) )

Slow-Moving Value (pattern) =
SUMX ( FILTER ( dim_item_location, [Avg Daily Demand] > 0 && [Active Weeks (Lookback)] <= [Slow Max Active Value] ), [On-Hand Value] )
```
Demand-active item-locations meeting the slow-moving rule (default: demand in 4 or fewer of the last 12 weeks), whatever their status. The rule is a **configurable management policy**. *Note:* `Slow-Moving Items (status)` counts only those not already flagged by a higher-priority status.

### Max Cover (days)
```dax
Max Cover (days) = SELECTEDVALUE ( dim_item_location[max_cover_days] )
```
Item-location level only.

### Excess Review Flag
```dax
Excess Review Flag = IF ( [Item Status] IN { "Excess", "No Demand", "Slow-Moving" }, 1 )
```
Returns 1 for item-locations in the review list; blank otherwise. Used as a visual filter on Page 3.

### Items by DOI Bucket
```dax
Items by DOI Bucket =
VAR lo = SELECTEDVALUE ( dim_doi_bucket[Lo] )
VAR hi = SELECTEDVALUE ( dim_doi_bucket[Hi] )
RETURN
    COUNTROWS (
        FILTER (
            dim_item_location,
            VAR d = [Days of Inventory]
            RETURN NOT ISBLANK ( d ) && d >= lo && d < hi
        )
    )
```
Item-locations by days-of-inventory bucket. No-demand items (blank DOI) fall in no bucket.

---

## 06 Replenishment

### Order-Up-To Qty
```dax
Order-Up-To Qty =
SUMX (
    dim_item_location,
    VAR a = [Avg Daily Demand]
    VAR lt = dim_item_location[planned_lead_time_days]
    RETURN
        MIN (
            a * ( lt + dim_item_location[safety_stock_days] + dim_item_location[order_cycle_days] ),
            a * ( lt + dim_item_location[max_cover_days] )
        )
)
```
Target inventory position: reorder point plus one order cycle of demand, capped so on-hand at arrival cannot exceed maximum cover. With the current policy settings the cap does not bind (maximum cover is at least safety days plus cycle days); it acts as a guard rail if settings change.

### Suggested Order Qty
```dax
Suggested Order Qty =
SUMX (
    dim_item_location,
    VAR a = [Avg Daily Demand]
    VAR lt = dim_item_location[planned_lead_time_days]
    VAR ip = [Inventory Position]
    VAR rp = a * ( lt + dim_item_location[safety_stock_days] )
    VAR s =
        MIN (
            rp + a * dim_item_location[order_cycle_days],
            a * ( lt + dim_item_location[max_cover_days] )
        )
    RETURN IF ( a > 0 && ip <= rp, ROUNDUP ( MAX ( 0, s - ip ), 0 ), 0 )
)
```
`max(0, Order-Up-To − Inventory Position)` only when Inventory Position ≤ Reorder Point and demand exists. On-hand and on-order both enter through Inventory Position, so quantity already in the pipeline (including open balances on partial receipts) is not re-ordered. *Limitation:* no MOQ or pack-size rounding. *Format:* whole number.

### Suggested Order Value
```dax
Suggested Order Value =
SUMX (
    dim_item_location,
    VAR a = [Avg Daily Demand]
    VAR lt = dim_item_location[planned_lead_time_days]
    VAR ip = [Inventory Position]
    VAR rp = a * ( lt + dim_item_location[safety_stock_days] )
    VAR s =
        MIN (
            rp + a * dim_item_location[order_cycle_days],
            a * ( lt + dim_item_location[max_cover_days] )
        )
    RETURN
        IF ( a > 0 && ip <= rp, ROUNDUP ( MAX ( 0, s - ip ), 0 ) * RELATED ( dim_item[unit_cost] ), 0 )
)
```
Suggested order quantity at standard cost. *Format:* ₹, 0 decimals.

### Cover Gap vs Lead Time (days)
```dax
Cover Gap vs Lead Time (days) = [Days of Inventory] - [Planned Lead Time (days)]
```
Negative means on-hand cover is shorter than planned lead time. *Limitation:* ignores stock already on order, which is why status uses Inventory Position.

### Recommended Action
```dax
Recommended Action =
VAR st = [Item Status]
VAR q = [Suggested Order Qty]
RETURN
    SWITCH (
        TRUE (),
        st IN { "Stocked Out", "Critical Risk", "Reorder Now" } && q > 0, "Place order",
        st IN { "Stocked Out", "Critical Risk", "Reorder Now" }, "Expedite open order",
        st = "Excess", "Hold ordering / review",
        st = "No Demand", "Review for disposal or redistribution",
        st = "Slow-Moving", "Review policy",
        "Monitor"
    )
```
Text action per item-location. A stocked-out item with enough already on order returns "Expedite open order" rather than a new order.

### Priority Score / Priority Rank
```dax
Priority Score =
VAR base = SWITCH ( [Item Status], "Stocked Out", 1, "Critical Risk", 2, "Reorder Now", 3, BLANK () )
RETURN
    IF (
        ISBLANK ( base ),
        BLANK (),
        base * 10000
            + IF ( SELECTEDVALUE ( dim_item_location[Criticality] ) = "Critical", 0, 5000 )
            + MIN ( COALESCE ( [Days of Inventory], 0 ), 4999 )
    )

Priority Rank =
VAR s = [Priority Score]
RETURN
    IF (
        ISBLANK ( s ),
        BLANK (),
        RANKX ( FILTER ( ALLSELECTED ( dim_item_location ), NOT ISBLANK ( [Priority Score] ) ), [Priority Score], s, ASC, SKIP )
    )
```
Ranks at-risk item-locations: status first, then Critical-class before Standard, then lowest cover first. Blank for items not at risk; ties share a rank.

---

## 07 Orders & Lead Time

### Orders Placed
```dax
Orders Placed =
CALCULATE ( COUNTROWS ( fact_replenishment_orders ), USERELATIONSHIP ( dim_date[Date], fact_replenishment_orders[order_date] ) )
```
Orders placed in the selected period (activates the inactive date relationship).

### Open Orders / Partially Received Orders / Open Order Qty
```dax
Open Orders = CALCULATE ( COUNTROWS ( fact_replenishment_orders ), fact_replenishment_orders[order_status] = "Open" )
Partially Received Orders = CALCULATE ( COUNTROWS ( fact_replenishment_orders ), fact_replenishment_orders[order_status] = "Partially Received" )
Open Order Qty = SUM ( fact_replenishment_orders[Open Qty] )
```
Order counts by status and the unreceived quantity. With no filters, `Open Order Qty` equals the final-week `On-Order Qty`, a reconciliation check between the order table and the weekly table.

### Avg Actual Lead Time (days)
```dax
Avg Actual Lead Time (days) = AVERAGE ( fact_replenishment_orders[Actual Lead Time] )
```
Average days from order to first receipt, for orders with at least one receipt. *Format:* 1 decimal.

### Avg Planned Lead Time (received orders)
```dax
Avg Planned Lead Time (received orders) =
AVERAGEX ( FILTER ( fact_replenishment_orders, NOT ISBLANK ( fact_replenishment_orders[Actual Lead Time] ) ), fact_replenishment_orders[Planned Lead Time] )
```
Planned lead time over the same set of orders, for a like-for-like comparison.

### Avg Lead Time Variance (days)
```dax
Avg Lead Time Variance (days) = AVERAGE ( fact_replenishment_orders[Lead Time Variance] )
```
Positive means later than planned. *Format:* 1 decimal.

### % Orders Late
```dax
% Orders Late =
DIVIDE (
    COUNTROWS ( FILTER ( fact_replenishment_orders, fact_replenishment_orders[Lead Time Variance] > 0 ) ),
    COUNTROWS ( FILTER ( fact_replenishment_orders, NOT ISBLANK ( fact_replenishment_orders[Lead Time Variance] ) ) )
)
```
Share of orders with first receipt later than planned. *Format:* % with 1 decimal. Open orders are excluded.

---

## 08 Turnover

### Consumption Value
```dax
Consumption Value = SUMX ( fact_inventory_weekly, fact_inventory_weekly[fulfilled_qty] * RELATED ( dim_item[unit_cost] ) )
```
Fulfilled quantity at standard cost.

### Avg Inventory Value
```dax
Avg Inventory Value =
AVERAGEX (
    VALUES ( fact_inventory_weekly[week_start_date] ),
    CALCULATE ( SUMX ( fact_inventory_weekly, fact_inventory_weekly[closing_stock] * RELATED ( dim_item[unit_cost] ) ) )
)
```
Average of weekly closing inventory value across the selected weeks.

### Days in Period
```dax
Days in Period = DISTINCTCOUNT ( fact_inventory_weekly[week_start_date] ) * 7
```

### Inventory Turnover (annualized)
```dax
Inventory Turnover (annualized) = DIVIDE ( [Consumption Value] * 365 / [Days in Period], [Avg Inventory Value] )
```
Annualized consumption at standard cost ÷ average inventory value. *Limitation:* consumption-based at standard cost, **not accounting COGS**. *Format:* 1 decimal with "x".

---

## What-If parameter measures (auto-generated)

`ADD Window Value`, `Slow Lookback Value` and `Slow Max Active Value` return the selected value of the corresponding What-If parameter (defaults 8, 12 and 4).

---

## Verified reference values (latest week, no slicers)

| Measure | Value |
| --- | --- |
| On-Hand Value | ₹22,542,829 |
| Days of Inventory | 23.0 |
| Fill Rate | 96.1% |
| Items at Risk | 9 |
| Excess Value | ₹3,194,536 |
| Non-Moving Stock Value | ₹1,809,514 |
| Suggested Order Value | ₹2,280,695 |
| Inventory Turnover (annualized) | 11.3 |

These match the Python exploratory analysis on the same data.
