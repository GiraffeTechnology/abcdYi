"""
CAD-to-CNC Matcher — compares buyer CAD requirements with shop machining capability.
"""

import uuid
from typing import Literal
from pydantic import BaseModel, Field

from src.m_side.professional_free.cad_requirement_packet import CADRequirementPacket
from src.integrations.machinacheck_embedded.feature_extractor import ManufacturingFeatureSet
from src.m_side.capability_profiles.shop_capability_profile import ShopCapabilityProfile
from src.m_side.m_event_logger import log_m_event


class CADCNCMachiningMatchResult(BaseModel):
    match_id: str
    project_id: str
    actor_id: str
    can_make_in_house: bool
    recommended_machine_ids: list[str] = Field(default_factory=list)
    machine_fit_score: float = 0.0
    work_envelope_fit: Literal["fit", "not_fit", "unknown"] = "unknown"
    material_fit: Literal["in_stock", "purchasable", "not_supported", "unknown"] = "unknown"
    tolerance_fit: Literal["fit", "marginal", "not_fit", "unknown"] = "unknown"
    surface_finish_fit: Literal["fit", "requires_external_process", "not_fit", "unknown"] = "unknown"
    tooling_fit: Literal["fit", "setup_required", "missing", "unknown"] = "unknown"
    qc_fit: Literal["fit", "external_qc_required", "missing", "unknown"] = "unknown"
    schedule_fit: Literal["fit", "limited", "not_fit", "unknown"] = "unknown"
    required_upstream_dependencies: list[str] = Field(default_factory=list)
    required_subcontract_dependencies: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    confidence_score: float = 0.0
    explanation: str = ""


def _check_work_envelope(
    feature_set: ManufacturingFeatureSet,
    shop: ShopCapabilityProfile,
) -> tuple[Literal["fit", "not_fit", "unknown"], list[str]]:
    env = feature_set.work_envelope_required
    if not env:
        return "unknown", []

    length = env.get("length_mm", 0)
    width = env.get("width_mm", 0)
    height = env.get("height_mm", 0)

    if not length and not width and not height:
        return "unknown", []

    for machine in shop.machines:
        if machine.can_fit_part(length or 0, width or 0, height or 0):
            return "fit", []

    return "not_fit", [f"Part dimensions ({length}x{width}x{height}mm) exceed all available machine envelopes"]


def _check_material(
    feature_set: ManufacturingFeatureSet,
    shop: ShopCapabilityProfile,
) -> tuple[Literal["in_stock", "purchasable", "not_supported", "unknown"], list[str]]:
    material = feature_set.material_required
    if not material:
        return "unknown", []

    if shop.has_material_in_stock(material):
        return "in_stock", []

    if shop.material_is_supported(material):
        return "purchasable", [f"Material '{material}' not in stock — purchase required"]

    return "not_supported", [f"Material '{material}' not supported by any shop machine"]


def _check_tolerance(
    feature_set: ManufacturingFeatureSet,
    shop: ShopCapabilityProfile,
) -> tuple[Literal["fit", "marginal", "not_fit", "unknown"], list[str]]:
    tol_class = feature_set.tolerance_class
    tol_req = {}
    if tol_class == "unknown":
        return "unknown", []

    # Get numeric tolerance from feature set work_envelope or tolerance class
    tol_map = {"standard": 0.1, "medium": 0.05, "tight": 0.01}
    required_tol = tol_map.get(tol_class, 0.1)

    best_machine_tol = None
    for m in shop.machines:
        if m.best_tolerance_mm is not None:
            if best_machine_tol is None or m.best_tolerance_mm < best_machine_tol:
                best_machine_tol = m.best_tolerance_mm

    if best_machine_tol is None:
        return "unknown", []

    if required_tol >= best_machine_tol * 2:
        return "fit", []
    elif required_tol >= best_machine_tol:
        return "marginal", [f"Tolerance {required_tol}mm is close to machine limit {best_machine_tol}mm — QC review recommended"]
    else:
        return "not_fit", [f"Required tolerance {required_tol}mm tighter than best machine capability {best_machine_tol}mm"]


def _check_surface_finish(
    feature_set: ManufacturingFeatureSet,
    shop: ShopCapabilityProfile,
) -> tuple[Literal["fit", "requires_external_process", "not_fit", "unknown"], list[str]]:
    sf_class = feature_set.surface_finish_class
    if sf_class == "unknown" or sf_class == "standard":
        return "fit", []

    if sf_class == "mirror":
        if shop.can_do_process_in_house("surface_polishing") or shop.can_do_process_in_house("polishing"):
            return "fit", []
        return "requires_external_process", ["Mirror surface finish requires external polishing process"]

    if sf_class == "fine":
        if shop.can_do_process_in_house("fine_finishing") or shop.can_do_process_in_house("grinding"):
            return "fit", []
        return "requires_external_process", ["Fine surface finish may require external grinding/polishing"]

    return "fit", []


def _check_tooling(
    feature_set: ManufacturingFeatureSet,
    shop: ShopCapabilityProfile,
) -> tuple[Literal["fit", "setup_required", "missing", "unknown"], list[str]]:
    if not shop.tooling_inventory:
        return "unknown", []

    processes = feature_set.required_processes
    if not processes:
        return "unknown", []

    # Check if tooling inventory covers required operations
    available_types = {k.lower() for k in shop.tooling_inventory.keys()}
    missing_tooling = []
    for process in processes:
        if process in ("cnc_milling", "cnc_turning", "grinding"):
            if not any(process.replace("cnc_", "") in t or process in t for t in available_types):
                missing_tooling.append(process)

    if not missing_tooling:
        return "fit", []
    if len(missing_tooling) < len(processes):
        return "setup_required", [f"Some tooling setup required for: {', '.join(missing_tooling)}"]
    return "missing", [f"Tooling missing for: {', '.join(missing_tooling)}"]


def _check_qc(
    feature_set: ManufacturingFeatureSet,
    shop: ShopCapabilityProfile,
) -> tuple[Literal["fit", "external_qc_required", "missing", "unknown"], list[str]]:
    qc_needed = feature_set.qc_required
    if not qc_needed:
        return "fit", []

    if not shop.qc_equipment:
        if qc_needed:
            return "missing", ["No QC equipment registered in shop profile"]
        return "unknown", []

    unmet = []
    for qc_type in qc_needed:
        if not shop.has_qc_capability(qc_type):
            unmet.append(qc_type)

    if not unmet:
        return "fit", []
    if "cmm_inspection" in unmet or "dimensional_check" in unmet:
        return "external_qc_required", [f"External QC required for: {', '.join(unmet)}"]
    return "external_qc_required", [f"QC capability missing: {', '.join(unmet)}"]


def _check_schedule(
    feature_set: ManufacturingFeatureSet,
    shop: ShopCapabilityProfile,
) -> tuple[Literal["fit", "limited", "not_fit", "unknown"], list[str]]:
    schedule = shop.schedule_summary
    if not schedule:
        # Check machines
        statuses = [m.schedule_status for m in shop.machines]
        if not statuses:
            return "unknown", []
        if all(s == "busy" for s in statuses):
            return "not_fit", ["All machines busy"]
        if any(s == "busy" for s in statuses) or any(s == "limited" for s in statuses):
            return "limited", ["Some machine capacity limited"]
        return "fit", []

    status = schedule.get("status", "unknown")
    if status == "available":
        return "fit", []
    elif status in ("limited", "partial"):
        return "limited", ["Limited capacity — subcontractor backup recommended"]
    elif status == "busy":
        return "not_fit", ["Shop at full capacity"]
    return "unknown", []


def _check_axis_requirement(
    feature_set: ManufacturingFeatureSet,
    shop: ShopCapabilityProfile,
) -> tuple[bool, list[str]]:
    """Returns (can_meet_axis_req, subcontract_deps_needed)"""
    needed = feature_set.min_axis_requirement or 3
    capable_machines = shop.get_best_machines_for(axis_count=needed)
    if capable_machines:
        return True, []
    return False, [f"{needed}_axis_machining"]


def match_cad_to_cnc_capability(
    packet: CADRequirementPacket,
    feature_set: ManufacturingFeatureSet,
    shop_profile: ShopCapabilityProfile,
) -> CADCNCMachiningMatchResult:
    """
    Compare buyer CAD requirements with shop machining capability.
    Returns a match result with fit scores and identified dependency gaps.
    """
    project_id = packet.project_id
    actor_id = shop_profile.actor_id

    log_m_event(
        event_type="CAD_CNC_MATCH_STARTED",
        b_workspace_id=project_id,
        supplier_id=actor_id,
        payload={"packet_id": packet.packet_id, "feature_set_id": feature_set.feature_set_id},
    )

    risk_flags: list[str] = list(feature_set.risk_flags)
    missing_info: list[str] = list(feature_set.missing_information)
    upstream_deps: list[str] = []
    subcontract_deps: list[str] = []
    explanations: list[str] = []

    # 1. Work envelope check
    envelope_fit, envelope_risks = _check_work_envelope(feature_set, shop_profile)
    risk_flags.extend(envelope_risks)
    if envelope_fit == "not_fit":
        subcontract_deps.append("large_part_subcontract")
        explanations.append(f"Work envelope: NOT FIT — {'; '.join(envelope_risks)}")
    else:
        explanations.append(f"Work envelope: {envelope_fit.upper()}")

    # 2. Axis requirement check
    axis_ok, axis_subcontracts = _check_axis_requirement(feature_set, shop_profile)
    if not axis_ok:
        subcontract_deps.extend(axis_subcontracts)
        risk_flags.append(f"axis_requirement_not_met_{feature_set.min_axis_requirement}axis")
        explanations.append(f"Axis requirement: NOT MET — {feature_set.min_axis_requirement}-axis required")
    else:
        explanations.append(f"Axis requirement: {feature_set.min_axis_requirement or 3}-axis available")

    # 3. Material check
    material_fit, mat_risks = _check_material(feature_set, shop_profile)
    risk_flags.extend(mat_risks)
    if material_fit == "purchasable":
        upstream_deps.append("raw_material")
        explanations.append(f"Material: PURCHASABLE — {'; '.join(mat_risks)}")
    elif material_fit == "not_supported":
        upstream_deps.append("alternative_material_supplier")
        risk_flags.append(f"material_not_supported_{feature_set.material_required}")
        explanations.append(f"Material: NOT SUPPORTED — {'; '.join(mat_risks)}")
    else:
        explanations.append(f"Material: {material_fit.upper()}")

    # 4. Tolerance check
    tol_fit, tol_risks = _check_tolerance(feature_set, shop_profile)
    risk_flags.extend(tol_risks)
    if tol_fit == "marginal":
        upstream_deps.append("qc_review")
        explanations.append(f"Tolerance: MARGINAL — {'; '.join(tol_risks)}")
    elif tol_fit == "not_fit":
        subcontract_deps.append("precision_machining_subcontract")
        explanations.append(f"Tolerance: NOT FIT — {'; '.join(tol_risks)}")
    else:
        explanations.append(f"Tolerance: {tol_fit.upper()}")

    # 5. Surface finish check
    sf_fit, sf_risks = _check_surface_finish(feature_set, shop_profile)
    risk_flags.extend(sf_risks)
    if sf_fit == "requires_external_process":
        subcontract_deps.append("surface_treatment")
        explanations.append(f"Surface finish: EXTERNAL PROCESS — {'; '.join(sf_risks)}")
    else:
        explanations.append(f"Surface finish: {sf_fit.upper()}")

    # 6. Heat treatment check
    if feature_set.heat_treatment_required:
        if not shop_profile.can_do_process_in_house("heat_treatment"):
            subcontract_deps.append("heat_treatment")
            explanations.append("Heat treatment: OUTSOURCE REQUIRED")
        else:
            explanations.append("Heat treatment: IN-HOUSE")

    # 7. Tooling check
    tooling_fit, tool_risks = _check_tooling(feature_set, shop_profile)
    risk_flags.extend(tool_risks)
    if tooling_fit in ("missing", "setup_required"):
        explanations.append(f"Tooling: {tooling_fit.upper()} — {'; '.join(tool_risks)}")
    else:
        explanations.append(f"Tooling: {tooling_fit.upper()}")

    # 8. QC check
    qc_fit, qc_risks = _check_qc(feature_set, shop_profile)
    risk_flags.extend(qc_risks)
    if qc_fit == "external_qc_required":
        upstream_deps.append("qc_testing")
        explanations.append(f"QC: EXTERNAL REQUIRED — {'; '.join(qc_risks)}")
    elif qc_fit == "missing":
        upstream_deps.append("qc_testing")
        explanations.append("QC: MISSING — external QC provider required")
    else:
        explanations.append(f"QC: {qc_fit.upper()}")

    # 9. Schedule check
    schedule_fit, sched_risks = _check_schedule(feature_set, shop_profile)
    risk_flags.extend(sched_risks)
    if schedule_fit == "limited":
        subcontract_deps.append("backup_subcontract_capacity")
        explanations.append(f"Schedule: LIMITED — {'; '.join(sched_risks)}")
    elif schedule_fit == "not_fit":
        subcontract_deps.append("subcontract_full_job")
        explanations.append("Schedule: NOT FIT — full subcontracting required")
    else:
        explanations.append(f"Schedule: {schedule_fit.upper()}")

    # Recommended machines
    needed_axes = feature_set.min_axis_requirement or 3
    material = feature_set.material_required
    recommended = shop_profile.get_best_machines_for(axis_count=needed_axes, material=material)
    if not recommended:
        recommended = shop_profile.get_best_machines_for(axis_count=needed_axes)
    recommended_ids = [m.machine_id for m in recommended]

    # can_make_in_house
    blocking_issues = [
        envelope_fit == "not_fit",
        not axis_ok,
        material_fit == "not_supported",
        tol_fit == "not_fit",
        schedule_fit == "not_fit",
    ]
    can_make_in_house = not any(blocking_issues)

    # Machine fit score
    fit_scores = [
        1.0 if envelope_fit == "fit" else (0.5 if envelope_fit == "unknown" else 0.0),
        1.0 if axis_ok else 0.0,
        1.0 if material_fit == "in_stock" else (0.7 if material_fit == "purchasable" else 0.0),
        1.0 if tol_fit == "fit" else (0.5 if tol_fit == "marginal" else 0.0),
        1.0 if sf_fit == "fit" else (0.3 if sf_fit == "requires_external_process" else 0.0),
        1.0 if qc_fit == "fit" else (0.3 if qc_fit == "external_qc_required" else 0.0),
        1.0 if schedule_fit == "fit" else (0.5 if schedule_fit == "limited" else 0.0),
    ]
    machine_fit_score = round(sum(fit_scores) / len(fit_scores), 3)

    # Confidence
    missing_penalty = len(missing_info) * 0.05
    confidence = round(max(0.0, min(1.0, machine_fit_score - missing_penalty)), 3)

    result = CADCNCMachiningMatchResult(
        match_id=f"MATCH-{uuid.uuid4().hex[:10].upper()}",
        project_id=project_id,
        actor_id=actor_id,
        can_make_in_house=can_make_in_house,
        recommended_machine_ids=recommended_ids,
        machine_fit_score=machine_fit_score,
        work_envelope_fit=envelope_fit,
        material_fit=material_fit,
        tolerance_fit=tol_fit,
        surface_finish_fit=sf_fit,
        tooling_fit=tooling_fit,
        qc_fit=qc_fit,
        schedule_fit=schedule_fit,
        required_upstream_dependencies=list(dict.fromkeys(upstream_deps)),
        required_subcontract_dependencies=list(dict.fromkeys(subcontract_deps)),
        risk_flags=list(dict.fromkeys(risk_flags)),
        missing_information=missing_info,
        confidence_score=confidence,
        explanation="\n".join(explanations),
    )

    log_m_event(
        event_type="CAD_CNC_MATCH_COMPLETED",
        b_workspace_id=project_id,
        supplier_id=actor_id,
        payload={
            "match_id": result.match_id,
            "can_make_in_house": can_make_in_house,
            "machine_fit_score": machine_fit_score,
            "upstream_deps": upstream_deps,
            "subcontract_deps": subcontract_deps,
            "risk_flags": risk_flags,
        },
    )

    # Log parameter match events
    matches = [
        ("work_envelope", envelope_fit),
        ("material", material_fit),
        ("tolerance", tol_fit),
        ("surface_finish", sf_fit),
        ("qc", qc_fit),
        ("schedule", schedule_fit),
    ]
    for param, fit in matches:
        if fit in ("fit", "in_stock"):
            log_m_event(
                event_type="MACHINE_PARAMETER_MATCHED",
                b_workspace_id=project_id,
                supplier_id=actor_id,
                payload={"parameter": param, "fit": fit},
            )
        elif fit not in ("unknown",):
            log_m_event(
                event_type="MACHINE_PARAMETER_GAP_FOUND",
                b_workspace_id=project_id,
                supplier_id=actor_id,
                payload={"parameter": param, "fit": fit},
            )

    return result
