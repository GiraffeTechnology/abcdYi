from typing import Literal

OrderExecutionState = Literal[
    "ORDER_CONFIRMED",
    "SUPPLIER_ACCEPTANCE_PENDING",
    "SUPPLIER_ACCEPTED",
    "PRODUCTION_PLAN_CREATED",
    "MATERIAL_CONFIRMATION_PENDING",
    "MATERIAL_CONFIRMED",
    "PRODUCTION_STARTED",
    "MILESTONE_PENDING",
    "MILESTONE_MEDIA_REQUESTED",
    "MILESTONE_MEDIA_UPLOADED",
    "MILESTONE_BUYER_REVIEW_PENDING",
    "MILESTONE_CONFIRMED",
    "QC_PENDING",
    "QC_CONFIRMED",
    "PACKAGING_PENDING",
    "PACKAGING_CONFIRMED",
    "LOGISTICS_HANDOVER_PENDING",
    "LOGISTICS_HANDOVER_RECEIVED",
    "IN_TRANSIT",
    "CUSTOMS",
    "OUT_FOR_DELIVERY",
    "DELIVERED",
    "BUYER_SIGNOFF_PENDING",
    "BUYER_SIGNED_OFF",
    "ORDER_CLOSED",
    "EXCEPTION_RAISED",
    "EXCEPTION_RESOLUTION_PENDING",
    "EXCEPTION_RESOLVED",
    "CANCELLED",
]

# Logistics status → order state mapping
_LOGISTICS_TO_ORDER: dict[str, str] = {
    "label_created": "LOGISTICS_HANDOVER_RECEIVED",
    "picked_up": "IN_TRANSIT",
    "in_transit": "IN_TRANSIT",
    "customs": "CUSTOMS",
    "out_for_delivery": "OUT_FOR_DELIVERY",
    "delivered": "DELIVERED",
    "exception": "EXCEPTION_RAISED",
}


def logistics_status_to_order_state(normalized_status: str) -> str | None:
    return _LOGISTICS_TO_ORDER.get(normalized_status)
