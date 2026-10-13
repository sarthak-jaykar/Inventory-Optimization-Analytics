# Insights & Strategy

> **Read this first.** All figures come from the validated **synthetic** dataset and the Power BI report (latest week: 29 Jun 2026). Several patterns, including under-set ERP reorder points and late-prone lanes, were seeded by the data generator, so these findings demonstrate the analytical method and are not real-world evidence. Targets are **proposed management targets**, not proven results. No financial savings are claimed; "excess value" means capital held above the stated maximum-cover policy.

## Summary

| # | Finding | Priority |
| --- | --- | --- |
| 1 | Two item-locations are stocked out; one needs a new order, the other needs expediting | High |
| 2 | Six Critical Risk item-locations; cover is shorter than lead time for key critical items | High |
| 3 | Service loss is concentrated in a few item-locations | High |
| 4 | ERP reorder points are out of line with the policy reorder point | Medium-High |
| 5 | ₹3.19M of stock exceeds maximum cover, concentrated in Power Adapters and Chennai | Medium-High |
| 6 | Same-item stock is imbalanced across warehouses | Medium |
| 7 | ₹4.05M of non-moving and slow-moving stock needs an owner and a decision | Medium |
| 8 | Actual lead times run later than planned | Medium |

**Operating view:** *buy now* (findings 1–2), *fix the rules* (findings 3, 4 and 8), *release capital* (findings 5–7).

---

## Finding 1: Two item-locations are stocked out

**Evidence.** Two item-locations have on-hand = 0 in the latest week: **Voltage Regulator IC (Pune)** with a 34-day lead time, and **Wiring Harness (Chennai)**. Both are Standard class.

**Business implication.** Production using these items is exposed, but the cases differ. The Voltage Regulator IC has 7,920 units on order against a reorder point of about 9,847, so its inventory position is still below the reorder point. The Wiring Harness already has 4,120 units on order and its inventory position is above the reorder point.

**Recommended action.**
- Voltage Regulator IC: place an order for the suggested **6,972 units** (about ₹98K at standard cost) and expedite the open orders.
- Wiring Harness: **expedite** the open order; the suggested new order quantity is 0.

**Priority.** High. **Proposed target.** 0 stocked-out item-locations at the weekly planning review.

---

## Finding 2: Six Critical Risk item-locations

**Evidence.** Six item-locations are Critical Risk (5 are Critical class). The total suggested order value across the 9 action items is **₹2.28M**. Examples:

| Item-location | On-hand | Days of cover | Lead time | Suggested qty |
| --- | --- | --- | --- | --- |
| 1-Phase Smart Meter, Pune | 31 | 1.1 | 10 days | 408 |
| USB-C PD 65W Adapter, Gurugram | 55 | 4.9 | 15 days | 292 |
| LCD Display Module, Gurugram | 436 | 8.8 | 29 days | 1,518 |
| 32-bit Microcontroller, Pune | 697 | 11.9 | 42 days | 1,651 |

**Business implication.** Cover is shorter than the replenishment lead time. Unless open orders arrive early, further shortages are likely. This is a risk indicator based on policy thresholds, not a confirmed stockout.

**Recommended action.** Place orders in the priority order shown on Page 2, starting with the five Critical-class items. Review open orders for these items for expediting.

**Priority.** High. **Proposed target.** On-hand cover at least equal to lead time for all Critical-class items.

*Sensitivity:* the 8-week demand window includes a seeded demand spike for some items (for example the 32-bit Microcontroller), which raises the calculated reorder point. Some flags partly reflect temporarily high demand.

---

## Finding 3: Service loss is concentrated

**Evidence.** Demand went unmet in **111 of 2,340 item-weeks (4.7%)** across **31 item-locations**. Fill rate is **96.1%** overall: Pune 95.0%, Gurugram 98.0%, Chennai 99.8%; raw materials 95.9%, finished goods 99.1%. Two item-locations, the **32-bit Microcontroller at Pune** (11 shortage weeks, about ₹734K) and the **1-Phase Smart Meter at Pune** (6 weeks, about ₹568K), account for about **45%** of unmet demand value (₹2.90M at standard cost).

**Business implication.** Service loss is concentrated rather than spread evenly, so targeted policy changes can have a large effect. Unmet value is at standard cost and is not lost revenue or margin.

**Recommended action.** Revisit the reorder point and safety stock for these two item-locations first, then work through the other top unmet-demand items (Page 2).

**Priority.** High. **Proposed target.** Fill rate of at least 98% for Critical-class items.

---

## Finding 4: ERP reorder points are out of line with the policy

**Evidence.** Of 87 demand-active item-locations, **10** have an ERP reorder point more than 25% below the policy reorder point, and **16** have one more than 50% above it. All 10 low item-locations had at least one shortage, compared with 21 of the other 77. Example: the 1-Phase Smart Meter at Pune has an ERP reorder point of 370 against a policy reorder point of about 694.

**Business implication.** Static reorder points go stale as demand and lead times change. *Note:* this pattern was seeded by the generator, so it illustrates the method; it is not independent evidence about a real ERP.

**Recommended action.** Replace static settings with `average daily demand × lead time + safety stock`, recalculated regularly. Start with the 10 item-locations set too low, then review the 16 set too high.

**Priority.** Medium-High. **Proposed target.** ERP reorder point within ±25% of the policy reorder point for Critical-class items.

---

## Finding 5: Excess stock

**Evidence.** **₹3.19M** of stock (**14.2%** of on-hand value) exceeds maximum cover, across **15 item-locations**. Power Adapters hold about **51%** (₹1.63M) and Chennai about **48%** (₹1.55M, 8 of the 15). The largest cases:

| Item-location | Days of cover | Max cover | Excess value |
| --- | --- | --- | --- |
| Prepaid Smart Meter, Chennai | 89.3 | 42 | ₹682K |
| Adapter 12V 2A, Gurugram | 206.9 | 42 | ₹562K |
| USB-C PD 65W Adapter, Chennai | 79.3 | 42 | ₹325K |
| Adapter 12V 2A, Pune | 64.0 | 42 | ₹319K |

**Business implication.** Capital is tied up above what the stated policy supports. This is policy-based and is not a savings estimate.

**Recommended action.** Freeze new orders on the top excess item-locations until days of cover falls below maximum cover. Check whether open orders on these items can be deferred.

**Priority.** Medium-High. **Proposed target.** No demand-active item-location above its maximum cover.

---

## Finding 6: Stock is imbalanced across warehouses

**Evidence.** The **USB-C PD 65W Adapter** is Critical Risk at Gurugram (4.9 days of cover) while the same item at Chennai holds 79.3 days (excess ₹325K).

**Business implication.** A transfer may relieve the shortage faster than a new order. Inter-warehouse transfers are **not modelled** in this dataset, so no benefit is quantified.

**Recommended action.** Before placing a new order, evaluate a Chennai-to-Gurugram transfer for items that appear in both the at-risk and excess lists.

**Priority.** Medium. **Proposed target.** Cross-location balance reviewed for every item flagged in both lists.

---

## Finding 7: Non-moving and slow-moving stock

**Evidence.** Three item-locations had **no demand in the last 8 weeks**, holding **₹1.81M**; the largest is PCB - LED Driver at Pune (₹782K, 18,622 units). A further group meeting the slow-moving rule (demand in 4 or fewer of the last 12 weeks) holds **₹2.24M** (for example CT-Operated Meter at Pune, ₹1.14M). The two groups do not overlap and together are about **₹4.05M (18.0% of on-hand value)**. The slow-moving group can overlap with the excess group.

**Business implication.** This stock may have no near-term use. The reason demand stopped needs confirming before any write-off or disposal decision.

**Recommended action.** Confirm with planning and engineering why demand stopped, stop reordering, and decide whether to hold, redistribute or dispose.

**Priority.** Medium. **Proposed target.** Monthly review; every non-moving item has an owner and a decision.

---

## Finding 8: Lead times run later than planned

**Evidence.** Actual first-receipt lead time averages **16.4 days** against **15.0** planned, and **46%** of orders arrived later than planned. Late shares are highest for Passive Components (about 64%) and Packaging (60%).

**Business implication.** The reorder point uses planned lead time, so consistently optimistic plans understate the reorder trigger. Late-prone lanes were seeded in the generator.

**Recommended action.** Review planned lead times by category, starting with those with the highest late share, and feed realistic values into the reorder-point calculation.

**Priority.** Medium. **Proposed target.** Late orders at or below 30% in each category.

---

## Management recommendations at a glance

| Priority | Area | Action | Proposed target |
| --- | --- | --- | --- |
| **P1** | Replenishment | Order the 9 action items in priority order; expedite where stock is already on order | 0 stocked-out item-locations |
| **P1** | Service | Fix reorder point and safety stock for the two highest unmet-demand items | Critical-class fill rate ≥ 98% |
| **P2** | Policy | Replace static ERP reorder points with the policy calculation | Within ±25% of policy |
| **P2** | Excess | Hold new orders on top excess item-locations | Nothing above max cover |
| **P3** | Non-moving | Assign owners; hold, redistribute or dispose | Monthly review |
| **P3** | Lead times | Review planned lead times by category | Late orders ≤ 30% |

---

## Limitations

- **Synthetic data.** Fictional company, seeded patterns, one 26-week window. Patterns do not represent a real organization.
- **Simplified safety stock.** A days-of-cover policy by criticality. The data has no service-level target, lead-time variance model or forecast error, so no statistical safety-stock model is claimed.
- **Policy values are proposals.** Safety-stock days, order cycle, maximum cover, the 8-week demand window and the slow-moving rule are management settings that can be changed (the demand window and slow-moving rule are defined as What-If parameters in the model; the report pages use the defaults and do not expose them as slicers).
- **Demand window sensitivity.** The 8-week average includes the seeded spike (weeks 18 to 23).
- **Not modelled.** MOQ and pack sizes, inter-warehouse transfers, backorders, order cancellations, reservations (available stock equals on-hand).
- **Costs.** Standard unit costs; unmet demand value is not lost revenue; turnover is consumption-based, not accounting COGS.
- **No implementation.** The report supports decisions; it does not place orders or change any inventory system.
