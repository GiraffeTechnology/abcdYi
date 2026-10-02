# abcdYi — Giraffe Agent Apparel and Textile Application PRD

| Field | Definition |
| --- | --- |
| Version | 2.2, 2026-10-02 |
| Product | abcdYi, the first vertical application of Giraffe Agent |
| Industry | Apparel and textile order execution |
| Users | Professional buyers, brands, designers, apparel trading firms, manufacturers, and their supply chain participants |
| Product boundary | abcdYi is a Giraffe Agent industry application whose front end calls Aivan. Aivan is the Giraffe Agent front-end application for inquiry, quotation, and order confirmation. myAivan is Aivan's web version; OpenClaw-aivan is its IM and email access dependency. |
| Product authority | The original AIVAN and abcdYi product descriptions and the product owner's current clarifications; [Issue #25](https://github.com/GiraffeTechnology/abcdYi/issues/25) is a historical positioning reference |
| Status | Product requirements and acceptance criteria; implementation status requires separate code and integration evidence |

## 1. Product definition

abcdYi is **Giraffe Agent's first vertical application**, built specifically for apparel and textile orders. It connects buyer inquiry, requirement clarification, supplier coordination, quote and lead-time comparison, human approval, order confirmation, production, quality control, logistics, and buyer sign-off within one traceable project.

Supported work includes garments, fabric, trims, and other inputs to apparel and textile production. The application supports small batches, multiple styles, custom orders, and regular volume orders. Every requirement and acceptance scenario in this PRD is tied to apparel or textile production.

abcdYi does not replace ERP, the user's private database, financial settlement, or human commercial judgment. An inquiry draft, recommendation, or approved proposal is not itself a formal contract.

## 2. Product architecture and ownership

**Aivan is the Giraffe Agent front-end application for inquiry, quotation, and order confirmation.** abcdYi is a Giraffe Agent industry application, and its front end calls Aivan. **myAivan is the web version of Aivan. OpenClaw-aivan is Aivan's access dependency for IM and email.** These relationships describe product responsibilities, not additional prerequisites for order confirmation or production.

| Phase | Owner | Required output |
| --- | --- | --- |
| Buyer RFQ intake and clarification | Aivan front end, using abcdYi apparel and textile fields | Versioned structured requirements, open questions, and source references |
| Supplier inquiry and response | Aivan front end | Approved outbound inquiry, comparable supplier replies, and evidence |
| Lead-time and option analysis | Aivan calling the GLTG and GPM dependency modules through APIs and using the configured private-data provider | Lead-time and quotation analysis, options, and source references |
| Human commercial approval | Aivan approval workflow | Approved or rejected versioned proposal, with approver and audit record |
| Order confirmation | Aivan front end, called by abcdYi | Confirmed order linked to the approved quotation, parties, requirements, and approval evidence |
| Order fulfillment | abcdYi apparel and textile execution workflow | Production, QC, logistics, sign-off, and supplier-performance records |

Aivan's seven-step Stage 1 loop covers RFQ input → requirement structuring → supplier inquiry draft → supplier reply parsing → GLTG invocation → execution recommendation → human approval. It is a delivery slice within Aivan's inquiry-to-order-confirmation responsibility. Completion of that slice alone does not demonstrate order confirmation or abcdYi's full order lifecycle.

The order handoff preserves tenant and project IDs, confirmed requirement version, selected option, price and lead-time evidence, approval identity and time, order parties, and source references. Quote approval and order confirmation remain distinct steps. A formal contract, contract identifier, signature, or contract-confirmation state is not a prerequisite for production.

OpenClaw is the gateway and runtime for the agent. WeChat, LINE, email, and other supported messaging services are communication channels; OpenClaw is not a peer channel.

## 3. Apparel and textile domain model

### 3.1 Requirements and evidence

The structured requirement records product category, style or SKU, quantity, color and size ratio, fabric and trims, construction, quality standard, packaging, destination, and requested delivery window. It associates sketches, size charts, material specifications, reference images, and revisions with access controls and source references.

Unclear or conflicting details remain open questions. An LLM may suggest a clarification, but it must not convert a guess into an approved specification. Fabric availability, supplier capacity, production schedule, and shipping cutoff must distinguish verified evidence, supplier declarations, estimates, and missing information.

### 3.2 Participants and contextual roles

Participants may include the buyer or brand, primary manufacturer, fabric supplier, trim and packaging supplier, subcontractor, QC provider, and logistics provider. A manufacturer can be a supplier to the original buyer and a buyer to an upstream fabric supplier in the same project. Permissions, inquiry threads, approvals, and evidence must follow the relevant project and procurement edge.

### 3.3 Core records

The configured private database is extensible and dynamic. It records business history and in-progress business-process data, including linked requirements, inquiries, supplier responses, delivery scenarios, commercial proposals, approvals, orders, production milestones, QC records, shipments, buyer sign-offs, and execution events. Giraffe Agent, Aivan, and abcdYi use database records as the source of business truth rather than conversation context. Workflow state is persisted and recovered from those records. A revision points back to the earlier version; correcting an event does not silently overwrite its history.

## 4. Functional requirements

### 4.1 Inquiry and quotation through Aivan

1. **RFQ intake.** Capture the apparel or textile inquiry, extract the fields in Section 3, and ask for missing quantity, size ratio, fabric, quality, and delivery details. Preserve the relationship between original input and normalized facts.
2. **Supplier coordination.** Prepare inquiries for the primary manufacturer and necessary upstream participants. An authorized human approves every outbound inquiry. Normalize supplier replies into a comparable structure without discarding original evidence.
3. **Lead-time and commercial analysis.** Aivan calls its GLTG and GPM dependency modules through APIs for lead-time and quotation analysis. Preserve the returned numerical results and source references. Read and write private business data through the configured provider interface: giraffe-db can be hot-swapped for the user's own private database. Do not report local drafts, failed writes, or unverified persistence as successful durable storage.
4. **Execution options.** Present feasible single-delivery and split-delivery alternatives, including launch or shipping windows when relevant. Show price, schedule, evidence gaps, and risk. An unsupported supplier claim must not appear as a verified fact.
5. **Human approval.** Bind approval to the exact proposal and quotation version. Rejection permits revision and resubmission. No buyer quote or supplier commitment is sent without the required approval.
6. **Order preparation.** Carry the approved quotation, selected option, and their evidence into order confirmation. Quote approval alone does not mean that the order has been confirmed.

### 4.2 Order confirmation through Aivan

The approved quotation proceeds to order confirmation through Aivan. The order records the selected parties, specifications, quantity and size ratio, price, delivery terms, quality criteria, and confirmation evidence. The workflow is approved quotation → order confirmation → production. It does not require formal-contract generation, signing, or confirmation as an extra step. Material changes to price, delivery, or quality terms require a new approval tied to the revised version.

### 4.3 Order execution through abcdYi

1. **Order launch.** Create the order from the approved quotation and prepare the production plan after order confirmation. Record manufacturer acceptance, fabric and trim confirmation, capacity, and subcontractor dependencies.
2. **Production progress.** Track applicable sampling, procurement, cutting, sewing, finishing, inspection, and packing milestones with planned and actual dates. Record delays and proposed remedies; a change affecting the buyer's commitment requires human confirmation.
3. **Quality control.** Link inspection criteria and sample or batch IDs to QC results, images, video, and reinspection. A failed inspection cannot advance to ready-to-ship without an authorized resolution.
4. **Logistics and acceptance.** Record handover, carrier, tracking reference, status, and source. A delivered tracking event requests buyer sign-off; it does not automatically constitute buyer acceptance or close the order.
5. **Supplier memory.** After buyer sign-off and closure, update performance from observed response, delivery, quality, and cooperation evidence. Forecasts and supplier assertions must not be recorded as completed facts.

## 5. Service contracts and data ownership

- **Private-data source of truth.** Giraffe Agent, Aivan, and abcdYi share the same data-dependency design: an extensible, dynamic private database stores business history and business-process records. They read and persist workflow facts there rather than depending on conversation context. **giraffe-db** is a replaceable implementation that can be hot-swapped for the user's own private database through the provider interface. Preserve authentication, tenant isolation, access controls, and truthful read/write status across providers. Product completion does not require exclusive use of giraffe-db. Its two simulated databases, generated from real-data sources, are valid product-test and acceptance data sources; replacing them with live customer production data is not an acceptance prerequisite.
- **GLTG and GPM** are Aivan dependency modules, called through APIs. GLTG supplies lead-time analysis; GPM supplies quotation guidance. Preserve their returned results and evidence rather than substituting invented values. This relationship does not turn them into separate end-user products or impose whole-platform production acceptance on an Aivan front-end delivery.
- **Aivan** is the Giraffe Agent front-end application for inquiry, quotation, and order confirmation, including interaction, workflow orchestration, recommendation presentation, and human approval. abcdYi's front end calls Aivan. myAivan is Aivan's web version, and OpenClaw-aivan is its IM and email access dependency. Keep dependency and private-data access within their authorized API and provider interfaces.
- **abcdYi** is the Giraffe Agent industry application for apparel and textile rules and order execution. Records across services share tenant, project, order, and evidence identifiers; a contract identifier is not required to begin production.
- **Human operators** own commercial approvals and formal commitments. Service responses or an AI recommendation cannot substitute for their authorization.

The modules and applications may retain their own engineering tests. Acceptance identifies the application workflow and dependency interfaces actually exercised; one delivery slice does not imply completion of every module or the whole platform.

## 6. Approval, security, and audit requirements

- A supplier inquiry, buyer quote, formal contract, or change to price, lead time, or quality commitment cannot be sent or accepted without its required human approval.
- Every approval references an immutable draft or contract version, approver identity, role, and time. Changing a material term invalidates the prior approval for the changed version.
- A participant sees only information permitted by its tenant, project, and role. Role switching cannot expose another tenant's records or a competing supplier's confidential response.
- Events preserve source, time, version, and correction lineage. Rejection, exceptions, and amendments remain visible in the audit trail.
- Real channel receipts, database readback, contract signatures, simulations, and synthetic fixtures are distinct evidence classes. Synthetic inputs must be labeled.

## 7. Acceptance criteria

### AC-1: Inquiry and quotation delivery slice

Run an apparel RFQ, such as 10,000 shirts across five colors and a size ratio, through intake, clarification, approved supplier inquiry, response parsing, dependency analysis, option comparison, and human approval. Identify the Aivan revision, the GLTG/GPM APIs actually exercised, and the configured private-data provider. Record executed tests, failures, and skipped steps; distinguish real API and read/write evidence from mocks and local drafts. Aivan acceptance must not depend on using giraffe-db exclusively or on declaring the entire dependency platform production-ready. The two designated giraffe-db simulated databases are valid acceptance sources through the same provider interface. Their simulated-data status is not grounds to reject acceptance, and live customer production data is not required. Demonstrate that business-process writes can be read back and that the workflow resumes from the configured database after restart or reload without relying on prior conversation context. Apply the same data-dependency requirement to Giraffe Agent, Aivan, and abcdYi. A designated simulated database behind actual executed APIs is valid integration evidence. The application code, API calls, and state transitions under test must actually execute; skipped jobs or fabricated outputs are not passing evidence.

### AC-2: Order confirmation

Demonstrate abcdYi calling Aivan for inquiry, quotation, and order confirmation. An approved quotation produces a traceable order for buyer confirmation. Rejected proposals and drafts with unresolved material requirements cannot become confirmed orders. Confirmed orders can proceed to production without a formal contract, contract identifier, signature, or separate contract-confirmation step. Preserve the approval and confirmation evidence and subsequent amendments.

### AC-3: Apparel order fulfillment

Follow the same confirmed apparel order through fabric and trim confirmation, production milestones, QC, logistics handover, buyer sign-off, and supplier-performance recording. Preserve the project event and evidence chain. Delays and failed QC require recorded human handling. A carrier's delivered status does not automatically close the order.

### AC-4: Separate delivery claims

Record Aivan Stage 1 acceptance and the full abcdYi order lifecycle acceptance separately. A document claim, an unmerged PR, a skipped integration job, or an earlier revision's test result cannot substitute for evidence from the candidate under review.

## 8. Scope exclusions

This PRD excludes generic agent platforms, non-apparel industrial orders, mechanical machining, CAD/CNC capability matching, a full Digital Twin, payment or settlement, ERP replacement, and autonomous commercial commitments. Existing code outside this product scope is a separate code-governance matter; the presence of that code does not expand abcdYi requirements.

## 9. Document authority

The original AIVAN and abcdYi product descriptions and the product owner's current instructions take precedence over this working PRD and historical repository documents. Resolve inconsistent requirements against those sources rather than treating an existing repository statement as authorization. Historical Git revisions and [Issue #25](https://github.com/GiraffeTechnology/abcdYi/issues/25) remain available for traceability. Acceptance evidence must distinguish the inquiry-and-quotation delivery slice, order confirmation through Aivan, and the complete abcdYi execution workflow.
