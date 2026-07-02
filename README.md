# abcdYi — Apparel & Textile B2M Industry Edition

`B2M` | `Apparel / Textile / Handicraft` | `Giraffe Agent Industry Edition` | `giraffe-language-skill` | `giraffe-db` | `GLTG` | `Human Approval`

abcdYi is the first complete B2M industry edition of the Giraffe industrial execution architecture.

It is built for multi-party supply-chain coordination in apparel, textiles, and handicraft-based production. It serves independent designers, small fashion brands, trading companies, merchandisers, and SMEs that need structured order execution from buyer inquiry through supplier matching, RFQ, production monitoring, quality control, delivery, pricing benchmark validation, and human approval.

The core user is not an end consumer. The core user is a professional buyer, designer, brand, trader, merchandiser, or SME coordinating production with manufacturers, workshops, material suppliers, process suppliers, QC participants, logistics partners, and pricing intelligence services.

---

## What abcdYi Is

abcdYi is:

```text
Giraffe Agent's B2M apparel/textile industry edition
an order execution workflow product
a multi-party supply-chain coordination system
a designer / small-brand production assistant
a small-batch quick-response workflow engine
a patent-aligned implementation of multi-party apparel/textile execution logic
a consumer of giraffe-language-skill, giraffe-db, GPM, GLTG, and giraffe-qc-model
```

---

## What abcdYi Is Not

abcdYi is not:

```text
a consumer shopping app
a marketplace
a generic ERP
a generic CRM
a simple supplier directory
a hardcoded demo
a standalone pricing database
a replacement for GPM or GLTG
a replacement for human commercial approval
```

---

## B2M Role Model

B2M means Buyer-to-Manufacturer.

In this repository, Buyer means a commercial or professional buyer:

```text
independent designer
small fashion brand
boutique label
trading company
merchandiser
SME placing production orders
buyer coordinating apparel, textile, or handicraft production
```

Manufacturer side may include:

```text
garment factories
textile mills
CMT workshops
fabric suppliers
trim suppliers
packaging suppliers
embroidery providers
printing providers
handicraft workshops
QC providers
logistics partners
```

abcdYi coordinates this multi-party production workflow.

---

## System Boundary

```text
giraffe-language-skill = multilingual canonicalization and localized output
giraffe-db             = private business facts, supplier memory, lead-time evidence
GLTG                   = lead-time and delivery-feasibility simulation
GPM                    = procurement path and supplier-set reasoning
giraffe-qc-model       = visual QC training and inspection intelligence
abcdYi                 = apparel/textile B2M application workflow
human operator         = final commercial/legal approval
```

abcdYi must not embed its own language alias maps, supplier fact store, GLTG calculator, QC model, or channel credential runtime.

---

## P0 Language Boundary

Standard English is the only internal working language across Giraffe products.

All raw multilingual buyer, supplier, designer, merchandiser, QC, IM, email, or order text must pass through `giraffe-language-skill` before abcdYi extracts business fields, creates RFQs, routes suppliers, calls GLTG, writes graph data, generates QC requirements, or creates outbound drafts.

Allowed path:

```text
raw multilingual input
-> giraffe-language-skill
-> canonical English apparel/textile packet
-> abcdYi workflow
-> giraffe-db / GLTG / GPM / QC integrations
-> localized user-facing output
```

abcdYi must not add:

```text
multilingual product alias maps
city / destination alias maps
material alias maps
SKU alias maps
quality alias maps
supplier capability maps
raw non-English extraction shortcuts
LLM extraction directly from raw non-English business text
```

If canonicalization fails, abcdYi must ask for clarification instead of guessing.

---

## Core Workflow

```text
Buyer / designer requirement
-> language canonicalization
-> structured apparel/textile requirement packet
-> buyer profile and preference lookup
-> supplier / process / material matching
-> RFQ package generation
-> supplier response collection
-> GPM procurement path reasoning
-> GLTG lead-time simulation
-> pricing benchmark / quote validation
-> QC requirement and detection-point preparation
-> human approval
-> production follow-up
-> QC evidence review
-> logistics tracking
-> final sign-off
-> execution graph and supplier memory update
```

---

## GLTG / Lead-Time Boundary

abcdYi must not calculate delivery feasibility locally when GLTG is available.

GLTG owns:

```text
P50 / P80 / P90 lead-time estimates
supplier behavior adjustments
buyer decision delay buffers
fallback supplier recommendation
manual review triggers
lead-time explanation JSON
source observation traceability
```

abcdYi may display, explain, and use GLTG results, but it must not replace them with LLM guesses.

---

## QC Boundary

abcdYi may generate or collect apparel/textile QC requirements, but actual visual QC intelligence belongs to `giraffe-qc-model`.

QC requirement text must pass through `giraffe-language-skill` before it becomes:

```text
inspection requirement
training pack source
rule proposal
detection point
QC decision packet
```

Visual pass/fail decisions must be produced by the QC model or human review, not by abcdYi's general workflow logic.

---

## Human Approval Boundary

Human approval is required for:

```text
supplier inquiry release
quote submission
supplier selection
production commitment
delivery commitment
QC exception acceptance
payment / contract / commercial commitment
```

abcdYi can assist and recommend; it cannot become the legal counterparty.

---

## Current Product Direction

abcdYi is the apparel/textile vertical product layer for Giraffe's industrial execution system.

Near-term alignment targets:

```text
consume giraffe-language-skill canonical packets
consume giraffe-db private/synthetic behavior evidence
call GLTG v1, then GLTG v2 after contract stabilization
use GPM for supplier-set and procurement-path reasoning
integrate giraffe-qc-model for SKU-specific QC workflows
preserve human approval gates
write auditable execution graph events
```

---

## License

See `LICENSE`.
