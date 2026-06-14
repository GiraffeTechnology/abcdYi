"""Tests for merchandiser task planner."""
import pytest
from src.merchandiser.task_planner import (
    create_task, complete_task, get_tasks_for_project,
    get_pending_task, complete_task_by_type, mark_overdue_tasks,
    plan_tasks_after_confirmation,
)


_PROJECT = "test-tp-proj-01"
_SUP = "sup-tp-001"
_BUY = "buy-tp-001"


def test_create_task_basic():
    t = create_task(
        project_id=_PROJECT,
        task_type="supplier_acceptance",
        assigned_side="M_SIDE",
        assigned_actor_id=_SUP,
    )
    assert t.task_id.startswith("TASK-")
    assert t.task_type == "supplier_acceptance"
    assert t.status == "PENDING"
    assert t.assigned_side == "M_SIDE"


def test_create_task_with_order_id():
    t = create_task(
        project_id=_PROJECT,
        task_type="logistics_handover",
        assigned_side="M_SIDE",
        order_id="OE-TEST-001",
        priority="high",
    )
    assert t.order_id == "OE-TEST-001"
    assert t.priority == "high"


def test_create_task_b_side():
    t = create_task(
        project_id=_PROJECT,
        task_type="buyer_signoff",
        assigned_side="B_SIDE",
        assigned_actor_id=_BUY,
    )
    assert t.assigned_side == "B_SIDE"
    assert t.task_type == "buyer_signoff"


def test_get_tasks_for_project():
    proj = "test-tp-proj-02"
    create_task(project_id=proj, task_type="supplier_acceptance", assigned_side="M_SIDE")
    create_task(project_id=proj, task_type="qc_update", assigned_side="M_SIDE")
    tasks = get_tasks_for_project(proj)
    types = {t.task_type for t in tasks}
    assert "supplier_acceptance" in types
    assert "qc_update" in types


def test_complete_task():
    proj = "test-tp-proj-03"
    t = create_task(project_id=proj, task_type="material_confirmation", assigned_side="M_SIDE")
    done = complete_task(t.task_id, proj)
    assert done.status == "DONE"


def test_get_pending_task_found():
    proj = "test-tp-proj-04"
    create_task(project_id=proj, task_type="milestone_media_upload", assigned_side="M_SIDE", assigned_actor_id=_SUP)
    found = get_pending_task(proj, "milestone_media_upload", _SUP)
    assert found is not None
    assert found.task_type == "milestone_media_upload"


def test_get_pending_task_not_found():
    proj = "test-tp-proj-05"
    result = get_pending_task(proj, "supplier_memory_update")
    assert result is None


def test_complete_task_by_type():
    proj = "test-tp-proj-06"
    create_task(project_id=proj, task_type="packaging_update", assigned_side="M_SIDE", assigned_actor_id=_SUP)
    done = complete_task_by_type(proj, "packaging_update", _SUP, payload={"notes": "done"})
    assert done is not None
    assert done.status == "DONE"
    assert done.payload.get("notes") == "done"


def test_complete_task_by_type_missing():
    proj = "test-tp-proj-07"
    result = complete_task_by_type(proj, "tracking_update")
    assert result is None


def test_mark_overdue_tasks_future_due_date():
    proj = "test-tp-proj-08"
    t = create_task(project_id=proj, task_type="qc_update", assigned_side="M_SIDE")
    t.due_at = "2099-01-01T00:00:00+00:00"
    from pathlib import Path
    from src.merchandiser.task_planner import _DATA_DIR
    (Path(_DATA_DIR) / f"{t.task_id}.json").write_text(t.model_dump_json(indent=2), encoding="utf-8")
    overdue = mark_overdue_tasks(now="2025-01-01T00:00:00+00:00")
    assert all(o.task_id != t.task_id for o in overdue)


def test_plan_tasks_after_confirmation():
    proj = "test-tp-proj-09"
    tasks = plan_tasks_after_confirmation(
        project_id=proj,
        order_id="OE-PLAN-001",
        supplier_actor_id=_SUP,
        buyer_actor_id=_BUY,
        category="apparel",
    )
    assert len(tasks) >= 5
    types = {t.task_type for t in tasks}
    assert "supplier_acceptance" in types
    assert "buyer_signoff" in types
    assert "logistics_handover" in types


def test_plan_tasks_system_task_included():
    proj = "test-tp-proj-10"
    tasks = plan_tasks_after_confirmation(
        project_id=proj,
        order_id="OE-PLAN-002",
        supplier_actor_id=_SUP,
        buyer_actor_id=_BUY,
    )
    sides = {t.assigned_side for t in tasks}
    assert "SYSTEM" in sides
