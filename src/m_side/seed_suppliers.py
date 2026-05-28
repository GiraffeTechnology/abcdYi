"""
M-side seed supplier creator — creates 3 CNC seed suppliers for the E2E MVP test.
"""

from src.core_schema.m_side_types import MSideSupplierProfile, SupplierCapability
from src.m_side.supplier_profile import create_supplier_profile, get_supplier_profile


def seed_cnc_suppliers() -> list[MSideSupplierProfile]:
    """
    Create 3 seed CNC suppliers for the B+M E2E MVP:
    - Supplier A: Strong CNC, high confidence, slightly higher price
    - Supplier B: Mid CNC, lower price, longer lead time, outsourcing risk
    - Supplier C: Cannot-make supplier (over capacity)

    Returns list of MSideSupplierProfile.
    """
    suppliers = []

    # Supplier A: Strong CNC
    sup_a_id = "sup_cnc_strong_001"
    existing = get_supplier_profile(sup_a_id)
    if existing:
        suppliers.append(existing)
    else:
        cap_a = SupplierCapability(
            categories=["cnc", "precision_machining"],
            materials=["aluminum 6061", "aluminum 7075", "steel", "titanium"],
            processes=["CNC milling", "CNC turning", "anodizing", "surface grinding"],
            max_quantity_hint=5000,
            typical_lead_time_days=22,
            machines_or_lines=["Mazak 5-axis", "DMG MORI", "Fanuc"],
            qc_capabilities=["CMM", "dimensional inspection", "photo/video"],
            export_experience=["Germany", "USA", "EU"],
            notes="Strong CNC precision supplier. ISO 9001 certified.",
        )
        sup_a = create_supplier_profile(
            supplier_id=sup_a_id,
            name="Precision CNC Shenzhen (A)",
            channel="mock",
            external_user_id="supplier_a_wechat_001",
            contact_name="Wang Wei",
            language_preference="zh",
            region="Shenzhen",
            capability=cap_a,
        )
        suppliers.append(sup_a)

    # Supplier B: Mid CNC, lower price, outsourcing risk
    sup_b_id = "sup_cnc_mid_002"
    existing = get_supplier_profile(sup_b_id)
    if existing:
        suppliers.append(existing)
    else:
        cap_b = SupplierCapability(
            categories=["cnc", "general_machining"],
            materials=["aluminum 6061", "steel"],
            processes=["CNC milling", "outsourced anodizing"],
            max_quantity_hint=3000,
            typical_lead_time_days=30,
            machines_or_lines=["Haas VF-2", "FANUC"],
            qc_capabilities=["dimensional inspection"],
            export_experience=["EU"],
            notes="Mid-tier CNC supplier. Anodizing is outsourced.",
        )
        sup_b = create_supplier_profile(
            supplier_id=sup_b_id,
            name="FastMech Guangzhou (B)",
            channel="mock",
            external_user_id="supplier_b_wechat_002",
            contact_name="Li Ming",
            language_preference="zh",
            region="Guangzhou",
            capability=cap_b,
        )
        suppliers.append(sup_b)

    # Supplier C: Cannot make (over capacity)
    sup_c_id = "sup_cnc_cannot_003"
    existing = get_supplier_profile(sup_c_id)
    if existing:
        suppliers.append(existing)
    else:
        cap_c = SupplierCapability(
            categories=["cnc"],
            materials=["aluminum", "steel"],
            processes=["CNC milling"],
            max_quantity_hint=2000,
            typical_lead_time_days=45,
            notes="Currently over capacity.",
        )
        sup_c = create_supplier_profile(
            supplier_id=sup_c_id,
            name="BusyMetal Dongguan (C)",
            channel="mock",
            external_user_id="supplier_c_wechat_003",
            contact_name="Zhang Fang",
            language_preference="zh",
            region="Dongguan",
            capability=cap_c,
        )
        suppliers.append(sup_c)

    return suppliers
