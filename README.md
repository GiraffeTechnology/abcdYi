# abcdYi — Industrial Apparel Execution Agent

`B2M` | `Apparel / Textile` | `Giraffe Agent Industry Edition` | `Aivan` | `GLTG` | `giraffe-db` | `Human Approval`

## Product Positioning

abcdYi is Giraffe Technology's industrial apparel execution agent.

It has evolved from an AI-assisted apparel and textile workflow product into a vertical execution layer for apparel, textile, and handicraft production.

abcdYi coordinates professional buyers, designers, brands, merchandisers, suppliers, factories, workshops, QC providers, and logistics partners through an AI-assisted execution workflow.

This repository follows:

**PRD v2.0 Product Scope Reset — abcdYi Industrial Apparel Execution Agent**

See GitHub Issue #25 for the frozen product baseline.

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
- Replacing supply chain fact databases;
- Automatic commercial commitments.

---

## System Boundary

```
Buyer / Brand
      ↓
abcdYi Apparel Execution
      ↓
Aivan Workflow
      ↓
giraffe-db + GLTG
      ↓
Human Approval
      ↓
Execution
```

Component ownership:

- abcdYi = apparel vertical execution workflow
- Aivan = execution workflow and AI interaction layer
- giraffe-db = business facts and evidence
- GLTG = lead-time intelligence
- Human operator = commercial approval

---

## M-side Role Switching

The M-side runtime uses role-switching to move between supplier inquiry, production
follow-up, QC, logistics, and exception-handling responsibilities while preserving the
same project context and human approval boundary.

Specification: `docs/MSIDE_ROLE_SWITCHING_AGENT_SPEC.md`.
Patent position: `PATENT_NOTICE.md`.

---

## v1.0 Frozen Delivery Scope

Must complete:

1. Apparel RFQ input
2. Product requirement structuring
3. Supplier coordination
4. Quote and lead-time analysis
5. GLTG integration
6. Execution recommendation generation
7. Human confirmation workflow

---

## Prohibited Scope Expansion

During v1.0, do not add:

- Generic Agent platform capabilities;
- Non-business infrastructure;
- Unvalidated industry expansion;
- Full Digital Twin implementation.

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
