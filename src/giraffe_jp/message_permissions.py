import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db.models.giraffe_jp import GiraffeJPMessageCategoryPermission

# 22 default message categories: 8 customer, 7 supplier, 7 model partner.
# auto_send=True for routine transactional notifications;
# auto_send=False for anything requiring human review before sending.
DEFAULT_CATEGORIES: list[dict] = [
    # Customer
    {"category_id": "CUST_ORDER_CONFIRMATION", "category_name": "Order Confirmation", "party_type": "CUSTOMER", "channel": "EMAIL", "auto_send": True},
    {"category_id": "CUST_MEASUREMENT_REQUEST", "category_name": "Measurement Collection Request", "party_type": "CUSTOMER", "channel": "EMAIL", "auto_send": True},
    {"category_id": "CUST_QC_RESULT_NOTIFICATION", "category_name": "Quality Evidence Review Result", "party_type": "CUSTOMER", "channel": "EMAIL", "auto_send": True},
    {"category_id": "CUST_DELIVERY_SCHEDULE_UPDATE", "category_name": "Delivery Schedule Update", "party_type": "CUSTOMER", "channel": "EMAIL", "auto_send": True},
    {"category_id": "CUST_FITTING_APPOINTMENT", "category_name": "Fitting Appointment Reminder", "party_type": "CUSTOMER", "channel": "EMAIL", "auto_send": True},
    {"category_id": "CUST_ALTERATION_REQUEST", "category_name": "Alteration Request Acknowledgment", "party_type": "CUSTOMER", "channel": "EMAIL", "auto_send": False},
    {"category_id": "CUST_PAYMENT_REMINDER", "category_name": "Payment Reminder", "party_type": "CUSTOMER", "channel": "EMAIL", "auto_send": False},
    {"category_id": "CUST_WELCOME_MESSAGE", "category_name": "Welcome Message", "party_type": "CUSTOMER", "channel": "EMAIL", "auto_send": True},
    # Supplier
    {"category_id": "SUPP_PRODUCTION_BRIEF", "category_name": "Production Brief", "party_type": "SUPPLIER", "channel": "EMAIL", "auto_send": True},
    {"category_id": "SUPP_MATERIAL_SPECIFICATION", "category_name": "Material Specification", "party_type": "SUPPLIER", "channel": "EMAIL", "auto_send": True},
    {"category_id": "SUPP_QC_EVIDENCE_REQUEST", "category_name": "Quality Evidence Request", "party_type": "SUPPLIER", "channel": "EMAIL", "auto_send": True},
    {"category_id": "SUPP_PRODUCTION_TIMELINE_CONFIRM", "category_name": "Production Timeline Confirmation", "party_type": "SUPPLIER", "channel": "EMAIL", "auto_send": True},
    {"category_id": "SUPP_DEFECT_REPORT", "category_name": "Defect Report", "party_type": "SUPPLIER", "channel": "EMAIL", "auto_send": False},
    {"category_id": "SUPP_SHIPMENT_INSTRUCTION", "category_name": "Shipment Instruction", "party_type": "SUPPLIER", "channel": "EMAIL", "auto_send": False},
    {"category_id": "SUPP_INVOICE_REQUEST", "category_name": "Invoice Request", "party_type": "SUPPLIER", "channel": "EMAIL", "auto_send": True},
    # Model Partner
    {"category_id": "MP_TRY_ON_APPOINTMENT", "category_name": "Try-On Appointment Scheduling", "party_type": "MODEL_PARTNER", "channel": "EMAIL", "auto_send": True},
    {"category_id": "MP_FIT_REVIEW_REQUEST", "category_name": "Fit Review Request", "party_type": "MODEL_PARTNER", "channel": "EMAIL", "auto_send": True},
    {"category_id": "MP_PHOTO_EVIDENCE_REQUEST", "category_name": "Photo Evidence Request", "party_type": "MODEL_PARTNER", "channel": "EMAIL", "auto_send": True},
    {"category_id": "MP_COMPENSATION_NOTICE", "category_name": "Compensation Notice", "party_type": "MODEL_PARTNER", "channel": "EMAIL", "auto_send": False},
    {"category_id": "MP_FITTING_FEEDBACK", "category_name": "Fitting Feedback Request", "party_type": "MODEL_PARTNER", "channel": "EMAIL", "auto_send": True},
    {"category_id": "MP_SCHEDULE_CHANGE", "category_name": "Schedule Change Notification", "party_type": "MODEL_PARTNER", "channel": "EMAIL", "auto_send": True},
    {"category_id": "MP_ENGAGEMENT_BRIEF", "category_name": "Engagement Brief", "party_type": "MODEL_PARTNER", "channel": "EMAIL", "auto_send": True},
]


async def seed_default_permissions(
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> list[GiraffeJPMessageCategoryPermission]:
    result = await db.execute(
        select(GiraffeJPMessageCategoryPermission).where(
            GiraffeJPMessageCategoryPermission.tenant_id == tenant_id
        )
    )
    existing = {p.category_id for p in result.scalars().all()}

    created: list[GiraffeJPMessageCategoryPermission] = []
    for cat in DEFAULT_CATEGORIES:
        if cat["category_id"] not in existing:
            perm = GiraffeJPMessageCategoryPermission(
                tenant_id=tenant_id,
                category_id=cat["category_id"],
                category_name=cat["category_name"],
                party_type=cat["party_type"],
                channel=cat["channel"],
                auto_send=cat["auto_send"],
            )
            db.add(perm)
            created.append(perm)

    await db.flush()
    return created


async def is_auto_send_allowed(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    category_id: str,
    channel: str | None = None,
) -> bool:
    result = await db.execute(
        select(GiraffeJPMessageCategoryPermission).where(
            GiraffeJPMessageCategoryPermission.tenant_id == tenant_id,
            GiraffeJPMessageCategoryPermission.category_id == category_id,
        )
    )
    perm = result.scalar_one_or_none()
    # Spec rule 7: unknown categories must default to auto_send=False
    if perm is None:
        return False
    return perm.auto_send
