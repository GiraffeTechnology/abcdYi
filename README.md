# abcdYi
> Giraffe Agent Industry Edition for Apparel, Textiles, and Handicrafts

abcdYi is the first complete industry edition of Giraffe Agent, built for multi-party supply-chain coordination in apparel, textiles, and handicraft-based custom production.

It serves independent designers, small fashion brands, and SME-led fashion ecosystems that need structured, multi-party order execution — from buyer inquiry through supplier matching, RFQ, production monitoring, quality control, and delivery — with human approval at every critical decision boundary.

---

## What abcdYi Is Not

abcdYi is not:
- a marketplace
- an e-commerce store
- a consumer shopping app
- a generic ERP
- a generic CRM
- a virtual fitting product
- a blockchain product
- a simple supplier directory
- a hardcoded demo
- a one-order simulation

---

## What abcdYi Is

abcdYi is:
- Giraffe Agent's first complete industry edition
- a supply-chain workflow execution product
- a multi-party coordination system for fashion SMEs
- a designer and small-brand order execution assistant
- a small-batch quick-response workflow engine
- a patent-aligned implementation of multi-party C2M execution logic for apparel, textiles, and handicrafts

---

## Who It Is For

- **Independent designers** placing small-batch custom orders with workshops and factories
- **Small fashion brands** coordinating multi-tier supply chains (fabric, trims, manufacturing, QC, logistics)
- **SME apparel and textile businesses** executing C2M orders with multiple participants
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

Or all-in-one (manual migration step required):
```bash
docker compose up --build
```

### Clean-state Test Run

```bash
./scripts/run_clean_db_validation.sh
```

Or manually:
```bash
docker compose down -v
docker compose up -d db
uv run alembic upgrade head
uv run pytest tests/api/ tests/unit/ -v
```

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

## Project Structure

```
api/           FastAPI routes and app entry point
src/           Business logic and service modules
  matching/    12-dimension supplier matching
  rfq/         RFQ state machine and service
  decision_packets/  Decision packet generation
  orders/      Order state machine
  milestones/  12-milestone production tracking
  production_monitoring/  Delay predictor
  apparel_inspection/  QC evaluation engine
  logistics/   Shipment and tracking
  supplier_memory/  Performance tracking
  execution_graph/  Append-only audit trail
  approval_gates/  Human approval gate pattern
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

Certain workflows, system logic, role-based participant coordination mechanisms, dynamic order forms, participant matching, production monitoring, quality inspection, participant supervision, supplier memory, and multi-party C2M / order-execution workflows in this project may be covered by patents owned by Giraffe Technology Holding Limited.

abcdYi is the Apparel / Textile / Handicraft industry edition of Giraffe Agent. Its workflow is designed to implement patent-aligned execution logic for multi-party supply-chain coordination in small-batch, fast-response fashion and craft-based production.

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
