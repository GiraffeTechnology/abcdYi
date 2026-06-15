# Human Approval Policy — abcdYi

## Why Every External Action Requires Human Approval

abcdYi implements a human approval gate at every critical decision boundary in the order execution workflow. No message is sent to a supplier, no order is confirmed, no shipment is released, and no buyer sign-off is recorded without a human explicitly reviewing and authorizing the action first.

This is not a UX choice or a precautionary add-on. It is a foundational design principle grounded in the realities of multi-party apparel and textile supply chains:

**External actions have real commercial consequences.** Sending an RFQ commits the buyer's requirements to paper and invites supplier proposals. Confirming an order creates a commercial obligation. Releasing a shipment authorizes a logistics provider to take possession of goods. In small-batch production, these actions happen quickly, with lean teams, and often involve supplier relationships where trust is still being established. An agent acting autonomously on any of these actions — even with the right data — would be taking commercial risks on behalf of humans who have not consented to delegate that authority.

**Apparel supply chains require contextual judgment.** The system can score suppliers, normalize quotations, and calculate delay risk. But a human operator brings context that no system captures fully: a long-standing relationship with a factory that historically under-quotes and over-delivers, a buyer's undocumented preference to avoid a specific shipper, or a QC failure that looks borderline in numbers but is actually a clear reject when viewed in photos. Human approval gates are the mechanism for that judgment to enter the workflow.

**Every approval is a record.** Approvals are not just permission slips — they are timestamped, attributed records of who decided what and why. In dispute resolution, compliance review, or post-mortem analysis, the approval record is evidence. An autonomous system that acts without approval has no equivalent record.

The pattern is: the system prepares, recommends, and stages. Humans decide and authorize.

---

## The Approval Gate Pattern

Every action that crosses a party boundary or commits a commercial obligation follows the same four-step pattern:

1. The system creates an `ApprovalRequest` record with `status = PENDING`, containing the proposed action payload, any risk flags identified, and contextual evidence to support the decision.
2. A human operator reviews the request — seeing the proposed payload, the risk flags, and the resource context (which project, order, or participant is affected).
3. The human approves or rejects, optionally adding review notes.
4. Only after `status = APPROVED` does the system execute the action. The approval decision, reviewer identity, timestamp, and notes are recorded in the Industrial Execution Graph.

Rejection does not cancel the workflow automatically. It returns control to the human operator to decide the next step: revise and resubmit, take a different action, or cancel the workflow.

---

## All Approval Gate Action Types

| Action Type | Triggered When | What Execution It Gates |
|---|---|---|
| `RFQ_SEND` | RFQ packets are prepared and staged for dispatch | Sending RFQ documents to shortlisted suppliers |
| `QUOTE_APPROVE` | Supplier responses are normalized and a decision packet is assembled | Selecting a supplier quote and advancing to order confirmation |
| `ORDER_CONFIRM` | A supplier is selected and an order confirmation is prepared | Dispatching the formal order confirmation to the supplier |
| `EXPEDITE_NOTIFY` | Delay prediction reaches HIGH or CRITICAL risk level | Sending an expedite alert to the responsible supplier or participant |
| `PARTICIPANT_REPLACE` | A participant accumulates 3 quality incidents | Recommending and executing a mid-order supplier replacement |
| `BUYER_SIGNOFF` | A delivery summary is presented to the buyer | Recording formal buyer acceptance and closing the order |
| `QC_ESCALATE` | QC non-conformances exceed the defined tolerance threshold | Escalating a QC failure beyond the standard rework loop |
| `SHIPMENT_APPROVE` | QC is cleared and a shipment is ready for logistics handover | Releasing goods to the logistics provider for shipment |

---

## How to Approve or Reject via API

All approval gate interactions use the `/api/approval-requests` endpoint. Authentication is required for all calls.

### List Pending Approval Requests

```http
GET /api/approval-requests?status=PENDING
Authorization: Bearer <token>
```

Returns all approval requests with `status = PENDING` for the authenticated tenant, ordered by `created_at` descending. Use `status=ALL` to retrieve requests in all states.

### View a Specific Approval Request

```http
GET /api/approval-requests/{approval_id}
Authorization: Bearer <token>
```

The response includes:
- `action_type` — which gate this is (e.g., `RFQ_SEND`)
- `resource_type` and `resource_id` — the object being acted upon
- `proposed_payload` — the full content of the action that will execute on approval
- `risk_flags` — any risks the system identified during preparation
- `evidence` — supporting context for the decision
- `status` — PENDING, APPROVED, REJECTED, or EXPIRED
- `created_at` — when the request was created

### Approve

```http
POST /api/approval-requests/{approval_id}/approve
Authorization: Bearer <token>
Content-Type: application/json

{"review_notes": "Reviewed supplier shortlist and RFQ content — approved for dispatch"}
```

Returns the updated `ApprovalRequest` with `status = APPROVED`, `reviewed_by`, and `reviewed_at` populated.

### Reject

```http
POST /api/approval-requests/{approval_id}/reject
Authorization: Bearer <token>
Content-Type: application/json

{"review_notes": "Unit price from Supplier A is above target. Removing Supplier A and re-sending to remaining two."}
```

Returns the updated `ApprovalRequest` with `status = REJECTED`.

---

## What Happens When Rejected

Rejection sets `status = REJECTED` on the `ApprovalRequest` and records a rejection event in the Industrial Execution Graph with the review notes. The system does not automatically determine what happens next — that is a human decision.

Depending on the action type, typical follow-on actions after rejection are:

- **`RFQ_SEND` rejected:** Operator revises the supplier shortlist or RFQ content and initiates a new RFQ preparation. A new `ApprovalRequest` is created for the revised RFQ.
- **`QUOTE_APPROVE` rejected:** Operator may request a second round of quotations from additional suppliers, or negotiate directly. A new decision packet is prepared when additional responses arrive.
- **`ORDER_CONFIRM` rejected:** Operator revises the order terms or selects a different supplier. A new confirmation is staged.
- **`EXPEDITE_NOTIFY` rejected:** Operator decides to monitor for another cycle before intervening, or handles the supplier communication outside the system.
- **`PARTICIPANT_REPLACE` rejected:** Operator chooses to continue with the existing participant despite the quality incident history.
- **`QC_ESCALATE` rejected:** Operator accepts the non-conformance or arranges an alternative resolution directly.
- **`SHIPMENT_APPROVE` rejected:** Operator holds the shipment pending rework or re-inspection.
- **`BUYER_SIGNOFF` rejected:** Buyer does not accept delivery; the order remains open for resolution.

---

## Connection to the Industrial Execution Graph

Every approval and rejection is recorded as an immutable event in the Industrial Execution Graph. The record includes:

- The action type
- The reviewer's user ID (`reviewed_by`)
- The timestamp (`reviewed_at`)
- The review notes
- The full proposed payload at the time of the decision

This means that every decision made in the order lifecycle — who approved what, when, and with what rationale — is permanently traceable. There is no such thing as an undocumented approval in abcdYi. The Execution Graph is the audit backbone that makes this guarantee possible.
