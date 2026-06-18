# abcdYi
> Giraffe Agent B2M Industry Edition for Apparel, Textiles, and Handicrafts

abcdYi is the first complete B2M industry edition of Giraffe Agent, built for multi-party supply-chain coordination in apparel, textiles, and handicraft-based production.

It serves independent designers, small fashion brands, and SME-led fashion ecosystems that need structured, multi-party order execution — from buyer inquiry through supplier matching, RFQ, production monitoring, quality control, and delivery — with human approval at every critical decision boundary.

The core user is not an end consumer. The core user is a buyer, designer, small brand, trader, merchandiser, or SME coordinating production with manufacturers, workshops, material suppliers, process suppliers, QC participants, and logistics partners.

---

## Why B2M

abcdYi is B2M: Buyer-to-Manufacturer.

In this repository, "Buyer" means a commercial or professional buyer, such as:
- an independent designer;
- a small fashion brand;
- a boutique label;
- a trading company;
- a merchandiser;
- an SME placing production orders;
- a buyer coordinating apparel, textile, or handicraft production.

The buyer is not treated as a retail consumer.

The manufacturer side may include:
- garment factories;
- textile mills;
- CMT workshops;
- fabric suppliers;
- trim suppliers;
- packaging suppliers;
- embroidery providers;
- printing providers;
- handicraft workshops;
- QC providers;
- logistics partners.

abcdYi exists to coordinate this B2M production workflow.

---

## What abcdYi Is Not

abcdYi is not:
- a marketplace
- an e-commerce store
- a consumer shopping app
- a generic ERP
- a generic CRM
- a simple supplier directory
- a hardcoded demo
- a one-order simulation

---

## What abcdYi Is

abcdYi is:
- Giraffe Agent's first complete B2M industry edition
- a supply-chain workflow execution product
- a multi-party coordination system for fashion SMEs
- a designer and small-brand order execution assistant
- a small-batch quick-response workflow engine
- a patent-aligned implementation of multi-party B2M execution logic for apparel, textiles, and handicrafts

---

## Who It Is For

- **Independent designers** placing small-batch custom orders with workshops and factories
- **Small fashion brands** coordinating multi-tier supply chains (fabric, trims, manufacturing, QC, logistics)
- **SME apparel and textile businesses** executing B2M orders with multiple participants
- **Handicraft producers** coordinating fragmented material and process suppliers
- **Developer teams** building industry-specific supply-chain coordination tools on top of Giraffe Agent

---

## Core Workflow

```text
Designer / Buyer Inquiry
    ↓
Requirement Extraction
    ↓
Dynamic Order Form
    ↓
Missing Information Detection
    ↓
Participant Classification
    ↓
Permission Assignment
    ↓
Supplier / Workshop / Process Matching
    ↓
RFQ Preparation
    ↓
Human Approval
    ↓
RFQ Dispatch
    ↓
Supplier Response Intake
    ↓
Response Normalization
    ↓
Decision Packet
    ↓
Human Approval
    ↓
Order Confirmation
    ↓
Production Time Setting
    ↓
Milestone Monitoring
    ↓
Delay Prediction / Acceleration Reminder
    ↓
Quality Evidence Review
    ↓
Delivery Handover
    ↓
Buyer / Designer Sign-Off
    ↓
Supplier Memory Update
    ↓
Execution Graph Record
```

---

## Role-Switching (M-Side / B-Side)

A single actor's role is contextual, not fixed: the same supplier can be the M-side (main supplier) responding to the original buyer on one edge, and the B-side (upstream buyer) sourcing from material/process suppliers on another edge of the same project. Role context is resolved per (project, edge, actor) rather than assigned statically.

See [docs/MSIDE_ROLE_SWITCHING_AGENT_SPEC.md](docs/MSIDE_ROLE_SWITCHING_AGENT_SPEC.md) for the full role-switching agent spec.

---

## Expected Modules

- Inquiry intake
- Requirement extraction
- Dynamic order form
- Participant classification
- Permission assignment
- Participant matching
- RFQ workflow
- Supplier response normalization
- Decision packet
- Human approval gate
- Production monitoring
- Delay prediction
- Acceleration reminder
- QC evidence
- Difference detection
- Logistics handover
- Supplier memory
- Execution graph

---

## Order State Machine

```text
DRAFT_FROM_APPROVED_QUOTE
    → PENDING_BUYER_CONFIRMATION
    → CONFIRMED
    → IN_PRODUCTION
    → QC_PENDING
    → QC_PASSED / QC_FAILED
    → READY_TO_SHIP
    → SHIPPED
    → DELIVERED
    → BUYER_SIGNED_OFF
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 16+
- `uv` package manager

### Local Development

```bash
# 1. Install dependencies
uv sync

# 2. Configure environment
cp .env.example .env
# Edit .env: set DATABASE_URL and SECRET_KEY

# 3. Run migrations
uv run alembic upgrade head

# 4. Start the API
uv run uvicorn api.main:app --reload

# 5. Health check
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "ok",
  "product": "abcdYi — Giraffe Agent Apparel / Textile / Handicraft Industry Edition"
}
```

### Docker

```bash
# Start database
docker compose up -d db

# Run migrations
docker compose run --rm migrate

# Start API
docker compose up api
```

---

## Validation

Run a clean-state validation:

```bash
./scripts/run_clean_db_validation.sh
```

The validation performs:

1. Docker cleanup (`docker compose down -v`)
2. Docker image build (`docker compose build`)
3. Fresh PostgreSQL startup
4. Alembic migration (`docker compose run --rm migrate`)
5. API startup
6. `/health` check
7. Unit tests — no DB required (`uv run pytest tests/unit/ -v -m "not integration"`)
8. Integration tests — requires migrated DB (`uv run pytest tests/integration/ -v`)

Run unit tests alone (no Docker needed):

```bash
uv run pytest tests/unit/ -v -m "not integration"
```

The repository must pass at least three consecutive clean-state validation runs before being treated as release-ready.

Note: `tests/api/*` and `tests/integration/*` connect to a live PostgreSQL instance
(`AsyncSessionLocal` defaults to `postgresql+asyncpg://...`) and will fail with
`ConnectionRefusedError` in any environment without a running Postgres (e.g. no
`docker compose up -d db`, no Docker daemon at all). This is expected outside the
Docker-based validation flow above — `pytest -q` run without Postgres available will
show ~60 such errors confined to those two directories; every other test file
(`tests/db/*`, `tests/unit/*`, `tests/test_*.py`, etc.) is DB-independent (in-memory
SQLite or pure-Python) and must pass cleanly on its own.

---

## API Overview

All routes except `/health` and `/api/auth/*` require:
```
Authorization: Bearer <jwt_token>
```

Key routes:

| Method | Path | Description |
|---|---|---|
| POST | `/api/auth/register` | Register user |
| POST | `/api/auth/login` | Login |
| POST | `/api/participants` | Register supplier / workshop |
| POST | `/api/projects` | Create a project |
| POST | `/api/projects/{id}/buyer-inquiries` | Submit buyer inquiry |
| POST | `/api/projects/{id}/dynamic-forms` | Generate order form |
| POST | `/api/projects/{id}/run-participant-matching` | Match suppliers |
| POST | `/api/projects/{id}/rfqs` | Create RFQ |
| POST | `/api/rfqs/{id}/send` | Send RFQ (after approval) |
| POST | `/api/projects/{id}/decision-packets` | Generate decision packet |
| POST | `/api/projects/{id}/orders/from-approved-option` | Create order |
| POST | `/api/orders/{id}/confirm` | Confirm order |
| POST | `/api/orders/{id}/run-delay-prediction` | Run delay prediction |
| POST | `/api/orders/{id}/qc-records` | Submit QC record |
| POST | `/api/orders/{id}/shipments` | Create shipment |
| POST | `/api/orders/{id}/buyer-sign-off` | Buyer sign-off |
| GET | `/api/execution-graph/orders/{id}` | Audit trail |

See `docs/api_reference.md` for the full API reference.

---

## Acceptance Test

```bash
BASE_URL=http://localhost:8000 uv run python scripts/run_v1_acceptance_apparel_order.py
```

Expected output:
```
GIRAFFE APPAREL & TEXTILE V1 ACCEPTANCE: PASS
```

5x readiness verification:
```bash
BASE_URL=http://localhost:8000 uv run python scripts/verify_v1_product_readiness_5x.py
```

---

## GLTG — Giraffe Lead-Time Graph Engine

abcdYi does not implement lead-time calculation logic directly. All delivery feasibility reasoning is delegated to the **GLTG** (Giraffe Lead-Time Graph) engine, a standalone local package at `libs/GLTG/`.

GLTG takes a supply-chain graph as input — participant nodes with role-specific lead times — and returns a ranked `DeliveryFeasibilityPacket` with:

- Parallel lead time (max of fabric / trim / packaging sourcing stages)
- Sequential lead time (sum of production / QC / logistics stages)
- Most-likely, risk-adjusted, and committable delivery dates
- Up to 3 ranked feasible paths (never faked — fewer paths returned if fewer feasible options exist)
- Milestone-based reforecasting when a milestone is marked DELAYED
- Human-readable explanation when 0 feasible paths are found

GLTG integrates at two points in abcdYi:

1. **Decision packet generation** — when supplier responses are received and a decision packet is assembled, GLTG evaluates each supplier as a candidate path and enriches decision options with risk-adjusted delivery dates and confidence levels.

2. **Production monitoring** — each time a delay prediction is run (triggered by milestone updates), abcdYi calls GLTG to reforecast delivery feasibility against the current milestone state.

GLTG results are persisted to the `delivery_feasibility_packets` table and recorded as `DELIVERY_FEASIBILITY_EVALUATED` events in the Industrial Execution Graph.

---

## Project Structure

```
api/           FastAPI routes and app entry point
src/           Business logic and service modules
  lead_time/   GLTG adapter (build_gltg_input_from_order, evaluate_delivery_feasibility)
  services/    DeliveryFeasibilityService (GLTG single entry point)
  matching/    12-dimension supplier matching
  rfq/         RFQ state machine and service
  decision_packets/  Decision packet generation (GLTG-enriched)
  orders/      Order state machine
  milestones/  12-milestone production tracking
  production_monitoring/  Delay predictor + GLTG reforecast
  apparel_inspection/  QC evaluation engine
  logistics/   Shipment and tracking
  supplier_memory/  Performance tracking
  execution_graph/  Append-only audit trail
  approval_gates/  Human approval gate pattern
libs/GLTG/     GLTG engine (local package — gltg)
alembic/       Database migrations
tests/         API and unit test suite
scripts/       Seed data, acceptance, readiness scripts
docs/          Product documentation
```

---

## Documentation

| Document | Description |
|---|---|
| `docs/user_manual.md` | 13-chapter user guide |
| `docs/admin_manual.md` | Admin and operations guide |
| `docs/deployment_guide.md` | Deployment guide |
| `docs/api_reference.md` | Full API reference |
| `docs/patent_alignment_matrix.md` | Patent unit mapping |
| `docs/workflow_overview.md` | Workflow documentation |
| `docs/product_scope.md` | Product scope and positioning |
| `docs/sme_designer_ecosystem.md` | SME and designer use cases |
| `docs/acceptance_criteria_v1.md` | V1 acceptance criteria |
| `docs/release_notes_v1.md` | Release notes |

---

## Patent Notice and License

This repository is released under the **Apache-2.0** software license.

Certain workflows, system logic, role-based participant coordination mechanisms, dynamic order forms, participant matching, production monitoring, quality inspection, participant supervision, supplier memory, and multi-party B2M / order-execution workflows in this project may be covered by patents owned by Giraffe Technology Holding Limited.

abcdYi is the Apparel / Textile / Handicraft industry edition of Giraffe Agent. Its workflow is designed to implement patent-aligned execution logic for multi-party supply-chain coordination in small-batch, fast-response fashion and craft-based production.

The official patent titles may contain the term C2M because that is the registered legal title. abcdYi's product implementation and repository positioning are B2M.

Patent references:

| Jurisdiction | Patent |
|---|---|
| China | ZL 2023 1 1645939.9 / CN 117670482 B |
| Japan | P7644545 / 特許第7644545号 |

Giraffe Technology Holding Limited grants a **Global Free Patent License** to:
- individuals
- developers
- researchers
- students
- SMEs for their own procurement, production coordination, sourcing, sampling, small-batch execution, and internal workflow use
- independent designers and small fashion brands for their own order execution and supplier coordination
- educational institutions for teaching and non-commercial use
- research institutions for non-commercial research

**Separate written permission is required for:**
- enterprise deployment
- hosted commercial operation
- high-volume commercial production use
- third-party system integration
- white-label, OEM, or resale
- commercial SaaS operation based on abcdYi workflows
- managed service operation for third-party buyers, brands, manufacturers, or suppliers
- use of Giraffe commercial assets, trademarks, supplier/buyer network data, order archives, or proprietary industry datasets

Access to this source code does not automatically grant patent rights beyond the free license scope.

The Apache-2.0 software license applies to the source code in this repository. It does not waive or exhaust patent rights outside the expressly granted free patent license scope.

Commercial users should obtain written authorization before using abcdYi workflows in enterprise, hosted, integration, resale, or high-volume production environments.

Authorization contact:
```
mich@giraffe.technology
```

See also: [PATENT_NOTICE.md](PATENT_NOTICE.md) · [LICENSE_NOTICE.md](LICENSE_NOTICE.md) · [LICENSE](LICENSE)

---

## Related sub-modules

### QC (visual quality control)

Visual quality-control inspection — on-device-first, with Qwen
vision-language model inference running directly on Android QC
devices and cloud fallback for uncertain cases — is implemented as a
separate sub-module: **[`giraffe-qc-model`](https://github.com/GiraffeTechnology/giraffe-qc-model)**.

It is independently deployed (separate codebase, release cycle, and
database by default) but its SKU/order/asset identity and event
emission are abcdYi's, not locally invented — see that repository's
README for the full architecture and module-relationship details.
