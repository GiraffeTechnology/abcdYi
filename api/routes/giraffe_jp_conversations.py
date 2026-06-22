import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from api.deps import get_current_user, get_db
from src.db.models.user import User
from src.db.models.giraffe_jp import (
    GiraffeJPConversationThread,
    GiraffeJPOutboundMessageDraft,
)
from src.giraffe_jp.schemas import (
    ConversationThreadCreate,
    ConversationThreadRead,
    InboundMessageCreate,
    MessageRead,
    OutboundDraftCreate,
    OutboundDraftRead,
)
from src.giraffe_jp.communication import (
    create_thread,
    record_inbound_message,
    create_outbound_draft,
    approve_draft,
    reject_draft,
)

router = APIRouter()


@router.post("/conversations", response_model=ConversationThreadRead, status_code=201)
async def create_conversation(
    body: ConversationThreadCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    thread = await create_thread(
        db,
        tenant_id=current_user.tenant_id,
        party_type=body.party_type,
        project_id=body.project_id,
        party_ref_id=body.party_ref_id,
        thread_type=body.thread_type,
        subject=body.subject,
        triggered_by_user_id=current_user.id,
    )
    await db.commit()
    await db.refresh(thread)
    return thread


@router.get("/conversations", response_model=list[ConversationThreadRead])
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(GiraffeJPConversationThread)
        .where(GiraffeJPConversationThread.tenant_id == current_user.tenant_id)
        .order_by(GiraffeJPConversationThread.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/conversations/{thread_id}", response_model=ConversationThreadRead)
async def get_conversation(
    thread_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(GiraffeJPConversationThread).where(
            GiraffeJPConversationThread.id == thread_id,
            GiraffeJPConversationThread.tenant_id == current_user.tenant_id,
        )
    )
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=404, detail="Conversation thread not found")
    return thread


@router.post("/conversations/{thread_id}/messages/inbound", response_model=MessageRead, status_code=201)
async def record_inbound(
    thread_id: uuid.UUID,
    body: InboundMessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(GiraffeJPConversationThread).where(
            GiraffeJPConversationThread.id == thread_id,
            GiraffeJPConversationThread.tenant_id == current_user.tenant_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Conversation thread not found")

    msg = await record_inbound_message(
        db,
        tenant_id=current_user.tenant_id,
        thread_id=thread_id,
        body=body.body,
        sender_ref=body.sender_ref,
        message_metadata=body.message_metadata,
        triggered_by_user_id=current_user.id,
    )
    await db.commit()
    await db.refresh(msg)
    return msg


@router.post("/conversations/{thread_id}/outbound-drafts", response_model=OutboundDraftRead, status_code=201)
async def create_draft(
    thread_id: uuid.UUID,
    body: OutboundDraftCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(GiraffeJPConversationThread).where(
            GiraffeJPConversationThread.id == thread_id,
            GiraffeJPConversationThread.tenant_id == current_user.tenant_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Conversation thread not found")

    draft = await create_outbound_draft(
        db,
        tenant_id=current_user.tenant_id,
        thread_id=thread_id,
        category_id=body.category_id,
        body=body.body,
        triggered_by_user_id=current_user.id,
    )
    await db.commit()
    await db.refresh(draft)
    return draft


@router.get("/conversations/{thread_id}/outbound-drafts", response_model=list[OutboundDraftRead])
async def list_drafts(
    thread_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(GiraffeJPOutboundMessageDraft).where(
            GiraffeJPOutboundMessageDraft.thread_id == thread_id,
            GiraffeJPOutboundMessageDraft.tenant_id == current_user.tenant_id,
        ).order_by(GiraffeJPOutboundMessageDraft.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/outbound-drafts/{draft_id}/approve", response_model=OutboundDraftRead)
async def approve(
    draft_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        draft = await approve_draft(db, draft_id=draft_id, reviewed_by_user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    await db.refresh(draft)
    return draft


@router.post("/outbound-drafts/{draft_id}/reject", response_model=OutboundDraftRead)
async def reject(
    draft_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        draft = await reject_draft(db, draft_id=draft_id, reviewed_by_user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    await db.refresh(draft)
    return draft
