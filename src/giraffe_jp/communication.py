import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db.models.giraffe_jp import (
    GiraffeJPConversationThread,
    GiraffeJPMessage,
    GiraffeJPOutboundMessageDraft,
    GiraffeJPMessageDeliveryLog,
)
from src.giraffe_jp.message_permissions import is_auto_send_allowed
from src.execution_graph.writer import emit_event
from src.execution_graph import event_types


async def create_thread(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    party_type: str,
    project_id: uuid.UUID | None = None,
    party_ref_id: str | None = None,
    thread_type: str = "GENERAL",
    subject: str | None = None,
    triggered_by_user_id: uuid.UUID | None = None,
) -> GiraffeJPConversationThread:
    thread = GiraffeJPConversationThread(
        tenant_id=tenant_id,
        project_id=project_id,
        party_type=party_type,
        party_ref_id=party_ref_id,
        thread_type=thread_type,
        subject=subject,
    )
    db.add(thread)
    await db.flush()
    await emit_event(
        db,
        event_type=event_types.CONVERSATION_THREAD_CREATED,
        payload={"thread_id": str(thread.id), "party_type": party_type, "thread_type": thread_type},
        tenant_id=tenant_id,
        project_id=project_id,
        triggered_by_user_id=triggered_by_user_id,
    )
    return thread


async def record_inbound_message(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    thread_id: uuid.UUID,
    body: str,
    sender_ref: str | None = None,
    message_metadata: dict | None = None,
    triggered_by_user_id: uuid.UUID | None = None,
) -> GiraffeJPMessage:
    msg = GiraffeJPMessage(
        tenant_id=tenant_id,
        thread_id=thread_id,
        direction="INBOUND",
        body=body,
        sender_ref=sender_ref,
        message_metadata=message_metadata,
    )
    db.add(msg)
    await db.flush()
    await emit_event(
        db,
        event_type=event_types.INBOUND_MESSAGE_RECORDED,
        payload={"message_id": str(msg.id), "thread_id": str(thread_id)},
        tenant_id=tenant_id,
        triggered_by_user_id=triggered_by_user_id,
    )
    return msg


async def create_outbound_draft(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    thread_id: uuid.UUID,
    category_id: str,
    body: str,
    triggered_by_user_id: uuid.UUID | None = None,
) -> GiraffeJPOutboundMessageDraft:
    allowed = await is_auto_send_allowed(db, tenant_id, category_id)
    approval_status = "AUTO_SENT" if allowed else "PENDING_HUMAN_CONFIRMATION"

    draft = GiraffeJPOutboundMessageDraft(
        tenant_id=tenant_id,
        thread_id=thread_id,
        category_id=category_id,
        body=body,
        approval_status=approval_status,
    )
    db.add(draft)
    await db.flush()

    if allowed:
        log = GiraffeJPMessageDeliveryLog(
            tenant_id=tenant_id,
            draft_id=draft.id,
            channel="SIMULATED",
            delivery_status="SIMULATED",
        )
        db.add(log)
        await db.flush()
        await emit_event(
            db,
            event_type=event_types.OUTBOUND_MESSAGE_AUTO_SENT,
            payload={"draft_id": str(draft.id), "category_id": category_id},
            tenant_id=tenant_id,
            triggered_by_user_id=triggered_by_user_id,
        )
    else:
        await emit_event(
            db,
            event_type=event_types.OUTBOUND_MESSAGE_PENDING_APPROVAL,
            payload={"draft_id": str(draft.id), "category_id": category_id},
            tenant_id=tenant_id,
            triggered_by_user_id=triggered_by_user_id,
        )

    await emit_event(
        db,
        event_type=event_types.OUTBOUND_DRAFT_CREATED,
        payload={"draft_id": str(draft.id), "category_id": category_id, "auto_sent": allowed},
        tenant_id=tenant_id,
        triggered_by_user_id=triggered_by_user_id,
    )
    return draft


async def approve_draft(
    db: AsyncSession,
    draft_id: uuid.UUID,
    reviewed_by_user_id: uuid.UUID,
) -> GiraffeJPOutboundMessageDraft:
    result = await db.execute(
        select(GiraffeJPOutboundMessageDraft).where(
            GiraffeJPOutboundMessageDraft.id == draft_id
        )
    )
    draft = result.scalar_one_or_none()
    if draft is None:
        raise ValueError(f"Draft {draft_id} not found")
    if draft.approval_status != "PENDING_HUMAN_CONFIRMATION":
        raise ValueError(f"Draft is not pending approval (current status: {draft.approval_status})")

    draft.approval_status = "APPROVED"
    draft.reviewed_by_user_id = reviewed_by_user_id
    draft.reviewed_at = datetime.now(timezone.utc)
    await db.flush()

    log = GiraffeJPMessageDeliveryLog(
        tenant_id=draft.tenant_id,
        draft_id=draft.id,
        channel="SIMULATED",
        delivery_status="SIMULATED",
    )
    db.add(log)
    await db.flush()

    await emit_event(
        db,
        event_type=event_types.OUTBOUND_MESSAGE_APPROVED_SENT,
        payload={"draft_id": str(draft.id), "reviewed_by": str(reviewed_by_user_id)},
        tenant_id=draft.tenant_id,
        triggered_by_user_id=reviewed_by_user_id,
    )
    return draft


async def reject_draft(
    db: AsyncSession,
    draft_id: uuid.UUID,
    reviewed_by_user_id: uuid.UUID,
) -> GiraffeJPOutboundMessageDraft:
    result = await db.execute(
        select(GiraffeJPOutboundMessageDraft).where(
            GiraffeJPOutboundMessageDraft.id == draft_id
        )
    )
    draft = result.scalar_one_or_none()
    if draft is None:
        raise ValueError(f"Draft {draft_id} not found")
    if draft.approval_status != "PENDING_HUMAN_CONFIRMATION":
        raise ValueError(f"Draft is not pending rejection (current status: {draft.approval_status})")

    draft.approval_status = "REJECTED"
    draft.reviewed_by_user_id = reviewed_by_user_id
    draft.reviewed_at = datetime.now(timezone.utc)
    await db.flush()

    await emit_event(
        db,
        event_type=event_types.OUTBOUND_MESSAGE_REJECTED,
        payload={"draft_id": str(draft.id), "reviewed_by": str(reviewed_by_user_id)},
        tenant_id=draft.tenant_id,
        triggered_by_user_id=reviewed_by_user_id,
    )
    return draft
