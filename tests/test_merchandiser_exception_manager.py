"""Tests for merchandiser exception manager."""
import pytest
from src.merchandiser.exception_manager import (
    raise_exception, raise_order_exception, resolve_exception,
    generate_exception_options, get_exceptions_for_project,
)


_PROJECT = "test-em-proj-01"
_SUP = "sup-em-001"


def test_raise_exception_basic():
    exc = raise_exception(
        project_id=_PROJECT,
        exception_type="capacity_delay",
        description="Factory at capacity for 2 weeks",
        raised_by_actor_id=_SUP,
    )
    assert exc.exception_id.startswith("EXC-")
    assert exc.exception_type == "capacity_delay"
    assert exc.status == "OPEN"


def test_raise_exception_high_risk_auto_severity():
    exc = raise_exception(
        project_id=_PROJECT,
        exception_type="material_shortage",
        description="Cotton fabric out of stock",
    )
    assert exc.severity == "high"
    assert exc.buyer_confirmation_required is True


def test_raise_exception_low_risk():
    exc = raise_exception(
        project_id=_PROJECT,
        exception_type="capacity_delay",
        description="Minor delay",
    )
    assert exc.severity == "medium"
    assert exc.buyer_confirmation_required is False


def test_raise_exception_explicit_severity():
    exc = raise_exception(
        project_id=_PROJECT,
        exception_type="other",
        description="Custom exception",
        severity="low",
    )
    assert exc.severity == "low"


def test_raise_order_exception():
    exc = raise_order_exception(
        project_id=_PROJECT,
        exception_type="logistics_delay",
        description="Package stuck at customs",
        order_id="OE-EM-001",
        raised_by_actor_id=_SUP,
    )
    assert exc.exception_id.startswith("EXC-")
    assert exc.exception_type == "logistics_delay"
    assert exc.project_id == _PROJECT


def test_raise_exception_lead_time_change():
    exc = raise_exception(
        project_id=_PROJECT,
        exception_type="lead_time_change",
        description="Lead time extended by 5 days",
    )
    assert exc.exception_type == "lead_time_change"


def test_resolve_exception():
    exc = raise_exception(
        project_id=_PROJECT,
        exception_type="production_delay",
        description="Production delayed",
    )
    resolved = resolve_exception(exc.exception_id, _PROJECT, resolution="Rescheduled production")
    assert resolved.status == "RESOLVED"
    assert any("Rescheduled" in str(o) for o in resolved.proposed_options)


def test_generate_exception_options_existing():
    exc = raise_exception(
        project_id=_PROJECT,
        exception_type="material_shortage",
        description="No cotton",
        proposed_options=[
            {"option": "A", "description": "Switch to polyester"},
            {"option": "B", "description": "Wait 2 weeks"},
        ],
    )
    options = generate_exception_options(exc.exception_id)
    assert len(options) == 2
    option_descs = [o["description"] for o in options]
    assert "Switch to polyester" in option_descs


def test_generate_exception_options_nonexistent():
    options = generate_exception_options("EXC-DOESNOTEXIST")
    assert len(options) >= 1
    assert all("option" in o for o in options)


def test_get_exceptions_for_project():
    proj = "test-em-proj-02"
    raise_exception(project_id=proj, exception_type="qc_issue", description="QC failed")
    raise_exception(project_id=proj, exception_type="other", description="Other issue")
    exceptions = get_exceptions_for_project(proj)
    assert len(exceptions) >= 2
    types = {e.exception_type for e in exceptions}
    assert "qc_issue" in types


def test_exception_human_review_required():
    exc = raise_exception(
        project_id=_PROJECT,
        exception_type="quality_dispute",
        description="Buyer disputes quality",
    )
    assert exc.human_review_required is True
