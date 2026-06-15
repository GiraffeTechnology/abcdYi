# Small-Batch Quick-Response Production

## Why Small Orders Are Harder to Coordinate

Large-volume orders (50,000+ pcs) have long lead times, fixed supplier relationships, and dedicated account managers. Small-batch orders (100–5,000 pcs) face:

- **Tighter lead time windows** — buyers expect the same or faster delivery despite smaller quantities
- **Less priority at factories** — small orders often get fit in around larger runs
- **More styles, more complexity** — multi-style orders have different material requirements per SKU
- **More fragmented supply chains** — small factories often source fabric and trims from separate specialists
- **Higher coordination overhead** — the same number of coordination steps for a fraction of the volume

abcdYi is built specifically for this environment.

---

## Lead Time Calculation

abcdYi uses parallel + sequential lead time calculation:

```
Parallel stages (run simultaneously, take the max):
  fabric_lead_time_days
  trim_lead_time_days
  packaging_lead_time_days

Sequential stages (run one after another, sum them):
  production_time_days
  qc_time_days
  logistics_time_days

Total = max(fabric, trim, packaging) + production + qc + logistics
```

Missing values are handled safely — no sentinel values (0, -1, 999). If any value is missing, `has_missing_values=True` is flagged and `calculated_total_lead_time_days=None`.

---

## 12-Milestone Production Tracking

Each order gets 12 milestones created at order confirmation, with planned dates derived from the lead time breakdown:

1. SAMPLE_CONFIRMATION
2. FABRIC_BOOKING
3. TRIM_BOOKING
4. PACKAGING_BOOKING
5. CUTTING
6. SEWING
7. WASHING / FINISHING
8. IRONING
9. FINAL_QC
10. PACKING
11. SHIPMENT_HANDOVER
12. BUYER_SIGN_OFF

Each milestone tracks `planned_date`, `actual_date`, `predicted_date`, and `status` (PENDING / IN_PROGRESS / COMPLETED / DELAYED).

Setting a `predicted_date` later than `planned_date` automatically transitions the milestone to DELAYED.

---

## Delay Prediction

The delay predictor assesses overall order risk by comparing predicted milestone completion dates against the delivery deadline:

| Risk Level | Delay Days | Action |
|---|---|---|
| ON_TRACK | ≤ 0 | No action |
| LOW | 1–3 days | Monitor |
| MEDIUM | 4–7 days | Review |
| HIGH | 8–14 days | Expedite alert (requires approval) |
| CRITICAL | > 14 days | Expedite alert (requires approval) |

At HIGH or CRITICAL, an ExpediteAlert is created and an ApprovalRequest (`EXPEDITE_NOTIFY`) is generated. The alert is not sent until a human approves.

---

## Multi-Style, Small-Quantity Handling

For multi-style orders, each style can have:
- Different fabric/trim requirements captured in the dynamic order form
- Separate QC standard configurations per form version
- Independent milestone tracking if needed

The participant matching engine scores suppliers per production section, allowing a single order to use different fabric mills, trim suppliers, and manufacturers where appropriate.
