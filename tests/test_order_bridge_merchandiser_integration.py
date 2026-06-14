"""Tests for order bridge to merchandiser integration."""
import pytest
from unittest.mock import patch, MagicMock
from src.merchandiser.merchandiser_engine import (
    create_post_confirmation_execution, find_execution_plan_by_order_id,
    find_execution_plan_by_project_id,
)
from src.merchandiser.task_planner import get_tasks_for_project
from src.merchandiser.milestone_manager import get_milestones_for_project


_PROJECT = "proj-bridge-test-01"
_SUP = "sup-bridge-001"
_BUY = "buy-bridge-001"
_ORDER = "OE-BRIDGE-001"


def test_create_post_confirmation_execution_basic():
    plan = create_post_confirmation_execution(
        project_id=_PROJECT,
        order_id=_ORDER,
        supplier_actor_id=_SUP,
        buyer_actor_id=_BUY,
        category="apparel",
        source="test_bridge",
    )
    assert plan.plan_id.startswith("EXECPLAN-")
    assert plan.project_id == _PROJECT
    assert plan.order_id == _ORDER
    assert plan.supplier_actor_id == _SUP
    assert plan.buyer_actor_id == _BUY


def test_execution_plan_creates_tasks():
    proj = "proj-bridge-test-02"
    plan = create_post_confirmation_execution(
        project_id=proj,
        order_id="OE-BRIDGE-002",
        supplier_actor_id=_SUP,
        buyer_actor_id=_BUY,
        category="apparel",
        source="test",
    )
    assert len(plan.task_ids) > 0
    tasks = get_tasks_for_project(proj)
    assert len(tasks) > 0


def test_execution_plan_creates_milestones():
    proj = "proj-bridge-test-03"
    plan = create_post_confirmation_execution(
        project_id=proj,
        order_id="OE-BRIDGE-003",
        supplier_actor_id=_SUP,
        buyer_actor_id=_BUY,
        category="apparel",
        source="test",
    )
    assert len(plan.milestone_ids) > 0
    milestones = get_milestones_for_project(proj)
    assert len(milestones) > 0


def test_find_execution_plan_by_order_id():
    import uuid as _uuid
    proj = "proj-bridge-test-04"
    order = f"OE-BRIDGE-FIND-{_uuid.uuid4().hex[:6].upper()}"
    plan = create_post_confirmation_execution(
        project_id=proj,
        order_id=order,
        supplier_actor_id=_SUP,
        buyer_actor_id=_BUY,
        source="test",
    )
    found = find_execution_plan_by_order_id(order)
    assert found is not None
    assert found.order_id == order


def test_find_execution_plan_by_project_id():
    proj = "proj-bridge-test-05"
    plan = create_post_confirmation_execution(
        project_id=proj,
        order_id="OE-BRIDGE-005",
        supplier_actor_id=_SUP,
        buyer_actor_id=_BUY,
        source="test",
    )
    found = find_execution_plan_by_project_id(proj)
    assert found is not None
    assert found.project_id == proj


def test_find_execution_plan_by_order_id_not_found():
    result = find_execution_plan_by_order_id("OE-DOES-NOT-EXIST-XYZ")
    assert result is None


def test_find_execution_plan_by_project_id_not_found():
    result = find_execution_plan_by_project_id("proj-does-not-exist-xyz-9999")
    assert result is None


def test_cnc_category_creates_appropriate_milestones():
    proj = "proj-bridge-cnc-01"
    plan = create_post_confirmation_execution(
        project_id=proj,
        order_id="OE-CNC-001",
        supplier_actor_id=_SUP,
        buyer_actor_id=_BUY,
        category="cnc_machining",
        source="test",
    )
    milestones = get_milestones_for_project(proj)
    types = {m.milestone_type for m in milestones}
    assert "machining" in types


def test_execution_plan_initial_state():
    proj = "proj-bridge-test-06"
    plan = create_post_confirmation_execution(
        project_id=proj,
        order_id="OE-BRIDGE-006",
        supplier_actor_id=_SUP,
        buyer_actor_id=_BUY,
        source="test",
    )
    assert plan.current_order_state == "ORDER_CONFIRMED"


def test_plan_has_both_b_and_m_tasks():
    proj = "proj-bridge-test-07"
    plan = create_post_confirmation_execution(
        project_id=proj,
        order_id="OE-BRIDGE-007",
        supplier_actor_id=_SUP,
        buyer_actor_id=_BUY,
        source="test",
    )
    tasks = get_tasks_for_project(proj)
    sides = {t.assigned_side for t in tasks}
    assert "B_SIDE" in sides
    assert "M_SIDE" in sides
