import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db, get_current_user
from src.decision_packets.schemas import (
    DecisionPacketOut, DecisionOptionOut, ApproveOptionRequest
)
from src.decision_packets.service import (
    generate_decision_packet,
    approve_decision_option,
    get_latest_decision_packet,
    get_options_for_packet,
)
from src.approval_gates.schemas import ApprovalRequestOut
from src.db.models.decision import ApprovalRequest

from src.permissions.project_access import bind_request_actor

router = APIRouter(dependencies=[Depends(bind_request_actor)])


class GeneratePacketRequest:
    pass


from pydantic import BaseModel


class GeneratePacketBody(BaseModel):
    rfq_id: uuid.UUID


@router.post(
    "/projects/{project_id}/decision-packets",
    status_code=status.HTTP_201_CREATED,
)
async def create_decision_packet(
    project_id: uuid.UUID,
    body: GeneratePacketBody,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    packet, approval_id = await generate_decision_packet(
        db=db,
        project_id=project_id,
        rfq_id=body.rfq_id,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )
    await db.commit()
    await db.refresh(packet)
    options = await get_options_for_packet(db, packet.id)
    return {
        "packet": DecisionPacketOut(
            **{
                k: getattr(packet, k)
                for k in DecisionPacketOut.model_fields
                if k != "options" and hasattr(packet, k)
            },
            options=[DecisionOptionOut.model_validate(o) for o in options],
        ),
        "approval_request_id": str(approval_id),
    }


@router.get(
    "/projects/{project_id}/decision-packets/latest",
    response_model=DecisionPacketOut,
)
async def get_latest_packet(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    packet = await get_latest_decision_packet(db, project_id, current_user.tenant_id)
    if not packet:
        raise HTTPException(status_code=404, detail="No decision packet found")
    options = await get_options_for_packet(db, packet.id)
    return DecisionPacketOut(
        **{
            k: getattr(packet, k)
            for k in DecisionPacketOut.model_fields
            if k != "options" and hasattr(packet, k)
        },
        options=[DecisionOptionOut.model_validate(o) for o in options],
    )


@router.post("/decision-packets/{packet_id}/approve-option")
async def approve_option(
    packet_id: uuid.UUID,
    body: ApproveOptionRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    packet = await approve_decision_option(
        db=db,
        packet_id=packet_id,
        option_id=body.option_id,
        approval_id=body.approval_id,
        reviewed_by=current_user.id,
        review_notes=body.review_notes or "",
        tenant_id=current_user.tenant_id,
    )
    await db.commit()
    await db.refresh(packet)
    options = await get_options_for_packet(db, packet.id)
    return DecisionPacketOut(
        **{
            k: getattr(packet, k)
            for k in DecisionPacketOut.model_fields
            if k != "options" and hasattr(packet, k)
        },
        options=[DecisionOptionOut.model_validate(o) for o in options],
    )
