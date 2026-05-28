"""
Embedded MachinaCheck-like Assessor — orchestrates feature extraction from mock parsers.
"""

from src.m_side.professional_free.cad_requirement_packet import CADRequirementPacket
from src.integrations.machinacheck_embedded.feature_extractor import (
    ManufacturingFeatureSet,
    extract_manufacturing_features,
)
from src.integrations.machinacheck_embedded.mock_cad_parser import parse_cad_file
from src.integrations.machinacheck_embedded.mock_step_parser import parse_step_file
from src.integrations.machinacheck_embedded.mock_bom_parser import parse_bom_file


def assess_from_file_refs(
    packet: CADRequirementPacket,
    enrich_from_files: bool = True,
) -> ManufacturingFeatureSet:
    """
    Run the embedded MachinaCheck-like assessment on a CAD Requirement Packet.
    Optionally enriches the packet with parsed file data.
    """
    if enrich_from_files and packet.file_refs:
        # Enrich packet fields from file references if dimensions/operations are empty
        for ref in packet.file_refs:
            if ref.endswith(".step") or "step" in ref.lower():
                parsed = parse_step_file(ref)
            elif ref.endswith(".bom") or "bom" in ref.lower():
                parsed = parse_bom_file(ref)
            else:
                parsed = parse_cad_file(ref)

            # Merge only if packet is missing fields
            if not packet.dimensions and parsed.get("dimensions"):
                packet.dimensions = parsed["dimensions"]
            if not packet.material and parsed.get("material"):
                packet.material = parsed["material"]
            if not packet.operation_requirements and parsed.get("operation_requirements"):
                packet.operation_requirements = parsed["operation_requirements"]
            if not packet.tolerance_requirements and parsed.get("tolerance_requirements"):
                packet.tolerance_requirements = parsed["tolerance_requirements"]

    return extract_manufacturing_features(packet)
