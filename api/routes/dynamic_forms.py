import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from api.deps import get_db, get_current_user
from src.dynamic_forms import service
from src.dynamic_forms.schemas import (
    DynamicFormCreateRequest,
    DynamicFormFieldUpdate,
    DynamicFormVersionOut,
    ClarificationQuestionCreate,
)

router = APIRouter()


@router.post(
    "/projects/{project_id}/dynamic-forms",
    status_code=status.HTTP_201_CREATED,
    response_model=DynamicFormVersionOut,
)
async def create_dynamic_form(
    project_id: uuid.UUID,
    data: DynamicFormCreateRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    version = await service.create_dynamic_form_from_inquiry(
        db,
        project_id=project_id,
        inquiry_id=data.inquiry_id,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )
    if version is None:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    await db.commit()
    return DynamicFormVersionOut.model_validate(version)


@router.get(
    "/projects/{project_id}/dynamic-forms/current",
    response_model=DynamicFormVersionOut,
)
async def get_current_form(
    project_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    version = await service.get_current_form(db, project_id)
    if not version:
        raise HTTPException(status_code=404, detail="No form found for this project")
    return DynamicFormVersionOut.model_validate(version)


@router.patch("/dynamic-forms/{form_id}", response_model=DynamicFormVersionOut)
async def update_form_fields(
    form_id: uuid.UUID,
    data: DynamicFormFieldUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        version = await service.update_form_fields(
            db=db,
            form_id=form_id,
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            field_updates=data.field_updates,
            confirmed_fields=data.confirmed_fields,
        )
    except ValueError as e:
        if "locked" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Form is locked after order confirmation.",
            )
        raise HTTPException(status_code=400, detail=str(e))

    if version is None:
        raise HTTPException(status_code=404, detail="Form not found")
    await db.commit()
    return DynamicFormVersionOut.model_validate(version)


@router.post("/dynamic-forms/{form_id}/versions", response_model=list[DynamicFormVersionOut])
async def list_form_versions(
    form_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    versions = await service.get_form_versions(db, form_id)
    return [DynamicFormVersionOut.model_validate(v) for v in versions]


@router.post("/dynamic-forms/{form_id}/clarification-questions", status_code=status.HTTP_201_CREATED)
async def add_clarification_question(
    form_id: uuid.UUID,
    data: ClarificationQuestionCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        question = await service.add_clarification_question(
            db, form_id, data.question_text, data.field_reference
        )
    except ValueError as e:
        if "locked" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Form is locked after order confirmation.",
            )
        raise HTTPException(status_code=400, detail=str(e))

    if question is None:
        raise HTTPException(status_code=404, detail="Form not found")
    await db.commit()
    return {
        "id": str(question.id),
        "form_id": str(question.form_id),
        "question_text": question.question_text,
        "field_reference": question.field_reference,
        "status": question.status,
    }


@router.post("/dynamic-forms/{form_id}/lock")
async def lock_form(
    form_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    form = await service.lock_form(db, form_id)
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    await db.commit()
    return {"id": str(form.id), "is_locked": form.is_locked}
