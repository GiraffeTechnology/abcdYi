# Industrial Execution Graph — abcdYi

## What It Is

The Industrial Execution Graph is an append-only audit trail that records every significant action taken in the abcdYi system as an immutable event with a timestamp, full payload, and linkage to the relevant project, order, and participant.

It is the system of record for the order lifecycle — a complete forensic trail from buyer inquiry to buyer sign-off, covering every approval decision, every supplier response, every milestone update, and every QC outcome.

Unlike a log file, the Execution Graph is a first-class system entity. Every event is linked to the tenant, the project, the order, and the participant(s) involved, making it queryable along any of those dimensions. Every approval gate in the workflow writes to the Execution Graph. Supplier memory updates reference it. Dispute resolution and compliance review start with it.

---

## Design Principles

**Append-only** — Events are written once and never modified or deleted. The `execution_events` table has no UPDATE or DELETE operations in the application layer. This is enforced by convention and by the absence of any update path in the repository layer.

**Full payload** — Every event stores the complete context of what happened in a `payload` JSONB column, not just a reference ID. The event record is self-contained: reading it tells you what happened without requiring joins to reconstruct the state.

**Chronological** — Events are ordered by `occurred_at` (timezone-aware), enabling replay of the full order timeline in sequence.

**Linked** — Each event carries `tenant_id`, `project_id` (nullable), `order_id` (nullable), and `participant_id` (nullable) where applicable. Events at the project level may not yet have an order ID; events at the participant level may not have a project ID. Null linkages are intentional, not errors.

**Attributed** — Every event records `triggered_by_user_id` where a human action caused the event. System-generated events (delay prediction, normalization) record `triggered_by_user_id = null`.

---

## All 31 Event Types

| Event Type | Description |
|---|---|
| `PROJECT_CREATED` | A new project was created from a buyer inquiry |
| `BUYER_INQUIRY_RECEIVED` | A buyer inquiry was submitted and linked to a project |
| `DYNAMIC_FORM_CREATED` | A dynamic order form was generated for the project |
| `DYNAMIC_FORM_UPDATED` | An existing order form was updated |
| `PARTICIPANT_REGISTERED` | A new participant was registered in the tenant |
| `PARTICIPANT_CLASSIFIED` | A participant was assigned a role in the context of an order |
| `PARTICIPANT_MATCHED` | The participant matching engine produced a scored shortlist for the project |
| `RFQ_DRAFTED` | An RFQ packet was assembled and staged for human review |
| `RFQ_APPROVAL_REQUESTED` | An `ApprovalRequest` with action type `RFQ_SEND` was created |
| `RFQ_APPROVED` | The `RFQ_SEND` approval was granted by a human operator |
| `RFQ_SENT` | An RFQ was dispatched to a supplier |
| `SUPPLIER_RESPONSE_RECEIVED` | A supplier submitted a quotation in response to an RFQ |
| `SUPPLIER_RESPONSE_NORMALIZED` | A supplier response was normalized into the comparison schema |
| `DECISION_PACKET_GENERATED` | A decision packet with side-by-side supplier comparison was assembled |
| `QUOTE_APPROVAL_REQUESTED` | An `ApprovalRequest` with action type `QUOTE_APPROVE` was created |
| `QUOTE_APPROVED` | The `QUOTE_APPROVE` approval was granted; a supplier was selected |
| `ORDER_CREATED` | An order record was created from an approved quote |
| `ORDER_CONFIRMED` | The `ORDER_CONFIRM` approval was granted and the order confirmation was dispatched |
| `MILESTONE_UPDATED` | A production milestone changed status or had a date updated |
| `PRODUCTION_DELAY_PREDICTED` | The delay prediction engine produced a monitoring packet |
| `EXPEDITE_ALERT_CREATED` | An expedite alert was staged pending human approval |
| `EXPEDITE_ALERT_APPROVED` | The `EXPEDITE_NOTIFY` approval was granted and the alert was sent |
| `QC_STANDARD_CREATED` | A QC standard was configured for an order |
| `QC_RECORD_RECEIVED` | A QC inspection record was submitted by a QC inspector |
| `QC_FAILED` | A QC inspection record resulted in a failure outcome |
| `QC_PASSED` | A QC inspection record resulted in a pass outcome |
| `QUALITY_INCIDENT_CREATED` | A quality incident was recorded against a participant |
| `REPLACEMENT_ALERT_CREATED` | A participant replacement alert was triggered (3rd quality incident) |
| `LOGISTICS_HANDOVER_CREATED` | A shipment was created and the `SHIPMENT_APPROVE` gate was initiated |
| `SHIPMENT_UPDATED` | A tracking event was added to a shipment record |
| `BUYER_SIGNED_OFF` | The buyer formally signed off on the delivery; the order is closed |

---

## How to Query

All execution graph queries require authentication (`Authorization: Bearer <token>`). Events are always returned in chronological order (`occurred_at ASC`).

### Events for a Project

```http
GET /api/execution-graph/projects/{project_id}
```

Returns all events linked to the project — the full timeline from inquiry received to order closed, regardless of which order or participant the events are linked to.

### Events for an Order

```http
GET /api/execution-graph/orders/{order_id}
```

Returns all events linked to a specific order — useful for reviewing the execution history of a single confirmed order, from ORDER_CREATED through BUYER_SIGNED_OFF.

### Events for a Participant

```http
GET /api/execution-graph/participants/{participant_id}
```

Returns all events involving a specific participant across all orders — useful for supplier performance analysis, showing every RFQ sent, response received, milestone reported, and QC outcome.

### Single Event

```http
GET /api/execution-graph/events/{event_id}
```

Returns a single event with its full payload. Use this to inspect the exact content of a specific decision or action.

---

## Response Schema

```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "project_id": "uuid | null",
  "order_id": "uuid | null",
  "participant_id": "uuid | null",
  "event_type": "ORDER_CONFIRMED",
  "payload": {
    "order_id": "uuid",
    "supplier_id": "uuid",
    "confirmed_at": "2026-06-15T10:00:00Z",
    "approved_by": "uuid"
  },
  "triggered_by_user_id": "uuid | null",
  "occurred_at": "2026-06-15T10:00:00Z"
}
```

---

## Why It's Append-Only

The append-only constraint is not a technical limitation — it is the guarantee that makes the Execution Graph useful. If events could be modified or deleted:

- Approval records could be altered after the fact, removing the audit trail for disputed decisions
- Milestone history could be retroactively cleaned up to hide delays
- QC failure records could be erased to inflate a supplier's quality score

By enforcing append-only, abcdYi ensures that the Execution Graph reflects what actually happened, not a revised version of events. Every entry is permanent from the moment it is written. The `execution_events` table should never be subject to UPDATE, DELETE, or TRUNCATE operations.

---

## Use Cases

**Audit trail for dispute resolution**
When a buyer disputes whether a colorway change was approved, or a supplier claims they never received an RFQ version, the Execution Graph provides a timestamped, attributed record of every action. `RFQ_APPROVED`, `RFQ_SENT`, `SUPPLIER_RESPONSE_RECEIVED` events are all timestamped and carry the full payload of what was communicated.

**Supplier performance analysis**
Querying the Execution Graph by participant ID returns every event in that supplier's history across all orders: response times (gap between `RFQ_SENT` and `SUPPLIER_RESPONSE_RECEIVED`), QC outcomes (`QC_PASSED` vs. `QC_FAILED` counts), milestone update frequency, and quality incident history. This data feeds the supplier memory update at every order close.

**Debugging workflow failures**
When an order stalls — a milestone is not updating, an approval is not progressing — the Execution Graph provides the exact sequence of events leading up to the stall. The last recorded event and its payload show the system state at the point where progress stopped.

**Order lifecycle replay**
The chronological event sequence for a project or order can be replayed in sequence to reconstruct the full history of an order: what was requested, who was selected, what was confirmed, what delays occurred, and how QC was resolved. This is the closest thing to a complete production dossier that the system produces.
