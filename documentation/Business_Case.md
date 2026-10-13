# Business Case: Inventory Optimization & Stockout Risk Analytics

> Fictional company and synthetic data. This is a portfolio project, not an implementation for a real organization.

## 1. Business scenario

**Apex Electronics Manufacturing Pvt. Ltd.** (fictional) manufactures smart energy meters, LED drivers and power adapters. It holds:

- **Raw materials and components:** semiconductors, PCBs, passive components, connectors, enclosures and displays, packaging
- **Finished goods:** smart energy meters, LED drivers, power adapters

Stock is held at three warehouses: **Pune** (main plant), **Chennai** and **Gurugram** (regional).

Planners replenish using static ERP rules (a fixed reorder point and a fixed order quantity per item-location). These rules are not reviewed regularly. As demand and lead times change, some critical items run short while others accumulate months of cover.

## 2. How this project differs from MPW

The first portfolio project, **MPW Performance Analytics**, monitors production, supplier and warehouse performance. It answers *how well the operation performed*.

This project answers *what to do about inventory*:

| MPW Performance Analytics | Inventory Optimization & Stockout Risk |
| --- | --- |
| Production plan attainment, downtime, yield | Inventory position, cover and reorder timing |
| Supplier on-time delivery scorecards | Replenishment quantity and open orders |
| Warehouse dock-to-stock performance | Excess, slow-moving and non-moving stock |
| Performance monitoring | Replenishment and review decisions |

Nothing from MPW is rebuilt here.

## 3. Business problem

Management is concerned about:

- Stockout risk for critical items
- Excess and slow-moving inventory
- Inventory availability versus demand
- Reorder timing and reorder quantities
- Safety-stock adequacy
- Inventory turnover and days of inventory
- Capital tied up in excess stock
- Differences in inventory risk across products, materials and locations

## 4. Objectives

1. Identify item-locations that are stocked out or at risk of running short.
2. Identify which items have reached their reorder point and suggest a quantity using a stated policy.
3. Test whether current ERP reorder settings are consistent with demand and lead time.
4. Quantify excess and non-moving inventory under an explicit policy.
5. Compare inventory health across warehouses, categories and criticality classes.
6. Compare actual with planned replenishment lead times.
7. Turn the findings into prioritized, actionable recommendations.

## 5. Key business questions

1. Which item-locations are stocked out or at risk, and which are critical?
2. Which items have reached their reorder point and need an order now?
3. Is safety stock adequate relative to demand and lead time?
4. How many days of cover does each item have, and is that more or less than its lead time?
5. Where is stock excessive or slow-moving, and how much capital is tied up under the stated policy?
6. How do warehouses, categories and criticality classes compare?
7. How fast does inventory turn?
8. Do actual lead times differ from planned lead times?

## 6. Scope

### In scope
- Inventory position and availability
- Demand and consumption patterns
- Stockout and shortage events
- Reorder point and safety stock (simplified policy)
- Excess, slow-moving and non-moving stock
- Days of inventory and turnover
- Warehouse and item comparisons
- Prioritized replenishment actions

### Out of scope
- Demand forecasting models
- Optimization algorithms (EOQ, multi-echelon)
- Full ERP implementation or data architecture
- Supplier scorecards and production-line KPIs (covered by MPW)
- Accounting COGS and financial savings estimates
- Real company data or real ERP system changes

## 7. Intended audience and decisions

| Audience | Decision supported |
| --- | --- |
| Inventory planner | Which orders to place today, in what order, and which to expedite |
| Supply chain head | Whether safety-stock, reorder-point and cover policies need revision |
| Procurement and finance | Which items to stop ordering, redistribute or review for disposal |

## 8. Approach

**Business problem → model design → synthetic data generation → validation → exploratory analysis → Power BI model → DAX → dashboard → insights → recommendations.**

- **Dataset:** a compact, rules-based synthetic dataset with a fixed random seed. A public dataset was considered but would not provide lead times, reconciled stock movements or a manufacturing context without heavy reshaping. Because the data is synthetic, seeded patterns (under-set reorder points, late-prone lanes, slow and dead stock) are properties of the generator, not real-world evidence.
- **Why this model is sufficient:** one weekly inventory fact, one order table and one receipt table support every approved question without extra tables.
- **Policies are simple and explainable:** safety stock as days of demand, reorder point as demand over lead time plus safety stock, maximum cover for excess.

## 9. Key assumptions

- All data is fictional and synthetic.
- Unmet demand is recorded as shortage and is **not back-ordered**; Inventory Position = On-Hand + On-Order.
- Available stock equals on-hand (no reservation or allocation data).
- Receipts are treated as available at the start of the week in which they arrive.
- Costs are standard unit costs. Policy thresholds are proposed management settings.
- Raw materials are replenished by supplier purchase orders; finished goods by production orders. Inter-warehouse transfers are not modelled.
- No financial savings are claimed. Excess value means capital held above the stated maximum-cover policy.

## 10. Definition of success

The project is complete when it has a validated dataset, a defensible data model, correct KPIs, a four-page Power BI report, evidence-based findings, clear limitations and documentation that lets a reader reproduce the analysis.
