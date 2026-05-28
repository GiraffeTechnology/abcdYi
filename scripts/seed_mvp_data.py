"""Seed MVP data: actors, projects, dynamic schemas, shop capability profile, legal notices."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
from src.db.session import SessionLocal
from src.db.repositories.actor_repo import ActorRepo
from src.db.repositories.project_repo import ProjectRepo
from src.db.repositories.cad_cnc_repo import CADCNCRepo
from src.db.mixins import new_uuid
from src.db.models.dynamic_schema import SchemaRegistry, FieldDefinition
from src.db.models.legal_notice import LegalNotice
from src.db.models.supplier_memory import SupplierScoreSnapshot


def utcnow():
    return datetime.now(timezone.utc)


def seed():
    db = SessionLocal()
    try:
        print("Seeding MVP data...")

        actor_repo = ActorRepo(db)
        project_repo = ProjectRepo(db)
        cad_repo = CADCNCRepo(db)

        # ── Actors ──────────────────────────────────────────────────────────
        buyer_b = actor_repo.create_actor(
            name="Buyer B", actor_type="buyer",
            default_language="en",
            contact_channels_json={"wechat": "buyer_b_wechat", "email": "buyer_b@example.com"},
            profile_json={"region": "Hong Kong"},
        )
        print(f"  Created actor: {buyer_b.name} ({buyer_b.actor_id})")

        manufacturer_m = actor_repo.create_actor(
            name="Manufacturer M", actor_type="manufacturer",
            default_language="zh",
            contact_channels_json={"wechat": "mfg_m_wechat", "whatsapp": "+8613800000001"},
            capabilities_json={"cnc": True, "apparel": True},
            profile_json={"region": "Guangzhou", "employees": 120},
        )
        print(f"  Created actor: {manufacturer_m.name} ({manufacturer_m.actor_id})")

        fabric_f1 = actor_repo.create_actor(
            name="Fabric Supplier F1", actor_type="fabric_supplier",
            default_language="zh",
            contact_channels_json={"wechat": "fabric_f1_wechat"},
            profile_json={"region": "Hangzhou", "speciality": "cotton"},
        )
        print(f"  Created actor: {fabric_f1.name} ({fabric_f1.actor_id})")

        fabric_f2 = actor_repo.create_actor(
            name="Fabric Supplier F2", actor_type="fabric_supplier",
            default_language="zh",
            contact_channels_json={"wechat": "fabric_f2_wechat"},
            profile_json={"region": "Shaoxing", "speciality": "polyester blend"},
        )
        print(f"  Created actor: {fabric_f2.name} ({fabric_f2.actor_id})")

        fabric_f3 = actor_repo.create_actor(
            name="Fabric Supplier F3", actor_type="fabric_supplier",
            default_language="zh",
            contact_channels_json={"wechat": "fabric_f3_wechat"},
            profile_json={"region": "Jiangsu", "speciality": "linen"},
        )
        print(f"  Created actor: {fabric_f3.name} ({fabric_f3.actor_id})")

        trim_t1 = actor_repo.create_actor(
            name="Trim Supplier T1", actor_type="trim_supplier",
            default_language="zh",
            contact_channels_json={"wechat": "trim_t1_wechat"},
            profile_json={"region": "Yiwu", "speciality": "buttons, zippers"},
        )
        print(f"  Created actor: {trim_t1.name} ({trim_t1.actor_id})")

        packaging_p1 = actor_repo.create_actor(
            name="Packaging Supplier P1", actor_type="packaging_supplier",
            default_language="zh",
            contact_channels_json={"wechat": "packaging_p1_wechat"},
            profile_json={"region": "Dongguan"},
        )
        print(f"  Created actor: {packaging_p1.name} ({packaging_p1.actor_id})")

        qc_q1 = actor_repo.create_actor(
            name="QC Provider Q1", actor_type="qc_provider",
            default_language="en",
            contact_channels_json={"email": "qc_q1@example.com"},
            profile_json={"region": "Guangzhou", "certification": "ISO9001"},
        )
        print(f"  Created actor: {qc_q1.name} ({qc_q1.actor_id})")

        logistics_l1 = actor_repo.create_actor(
            name="Logistics Provider L1", actor_type="logistics_provider",
            default_language="en",
            contact_channels_json={"email": "logistics_l1@example.com"},
            profile_json={"region": "Shenzhen", "modes": ["sea", "air", "rail"]},
        )
        print(f"  Created actor: {logistics_l1.name} ({logistics_l1.actor_id})")

        # ── Projects ─────────────────────────────────────────────────────────
        shirt_project = project_repo.create_project(
            original_buyer_actor_id=buyer_b.actor_id,
            main_supplier_actor_id=manufacturer_m.actor_id,
            category="apparel",
            product_summary="100 pcs custom shirt order",
            quantity=100,
            status="CREATED",
            product_tier="free",
            created_by_channel="wechat",
            metadata_json={"label": "shirt_100pcs_project"},
        )
        print(f"  Created project: shirt_100pcs_project ({shirt_project.project_id})")

        cnc_project = project_repo.create_project(
            original_buyer_actor_id=buyer_b.actor_id,
            main_supplier_actor_id=manufacturer_m.actor_id,
            category="cnc",
            product_summary="CNC precision part order",
            quantity=50,
            status="CREATED",
            product_tier="professional_free",
            created_by_channel="web_fallback",
            metadata_json={"label": "cnc_part_project"},
        )
        print(f"  Created project: cnc_part_project ({cnc_project.project_id})")

        # ── Shop Capability Profile ─────────────────────────────────────────
        shop_profile = cad_repo.create_shop_capability_profile(
            actor_id=manufacturer_m.actor_id,
            profile_name="manufacturer_m_basic_shop_profile",
            machines_json={
                "cnc_3axis": {
                    "name": "3-Axis CNC Machining Center",
                    "count": 3,
                    "work_envelope_mm": {"x": 600, "y": 500, "z": 400},
                    "axes": 3,
                },
                "cnc_5axis": {
                    "name": "5-Axis CNC Machining Center",
                    "count": 0,
                    "available": False,
                },
            },
            tooling_inventory_json={"standard_drills": True, "taps": True, "end_mills": True},
            qc_equipment_json={
                "caliper": True,
                "micrometer": True,
                "basic_inspection": True,
                "cmm": False,
            },
            material_inventory_json={
                "aluminum_6061": True,
                "steel": True,
                "brass": True,
                "titanium": False,
                "stainless_steel": False,
            },
            in_house_processes_json={
                "3_axis_cnc_milling": True,
                "3_axis_cnc_turning": True,
                "drilling": True,
                "tapping": True,
                "typical_tolerance_mm": 0.05,
                "best_tolerance_mm": 0.02,
            },
            outsourced_processes_json={
                "surface_treatment": True,
                "heat_treatment": True,
                "5_axis_cnc": True,
                "grinding": True,
                "edm": True,
            },
            schedule_summary_json={
                "status": "limited",
                "typical_lead_time_days": 14,
            },
        )
        print(f"  Created shop profile: {shop_profile.profile_name} ({shop_profile.profile_id})")

        # ── Dynamic Schemas ───────────────────────────────────────────────────
        apparel_schema = SchemaRegistry(
            schema_id=new_uuid(),
            industry="apparel",
            category="shirt",
            schema_version="v0.1",
            status="active",
            created_at=utcnow(),
            updated_at=utcnow(),
            metadata_json={},
        )
        db.add(apparel_schema)
        db.flush()
        print(f"  Created schema: apparel/shirt/v0.1 ({apparel_schema.schema_id})")

        shirt_fields = [
            ("category", "str", "required"),
            ("quantity", "int", "required"),
            ("fabric_type", "str", "required"),
            ("fabric_gsm", "float", "recommended"),
            ("color", "str", "required"),
            ("size_breakdown", "dict", "required"),
            ("trim_type", "str", "recommended"),
            ("button_type", "str", "optional"),
            ("packaging_type", "str", "recommended"),
            ("deadline", "str", "required"),
        ]
        for fname, ftype, req_level in shirt_fields:
            fd = FieldDefinition(
                field_id=new_uuid(),
                schema_id=apparel_schema.schema_id,
                field_name=fname,
                normalized_field_name=fname,
                field_type=ftype,
                required_level=req_level,
                validation_rule_json={},
                example_values_json={},
                source="manual",
                status="approved",
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            db.add(fd)
        db.flush()
        print(f"  Seeded {len(shirt_fields)} shirt schema fields")

        cnc_schema = SchemaRegistry(
            schema_id=new_uuid(),
            industry="cnc",
            category="precision_part",
            schema_version="v0.1",
            status="active",
            created_at=utcnow(),
            updated_at=utcnow(),
            metadata_json={},
        )
        db.add(cnc_schema)
        db.flush()
        print(f"  Created schema: cnc/precision_part/v0.1 ({cnc_schema.schema_id})")

        cnc_fields = [
            ("material", "str", "required"),
            ("quantity", "int", "required"),
            ("tolerance", "str", "required"),
            ("surface_finish", "str", "recommended"),
            ("axis_count_required", "int", "required"),
            ("work_envelope_x_mm", "float", "recommended"),
            ("work_envelope_y_mm", "float", "recommended"),
            ("work_envelope_z_mm", "float", "recommended"),
            ("qc_method", "str", "recommended"),
            ("heat_treatment_required", "bool", "recommended"),
        ]
        for fname, ftype, req_level in cnc_fields:
            fd = FieldDefinition(
                field_id=new_uuid(),
                schema_id=cnc_schema.schema_id,
                field_name=fname,
                normalized_field_name=fname,
                field_type=ftype,
                required_level=req_level,
                validation_rule_json={},
                example_values_json={},
                source="manual",
                status="approved",
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            db.add(fd)
        db.flush()
        print(f"  Seeded {len(cnc_fields)} cnc schema fields")

        packaging_schema = SchemaRegistry(
            schema_id=new_uuid(),
            industry="packaging",
            category="custom_box",
            schema_version="v0.1",
            status="active",
            created_at=utcnow(),
            updated_at=utcnow(),
            metadata_json={},
        )
        db.add(packaging_schema)
        db.flush()
        print(f"  Created schema: packaging/custom_box/v0.1 ({packaging_schema.schema_id})")

        # ── Legal Notice ──────────────────────────────────────────────────────
        patent_notice = LegalNotice(
            notice_id=new_uuid(),
            notice_type="patent_license",
            version="v1.0",
            text_en=(
                "China patent: ZL 2023 1 1645939.9 / CN 117670482 B. "
                "Japan patent: P7644545 / 特許第7644545号. "
                "Patent owner: Giraffe Technology Holding Limited. "
                "Free patent license applies globally to individuals, SMEs, educational institutions "
                "and research institutions for compliant use. "
                "Enterprise deployment, platform operation, high-volume commercial production use, "
                "third-party system integration, white-label resale, Enterprise CAP, and use of "
                "Giraffe commercial assets require separate written permission. "
                "Authorization contact: mich@giraffe.technology."
            ),
            text_zh=(
                "中国专利：ZL 2023 1 1645939.9 / CN 117670482 B。"
                "日本专利：P7644545 / 特許第7644545号。"
                "专利权人：Giraffe Technology Holding Limited。"
                "全球免费专利许可适用于个人、中小企业、教育机构及研究机构的合规使用。"
                "企业部署、平台运营、大批量商业生产使用、第三方系统集成、"
                "白标转售、Enterprise CAP及使用Giraffe商业资产需获得单独书面许可。"
                "授权联系：mich@giraffe.technology。"
            ),
            effective_at=utcnow(),
            metadata_json={"patents": ["ZL 2023 1 1645939.9", "P7644545"]},
            created_at=utcnow(),
        )
        db.add(patent_notice)
        db.flush()
        print(f"  Created legal notice: patent_license ({patent_notice.notice_id})")

        db.commit()
        print("\nSeed complete.")

        return {
            "actors": {
                "buyer_b": buyer_b.actor_id,
                "manufacturer_m": manufacturer_m.actor_id,
                "fabric_f1": fabric_f1.actor_id,
                "fabric_f2": fabric_f2.actor_id,
                "fabric_f3": fabric_f3.actor_id,
                "trim_t1": trim_t1.actor_id,
                "packaging_p1": packaging_p1.actor_id,
                "qc_q1": qc_q1.actor_id,
                "logistics_l1": logistics_l1.actor_id,
            },
            "projects": {
                "shirt_project": shirt_project.project_id,
                "cnc_project": cnc_project.project_id,
            },
            "shop_profile": shop_profile.profile_id,
            "schemas": {
                "apparel_shirt": apparel_schema.schema_id,
                "cnc_precision_part": cnc_schema.schema_id,
                "packaging_custom_box": packaging_schema.schema_id,
            },
        }

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    seed()
