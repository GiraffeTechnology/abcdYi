# Patent Alignment Matrix — abcdYi

abcdYi is the Apparel / Textile / Handicraft industry edition of Giraffe Agent.

**Patents covered:**
- CN ZL 2023 1 1645939.9 / CN 117670482 B — 基于多方配合的C2M模式的纺织品及服装定制运营平台系统
- JP P7644545 / 特許第7644545号 — 協働型C2Mモデルに基づく繊維及びアパレルカスタマイズ運用プラットフォームシステム

The patent titles are preserved as legal references. The abcdYi implementation is B2M, because the operational user is a buyer, designer, brand, trader, merchandiser, or SME placing production orders with manufacturers and related supply-chain participants.

---

## Patent Unit Mapping

| Patent-Aligned Logic | abcdYi Implementation | Files |
|---|---|---|
| Participant classification | Role model with 8 participant role types and capability profiling | `src/participants/`, `src/db/models/participant.py` |
| Permission assignment | Role-based visibility, approval gates enforced at route and service level | `src/approval_gates/`, `api/routes/approval_gates.py` |
| Dynamic form sending | Dynamic order form generated from buyer inquiry via LLM extraction | `src/dynamic_forms/`, `api/routes/dynamic_forms.py` |
| Participant matching | 12-dimension scoring: category, fabric capability, quantity, MOQ, capacity, lead time, location, trade terms, quality history, on-time delivery, response quality, risk penalty | `src/matching/scorer.py`, `src/matching/service.py` |
| Production monitoring | 12-milestone tracking (SAMPLE_CONFIRMATION through BUYER_SIGN_OFF) with planned, actual, and predicted dates | `src/milestones/`, `src/production_monitoring/` |
| Acceleration reminder | Delay predictor (ON_TRACK/LOW/MEDIUM/HIGH/CRITICAL) with expedite alert requiring human approval before sending | `src/production_monitoring/delay_predictor.py`, `src/production_monitoring/service.py` |
| Quality inspection | QC standard evaluation: defect limits, label compliance, packaging compliance, size deviation, color tolerance | `src/apparel_inspection/service.py`, `src/qc/` |
| Participant supervision | Quality incident tracking with replacement alert at 3 incidents threshold | `src/quality_ledger/service.py`, `src/replacement_alerts/service.py` |
| Execution record | Append-only Industrial Execution Graph with 31 event types, immutable timestamps, full payloads | `src/execution_graph/` |

---

## Expanded Module Coverage

| # | Patent Unit | abcdYi Module | Description |
|---|---|---|---|
| 1 | Multi-party B2M order execution workflow | Order state machine | 12-state order lifecycle from DRAFT_FROM_APPROVED_QUOTE to BUYER_SIGNED_OFF |
| 2 | Buyer inquiry intake and structured form generation | Dynamic order form | LLM-assisted extraction of product requirements into structured form fields |
| 3 | Participant role classification and capability profiling | Participant registry | 8 role types, capability profiles, country, MOQ, lead time, trade terms |
| 4 | Multi-dimensional supplier matching | 12-dimension scorer | Weighted scoring with supplier memory integration and risk flag computation |
| 5 | RFQ drafting and gated sending | RFQ workflow | 9-state RFQ state machine; RFQ_SEND approval required before dispatch |
| 6 | Supplier response normalization and comparison | Decision packets | LLM-normalized responses; up to 3 comparison options (best/fastest/cheapest) |
| 7 | Lead time calculation | Lead time calculator | Parallel (max) + sequential (sum) with missing-value safety; no sentinel values |
| 8 | Production monitoring | Milestone monitoring | 12 milestones per order; predicted date auto-triggers DELAYED status |
| 9 | Quality inspection and evidence | QC evaluation | QC standard per order; QC_PASSED → READY_TO_SHIP; QC_FAILED → incident |
| 10 | Supplier memory and performance supervision | Supplier memory | On-time delivery, QC pass rate, response time; updated at buyer sign-off |

---

## Human Approval Gate Coverage

All external actions require a prior PENDING `ApprovalRequest` that must reach APPROVED status. This implements the patent's human-in-the-loop requirement at every critical decision boundary.

| Action | Approval Type | Enforced In |
|---|---|---|
| Send RFQ to supplier | RFQ_SEND | `src/rfq/service.py` |
| Approve supplier quote | QUOTE_APPROVE | `src/decision_packets/service.py` |
| Confirm order | ORDER_CONFIRM | `src/order_confirmation/service.py` |
| Send expedite alert | EXPEDITE_NOTIFY | `src/production_monitoring/service.py` |
| Replace participant | PARTICIPANT_REPLACE | `src/replacement_alerts/service.py` |
| Buyer sign-off | BUYER_SIGNOFF | `src/order_confirmation/service.py` |
| QC escalation | QC_ESCALATE | `src/qc/service.py` |
| Shipment approval | SHIPMENT_APPROVE | `src/logistics/service.py` |

---

## Industrial Execution Graph

The append-only `ExecutionEvent` audit trail records all execution events — implementing the "execution record" patent unit with immutable timestamps and full JSON payloads.

- **Writer:** `src/execution_graph/writer.py`
- **Reader:** `src/execution_graph/service.py`
- **API:** `api/routes/execution_graph.py`
- **Event types:** 31 types covering the full workflow lifecycle (`src/execution_graph/event_types.py`)

Events are never deleted or updated. The execution graph is a complete forensic record of the order lifecycle.
