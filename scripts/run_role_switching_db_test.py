"""
Smoke Test 2: Role-Switching Graph
1. Buyer B creates shirt order project.
2. Manufacturer M receives buyer inquiry.
3. M is resolved as MAIN_M_SIDE.
4. Dependency needs are created: fabric, trim, packaging.
5. Procurement edges are created from M to fabric suppliers.
6. M is resolved as UPSTREAM_B_SIDE.
7. Fabric suppliers are resolved as UPSTREAM_M_SIDE.
8. Upstream inquiries and responses are created.
9. Options are created.
10. Approval request is approved.
11. Supplier Response Rollup is created.
12. Rollup is submitted back to B-side as SupplierResponse.
13. ExecutionEvents exist for all major transitions.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.base import Base
from src.db.session import engine, SessionLocal
import src.db.models  # noqa: F401
from src.db.repositories.actor_repo import ActorRepo
from src.db.repositories.project_repo import ProjectRepo
from src.db.repositories.graph_repo import GraphRepo
from src.db.repositories.role_repo import RoleRepo
from src.db.repositories.requirement_repo import RequirementRepo
from src.db.repositories.inquiry_repo import InquiryRepo
from src.db.repositories.response_repo import ResponseRepo
from src.db.repositories.rollup_repo import RollupRepo
from src.db.repositories.execution_event_repo import ExecutionEventRepo
from src.db.mixins import new_uuid
from src.db.models.upstream import DependencyNeed, UpstreamOption
from src.db.models.approval import ApprovalRequest
from src.db.models.response import SupplierResponse
from datetime import datetime, timezone


def utcnow():
    return datetime.now(timezone.utc)


def run():
    print("=" * 60)
    print("ROLE-SWITCHING DB TEST")
    print("=" * 60)

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        actor_repo = ActorRepo(db)
        project_repo = ProjectRepo(db)
        graph_repo = GraphRepo(db)
        role_repo = RoleRepo(db)
        req_repo = RequirementRepo(db)
        inquiry_repo = InquiryRepo(db)
        response_repo = ResponseRepo(db)
        rollup_repo = RollupRepo(db)
        event_repo = ExecutionEventRepo(db)

        # Step 1: Create actors
        print("\n[1] Buyer B creates shirt order project...")
        buyer_b = actor_repo.create_actor(name="Buyer B (RS)", actor_type="buyer")
        manufacturer_m = actor_repo.create_actor(name="Manufacturer M (RS)", actor_type="manufacturer")
        fabric_f1 = actor_repo.create_actor(name="Fabric F1 (RS)", actor_type="fabric_supplier")
        fabric_f2 = actor_repo.create_actor(name="Fabric F2 (RS)", actor_type="fabric_supplier")
        trim_t1 = actor_repo.create_actor(name="Trim T1 (RS)", actor_type="trim_supplier")
        packaging_p1 = actor_repo.create_actor(name="Packaging P1 (RS)", actor_type="packaging_supplier")

        project = project_repo.create_project(
            original_buyer_actor_id=buyer_b.actor_id,
            main_supplier_actor_id=manufacturer_m.actor_id,
            category="apparel",
            product_summary="100pcs shirt RS test",
            quantity=100,
        )
        print(f"    OK: project_id={project.project_id}")

        # Step 2: Create buyer inquiry
        print("\n[2] Manufacturer M receives buyer inquiry...")
        buyer_supplier_edge = graph_repo.create_edge(
            project_id=project.project_id,
            from_actor_id=buyer_b.actor_id,
            to_actor_id=manufacturer_m.actor_id,
            edge_type="BUYER_TO_MAIN_SUPPLIER",
            status="SENT",
        )
        requirement = req_repo.create_requirement(
            project_id=project.project_id,
            source_actor_id=buyer_b.actor_id,
            category="apparel",
            quantity=100,
            specs_json={"fabric": "cotton", "color": "white"},
            confidence_score=0.9,
        )
        inquiry = inquiry_repo.create_supplier_inquiry(
            project_id=project.project_id,
            edge_id=buyer_supplier_edge.edge_id,
            from_actor_id=buyer_b.actor_id,
            to_actor_id=manufacturer_m.actor_id,
            requirement_id=requirement.requirement_id,
            message_text_en="Please quote 100pcs white cotton shirt.",
            requested_fields_json=["price", "lead_time", "moq"],
            status="SENT",
        )
        event_repo.log_event(
            event_type="B_INQUIRY_CREATED",
            project_id=project.project_id,
            edge_id=buyer_supplier_edge.edge_id,
            actor_id=buyer_b.actor_id,
            payload_json={"inquiry_id": inquiry.inquiry_id},
            source_channel="mock",
        )
        print(f"    OK: inquiry_id={inquiry.inquiry_id}")

        # Step 3: M is resolved as MAIN_M_SIDE
        print("\n[3] Resolving M as MAIN_M_SIDE...")
        m_main_role = role_repo.create_role_context(
            project_id=project.project_id,
            actor_id=manufacturer_m.actor_id,
            role="MAIN_M_SIDE",
            edge_id=buyer_supplier_edge.edge_id,
            counterparty_actor_id=buyer_b.actor_id,
            role_reason="Manufacturer M is the main supplier for this shirt project.",
            can_create_upstream_inquiry=True,
            can_approve_upstream_option=True,
            can_submit_response_to_buyer=True,
        )
        event_repo.log_event(
            event_type="ROLE_CONTEXT_RESOLVED",
            project_id=project.project_id,
            edge_id=buyer_supplier_edge.edge_id,
            actor_id=manufacturer_m.actor_id,
            role_context_id=m_main_role.role_context_id,
            payload_json={"role": "MAIN_M_SIDE"},
            source_channel="mock",
        )
        event_repo.log_event(
            event_type="M_SIDE_RECEIVED_BUYER_INQUIRY",
            project_id=project.project_id,
            edge_id=buyer_supplier_edge.edge_id,
            actor_id=manufacturer_m.actor_id,
            payload_json={"inquiry_id": inquiry.inquiry_id},
            source_channel="mock",
        )
        print(f"    OK: MAIN_M_SIDE role_context_id={m_main_role.role_context_id}")

        # Step 4: Dependency needs: fabric, trim, packaging
        print("\n[4] Creating dependency needs: fabric, trim, packaging...")
        dep_fabric = DependencyNeed(
            dependency_id=new_uuid(), project_id=project.project_id,
            created_by_actor_id=manufacturer_m.actor_id,
            dependency_type="fabric", description="Cotton fabric 160gsm",
            required_specs_json={"gsm": 160, "type": "cotton"},
            quantity_required=120.0, risk_level="medium",
            why_needed="Main fabric for shirt body",
            candidate_actor_ids_json={"actors": [fabric_f1.actor_id, fabric_f2.actor_id]},
            source="m_side_analysis", status="pending",
            created_at=utcnow(), updated_at=utcnow(),
        )
        dep_trim = DependencyNeed(
            dependency_id=new_uuid(), project_id=project.project_id,
            created_by_actor_id=manufacturer_m.actor_id,
            dependency_type="trim", description="White buttons",
            required_specs_json={"type": "button", "color": "white"},
            quantity_required=600.0, risk_level="low",
            why_needed="Buttons for shirt",
            candidate_actor_ids_json={"actors": [trim_t1.actor_id]},
            source="m_side_analysis", status="pending",
            created_at=utcnow(), updated_at=utcnow(),
        )
        dep_packaging = DependencyNeed(
            dependency_id=new_uuid(), project_id=project.project_id,
            created_by_actor_id=manufacturer_m.actor_id,
            dependency_type="packaging", description="Custom poly bags",
            required_specs_json={"type": "poly_bag"},
            quantity_required=100.0, risk_level="low",
            why_needed="Individual packaging per shirt",
            candidate_actor_ids_json={"actors": [packaging_p1.actor_id]},
            source="m_side_analysis", status="pending",
            created_at=utcnow(), updated_at=utcnow(),
        )
        db.add_all([dep_fabric, dep_trim, dep_packaging])
        db.flush()
        event_repo.log_event(
            event_type="UPSTREAM_DEPENDENCY_PLANNED",
            project_id=project.project_id,
            actor_id=manufacturer_m.actor_id,
            payload_json={"dependencies": ["fabric", "trim", "packaging"]},
            source_channel="mock",
        )
        print(f"    OK: dep_fabric={dep_fabric.dependency_id}")
        print(f"    OK: dep_trim={dep_trim.dependency_id}")
        print(f"    OK: dep_packaging={dep_packaging.dependency_id}")

        # Step 5: Create procurement edges from M to fabric suppliers
        print("\n[5] Creating upstream procurement edges (M → fabric suppliers)...")
        edge_m_f1 = graph_repo.create_edge(
            project_id=project.project_id,
            from_actor_id=manufacturer_m.actor_id,
            to_actor_id=fabric_f1.actor_id,
            edge_type="MAIN_SUPPLIER_TO_FABRIC_SUPPLIER",
            parent_edge_id=buyer_supplier_edge.edge_id,
            status="SENT",
        )
        edge_m_f2 = graph_repo.create_edge(
            project_id=project.project_id,
            from_actor_id=manufacturer_m.actor_id,
            to_actor_id=fabric_f2.actor_id,
            edge_type="MAIN_SUPPLIER_TO_FABRIC_SUPPLIER",
            parent_edge_id=buyer_supplier_edge.edge_id,
            status="SENT",
        )
        print(f"    OK: edge_m_f1={edge_m_f1.edge_id}")
        print(f"    OK: edge_m_f2={edge_m_f2.edge_id}")

        # Step 6: M is resolved as UPSTREAM_B_SIDE
        print("\n[6] Resolving M as UPSTREAM_B_SIDE (dual role)...")
        m_upstream_buyer_role = role_repo.create_role_context(
            project_id=project.project_id,
            actor_id=manufacturer_m.actor_id,
            role="UPSTREAM_B_SIDE",
            edge_id=edge_m_f1.edge_id,
            counterparty_actor_id=fabric_f1.actor_id,
            role_reason="M acts as upstream buyer when sourcing fabric from F1.",
            can_create_upstream_inquiry=True,
        )
        event_repo.log_event(
            event_type="ROLE_SWITCH_OCCURRED",
            project_id=project.project_id,
            edge_id=edge_m_f1.edge_id,
            actor_id=manufacturer_m.actor_id,
            role_context_id=m_upstream_buyer_role.role_context_id,
            payload_json={"from_role": "MAIN_M_SIDE", "to_role": "UPSTREAM_B_SIDE"},
            source_channel="mock",
        )
        print(f"    OK: UPSTREAM_B_SIDE role_context_id={m_upstream_buyer_role.role_context_id}")

        # Verify same actor has two roles in same project
        all_m_roles = role_repo.list_actor_roles_in_project(project.project_id, manufacturer_m.actor_id)
        assert len(all_m_roles) == 2, f"Expected 2 roles for M, got {len(all_m_roles)}"
        roles_found = {rc.role for rc in all_m_roles}
        assert "MAIN_M_SIDE" in roles_found
        assert "UPSTREAM_B_SIDE" in roles_found
        print(f"    OK: Verified M has {len(all_m_roles)} roles: {roles_found}")

        # Step 7: Fabric suppliers resolved as UPSTREAM_M_SIDE
        print("\n[7] Resolving fabric suppliers as UPSTREAM_M_SIDE...")
        f1_role = role_repo.create_role_context(
            project_id=project.project_id,
            actor_id=fabric_f1.actor_id,
            role="UPSTREAM_M_SIDE",
            edge_id=edge_m_f1.edge_id,
            counterparty_actor_id=manufacturer_m.actor_id,
            role_reason="F1 is an upstream fabric supplier to M.",
        )
        f2_role = role_repo.create_role_context(
            project_id=project.project_id,
            actor_id=fabric_f2.actor_id,
            role="UPSTREAM_M_SIDE",
            edge_id=edge_m_f2.edge_id,
            counterparty_actor_id=manufacturer_m.actor_id,
            role_reason="F2 is an upstream fabric supplier to M.",
        )
        print(f"    OK: F1 role={f1_role.role}")
        print(f"    OK: F2 role={f2_role.role}")

        # Step 8: Upstream inquiries and responses
        print("\n[8] Creating upstream inquiries and responses...")
        uinq_f1 = inquiry_repo.create_upstream_inquiry(
            project_id=project.project_id,
            edge_id=edge_m_f1.edge_id,
            dependency_id=dep_fabric.dependency_id,
            parent_main_supplier_actor_id=manufacturer_m.actor_id,
            upstream_actor_id=fabric_f1.actor_id,
            message_text_en="Can you supply 120m cotton fabric at 160gsm?",
            requested_fields_json=["price", "lead_time", "available_quantity"],
            status="SENT",
        )
        uinq_f2 = inquiry_repo.create_upstream_inquiry(
            project_id=project.project_id,
            edge_id=edge_m_f2.edge_id,
            dependency_id=dep_fabric.dependency_id,
            parent_main_supplier_actor_id=manufacturer_m.actor_id,
            upstream_actor_id=fabric_f2.actor_id,
            message_text_en="Can you supply 120m polyester-blend fabric at 160gsm?",
            requested_fields_json=["price", "lead_time", "available_quantity"],
            status="SENT",
        )
        event_repo.log_event(
            event_type="UPSTREAM_INQUIRY_CREATED",
            project_id=project.project_id,
            edge_id=edge_m_f1.edge_id,
            actor_id=manufacturer_m.actor_id,
            payload_json={"upstream_inquiry_id": uinq_f1.upstream_inquiry_id},
            source_channel="mock",
        )
        event_repo.log_event(
            event_type="UPSTREAM_INQUIRY_DISPATCHED",
            project_id=project.project_id,
            edge_id=edge_m_f1.edge_id,
            actor_id=manufacturer_m.actor_id,
            payload_json={"dispatch_channel": "mock"},
            source_channel="mock",
        )

        uresp_f1 = response_repo.create_upstream_response(
            project_id=project.project_id,
            edge_id=edge_m_f1.edge_id,
            upstream_inquiry_id=uinq_f1.upstream_inquiry_id,
            dependency_id=dep_fabric.dependency_id,
            from_actor_id=fabric_f1.actor_id,
            can_supply=True,
            matched_specs_json={"gsm": 160, "type": "cotton"},
            price=2.5, currency="USD", moq=50.0, available_quantity=500.0,
            lead_time_days=7, earliest_dispatch_date="2026-06-10",
            confidence_score=0.9, completeness_score=0.95,
            raw_message="Yes, we can supply 160gsm cotton at USD2.5/m. Lead time 7 days.",
        )
        uresp_f2 = response_repo.create_upstream_response(
            project_id=project.project_id,
            edge_id=edge_m_f2.edge_id,
            upstream_inquiry_id=uinq_f2.upstream_inquiry_id,
            dependency_id=dep_fabric.dependency_id,
            from_actor_id=fabric_f2.actor_id,
            can_supply=True,
            matched_specs_json={"gsm": 160, "type": "polyester_blend"},
            price=1.8, currency="USD", moq=30.0, available_quantity=1000.0,
            lead_time_days=5, earliest_dispatch_date="2026-06-08",
            confidence_score=0.85, completeness_score=0.9,
            raw_message="Yes, 160gsm polyester blend at USD1.8/m. Lead time 5 days.",
        )
        event_repo.log_event(
            event_type="UPSTREAM_RESPONSE_RECEIVED",
            project_id=project.project_id,
            edge_id=edge_m_f1.edge_id,
            actor_id=fabric_f1.actor_id,
            payload_json={"upstream_response_id": uresp_f1.upstream_response_id},
            source_channel="mock",
        )
        event_repo.log_event(
            event_type="UPSTREAM_RESPONSE_PARSED",
            project_id=project.project_id,
            edge_id=edge_m_f1.edge_id,
            payload_json={"can_supply": True, "price": 2.5},
            source_channel="mock",
        )
        print(f"    OK: uinq_f1={uinq_f1.upstream_inquiry_id}, uresp_f1={uresp_f1.upstream_response_id}")
        print(f"    OK: uinq_f2={uinq_f2.upstream_inquiry_id}, uresp_f2={uresp_f2.upstream_response_id}")

        # Step 9: Create upstream options
        print("\n[9] Creating upstream options...")
        opt_best = response_repo.create_upstream_option(
            project_id=project.project_id,
            dependency_id=dep_fabric.dependency_id,
            upstream_actor_id=fabric_f1.actor_id,
            option_label="BEST",
            score=0.88,
            price_summary="USD2.5/m — pure cotton, best quality",
            lead_time_summary="7 days",
            risk_summary="Low risk — certified supplier",
            reason="Best quality match for cotton shirt requirement.",
            response_ids_json={"ids": [uresp_f1.upstream_response_id]},
            status="pending",
        )
        opt_fastest = response_repo.create_upstream_option(
            project_id=project.project_id,
            dependency_id=dep_fabric.dependency_id,
            upstream_actor_id=fabric_f2.actor_id,
            option_label="FASTEST",
            score=0.82,
            price_summary="USD1.8/m — polyester blend",
            lead_time_summary="5 days",
            risk_summary="Low risk — slightly different material",
            reason="Fastest delivery, lower cost polyester blend option.",
            response_ids_json={"ids": [uresp_f2.upstream_response_id]},
            status="pending",
        )
        event_repo.log_event(
            event_type="UPSTREAM_OPTIONS_GENERATED",
            project_id=project.project_id,
            actor_id=manufacturer_m.actor_id,
            payload_json={"options": ["BEST", "FASTEST"], "dependency_id": dep_fabric.dependency_id},
            source_channel="mock",
        )
        print(f"    OK: opt_best={opt_best.option_id} (BEST)")
        print(f"    OK: opt_fastest={opt_fastest.option_id} (FASTEST)")

        # Step 10: Approval request is approved
        print("\n[10] Creating and approving approval request...")
        approval = ApprovalRequest(
            approval_request_id=new_uuid(),
            project_id=project.project_id,
            dependency_id=dep_fabric.dependency_id,
            requested_by_actor_id=manufacturer_m.actor_id,
            approval_mode="human",
            status="PENDING",
            options_json={"options": [opt_best.option_id, opt_fastest.option_id]},
            created_at=utcnow(), updated_at=utcnow(),
            metadata_json={},
        )
        db.add(approval)
        db.flush()
        event_repo.log_event(
            event_type="UPSTREAM_OPTION_APPROVAL_REQUESTED",
            project_id=project.project_id,
            actor_id=manufacturer_m.actor_id,
            payload_json={"approval_request_id": approval.approval_request_id},
            source_channel="mock",
        )

        approval.status = "APPROVED"
        approval.approved_option_id = opt_best.option_id
        approval.approved_by_actor_id = manufacturer_m.actor_id
        approval.approved_by_mode = "human"
        approval.updated_at = utcnow()
        opt_best.status = "approved"
        db.flush()
        event_repo.log_event(
            event_type="UPSTREAM_OPTION_APPROVED",
            project_id=project.project_id,
            actor_id=manufacturer_m.actor_id,
            payload_json={"approved_option_id": opt_best.option_id, "option_label": "BEST"},
            source_channel="mock",
        )
        print(f"    OK: approval_request_id={approval.approval_request_id} → APPROVED (BEST option)")

        # Step 11: Supplier Response Rollup
        print("\n[11] Creating Supplier Response Rollup...")
        rollup = rollup_repo.create_rollup(
            project_id=project.project_id,
            main_supplier_actor_id=manufacturer_m.actor_id,
            can_accept_order=True,
            main_capacity_summary="M has capacity for 100pcs shirts in 21 days.",
            approved_upstream_options_json={
                "fabric": {"option_id": opt_best.option_id, "actor_id": fabric_f1.actor_id}
            },
            material_basis_json={"fabric": "cotton 160gsm from F1"},
            trim_basis_json={"buttons": "white buttons from T1 TBD"},
            completeness_score=0.85,
            confidence_score=0.88,
            recommended_response_to_buyer_en="M can supply 100pcs cotton shirts. Price USD18/pc, lead time 21 days.",
            recommended_response_to_buyer_zh="M可供应100件棉质衬衫，单价USD18，交货期21天。",
        )
        event_repo.log_event(
            event_type="SUPPLIER_RESPONSE_ROLLUP_GENERATED",
            project_id=project.project_id,
            actor_id=manufacturer_m.actor_id,
            payload_json={"rollup_id": rollup.rollup_id},
            source_channel="mock",
        )
        print(f"    OK: rollup_id={rollup.rollup_id}")

        # Step 12: Rollup submitted back to B-side as SupplierResponse
        print("\n[12] Submitting rollup back to B-side as SupplierResponse...")
        final_response = response_repo.create_supplier_response(
            project_id=project.project_id,
            edge_id=buyer_supplier_edge.edge_id,
            from_actor_id=manufacturer_m.actor_id,
            to_actor_id=buyer_b.actor_id,
            inquiry_id=inquiry.inquiry_id,
            can_supply=True,
            price=18.0, currency="USD",
            lead_time_days=21,
            earliest_dispatch_date="2026-06-20",
            confidence_score=0.88,
            completeness_score=0.85,
            parsed_json={"rollup_id": rollup.rollup_id, "can_accept_order": True},
        )
        graph_repo.update_edge_status(buyer_supplier_edge.edge_id, "RESPONDED")
        project_repo.update_project_status(project.project_id, "SUPPLIER_RESPONSE_SUBMITTED_TO_BUYER")
        event_repo.log_event(
            event_type="SUPPLIER_RESPONSE_ROLLUP_SUBMITTED_TO_B_SIDE",
            project_id=project.project_id,
            edge_id=buyer_supplier_edge.edge_id,
            actor_id=manufacturer_m.actor_id,
            payload_json={"response_id": final_response.response_id, "rollup_id": rollup.rollup_id},
            source_channel="mock",
        )
        print(f"    OK: final_response_id={final_response.response_id}")

        db.commit()

        # Step 13: Verify ExecutionEvents for all major transitions
        print("\n[13] Verifying ExecutionEvents for all major transitions...")
        events = event_repo.list_project_events(project.project_id)
        event_types_found = {e.event_type for e in events}
        required_events = {
            "B_INQUIRY_CREATED",
            "ROLE_CONTEXT_RESOLVED",
            "M_SIDE_RECEIVED_BUYER_INQUIRY",
            "UPSTREAM_DEPENDENCY_PLANNED",
            "UPSTREAM_INQUIRY_CREATED",
            "UPSTREAM_INQUIRY_DISPATCHED",
            "UPSTREAM_RESPONSE_RECEIVED",
            "UPSTREAM_RESPONSE_PARSED",
            "UPSTREAM_OPTIONS_GENERATED",
            "UPSTREAM_OPTION_APPROVAL_REQUESTED",
            "UPSTREAM_OPTION_APPROVED",
            "SUPPLIER_RESPONSE_ROLLUP_GENERATED",
            "SUPPLIER_RESPONSE_ROLLUP_SUBMITTED_TO_B_SIDE",
            "ROLE_SWITCH_OCCURRED",
        }
        missing = required_events - event_types_found
        assert not missing, f"Missing events: {missing}"
        print(f"    OK: {len(events)} events found. All required types present.")

        # Verify M has two roles
        m_roles = role_repo.list_actor_roles_in_project(project.project_id, manufacturer_m.actor_id)
        role_types = {r.role for r in m_roles}
        assert "MAIN_M_SIDE" in role_types, "MAIN_M_SIDE role missing"
        assert "UPSTREAM_B_SIDE" in role_types, "UPSTREAM_B_SIDE role missing"
        print(f"    OK: Manufacturer M has roles: {role_types}")

        # Verify project status updated
        reloaded = project_repo.get_project(project.project_id)
        assert reloaded.status == "SUPPLIER_RESPONSE_SUBMITTED_TO_BUYER"
        print(f"    OK: Project status = {reloaded.status}")

        print("\n" + "=" * 60)
        print("ROLE-SWITCHING TEST PASSED: All 13 steps completed.")
        print("=" * 60)

    except Exception as e:
        db.rollback()
        print(f"\nROLE-SWITCHING TEST FAILED: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
