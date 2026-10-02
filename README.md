# abcdYi — Industrial Apparel Execution Agent

`B2M` | `Apparel / Textile` | `Giraffe Agent Industry Edition` | `Aivan` | `GLTG / GPM` | `Private Data` | `Human Approval`

## Product Positioning

abcdYi is a Giraffe Agent industry application.

Its front end calls Aivan, the Giraffe Agent front-end application for inquiry, quotation, and order confirmation. myAivan is Aivan's web version. OpenClaw-aivan is Aivan's IM and email access dependency.

abcdYi coordinates professional buyers, designers, brands, merchandisers, suppliers, factories, workshops, QC providers, and logistics partners through an AI-assisted execution workflow.

The original AIVAN and abcdYi product descriptions and current product-owner instructions are the product authority. See `docs/Giraffe_Agent_MVP_v1.0_PRD.md` for the working PRD; GitHub Issue #25 is a historical positioning reference.

---

## Previous PRD Definition

Original positioning:

```
abcdYi = Apparel & Textile AI Execution Product
```

Original objectives:

- AI-assisted apparel and textile order execution;
- Supply chain coordination;
- Product information management;
- Procurement and production workflow assistance.

---

## Current Product Scope

abcdYi is responsible for:

- Apparel order execution;
- Product requirement structuring;
- Supplier coordination;
- Production node management;
- Delivery risk management;
- AI-assisted execution decisions.

abcdYi is not responsible for:

- Replacing ERP systems;
- Replacing the user's private database;
- Automatic commercial commitments.

---

## System Boundary

```
Buyer / Brand
      ↓
abcdYi Front End → Aivan (inquiry → quotation → order confirmation)
                         ├─ myAivan: web version
                         ├─ OpenClaw-aivan: IM and email access dependency
                         ├─ GLTG / GPM: dependency modules called through APIs
                         └─ Private-data provider: giraffe-db or the user's database
      ↓
abcdYi Order Execution → Production → QC → Logistics → Buyer Sign-off
```

Component ownership:

- abcdYi = Giraffe Agent industry application whose front end calls Aivan
- Aivan = Giraffe Agent front-end application for inquiry, quotation, and order confirmation
- myAivan = Aivan web version
- OpenClaw-aivan = Aivan IM and email access dependency
- GLTG / GPM = Aivan dependency modules called through APIs
- giraffe-db = extensible, dynamic private database, hot-swappable for the user's own private database
- Giraffe Agent / Aivan / abcdYi data dependency = database-backed business history and business-process records as the source of truth; workflow state does not depend on conversation context
- giraffe-language-skill = dynamic translation for non-English input and output
- Human operator = commercial approval

The standard product working and interaction language is English. Non-English input is dynamically translated through [`giraffe-language-skill`](https://github.com/GiraffeTechnology/giraffe-language-skill) into standard English before entering the workflow; non-English output uses the same translation module. Except for company and user profile information, the database stores only English content, including business history, process data, drafts, messages, and events. Preserve source references, content hashes, and English-normalized evidence without persisting non-English business originals. Static language packs or complete all-language translation coverage are not prerequisites for delivery.

The order flow is approved quotation → order confirmation → production. A formal contract, contract identifier, signature, or separate contract confirmation is not a production prerequisite.

---

## M-side Role Switching

The M-side runtime uses role-switching to move between supplier inquiry, production
follow-up, QC, logistics, and exception-handling responsibilities while preserving the
same project context and human approval boundary.

Specification: `docs/MSIDE_ROLE_SWITCHING_AGENT_SPEC.md`.
Patent position: `PATENT_NOTICE.md`.

---

## Stage 1 Inquiry and Quotation Delivery Slice

Must complete:

1. Apparel RFQ input
2. Product requirement structuring
3. Supplier coordination
4. Quote and lead-time analysis
5. Lead-time analysis through the GLTG API
6. Execution recommendation generation
7. Human confirmation workflow

This seven-step slice does not by itself demonstrate Aivan's order-confirmation responsibility or the complete abcdYi order lifecycle. Acceptance reports the dependency APIs and private-data provider exercised without requiring exclusive use of giraffe-db or whole-platform production acceptance. The two designated giraffe-db simulated databases, generated from real-data sources, are valid test and acceptance sources. Live customer production data is not a prerequisite. Execute the application/API workflow and state transitions, verify process-data writes and readback, and recover workflow state from the configured database after restart or reload without prior conversation context. The same data-dependency design applies to Giraffe Agent, Aivan, and abcdYi. Simulated database content is valid acceptance data; skipped jobs do not count as passes.

---

## Prohibited Scope Expansion

During v1.0, do not add:

- Generic Agent platform capabilities;
- Non-business infrastructure;
- Unvalidated industry expansion;
- Full Digital Twin implementation.

Inventory code outside the approved scope, record exact source revisions and paths, and freeze it for preservation without deleting it. Shared in-scope behavior remains intact.

---

## Core Principle

All future development must:

1. Map to the PRD scope;
2. Have explicit Acceptance Criteria;
3. Move toward customer-usable delivery;
4. Not use architecture refactoring as a substitute for delivery.

---

## License

See `LICENSE`.
