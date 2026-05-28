"""
Smoke Test 1: Database Basics
1. Initialize database.
2. Create actors.
3. Create project.
4. Create buyer-to-main-supplier edge.
5. Resolve role contexts.
6. Write execution event.
7. Read data back.
8. Print success.
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
from src.db.repositories.execution_event_repo import ExecutionEventRepo


def run():
    print("=" * 60)
    print("DB SMOKE TEST")
    print("=" * 60)

    # Step 1: Initialize database
    print("\n[1] Initializing database...")
    Base.metadata.create_all(bind=engine)
    print("    OK: All tables created/verified.")

    db = SessionLocal()
    try:
        actor_repo = ActorRepo(db)
        project_repo = ProjectRepo(db)
        graph_repo = GraphRepo(db)
        role_repo = RoleRepo(db)
        event_repo = ExecutionEventRepo(db)

        # Step 2: Create actors
        print("\n[2] Creating actors...")
        buyer = actor_repo.create_actor(name="Test Buyer", actor_type="buyer")
        supplier = actor_repo.create_actor(name="Test Manufacturer", actor_type="manufacturer")
        print(f"    OK: buyer_id={buyer.actor_id}")
        print(f"    OK: supplier_id={supplier.actor_id}")

        # Step 3: Create project
        print("\n[3] Creating project...")
        project = project_repo.create_project(
            original_buyer_actor_id=buyer.actor_id,
            main_supplier_actor_id=supplier.actor_id,
            category="apparel",
            product_summary="Smoke test shirt order",
            quantity=50,
        )
        print(f"    OK: project_id={project.project_id}")

        # Step 4: Create buyer-to-main-supplier edge
        print("\n[4] Creating procurement edge (buyer → main supplier)...")
        edge = graph_repo.create_edge(
            project_id=project.project_id,
            from_actor_id=buyer.actor_id,
            to_actor_id=supplier.actor_id,
            edge_type="BUYER_TO_MAIN_SUPPLIER",
            status="SENT",
        )
        print(f"    OK: edge_id={edge.edge_id}")

        # Step 5: Resolve role contexts
        print("\n[5] Resolving role contexts...")
        buyer_role = role_repo.create_role_context(
            project_id=project.project_id,
            actor_id=buyer.actor_id,
            role="ORIGINAL_BUYER",
            edge_id=edge.edge_id,
            counterparty_actor_id=supplier.actor_id,
            role_reason="Buyer B initiated this project",
        )
        supplier_role = role_repo.create_role_context(
            project_id=project.project_id,
            actor_id=supplier.actor_id,
            role="MAIN_M_SIDE",
            edge_id=edge.edge_id,
            counterparty_actor_id=buyer.actor_id,
            role_reason="Manufacturer M is the main supplier for this project",
            can_create_upstream_inquiry=True,
            can_approve_upstream_option=True,
            can_submit_response_to_buyer=True,
        )
        print(f"    OK: buyer role_context_id={buyer_role.role_context_id} (role={buyer_role.role})")
        print(f"    OK: supplier role_context_id={supplier_role.role_context_id} (role={supplier_role.role})")

        # Step 6: Write execution event
        print("\n[6] Writing execution events...")
        ev1 = event_repo.log_event(
            event_type="ROLE_CONTEXT_RESOLVED",
            project_id=project.project_id,
            edge_id=edge.edge_id,
            actor_id=buyer.actor_id,
            role_context_id=buyer_role.role_context_id,
            payload_json={"role": "ORIGINAL_BUYER"},
            source_channel="mock",
        )
        ev2 = event_repo.log_event(
            event_type="ROLE_CONTEXT_RESOLVED",
            project_id=project.project_id,
            edge_id=edge.edge_id,
            actor_id=supplier.actor_id,
            role_context_id=supplier_role.role_context_id,
            payload_json={"role": "MAIN_M_SIDE"},
            source_channel="mock",
        )
        ev3 = event_repo.log_event(
            event_type="B_INQUIRY_CREATED",
            project_id=project.project_id,
            edge_id=edge.edge_id,
            actor_id=buyer.actor_id,
            payload_json={"inquiry": "smoke test inquiry"},
            source_channel="mock",
        )
        print(f"    OK: event_id={ev1.event_id} (type={ev1.event_type})")
        print(f"    OK: event_id={ev2.event_id} (type={ev2.event_type})")
        print(f"    OK: event_id={ev3.event_id} (type={ev3.event_type})")

        db.commit()

        # Step 7: Read data back
        print("\n[7] Reading data back...")
        loaded_buyer = actor_repo.get_actor(buyer.actor_id)
        loaded_project = project_repo.get_project(project.project_id)
        loaded_edges = graph_repo.get_project_edges(project.project_id)
        loaded_role = role_repo.resolve_role_context(project.project_id, supplier.actor_id, edge.edge_id)
        loaded_events = event_repo.list_project_events(project.project_id)

        assert loaded_buyer is not None, "Buyer not found"
        assert loaded_buyer.name == "Test Buyer"
        assert loaded_project is not None, "Project not found"
        assert loaded_project.status == "CREATED"
        assert len(loaded_edges) == 1, f"Expected 1 edge, got {len(loaded_edges)}"
        assert loaded_edges[0].edge_type == "BUYER_TO_MAIN_SUPPLIER"
        assert loaded_role is not None, "Role context not found"
        assert loaded_role.role == "MAIN_M_SIDE"
        assert len(loaded_events) == 3, f"Expected 3 events, got {len(loaded_events)}"

        print(f"    OK: actor loaded: {loaded_buyer.name}")
        print(f"    OK: project loaded: status={loaded_project.status}")
        print(f"    OK: {len(loaded_edges)} edge(s) loaded")
        print(f"    OK: role context resolved: {loaded_role.role}")
        print(f"    OK: {len(loaded_events)} event(s) loaded")

        # Step 8: Print success
        print("\n" + "=" * 60)
        print("SMOKE TEST PASSED: All 7 steps completed successfully.")
        print("=" * 60)

    except Exception as e:
        db.rollback()
        print(f"\nSMOKE TEST FAILED: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
