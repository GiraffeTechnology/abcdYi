# abcdYi — Giraffe Agent Apparel and Textile Application PRD

| Field | Definition |
| --- | --- |
| Version | 2.1, 2026-10-01 |
| Product | abcdYi, the first vertical application of Giraffe Agent |
| Industry | Apparel and textile order execution |
| Users | Professional buyers, brands, designers, apparel trading firms, manufacturers, and their supply chain participants |
| Product boundary | Aivan is the pre-contract front end of abcdYi. abcdYi owns the formal contract handoff and post-contract execution. |
| Scope baseline | [abcdYi PRD v2.0 product positioning](https://github.com/GiraffeTechnology/abcdYi/issues/25), refined by this complete PRD |
| Status | Product requirements and acceptance criteria; implementation status requires separate code and integration evidence |

## 1. Product definition

abcdYi is **Giraffe Agent's first vertical application**, built specifically for apparel and textile orders. It connects buyer inquiry, requirement clarification, supplier coordination, quote and lead-time comparison, human approval, formal contract handoff, production, quality control, logistics, and buyer sign-off within one traceable project.

Supported work includes garments, fabric, trims, and other inputs to apparel and textile production. The application supports small batches, multiple styles, custom orders, and regular volume orders. Every requirement and acceptance scenario in this PRD is tied to apparel or textile production.

abcdYi does not replace ERP, an authoritative business-fact database, financial settlement, or human commercial judgment. An inquiry draft, recommendation, or approved proposal is not itself a formal contract.

## 2. Product architecture and ownership

**Aivan is the front-end part of abcdYi before a formal contract is generated.** It manages buyer and supplier interaction, requirement clarification, evidence collection, and preparation of a commercial proposal. A separate Aivan repository or API service does not create a separate user-facing product boundary for this application.

| Phase | Owner | Required output |
| --- | --- | --- |
| Buyer RFQ intake and clarification | Aivan front end, using abcdYi apparel and textile fields | Versioned structured requirements, open questions, and source references |
| Supplier inquiry and response | Aivan front end | Approved outbound inquiry, comparable supplier replies, and evidence |
| Lead-time and option analysis | Aivan orchestration using GLTG and giraffe-db APIs | Quantiles, risk explanation, cost and schedule options, and source references |
| Human commercial approval | Aivan approval workflow | Approved or rejected versioned proposal, with approver and audit record |
| Formal contract generation and handoff | abcdYi contract boundary | Contract input packet, contract version and status, parties, approvals, and provenance |
| Post-contract fulfillment | abcdYi apparel and textile execution workflow | Production, QC, logistics, sign-off, and supplier-performance records |

Aivan's seven-step Stage 1 loop is **pre-contract**: RFQ input → requirement structuring → supplier inquiry draft → supplier reply parsing → GLTG invocation → execution recommendation → human approval. Completion of that loop does not create a contract, start production, or complete abcdYi's full order lifecycle.

The handoff must preserve tenant and project IDs, confirmed requirement version, selected option, price and lead-time evidence, approval identity and time, contracting parties, contract version, and source references. If the handoff fails, the system must not mark a draft or proposal as a signed contract or confirmed production order.

OpenClaw is the gateway and runtime for the agent. WeChat, LINE, email, and other supported messaging services are communication channels; OpenClaw is not a peer channel.

## 3. Apparel and textile domain model

### 3.1 Requirements and evidence

The structured requirement records product category, style or SKU, quantity, color and size ratio, fabric and trims, construction, quality standard, packaging, destination, and requested delivery window. It associates sketches, size charts, material specifications, reference images, and revisions with access controls and source references.

Unclear or conflicting details remain open questions. An LLM may suggest a clarification, but it must not convert a guess into an approved specification. Fabric availability, supplier capacity, production schedule, and shipping cutoff must distinguish verified evidence, supplier declarations, estimates, and missing information.

### 3.2 Participants and contextual roles

Participants may include the buyer or brand, primary manufacturer, fabric supplier, trim and packaging supplier, subcontractor, QC provider, and logistics provider. A manufacturer can be a supplier to the original buyer and a buyer to an upstream fabric supplier in the same project. Permissions, inquiry threads, approvals, and evidence must follow the relevant project and procurement edge.

### 3.3 Core records

The application maintains linked versions of requirements, inquiries, supplier responses, delivery scenarios, commercial proposals, approvals, contracts, orders, production milestones, QC records, shipments, buyer sign-offs, and execution events. A revision points back to the earlier version; correcting an event does not silently overwrite its history.

## 4. Functional requirements

### 4.1 Pre-contract workflow through Aivan

1. **RFQ intake.** Capture the apparel or textile inquiry, extract the fields in Section 3, and ask for missing quantity, size ratio, fabric, quality, and delivery details. Preserve the relationship between original input and normalized facts.
2. **Supplier coordination.** Prepare inquiries for the primary manufacturer and necessary upstream participants. An authorized human approves every outbound inquiry. Normalize supplier replies into a comparable structure without discarding original evidence.
3. **Lead-time and commercial analysis.** Request lead-time simulation, P50/P80/P90, path comparison, and risk explanation through the GLTG API. Read and write relevant business facts through the giraffe-db API. Aivan must not replace GLTG's canonical numeric output with local estimates or treat local draft storage as successful authoritative persistence.
4. **Execution options.** Present feasible single-delivery and split-delivery alternatives, including launch or shipping windows when relevant. Show price, schedule, evidence gaps, and risk. An unsupported supplier claim must not appear as a verified fact.
5. **Human approval.** Bind approval to the exact proposal and quotation version. Rejection permits revision and resubmission. No buyer quote or supplier commitment is sent without the required approval.
6. **Contract input.** Deliver the approved option and its evidence as a versioned handoff packet. Draft approval alone does not mean that a formal contract has been generated or signed.

### 4.2 Formal contract boundary

abcdYi creates or receives the formal contract version from the approved input packet. It records parties, specifications, quantity and size ratio, price, delivery terms, quality criteria, changes, signatures or confirmation status, and evidence of authorization. Production begins only from a contract or order state that explicitly permits it. Material changes to price, delivery, or quality terms require a new approval tied to the revised version.

### 4.3 Post-contract execution through abcdYi

1. **Order launch.** Create the order and production plan from the formal contract. Record manufacturer acceptance, fabric and trim confirmation, capacity, and subcontractor dependencies.
2. **Production progress.** Track applicable sampling, procurement, cutting, sewing, finishing, inspection, and packing milestones with planned and actual dates. Record delays and proposed remedies; a change affecting the buyer's commitment requires human confirmation.
3. **Quality control.** Link inspection criteria and sample or batch IDs to QC results, images, video, and reinspection. A failed inspection cannot advance to ready-to-ship without an authorized resolution.
4. **Logistics and acceptance.** Record handover, carrier, tracking reference, status, and source. A delivered tracking event requests buyer sign-off; it does not automatically constitute buyer acceptance or close the order.
5. **Supplier memory.** After buyer sign-off and closure, update performance from observed response, delivery, quality, and cooperation evidence. Forecasts and supplier assertions must not be recorded as completed facts.

## 5. Service contracts and data ownership

- **giraffe-db** is the authoritative business-fact and evidence service. Aivan and abcdYi use authenticated, tenant-bound APIs for the consumed records. A successful write must support readback; a failed or partial write must not be reported as durable.
- **GLTG** owns lead-time calculations, P50/P80/P90, scenarios, and risk explanation. Its numeric output is canonical. LLM assistance may explain qualitative factors but must not overwrite canonical quantiles.
- **Aivan** owns the pre-contract interaction, workflow orchestration, recommendation presentation, and human approval. Its browser does not call GLTG or giraffe-db directly.
- **abcdYi** owns apparel and textile rules, the formal contract handoff, and post-contract order execution. Records across services share tenant, project, contract or order, and evidence identifiers.
- **Human operators** own commercial approvals and formal commitments. Service responses or an AI recommendation cannot substitute for their authorization.

The services may run independently and retain their engineering tests. Product acceptance for the complete apparel and textile application follows this end-to-end ownership model.

## 6. Approval, security, and audit requirements

- A supplier inquiry, buyer quote, formal contract, or change to price, lead time, or quality commitment cannot be sent or accepted without its required human approval.
- Every approval references an immutable draft or contract version, approver identity, role, and time. Changing a material term invalidates the prior approval for the changed version.
- A participant sees only information permitted by its tenant, project, and role. Role switching cannot expose another tenant's records or a competing supplier's confidential response.
- Events preserve source, time, version, and correction lineage. Rejection, exceptions, and amendments remain visible in the audit trail.
- Real channel receipts, database readback, contract signatures, simulations, and synthetic fixtures are distinct evidence classes. Synthetic inputs must be labeled.

## 7. Acceptance criteria

### AC-1: Pre-contract seven-step loop

Run an apparel RFQ, such as 10,000 shirts across five colors and a size ratio, through intake, clarification, approved supplier inquiry, response parsing, a real GLTG API call, option comparison, and human approval. Record the exact Aivan, GLTG, and giraffe-db revisions, real HTTP requests and responses, executed tests, failures, and skipped steps. Demonstrate authoritative giraffe-db write and readback, including persistence after the relevant service restart or reload. Mock-only or single-repository tests do not satisfy this integration criterion.

### AC-2: Contract handoff

An approved proposal produces a complete, traceable formal-contract input packet. Rejected proposals and drafts with unresolved material requirements cannot become signed contracts or confirmed orders. Contract signature or confirmation status and subsequent amendments are versioned and auditable.

### AC-3: Apparel order fulfillment

Follow the same contracted apparel order through fabric and trim confirmation, production milestones, QC, logistics handover, buyer sign-off, and supplier-performance recording. Preserve the project event and evidence chain. Delays and failed QC require recorded human handling. A carrier's delivered status does not automatically close the order.

### AC-4: Separate delivery claims

Record Aivan Stage 1 acceptance and the full abcdYi post-contract lifecycle acceptance separately. A document claim, an unmerged PR, a skipped integration job, or an earlier revision's test result cannot substitute for evidence from the candidate under review.

## 8. Scope exclusions

This PRD excludes generic agent platforms, non-apparel industrial orders, mechanical machining, CAD/CNC capability matching, a full Digital Twin, payment or settlement, ERP replacement, and autonomous commercial commitments. Existing code outside this product scope is a separate code-governance matter; the presence of that code does not expand abcdYi requirements.

## 9. Document authority

This is a complete revision of the abcdYi application PRD, aligned with the [v2.0 positioning baseline](https://github.com/GiraffeTechnology/abcdYi/issues/25). It supersedes the former cross-industry content of this file as a current product requirement. Historical Git revisions remain available for traceability. Other repository documents that describe handicrafts, unrelated industries, or Aivan as a separate end-to-end product must be reconciled with this PRD before they are used as current abcdYi acceptance criteria.
