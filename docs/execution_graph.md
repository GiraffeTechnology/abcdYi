# Industrial Execution Graph — abcdYi

## What It Is

The Industrial Execution Graph is an append-only audit trail that records every significant action taken in the abcdYi system as an immutable event with a timestamp, full payload, and linkage to the relevant project, order, and participant.

It is the system of record for the order lifecycle — a complete forensic trail from buyer inquiry to buyer sign-off.

---

## Design Principles

- **Append-only:** Events are never deleted or updated. The table is write-once.
- **Full payload:** Every event stores the complete context of what happened, not just an ID.
- **Chronological:** Events are ordered by `occurred_at`, enabling full timeline replay.
- **Linked:** Each event links to `tenant_id`, `project_id`, `order_id`, and `participant_id` where applicable.

---

## All 31 Event Types

| Event Type | Description |
|---|---|
| PROJECT_CREATED | A new project was created |
| BUYER_INQUIRY_RECEIVED | A buyer inquiry was submitted |
| DYNAMIC_FORM_CREATED | A dynamic order form was generated |
| DYNAMIC_FORM_UPDATED | A form was updated |
| PARTICIPANT_REGISTERED | A new participant was registered |
| PARTICIPANT_CLASSIFIED | A participant was assigned a role |
| PARTICIPANT_MATCHED | Participant matching was run for a project |
| RFQ_DRAFTED | An RFQ was drafted |
| RFQ_APPROVAL_REQUESTED | An approval request for RFQ send was created |
| RFQ_APPROVED | The RFQ send was approved |
| RFQ_SENT | The RFQ was sent to recipients |
| SUPPLIER_RESPONSE_RECEIVED | A supplier submitted a response |
| SUPPLIER_RESPONSE_NORMALIZED | The response was normalized |
| DECISION_PACKET_GENERATED | A decision packet was generated |
| QUOTE_APPROVAL_REQUESTED | An approval request for quote selection was created |
| QUOTE_APPROVED | The quote was approved |
| ORDER_CREATED | An order was created from an approved quote |
| ORDER_CONFIRMED | The order was confirmed |
| MILESTONE_UPDATED | A production milestone was updated |
| PRODUCTION_DELAY_PREDICTED | Delay prediction was run |
| EXPEDITE_ALERT_CREATED | An expedite alert was created |
| EXPEDITE_ALERT_APPROVED | An expedite alert was approved and sent |
| QC_STANDARD_CREATED | A QC standard was created for an order |
| QC_RECORD_RECEIVED | A QC inspection record was submitted |
| QC_FAILED | A QC record resulted in failure |
| QC_PASSED | A QC record resulted in pass |
| QUALITY_INCIDENT_CREATED | A quality incident was recorded |
| REPLACEMENT_ALERT_CREATED | A participant replacement alert was triggered |
| LOGISTICS_HANDOVER_CREATED | A shipment was created |
| SHIPMENT_UPDATED | A tracking event was added to a shipment |
| BUYER_SIGNED_OFF | The buyer completed sign-off |

---

## Query API

### Events for a Project

```http
GET /api/execution-graph/projects/{project_id}
```

Returns all events linked to the project in chronological order.

### Events for an Order

```http
GET /api/execution-graph/orders/{order_id}
```

Returns all events linked to the order in chronological order.

### Events for a Participant

```http
GET /api/execution-graph/participants/{participant_id}
```

Returns all events linked to the participant in chronological order.

### Single Event

```http
GET /api/execution-graph/events/{event_id}
```

Returns a single event with its full payload.

---

## Response Schema

```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "project_id": "uuid | null",
  "order_id": "uuid | null",
  "participant_id": "uuid | null",
  "event_type": "ORDER_CREATED",
  "payload": {},
  "triggered_by_user_id": "uuid | null",
  "occurred_at": "2026-06-15T10:00:00Z"
}
```

---

## Use Cases

- **Audit trail:** Reconstruct the full history of any order for dispute resolution, compliance review, or customer queries
- **Supplier performance analysis:** Query all events linked to a participant to see their RFQ response times, QC outcomes, and delivery history
- **Debugging:** Trace exactly what happened and in what order during a workflow failure
- **Replaying order lifecycle:** Use the chronological event sequence to understand how an order evolved from inquiry to sign-off

---

## Database Table

The `execution_events` table should never be truncated, partially deleted, or modified. It is the audit backbone of abcdYi.

```sql
SELECT event_type, occurred_at, payload
FROM execution_events
WHERE project_id = '<uuid>'
ORDER BY occurred_at ASC;
```
