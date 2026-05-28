from typing import Literal

CommunicationDirection = Literal["INBOUND", "OUTBOUND", "INTERNAL"]

MessagePurpose = Literal[
    "buyer_inquiry_received",
    "main_supplier_clarification_to_buyer",
    "upstream_inquiry_to_supplier",
    "upstream_response_received",
    "upstream_option_approval_request",
    "supplier_response_rollup_to_buyer",
    "buyer_rollup_confirmation",
    "production_progress_update",
    "media_upload_request",
    "qc_update",
    "logistics_handover",
    "tracking_update",
    "buyer_signoff_request",
    "buyer_signoff_response",
    "exception_report",
    "system_reminder",
    "unknown",
]
