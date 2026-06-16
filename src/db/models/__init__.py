from src.db.models.tenant import Tenant
from src.db.models.user import User, UserRole
from src.db.models.audit import AuditLog
from src.db.models.participant import (
    Participant, ParticipantRole, ParticipantProfile,
    ParticipantCapability, ParticipantPermission
)
from src.db.models.project import Project, BuyerInquiry, RawMessage
from src.db.models.procurement_edge import ProcurementEdge
from src.db.models.dynamic_form import (
    DynamicOrderForm, DynamicOrderFormVersion, ClarificationQuestion
)
from src.db.models.matching import ParticipantMatch
from src.db.models.rfq import RFQ, RFQRecipient, SupplierResponse, SupplierResponsePacket
from src.db.models.decision import DecisionPacket, DecisionOption, ApprovalRequest
from src.db.models.order import Order, OrderLine
from src.db.models.production import (
    Milestone, ProductionUpdate, ProductionMonitoringPacket, ExpediteAlert
)
from src.db.models.qc import QCStandard, QCRecord
from src.db.models.logistics import (
    QualityIncident, ReplacementAlert, Shipment,
    ShipmentTrackingEvent, SupplierMemoryRecord
)
from src.db.models.execution_graph import ExecutionEvent, UploadedFileMetadata
from src.db.models.delivery_feasibility import DeliveryFeasibilityPacketRecord

# Actor-based (M-side / GLTG role-switching) schema — coexists alongside the
# UUID-based core schema above. Names that collide with the core schema are
# imported under an "Upstream"/"Actor" alias to keep both tables registered.
from src.db.models.actor import Actor
from src.db.models.approval import ApprovalRequest as UpstreamApprovalRequest
from src.db.models.artifact import Artifact
from src.db.models.cad_cnc import (
    CADRequirementPacket, ManufacturingFeatureSet, CADCNCMatchResult, CapabilityFitReport
)
from src.db.models.capability import ShopCapabilityProfile
from src.db.models.dynamic_schema import (
    SchemaRegistry, FieldDefinition, ObservedField, FieldProposal,
    EntityDynamicValue, FieldAlias, UnitDictionary, FieldPromotionDecision
)
from src.db.models.execution_event import ExecutionEvent as ActorExecutionEvent
from src.db.models.im_message import ChannelSession, Message
from src.db.models.inquiry import SupplierInquiry
from src.db.models.legal_notice import LegalNotice
from src.db.models.merchandiser import (
    MerchandiserExecutionPlan, MerchandiserTask, OrderMilestoneORM,
    MediaEvidenceORM, OrderExceptionORM
)
from src.db.models.requirement import StructuredRequirement
from src.db.models.response import SupplierResponse as UpstreamSupplierResponse
from src.db.models.role_context import RoleContext
from src.db.models.rollup import SupplierResponseRollup
from src.db.models.supplier_memory import SupplierScoreSnapshot, SupplierProfileUpdate
from src.db.models.upstream import (
    DependencyNeed, UpstreamInquiry, UpstreamResponse, UpstreamOption
)

__all__ = [
    "Tenant", "User", "UserRole", "AuditLog",
    "Participant", "ParticipantRole", "ParticipantProfile",
    "ParticipantCapability", "ParticipantPermission",
    "Project", "ProcurementEdge", "BuyerInquiry", "RawMessage",
    "DynamicOrderForm", "DynamicOrderFormVersion", "ClarificationQuestion",
    "ParticipantMatch",
    "RFQ", "RFQRecipient", "SupplierResponse", "SupplierResponsePacket",
    "DecisionPacket", "DecisionOption", "ApprovalRequest",
    "Order", "OrderLine",
    "Milestone", "ProductionUpdate", "ProductionMonitoringPacket", "ExpediteAlert",
    "QCStandard", "QCRecord",
    "QualityIncident", "ReplacementAlert", "Shipment",
    "ShipmentTrackingEvent", "SupplierMemoryRecord",
    "ExecutionEvent", "UploadedFileMetadata",
    "DeliveryFeasibilityPacketRecord",
    "Actor", "UpstreamApprovalRequest", "Artifact",
    "CADRequirementPacket", "ManufacturingFeatureSet", "CADCNCMatchResult", "CapabilityFitReport",
    "ShopCapabilityProfile",
    "SchemaRegistry", "FieldDefinition", "ObservedField", "FieldProposal",
    "EntityDynamicValue", "FieldAlias", "UnitDictionary", "FieldPromotionDecision",
    "ActorExecutionEvent",
    "ChannelSession", "Message",
    "SupplierInquiry",
    "LegalNotice",
    "MerchandiserExecutionPlan", "MerchandiserTask", "OrderMilestoneORM",
    "MediaEvidenceORM", "OrderExceptionORM",
    "StructuredRequirement",
    "UpstreamSupplierResponse",
    "RoleContext",
    "SupplierResponseRollup",
    "SupplierScoreSnapshot", "SupplierProfileUpdate",
    "DependencyNeed", "UpstreamInquiry", "UpstreamResponse", "UpstreamOption",
]
