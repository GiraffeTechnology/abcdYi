# Giraffe JP API Reference

All routes are mounted under `/api/giraffe-jp`. All routes require JWT authentication:
```
Authorization: Bearer <token>
```

Unauthenticated requests return `401 Unauthorized`.

---

## Service Core — Qualified Production Partner Network Nodes

### POST /api/giraffe-jp/service-nodes

Register a new node in the qualified production partner network.

**Request body**
```json
{
  "name": "Kyoto Atelier Co.",
  "node_type": "ATELIER",
  "location_country": "JP",
  "node_metadata": {"specialty": "Nishiki weaving"}
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | yes | Display name |
| `node_type` | string | yes | Role: `ATELIER`, `SUPPLIER`, `MODEL_PARTNER`, `SPECIALIST`, etc. |
| `location_country` | string | no | ISO country code |
| `node_metadata` | object | no | Arbitrary metadata |

**Response** `201 Created`
```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "name": "Kyoto Atelier Co.",
  "node_type": "ATELIER",
  "location_country": "JP",
  "node_metadata": {"specialty": "Nishiki weaving"},
  "created_at": "2026-06-22T10:00:00Z",
  "updated_at": "2026-06-22T10:00:00Z"
}
```

### GET /api/giraffe-jp/service-nodes

List all service nodes for the current tenant.

**Response** `200 OK` — array of service node objects.

### GET /api/giraffe-jp/service-nodes/{node_id}

Get a single service node.

**Response** `200 OK` or `404 Not Found`.

---

## Iteration 02 — Message Category Auto-Send Permissions

### POST /api/giraffe-jp/permissions/seed-defaults

Seed 22 default message category permissions for the tenant. Idempotent.

**Response** `201 Created` — list of all 22 permission objects (existing + newly created).

```json
[
  {
    "id": "uuid",
    "tenant_id": "uuid",
    "category_id": "CUST_ORDER_CONFIRMATION",
    "category_name": "Order Confirmation",
    "party_type": "CUSTOMER",
    "channel": "EMAIL",
    "auto_send": true,
    "created_at": "...",
    "updated_at": "..."
  }
]
```

### GET /api/giraffe-jp/permissions

List all message category permissions for the current tenant.

**Response** `200 OK` — array of permission objects, ordered by `party_type`, `category_id`.

### GET /api/giraffe-jp/permissions/{permission_id}

Get a single permission.

**Response** `200 OK` or `404 Not Found`.

### PATCH /api/giraffe-jp/permissions/{permission_id}

Update the `auto_send` value for a permission.

**Request body**
```json
{"auto_send": true}
```

**Response** `200 OK` — updated permission object.
Emits `MESSAGE_CATEGORY_PERMISSION_UPDATED` to the Industrial Execution Graph.

---

## Iteration 03 — Web Dialog and Email Communication Layer

### POST /api/giraffe-jp/conversations

Open a new conversation thread.

**Request body**
```json
{
  "party_type": "CUSTOMER",
  "project_id": "uuid (optional)",
  "party_ref_id": "customer@example.com (optional)",
  "thread_type": "GENERAL",
  "subject": "Fitting appointment confirmation"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `party_type` | string | yes | `CUSTOMER`, `SUPPLIER`, `MODEL_PARTNER` |
| `project_id` | UUID | no | Link to an existing project |
| `party_ref_id` | string | no | External reference (email, phone, ID) |
| `thread_type` | string | no | Default: `GENERAL` |
| `subject` | string | no | Thread subject line |

**Response** `201 Created` — thread object. Emits `CONVERSATION_THREAD_CREATED`.

### GET /api/giraffe-jp/conversations

List all conversation threads for the tenant, newest first.

**Response** `200 OK` — array of thread objects.

### GET /api/giraffe-jp/conversations/{thread_id}

Get a single conversation thread.

**Response** `200 OK` or `404 Not Found`.

### POST /api/giraffe-jp/conversations/{thread_id}/messages/inbound

Record an inbound message received from a party.

**Request body**
```json
{
  "body": "I would like to adjust the hem length.",
  "sender_ref": "customer@example.com",
  "message_metadata": {}
}
```

**Response** `201 Created` — message object with `direction: "INBOUND"`. Emits `INBOUND_MESSAGE_RECORDED`.

### POST /api/giraffe-jp/conversations/{thread_id}/outbound-drafts

Create an outbound message draft. The system checks `is_auto_send_allowed()` for the given `category_id`:
- If `True`: `approval_status = AUTO_SENT`, delivery logged, `OUTBOUND_MESSAGE_AUTO_SENT` emitted.
- If `False` (or category unknown): `approval_status = PENDING_HUMAN_CONFIRMATION`, `OUTBOUND_MESSAGE_PENDING_APPROVAL` emitted.

**Request body**
```json
{
  "category_id": "CUST_ORDER_CONFIRMATION",
  "body": "Dear customer, your order has been confirmed."
}
```

**Response** `201 Created` — draft object with `approval_status`.

### GET /api/giraffe-jp/conversations/{thread_id}/outbound-drafts

List all outbound drafts for a thread.

**Response** `200 OK` — array of draft objects, newest first.

### POST /api/giraffe-jp/outbound-drafts/{draft_id}/approve

Approve a `PENDING_HUMAN_CONFIRMATION` draft. Sets `approval_status = APPROVED`, creates delivery log, emits `OUTBOUND_MESSAGE_APPROVED_SENT`.

**Response** `200 OK` — updated draft object.
**Error** `400 Bad Request` if draft is not in `PENDING_HUMAN_CONFIRMATION` state.

### POST /api/giraffe-jp/outbound-drafts/{draft_id}/reject

Reject a `PENDING_HUMAN_CONFIRMATION` draft. Sets `approval_status = REJECTED`, emits `OUTBOUND_MESSAGE_REJECTED`.

**Response** `200 OK` — updated draft object.
**Error** `400 Bad Request` if draft is not in `PENDING_HUMAN_CONFIRMATION` state.

---

## Iteration 04 — Formalwear C2B2M Order Extension

### POST /api/giraffe-jp/projects/{project_id}/formalwear-profile

Create a formalwear order profile for a project.

**Request body**
```json
{
  "garment_category": "BRIDALWEAR",
  "hollow_to_hem_cm": 145.0,
  "model_try_on_required": true,
  "local_alteration_possible": true,
  "custom_measurements": {"bust": 86, "waist": 68, "hips": 90}
}
```

| Field | Type | Notes |
|---|---|---|
| `garment_category` | string | One of: `FORMAL_DRESS`, `WOMENS_SUIT`, `BRIDALWEAR`, `LIGHT_WEDDING_DRESS`, `RECEPTION_DRESS` |
| `hollow_to_hem_cm` | float | Optional. Measurement in centimetres. |
| `model_try_on_required` | bool | Default: `true` |
| `local_alteration_possible` | bool | Default: `true` |
| `custom_measurements` | object | Optional key-value measurement dict |

`hollow_to_hem_required` is set automatically: `True` for `BRIDALWEAR`, `LIGHT_WEDDING_DRESS`, `FORMAL_DRESS`; `False` otherwise.

**Response** `201 Created` — profile object. Emits `FORMALWEAR_ORDER_PROFILE_CREATED`.

### GET /api/giraffe-jp/projects/{project_id}/formalwear-profile

Get the formalwear profile for a project.

**Response** `200 OK` or `404 Not Found`.

### PATCH /api/giraffe-jp/projects/{project_id}/formalwear-profile

Update mutable fields of the formalwear profile.

**Request body** (all fields optional)
```json
{
  "hollow_to_hem_cm": 152.0,
  "model_try_on_required": false,
  "local_alteration_possible": true,
  "custom_measurements": {"bust": 88}
}
```

**Response** `200 OK` — updated profile. Emits `FORMALWEAR_ORDER_PROFILE_UPDATED`.

### POST /api/giraffe-jp/projects/{project_id}/c2b2m-edges/initialize

Initialize the four default C2B2M role edges for a project. Idempotent — does not create duplicate edges.

**Response** `201 Created` — list of newly-created edge objects (empty list if all edges already exist).
Emits `C2B2M_ROLE_EDGE_CREATED` for each new edge and `C2B2M_DEFAULT_EDGES_INITIALIZED` once.

```json
[
  {"id": "uuid", "role_from": "CUSTOMER", "role_to": "SERVICE_PLATFORM", "edge_label": "customer_to_platform", ...},
  {"id": "uuid", "role_from": "SERVICE_PLATFORM", "role_to": "PRODUCTION_PARTNER", "edge_label": "platform_to_production", ...},
  {"id": "uuid", "role_from": "SERVICE_PLATFORM", "role_to": "LOCAL_MODEL_PARTNER", "edge_label": "platform_to_local_model", ...},
  {"id": "uuid", "role_from": "PRODUCTION_PARTNER", "role_to": "QUALITY_REVIEWER", "edge_label": "production_to_qc", ...}
]
```

### GET /api/giraffe-jp/projects/{project_id}/c2b2m-edges

List all C2B2M role edges for a project.

**Response** `200 OK` — array of edge objects, ordered by creation time.

---

## Execution Graph Event Types (Giraffe JP)

| Constant | Value | Module |
|---|---|---|
| `MESSAGE_CATEGORY_PERMISSIONS_SEEDED` | `"MESSAGE_CATEGORY_PERMISSIONS_SEEDED"` | Iter 02 |
| `MESSAGE_CATEGORY_PERMISSION_UPDATED` | `"MESSAGE_CATEGORY_PERMISSION_UPDATED"` | Iter 02 |
| `CONVERSATION_THREAD_CREATED` | `"CONVERSATION_THREAD_CREATED"` | Iter 03 |
| `INBOUND_MESSAGE_RECORDED` | `"INBOUND_MESSAGE_RECORDED"` | Iter 03 |
| `OUTBOUND_DRAFT_CREATED` | `"OUTBOUND_DRAFT_CREATED"` | Iter 03 |
| `OUTBOUND_MESSAGE_AUTO_SENT` | `"OUTBOUND_MESSAGE_AUTO_SENT"` | Iter 03 |
| `OUTBOUND_MESSAGE_PENDING_APPROVAL` | `"OUTBOUND_MESSAGE_PENDING_APPROVAL"` | Iter 03 |
| `OUTBOUND_MESSAGE_APPROVED_SENT` | `"OUTBOUND_MESSAGE_APPROVED_SENT"` | Iter 03 |
| `OUTBOUND_MESSAGE_REJECTED` | `"OUTBOUND_MESSAGE_REJECTED"` | Iter 03 |
| `FORMALWEAR_ORDER_PROFILE_CREATED` | `"FORMALWEAR_ORDER_PROFILE_CREATED"` | Iter 04 |
| `FORMALWEAR_ORDER_PROFILE_UPDATED` | `"FORMALWEAR_ORDER_PROFILE_UPDATED"` | Iter 04 |
| `C2B2M_ROLE_EDGE_CREATED` | `"C2B2M_ROLE_EDGE_CREATED"` | Iter 04 |
| `C2B2M_DEFAULT_EDGES_INITIALIZED` | `"C2B2M_DEFAULT_EDGES_INITIALIZED"` | Iter 04 |
