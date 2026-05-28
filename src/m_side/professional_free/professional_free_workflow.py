"""
Professional Free Workflow Orchestrator — ties all Phase 4 modules together.
"""

from src.m_side.professional_free.product_flags import PROFESSIONAL_FREE_FEATURES, assert_enterprise_cap_disabled
from src.m_side.professional_free.file_policy import get_professional_free_file_policy, show_file_warning, acknowledge_cap_limitation
from src.m_side.professional_free.cad_requirement_packet import CADRequirementPacket, create_cad_requirement_packet
from src.integrations.machinacheck_embedded.embedded_assessor import assess_from_file_refs
from src.integrations.machinacheck_embedded.feature_extractor import ManufacturingFeatureSet
from src.m_side.capability_profiles.shop_capability_profile import ShopCapabilityProfile
from src.m_side.professional_free.cad_cnc_matcher import CADCNCMachiningMatchResult, match_cad_to_cnc_capability
from src.m_side.professional_free.capability_fit_report import CapabilityFitReport, generate_capability_fit_report
from src.m_side.dependencies.dependency_planner import DependencyNeed, plan_dependencies_from_cad_cnc_match


def run_cad_cnc_assessment(
    project_id: str,
    original_buyer_actor_id: str,
    main_supplier_actor_id: str,
    buyer_input: dict,
    shop_profile: ShopCapabilityProfile,
) -> tuple[CADRequirementPacket, ManufacturingFeatureSet, CADCNCMachiningMatchResult, CapabilityFitReport, list[DependencyNeed]]:
    """
    Run the complete Professional Free CAD-to-CNC assessment workflow:
    1. Show file warning
    2. Create CAD Requirement Packet
    3. Extract manufacturing features
    4. Match against shop capability
    5. Generate fit report
    6. Plan dependencies from gaps
    """
    assert_enterprise_cap_disabled()

    show_file_warning(project_id, main_supplier_actor_id)
    acknowledge_cap_limitation(project_id, main_supplier_actor_id)

    packet = create_cad_requirement_packet(
        project_id=project_id,
        original_buyer_actor_id=original_buyer_actor_id,
        main_supplier_actor_id=main_supplier_actor_id,
        buyer_input=buyer_input,
    )

    feature_set = assess_from_file_refs(packet)

    match_result = match_cad_to_cnc_capability(packet, feature_set, shop_profile)

    fit_report = generate_capability_fit_report(match_result)

    dependencies = plan_dependencies_from_cad_cnc_match(
        project_id=project_id,
        match_result=match_result,
        main_supplier_actor_id=main_supplier_actor_id,
    )

    return packet, feature_set, match_result, fit_report, dependencies
