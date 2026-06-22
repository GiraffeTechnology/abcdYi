import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


# ── Service Core ──────────────────────────────────────────────────────────────

class ServiceNodeCreate(BaseModel):
    name: str
    node_type: str
    location_country: str | None = None
    node_metadata: dict | None = None


class ServiceNodeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    node_type: str
    location_country: str | None
    node_metadata: dict | None
    created_at: datetime
    updated_at: datetime


class ConfirmationRequestCreate(BaseModel):
    project_id: uuid.UUID | None = None
    service_node_id: uuid.UUID | None = None
    request_type: str
    payload: dict | None = None


class ConfirmationRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    project_id: uuid.UUID | None
    service_node_id: uuid.UUID | None
    request_type: str
    status: str
    payload: dict | None
    created_at: datetime
    updated_at: datetime


class CustomerServiceTaskCreate(BaseModel):
    project_id: uuid.UUID | None = None
    task_type: str
    description: str | None = None
    assignee_user_id: uuid.UUID | None = None


class CustomerServiceTaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    project_id: uuid.UUID | None
    task_type: str
    status: str
    description: str | None
    assignee_user_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


# ── Iteration 02: Message Category Auto-Send Permissions ─────────────────────

class MessageCategoryPermissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    category_id: str
    category_name: str
    party_type: str
    channel: str | None
    auto_send: bool
    created_at: datetime
    updated_at: datetime


class MessageCategoryPermissionUpdate(BaseModel):
    auto_send: bool


# ── Iteration 03: Web Dialog and Email Communication Layer ────────────────────

class ConversationThreadCreate(BaseModel):
    party_type: str
    project_id: uuid.UUID | None = None
    party_ref_id: str | None = None
    thread_type: str = "GENERAL"
    subject: str | None = None


class ConversationThreadRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    project_id: uuid.UUID | None
    party_type: str
    party_ref_id: str | None
    thread_type: str
    subject: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class InboundMessageCreate(BaseModel):
    body: str
    sender_ref: str | None = None
    message_metadata: dict | None = None


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    thread_id: uuid.UUID
    direction: str
    body: str
    sender_ref: str | None
    message_metadata: dict | None
    created_at: datetime


class OutboundDraftCreate(BaseModel):
    category_id: str
    body: str


class OutboundDraftRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    thread_id: uuid.UUID
    category_id: str
    body: str
    approval_status: str
    reviewed_by_user_id: uuid.UUID | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime


# ── Iteration 04: Formalwear C2B2M Order Extension ───────────────────────────

class FormalwearProfileCreate(BaseModel):
    garment_category: str
    hollow_to_hem_cm: float | None = None
    model_try_on_required: bool = True
    local_alteration_possible: bool = True
    custom_measurements: dict | None = None


class FormalwearProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    project_id: uuid.UUID
    garment_category: str
    hollow_to_hem_cm: float | None
    hollow_to_hem_required: bool
    model_try_on_required: bool
    local_alteration_possible: bool
    custom_measurements: dict | None
    created_at: datetime
    updated_at: datetime


class FormalwearProfileUpdate(BaseModel):
    hollow_to_hem_cm: float | None = None
    model_try_on_required: bool | None = None
    local_alteration_possible: bool | None = None
    custom_measurements: dict | None = None


class C2B2MEdgeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    project_id: uuid.UUID
    role_from: str
    role_to: str
    edge_label: str
    edge_metadata: dict | None
    created_at: datetime
