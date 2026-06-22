# Giraffe JP — Service-Led Custom Formalwear Backend

This document describes the architecture and business rules for the Giraffe JP backend, which extends abcdYi with a service-led custom formalwear platform for the Japan market.

---

## Overview

Giraffe JP is a made-to-order platform layer built on top of the existing abcdYi B2M coordination system. It introduces three backend modules:

| Module | Iteration | Purpose |
|---|---|---|
| Message Category Auto-Send Permissions | 02 | Per-tenant control over which outbound message categories can be sent automatically vs. held for human review |
| Web Dialog and Email Communication Layer | 03 | Structured conversation threads, inbound message recording, outbound draft creation with auto-send enforcement, human approve/reject flow |
| Formalwear C2B2M Order Extension | 04 | Formalwear order profiles with garment-specific requirements; C2B2M role-edge initialization |

Giraffe JP is additive. It does not modify any existing abcdYi models, routes, or business logic.

---

## Architecture

### Package structure

```
src/giraffe_jp/
  __init__.py
  schemas.py              Pydantic v2 schemas for all Giraffe JP resources
  service.py              Service-core helpers (ServiceNode, ConfirmationRequest, CustomerServiceTask)
  message_permissions.py  DEFAULT_CATEGORIES seed data + is_auto_send_allowed()
  communication.py        create_thread(), record_inbound_message(),
                          create_outbound_draft(), approve_draft(), reject_draft()
  formalwear.py           create_formalwear_profile(),
                          initialize_default_c2b2m_edges_for_project()

src/db/models/giraffe_jp.py
  GiraffeJPServiceNode
  GiraffeJPConfirmationRequest
  GiraffeJPCustomerServiceTask
  GiraffeJPMessageCategoryPermission
  GiraffeJPConversationThread
  GiraffeJPMessage
  GiraffeJPOutboundMessageDraft
  GiraffeJPMessageDeliveryLog
  GiraffeJPFormalwearOrderProfile
  GiraffeJPC2B2MRoleEdge

api/routes/
  giraffe_jp_service_nodes.py
  giraffe_jp_message_permissions.py
  giraffe_jp_conversations.py
  giraffe_jp_formalwear.py

alembic/versions/
  c3d4e5f6a7b8_add_giraffe_jp_iterations.py
```

### Database tables

All top-level Giraffe JP tables include `tenant_id` as a foreign key to `tenants.id`. Tables are created by migration `c3d4e5f6a7b8` (revises `a1b2c3d4e5f6`).

| Table | Description |
|---|---|
| `giraffe_jp_service_nodes` | Qualified production partner network nodes |
| `giraffe_jp_confirmation_requests` | Service confirmation requests |
| `giraffe_jp_customer_service_tasks` | Proactive customer service tasks |
| `giraffe_jp_message_category_permissions` | Per-tenant auto-send permissions; unique on `(tenant_id, category_id)` |
| `giraffe_jp_conversation_threads` | Communication threads (one per party/project/thread-type) |
| `giraffe_jp_messages` | Individual messages (INBOUND or OUTBOUND) within a thread |
| `giraffe_jp_outbound_message_drafts` | Outbound drafts with approval status tracking |
| `giraffe_jp_message_delivery_logs` | Delivery log records (simulated in this iteration) |
| `giraffe_jp_formalwear_order_profiles` | Per-project formalwear order profiles |
| `giraffe_jp_c2b2m_role_edges` | C2B2M role relationship edges for a project |

---

## Iteration 02 — Message Category Auto-Send Permissions

### Default categories

22 categories are seeded by `POST /api/giraffe-jp/permissions/seed-defaults`. Seeding is idempotent — calling the endpoint multiple times does not create duplicates.

| Party Type | Count | Examples |
|---|---|---|
| CUSTOMER | 8 | Order Confirmation, Measurement Request, QC Result, Payment Reminder |
| SUPPLIER | 7 | Production Brief, Quality Evidence Request, Defect Report, Invoice Request |
| MODEL_PARTNER | 7 | Try-On Appointment, Fit Review Request, Compensation Notice, Engagement Brief |

Automatic send is enabled (`auto_send=True`) for routine transactional notifications. Human review is required (`auto_send=False`) for payment reminders, defect reports, compensation notices, shipment instructions, and alteration acknowledgments.

### Spec-enforced rules

- **Rule 7**: Any category not present in the tenant's permission table defaults to `auto_send=False`.
- **Rule 8**: No outbound message draft may be created without checking `is_auto_send_allowed(db, tenant_id, category_id)` first.

### Execution Graph events

| Event type | Trigger |
|---|---|
| `MESSAGE_CATEGORY_PERMISSIONS_SEEDED` | Seed-defaults endpoint called |
| `MESSAGE_CATEGORY_PERMISSION_UPDATED` | PATCH auto_send value |

---

## Iteration 03 — Web Dialog and Email Communication Layer

### Draft lifecycle

```text
create_outbound_draft(category_id, body)
    ↓
  is_auto_send_allowed()?
    ├─ YES → approval_status = AUTO_SENT
    │         → delivery log created (SIMULATED)
    │         → OUTBOUND_MESSAGE_AUTO_SENT emitted
    └─ NO  → approval_status = PENDING_HUMAN_CONFIRMATION
              → OUTBOUND_MESSAGE_PENDING_APPROVAL emitted
              → Human operator must call /approve or /reject

Approve flow:
    approval_status = APPROVED
    delivery log created (SIMULATED)
    OUTBOUND_MESSAGE_APPROVED_SENT emitted

Reject flow:
    approval_status = REJECTED
    OUTBOUND_MESSAGE_REJECTED emitted
```

Only drafts in `PENDING_HUMAN_CONFIRMATION` state can be approved or rejected. Attempting to approve an `AUTO_SENT` or already-`APPROVED`/`REJECTED` draft returns HTTP 400.

### Execution Graph events

| Event type | Trigger |
|---|---|
| `CONVERSATION_THREAD_CREATED` | New thread opened |
| `INBOUND_MESSAGE_RECORDED` | Inbound message recorded |
| `OUTBOUND_DRAFT_CREATED` | Outbound draft created (any status) |
| `OUTBOUND_MESSAGE_AUTO_SENT` | Draft was auto-sent |
| `OUTBOUND_MESSAGE_PENDING_APPROVAL` | Draft placed in human review queue |
| `OUTBOUND_MESSAGE_APPROVED_SENT` | Human approved and message sent |
| `OUTBOUND_MESSAGE_REJECTED` | Human rejected the draft |

### Email delivery

No real external email provider is integrated in this iteration. All delivery is simulated (`delivery_status = SIMULATED`) and logged to `giraffe_jp_message_delivery_logs`. The delivery log record is created both for auto-sent drafts and for approved drafts.

---

## Iteration 04 — Formalwear C2B2M Order Extension

### Supported garment categories

| Category | `hollow_to_hem_required` default |
|---|---|
| `BRIDALWEAR` | `True` |
| `LIGHT_WEDDING_DRESS` | `True` |
| `FORMAL_DRESS` | `True` |
| `WOMENS_SUIT` | `False` |
| `RECEPTION_DRESS` | `False` |

`hollow_to_hem_required` is set automatically from the garment category when the profile is created. It cannot be overridden via PATCH.

### Default C2B2M role edges

`POST /api/giraffe-jp/projects/{project_id}/c2b2m-edges/initialize` creates the following edges if they do not already exist:

| role_from | role_to | edge_label |
|---|---|---|
| CUSTOMER | SERVICE_PLATFORM | customer_to_platform |
| SERVICE_PLATFORM | PRODUCTION_PARTNER | platform_to_production |
| SERVICE_PLATFORM | LOCAL_MODEL_PARTNER | platform_to_local_model |
| PRODUCTION_PARTNER | QUALITY_REVIEWER | production_to_qc |

Edge initialization is idempotent: calling the endpoint multiple times does not create duplicate edges. The response returns only newly-created edges (empty list on subsequent calls).

### Execution Graph events

| Event type | Trigger |
|---|---|
| `FORMALWEAR_ORDER_PROFILE_CREATED` | Profile created |
| `FORMALWEAR_ORDER_PROFILE_UPDATED` | Profile PATCH |
| `C2B2M_ROLE_EDGE_CREATED` | Each new edge created during initialization |
| `C2B2M_DEFAULT_EDGES_INITIALIZED` | Edge initialization endpoint called |

---

## Authentication

All `/api/giraffe-jp/*` routes require JWT authentication via the `get_current_user` dependency. Unauthenticated requests return HTTP 401.

## Tenant isolation

All Giraffe JP queries filter by `tenant_id = current_user.tenant_id`. No cross-tenant data leakage is possible through these routes.

## No external credentials

This iteration contains no real marketplace, Cainiao, EMS, Japan Post, or payment credentials. Delivery is fully simulated.
