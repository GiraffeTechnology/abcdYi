"""Platform-level operations coordinating projects, inquiries, and form generation."""
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from src.projects.service import create_project, import_buyer_inquiry
from src.dynamic_forms.service import create_dynamic_form_from_inquiry
from src.projects.schemas import ProjectCreate, BuyerInquiryCreate


async def create_project_with_inquiry(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    title: str,
    raw_text: str,
    source_channel: str = "manual",
):
    """Create project, import inquiry, and trigger form generation in one operation."""
    project_data = ProjectCreate(title=title)
    project = await create_project(db, tenant_id, user_id, project_data)

    inquiry_data = BuyerInquiryCreate(raw_text=raw_text, source_channel=source_channel)
    inquiry = await import_buyer_inquiry(db, project.id, user_id, tenant_id, inquiry_data)

    form_version = await create_dynamic_form_from_inquiry(
        db, project.id, inquiry.id, tenant_id, user_id
    )
    return {"project": project, "inquiry": inquiry, "form_version": form_version}
