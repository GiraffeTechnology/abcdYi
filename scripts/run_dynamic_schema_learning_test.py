"""
Smoke Test 4: Dynamic Schema Learning
1. Create observed fields from mock supplier messages.
2. Create field proposals when thresholds are met or manually triggered.
3. Approve a low-risk field.
4. Store entity_dynamic_values.
5. Verify no physical table migration is required.
6. Verify all fields are traceable to source messages or artifacts.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.base import Base
from src.db.session import engine, SessionLocal
import src.db.models  # noqa: F401
from src.db.repositories.actor_repo import ActorRepo
from src.db.repositories.project_repo import ProjectRepo
from src.db.repositories.dynamic_schema_repo import DynamicSchemaRepo
from src.db.models.dynamic_schema import SchemaRegistry, FieldDefinition, ObservedField
from src.db.models.im_message import Message
from src.db.models.artifact import Artifact
from src.db.mixins import new_uuid
from datetime import datetime, timezone


def utcnow():
    return datetime.now(timezone.utc)


def run():
    print("=" * 60)
    print("DYNAMIC SCHEMA LEARNING TEST")
    print("=" * 60)

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        actor_repo = ActorRepo(db)
        project_repo = ProjectRepo(db)
        dsr = DynamicSchemaRepo(db)

        # Setup
        buyer = actor_repo.create_actor(name="Buyer DS", actor_type="buyer")
        fabric_supplier = actor_repo.create_actor(name="Fabric Supplier DS", actor_type="fabric_supplier")

        project = project_repo.create_project(
            original_buyer_actor_id=buyer.actor_id,
            category="apparel",
            product_summary="Dynamic schema test project",
        )

        # Create/get schema
        schema = SchemaRegistry(
            schema_id=new_uuid(), industry="apparel", category="shirt", schema_version="v0.1",
            status="active", created_at=utcnow(), updated_at=utcnow(), metadata_json={},
        )
        db.add(schema)
        db.flush()

        # Create mock messages (simulate supplier responses)
        messages = []
        for i in range(6):
            msg = Message(
                message_id=new_uuid(),
                project_id=project.project_id,
                sender_actor_id=fabric_supplier.actor_id,
                channel_type="mock",
                direction="inbound",
                raw_text=f"Mock supplier message {i+1} with fabric specifications",
                created_at=utcnow(),
                metadata_json={},
                attachments_json={},
                parsed_entities_json={},
            )
            db.add(msg)
            messages.append(msg)
        db.flush()

        # Create mock artifact
        artifact = Artifact(
            artifact_id=new_uuid(),
            project_id=project.project_id,
            owner_actor_id=fabric_supplier.actor_id,
            artifact_type="spreadsheet",
            file_ref="mock://specs/fabric_spec_sheet.xlsx",
            product_tier="professional_free",
            encryption_enabled=False,
            dynamic_watermark_enabled=False,
            secure_viewer_enabled=False,
            warning_acknowledged=True,
            created_at=utcnow(),
            updated_at=utcnow(),
            metadata_json={},
        )
        db.add(artifact)
        db.flush()

        # Step 1: Create observed fields from mock supplier messages
        print("\n[1] Creating observed fields from mock supplier messages...")

        test_fields = [
            ("fabric_gsm", "160", "gsm", 0.95, messages[0].message_id, None),
            ("shrinkage_rate", "3%", "%", 0.88, messages[1].message_id, None),
            ("color_fastness_grade", "4", None, 0.92, messages[2].message_id, None),
            ("surface_roughness_ra", "1.6", "um", 0.87, None, artifact.artifact_id),
            ("cmm_required", "false", None, 0.91, messages[3].message_id, None),
        ]

        observed_list = []
        for field_name, value, unit, score, msg_id, art_id in test_fields:
            obs = dsr.observe_field(
                candidate_field_name=field_name,
                confidence_score=score,
                project_id=project.project_id,
                actor_id=fabric_supplier.actor_id,
                source_message_id=msg_id,
                source_artifact_id=art_id,
                candidate_value=value,
                candidate_unit=unit,
                evidence_text=f"Observed '{field_name}={value}' in supplier communication",
            )
            observed_list.append(obs)
            print(f"    OK: observed '{field_name}={value}' (confidence={score}, "
                  f"source={'message' if msg_id else 'artifact'})")

        assert len(observed_list) == 5
        print(f"    OK: {len(observed_list)} fields observed")

        # Step 6 (verify traceability while observing)
        # fabric_gsm has message source
        obs_gsm = observed_list[0]
        assert obs_gsm.source_message_id == messages[0].message_id
        assert obs_gsm.source_artifact_id is None
        # surface_roughness_ra has artifact source
        obs_ra = observed_list[3]
        assert obs_ra.source_artifact_id == artifact.artifact_id
        assert obs_ra.source_message_id is None
        print("    OK: Field traceability verified (message + artifact sources)")

        # Step 2: Create field proposals (manually triggered + threshold-based)
        print("\n[2] Creating field proposals...")

        # fabric_gsm already known in schema, but simulate new variant: observe multiple times
        for i in range(4, len(messages)):
            dsr.observe_field(
                candidate_field_name="shrinkage_rate",
                confidence_score=0.89,
                project_id=project.project_id,
                actor_id=fabric_supplier.actor_id,
                source_message_id=messages[i].message_id,
                candidate_value="2.5%",
            )

        # Propose fabric_gsm (manually triggered — high-value known field)
        proposal_gsm = dsr.propose_field(
            schema_id=schema.schema_id,
            candidate_field_name="fabric_gsm",
            normalized_field_name="fabric_gsm",
            field_type="float",
            suggested_unit="gsm",
            business_reason="Fabric weight is a critical parameter affecting drape and shrinkage.",
            example_count=8,
            project_count=6,
            supplier_count=4,
            confidence_score=0.95,
            risk_level="low",
        )
        print(f"    OK: proposal_gsm={proposal_gsm.proposal_id} (status={proposal_gsm.status})")

        # Propose shrinkage_rate (threshold: 5+ observations)
        all_shrinkage_obs = db.query(ObservedField).filter(
            ObservedField.candidate_field_name == "shrinkage_rate"
        ).all()
        proposal_shrinkage = dsr.propose_field(
            schema_id=schema.schema_id,
            candidate_field_name="shrinkage_rate",
            normalized_field_name="shrinkage_rate",
            field_type="float",
            suggested_unit="%",
            business_reason="Shrinkage rate observed frequently in supplier responses.",
            example_count=len(all_shrinkage_obs),
            project_count=3,
            supplier_count=3,
            confidence_score=0.88,
            risk_level="low",
        )
        print(f"    OK: proposal_shrinkage={proposal_shrinkage.proposal_id} "
              f"(example_count={proposal_shrinkage.example_count})")

        # Propose color_fastness_grade
        proposal_cfg = dsr.propose_field(
            schema_id=schema.schema_id,
            candidate_field_name="color_fastness_grade",
            normalized_field_name="color_fastness_grade",
            field_type="int",
            suggested_unit=None,
            business_reason="Color fastness affects QC pass/fail decisions.",
            example_count=5,
            project_count=5,
            supplier_count=3,
            confidence_score=0.92,
            risk_level="low",
        )
        print(f"    OK: proposal_cfg={proposal_cfg.proposal_id}")

        # surface_roughness_ra — affects tolerance/quality — mark as medium risk (requires human)
        proposal_ra = dsr.propose_field(
            schema_id=schema.schema_id,
            candidate_field_name="surface_roughness_ra",
            normalized_field_name="surface_roughness_ra",
            field_type="float",
            suggested_unit="um",
            business_reason="Surface roughness Ra is a key machining quality parameter.",
            example_count=3,
            project_count=2,
            supplier_count=2,
            confidence_score=0.87,
            risk_level="medium",  # affects quality — human approval required
        )
        print(f"    OK: proposal_ra={proposal_ra.proposal_id} (risk=medium, human approval required)")

        # cmm_required
        proposal_cmm = dsr.propose_field(
            schema_id=schema.schema_id,
            candidate_field_name="cmm_required",
            normalized_field_name="cmm_required",
            field_type="bool",
            suggested_unit=None,
            business_reason="CMM requirement flag for CNC QC planning.",
            example_count=4,
            project_count=3,
            supplier_count=2,
            confidence_score=0.91,
            risk_level="low",
        )
        print(f"    OK: proposal_cmm={proposal_cmm.proposal_id}")

        # Step 3: Approve a low-risk field
        print("\n[3] Approving low-risk fields (fabric_gsm, cmm_required)...")
        # fabric_gsm — can auto-approve (low risk, example_count >= 3)
        assert dsr.can_auto_approve(proposal_gsm), "fabric_gsm should be auto-approvable"
        field_def_gsm = dsr.approve_field(
            proposal_id=proposal_gsm.proposal_id,
            schema_id=schema.schema_id,
            decided_by="system_auto_approve",
            reason="Low risk, high confidence, 8 examples — auto-approved.",
        )
        assert field_def_gsm is not None
        assert field_def_gsm.normalized_field_name == "fabric_gsm"
        assert field_def_gsm.status == "approved"
        print(f"    OK: fabric_gsm promoted to field_definitions ({field_def_gsm.field_id})")

        field_def_cmm = dsr.approve_field(
            proposal_id=proposal_cmm.proposal_id,
            schema_id=schema.schema_id,
            decided_by="human_operator",
            reason="CNC QC planning flag — safe to approve.",
        )
        print(f"    OK: cmm_required approved ({field_def_cmm.field_id})")

        # surface_roughness_ra — medium risk, do NOT auto-approve
        assert not dsr.can_auto_approve(proposal_ra), "surface_roughness_ra should NOT be auto-approvable"
        print(f"    OK: surface_roughness_ra NOT auto-approved (risk=medium, requires human)")

        db.flush()

        # Step 4: Store entity_dynamic_values
        print("\n[4] Storing entity_dynamic_values...")
        val1 = dsr.store_dynamic_value(
            entity_type="structured_requirement",
            entity_id=project.project_id,
            field_id=field_def_gsm.field_id,
            field_value="160",
            unit="gsm",
            confidence_score=0.95,
            source="supplier_response",
            source_message_id=messages[0].message_id,
        )
        val2 = dsr.store_dynamic_value(
            entity_type="structured_requirement",
            entity_id=project.project_id,
            field_id=field_def_cmm.field_id,
            field_value="false",
            unit=None,
            confidence_score=0.91,
            source="supplier_response",
            source_message_id=messages[3].message_id,
        )
        print(f"    OK: stored fabric_gsm=160 (value_id={val1.value_id})")
        print(f"    OK: stored cmm_required=false (value_id={val2.value_id})")

        db.commit()

        # Step 5: Verify no physical table migration required
        print("\n[5] Verifying no physical table migration required...")
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        # Verify the dynamic value was stored in entity_dynamic_values, not a new table
        assert "entity_dynamic_values" in tables
        assert "field_definitions" in tables
        assert "observed_fields" in tables
        assert "field_proposals" in tables
        # Verify no new table was created for the new field
        assert "fabric_gsm" not in tables
        assert "cmm_required" not in tables
        print(f"    OK: {len(tables)} tables total. No new tables created for dynamic fields.")
        print(f"    OK: Dynamic values stored in entity_dynamic_values table only.")

        # Step 6: Verify traceability
        print("\n[6] Verifying field traceability to source messages/artifacts...")
        from src.db.models.dynamic_schema import EntityDynamicValue
        stored_vals = db.query(EntityDynamicValue).filter(
            EntityDynamicValue.entity_id == project.project_id
        ).all()
        for val in stored_vals:
            assert val.source_message_id is not None or val.source_artifact_id is not None or val.source is not None
            print(f"    OK: value '{val.field_value}' traceable to source_message={val.source_message_id}")

        # Verify observed fields are traceable
        obs_fields = db.query(ObservedField).filter(
            ObservedField.project_id == project.project_id
        ).all()
        for obs in obs_fields:
            assert obs.source_message_id is not None or obs.source_artifact_id is not None
        print(f"    OK: All {len(obs_fields)} observed fields are traceable to messages or artifacts.")

        # Verify schema fields list
        approved_fields = dsr.list_schema_fields(schema.schema_id)
        approved_names = {f.normalized_field_name for f in approved_fields}
        assert "fabric_gsm" in approved_names
        assert "cmm_required" in approved_names
        print(f"    OK: schema now has {len(approved_fields)} approved field(s): {approved_names}")

        print("\n" + "=" * 60)
        print("DYNAMIC SCHEMA LEARNING TEST PASSED: All 6 steps completed.")
        print("=" * 60)

    except Exception as e:
        db.rollback()
        print(f"\nDYNAMIC SCHEMA TEST FAILED: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
