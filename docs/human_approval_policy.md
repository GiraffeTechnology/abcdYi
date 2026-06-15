# Human Approval Policy — abcdYi

## Why Every External Action Requires Human Approval

abcdYi implements an approval gate at every critical decision boundary. No external action is executed automatically without a human reviewing and approving first.

This is not just a UX choice — it is a core workflow design principle, aligned with the patent's multi-party coordination model: the system proposes, prepares, and records; humans decide and authorize.

---

## Approval Gate Pattern

Every action that crosses a boundary (sends something to a supplier, confirms a commercial decision, or triggers a financial or operational consequence) follows the same pattern:

1. System creates an `ApprovalRequest` with `status=PENDING`
2. Human reviews the request (see the proposed payload, risk flags, and context)
3. Human approves or rejects
4. Only after APPROVED status does the action execute
5. The approval decision is recorded in the Industrial Execution Graph

---

## All Approval Gate Action Types

| Action Type | Trigger | What It Gates |
|---|---|---|
| `RFQ_SEND` | `POST /api/projects/{id}/rfqs` | Sending an RFQ to suppliers |
| `QUOTE_APPROVE` | `POST /api/projects/{id}/decision-packets` | Selecting a supplier quote |
| `ORDER_CONFIRM` | Implicitly via order creation workflow | Order confirmation |
| `EXPEDITE_NOTIFY` | HIGH/CRITICAL delay prediction | Sending an expedite alert to supplier |
| `PARTICIPANT_REPLACE` | 3rd quality incident | Recommending supplier replacement |
| `BUYER_SIGNOFF` | `POST /api/orders/{id}/buyer-sign-off` | Final buyer acceptance |
| `QC_ESCALATE` | QC failure escalation path | Escalating a QC failure |
| `SHIPMENT_APPROVE` | Shipment creation gate | Approving a shipment |

---

## How to Approve or Reject

### List Pending Approvals

```http
GET /api/approval-requests?status=PENDING
```

### View an Approval Request

```http
GET /api/approval-requests/{id}
```

The response includes `proposed_payload`, `risk_flags`, `action_type`, `resource_type`, and `resource_id`.

### Approve

```http
POST /api/approval-requests/{id}/approve
{"review_notes": "Reviewed and approved"}
```

### Reject

```http
POST /api/approval-requests/{id}/reject
{"review_notes": "Price too high, requesting revised quote"}
```

---

## What Happens When Rejected

Rejection does not automatically cancel the workflow. It:
1. Sets `ApprovalRequest.status = REJECTED`
2. Records the rejection and review notes in the audit log
3. Records a `APPROVAL_REJECTED` event in the execution graph
4. Returns control to the human to decide next steps (revise, resubmit, or cancel)

---

## Connection to the Industrial Execution Graph

Every approval and rejection is immutably recorded:

- Approval: emits the corresponding event (e.g., `RFQ_APPROVED`, `QUOTE_APPROVED`)
- Rejection: emits an audit record with `review_notes`

The execution graph provides a complete history of all decisions made in the order lifecycle, including who approved, when, and with what notes.

---

## Design Note

The approval gate pattern means abcdYi never sends a message to a supplier, confirms an order, or triggers an alert without a human saying "yes." This is intentional — in multi-party apparel supply chains, premature or unauthorized communication is a common source of confusion, cost, and relationship damage.
