# Workflow Overview — abcdYi

## Overview

abcdYi executes a structured, agent-assisted order coordination workflow across 22 stages. Every external action — sending an RFQ, confirming an order, approving a quote — requires explicit human approval before it executes. This policy is non-negotiable: the system prepares and recommends, humans decide and authorize.

The workflow is deterministic in sequence but adaptive in content. The agent adjusts order forms, supplier queries, and milestone intervals based on the specifics of each order. The full event history of every stage is recorded in the Industrial Execution Graph.

---

## Workflow Stages

### 1. Buyer Inquiry

The buyer submits an initial inquiry describing what they want to produce: product type, quantity, target delivery, quality level, and any other known requirements. Inquiries may arrive via API, form submission, or structured message. At this stage the input is treated as raw and unvalidated.

---

### 2. Requirement Extraction

The agent analyzes the inquiry and extracts structured data: product category, material specifications, order quantities per style/colorway/size, target ex-factory date, packaging requirements, and compliance or certification needs. Extraction uses a combination of pattern matching and LLM-assisted parsing. The output is a structured requirement record.

---

### 3. Dynamic Order Form

Based on the extracted requirements, a dynamic order form is generated. The form surfaces only the fields relevant to this order type — a cut-and-sew garment order asks different questions than a woven accessory or a knitted fabric order. Field visibility and validation rules are driven by the product category and initial requirement data.

---

### 4. Missing Info Detection

The agent scans the populated order form for gaps, contradictions, and ambiguities. Common gaps include: undeclared colorway split, missing size run, unspecified fabric weight or composition, absent lead-time constraint, or conflicting quantity vs. MOQ requirements. Detected gaps are returned to the buyer as a structured clarification request before the order advances.

---

### 5. Participant Classification

The agent identifies which participant roles are needed for this order: which combination of manufacturer, fabric supplier, trim supplier, packaging supplier, logistics provider, QC inspector, and agent roles are required. Classification is based on the product type, the buyer's stated requirements, and the complexity of the supply chain implied by the order.

---

### 6. Permission Assignment

Each participant is assigned a permission profile that controls what data they can see and what actions they can take within this order. A fabric supplier sees fabric-relevant specs and their own RFQ; they do not see the buyer's target price or other suppliers' quotes. Permission assignment follows the principle of least disclosure: participants receive exactly the information they need to do their part.

---

### 7. Supplier Matching

The agent scores and ranks candidate suppliers for each required participant role. Matching factors include: product category alignment, capacity availability, geographic proximity to other supply chain nodes, historical performance (from supplier memory), lead time compatibility, MOQ fit with the order quantity, and any buyer-specified preferences or exclusions. A ranked shortlist is prepared for each role.

---

### 8. RFQ Preparation

The agent assembles a request-for-quotation packet for each shortlisted supplier. Each RFQ contains the relevant portion of the order spec, quantity and delivery requirements, QC and compliance expectations, and the response format the supplier should follow. RFQ packets are staged for review — they are not sent until a human approves them.

---

### 9. Human Approval — RFQ Send

**Approval gate: `RFQ_SEND`**

A human operator reviews the prepared RFQ packets and the supplier shortlist. They may approve the RFQ as prepared, modify the supplier selection, edit RFQ content, or reject the dispatch entirely. Only after explicit approval does the system proceed to dispatch.

---

### 10. RFQ Dispatch

Approved RFQs are dispatched to selected suppliers via the configured communication channel (API notification, email integration, or in-system message). Each dispatch event is recorded in the Execution Graph with timestamp, recipient, and RFQ version.

---

### 11. Supplier Response Intake

Suppliers submit their quotations in response to the RFQ. Responses are accepted in structured format (via API) or parsed from semi-structured supplier submissions. Each response is timestamped and linked to the originating RFQ in the Execution Graph.

---

### 12. Response Normalization

Supplier responses are normalized into a common comparison schema: unit price, lead time, MOQ, payment terms, sample lead time, and any deviations from the RFQ spec. Normalization surfaces supplier-specific caveats and flags responses that do not meet the buyer's minimum requirements.

---

### 13. Decision Packet

The agent assembles a decision packet presenting the normalized supplier responses side by side. The packet includes a recommended selection with rationale, risk flags (e.g., a low price from a supplier with a weak performance history), and any trade-offs the human approver should consider.

---

### 14. Human Approval — Quote Approve

**Approval gate: `QUOTE_APPROVE`**

A human operator reviews the decision packet and selects which supplier(s) to proceed with. They may approve the agent's recommendation, override it with a different selection, or reject all responses and trigger a second RFQ round. The approval decision is recorded in the Execution Graph.

---

### 15. Order Confirmation

The agent prepares a formal order confirmation to the selected supplier(s), referencing the approved quote, delivery terms, and QC requirements. The confirmation is staged pending human approval.

**Approval gate: `ORDER_CONFIRM`**

After human approval, the order confirmation is dispatched to the supplier. The order status advances to "confirmed."

---

### 16. Production Time Setting

The agent calculates and sets the production timeline: material procurement lead time, cut-and-sew or production lead time, finishing and QC window, and shipment preparation time. For orders with multiple styles or suppliers, the timeline accounts for both sequential dependencies and parallel workstreams. Milestone dates are established and shared with relevant participants.

---

### 17. Milestone Monitoring

The agent monitors progress against the established milestones. Participants report status updates at each checkpoint (fabric in-house, cutting complete, sewing complete, finishing complete, QC inspection scheduled). The agent tracks actual vs. planned dates and flags deviations as they emerge.

---

### 18. Delay Prediction

Using current milestone status, historical supplier performance from supplier memory, and any reported issues, the agent calculates a delay risk score and projected completion date. When the projected completion date threatens the ex-factory date, an expedite notification is prepared for human approval.

**Approval gate: `EXPEDITE_NOTIFY`** (when delay risk crosses threshold)

---

### 19. QC Evidence Review

The QC inspector (or factory internal QC) submits inspection evidence: measurement reports, defect logs, fabric test results, and photo documentation. The agent reviews the evidence against the order's QC requirements and flags any non-conformances. If non-conformances require escalation beyond the defined tolerance, a QC escalation action is staged for human approval.

**Approval gate: `QC_ESCALATE`** (when non-conformances exceed tolerance)

---

### 20. Delivery Handover

Once QC is cleared, the agent coordinates delivery handover: shipment booking confirmation, packing list verification, and handover of shipping documentation to the logistics provider. Shipment approval is required before goods are released.

**Approval gate: `SHIPMENT_APPROVE`**

---

### 21. Buyer Sign-Off

The buyer receives a delivery summary: shipment details, QC evidence summary, and any deviations from the original order. The buyer formally signs off on the delivery, closing the order.

**Approval gate: `BUYER_SIGNOFF`**

After sign-off, the order status advances to "closed."

---

### 22. Supplier Memory Update

The agent updates each participating supplier's performance record in supplier memory: on-time delivery rate, QC pass rate, response time, and any buyer-noted issues. These records feed future supplier matching and scoring. Memory updates are append-only and tied to the Execution Graph record for this order.

---

### 23. Execution Graph Record

All events, approvals, dispatches, responses, and status changes across every stage are recorded in the Industrial Execution Graph. The graph entry for this order is finalized and becomes the permanent, append-only audit trail of the full order execution lifecycle.

---

## Human Approval Gates — Summary

| Gate | Action Type | Triggered When |
|------|-------------|----------------|
| RFQ Send | `RFQ_SEND` | RFQ packets are ready for dispatch |
| Quote Approve | `QUOTE_APPROVE` | Supplier responses have been normalized |
| Order Confirm | `ORDER_CONFIRM` | Supplier selected, confirmation ready |
| Expedite Notify | `EXPEDITE_NOTIFY` | Delay risk crosses threshold |
| Participant Replace | `PARTICIPANT_REPLACE` | A participant needs to be swapped mid-order |
| QC Escalate | `QC_ESCALATE` | Non-conformances exceed tolerance |
| Shipment Approve | `SHIPMENT_APPROVE` | QC cleared, shipment ready |
| Buyer Sign-Off | `BUYER_SIGNOFF` | Delivery summary presented to buyer |

Human approval is required at every critical boundary. The system will not proceed past any of these gates autonomously.
