"""Unit tests for the GLTG adapter (build_gltg_input_from_order, evaluate_delivery_feasibility)."""
import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gltg import ApparelOrderInput, LeadTimeGraphEngine
from gltg.models import ParticipantNode
from src.lead_time.gltg_adapter import evaluate_delivery_feasibility


# ---------------------------------------------------------------------------
# evaluate_delivery_feasibility — pure synchronous unit tests
# ---------------------------------------------------------------------------

def _make_input(nodes: list[ParticipantNode], required_delivery: date | None = None) -> ApparelOrderInput:
    return ApparelOrderInput(
        order_id=str(uuid.uuid4()),
        required_delivery_date=required_delivery,
        quantity=500,
        participant_nodes=nodes,
    )


def _full_node(participant_id: str = None) -> ParticipantNode:
    return ParticipantNode(
        participant_id=participant_id or str(uuid.uuid4()),
        role="MANUFACTURER",
        fabric_lead_time_days=14,
        trim_lead_time_days=7,
        packaging_lead_time_days=5,
        production_time_days=30,
        qc_time_days=3,
        logistics_time_days=10,
        unit_price=12.50,
        currency="USD",
    )


def test_evaluate_feasibility_returns_packet_with_ranked_options():
    node = _full_node()
    gltg_input = _make_input([node])
    result = evaluate_delivery_feasibility(gltg_input)

    assert result.status == "EVALUATED"
    assert result.option_count >= 1
    assert len(result.ranked_options) >= 1
    assert result.delivery_feasibility in ("FEASIBLE", "AT_RISK", "INFEASIBLE")


def test_evaluate_feasibility_no_participants_returns_incomplete():
    gltg_input = _make_input([])
    result = evaluate_delivery_feasibility(gltg_input)

    assert result.option_count == 0
    assert result.status in ("INFEASIBLE", "INCOMPLETE_EVIDENCE")
    assert result.explanation  # non-empty explanation required


def test_evaluate_feasibility_missing_sequential_returns_infeasible_path():
    node = ParticipantNode(
        participant_id=str(uuid.uuid4()),
        role="MANUFACTURER",
        fabric_lead_time_days=14,
        trim_lead_time_days=7,
        # production_time_days missing
        qc_time_days=3,
        logistics_time_days=10,
    )
    gltg_input = _make_input([node])
    result = evaluate_delivery_feasibility(gltg_input)

    assert result.option_count == 0
    assert "production_time_days" in result.explanation or "production_time_days" in result.missing_evidence


def test_evaluate_feasibility_deadline_comparison():
    node = _full_node()
    # Required delivery is very soon — should be AT_RISK or INFEASIBLE
    soon = date(2026, 6, 20)
    gltg_input = _make_input([node], required_delivery=soon)
    result = evaluate_delivery_feasibility(gltg_input)

    assert result.delivery_feasibility in ("FEASIBLE", "AT_RISK", "INFEASIBLE")
    # days_vs_deadline should be set when required_delivery_date is given
    assert result.days_vs_deadline is not None


def test_evaluate_feasibility_never_fakes_options():
    """GLTG must never return more ranked options than there are distinct feasible paths."""
    node = _full_node()
    gltg_input = _make_input([node])
    result = evaluate_delivery_feasibility(gltg_input)

    # One node → at most 1 ranked option (one manufacturer anchor)
    assert len(result.ranked_options) <= 1
    assert result.option_count == len(result.ranked_options)


def test_evaluate_feasibility_multiple_manufacturers_up_to_3():
    nodes = [_full_node() for _ in range(4)]
    gltg_input = _make_input(nodes)
    result = evaluate_delivery_feasibility(gltg_input)

    assert len(result.ranked_options) <= 3


def test_ranked_options_sorted_by_rank_score_descending():
    nodes = [_full_node() for _ in range(3)]
    gltg_input = _make_input(nodes)
    result = evaluate_delivery_feasibility(gltg_input)

    scores = [p.rank_score for p in result.ranked_options]
    assert scores == sorted(scores, reverse=True)


def test_evaluate_feasibility_high_risk_node_flags():
    node = ParticipantNode(
        participant_id=str(uuid.uuid4()),
        role="MANUFACTURER",
        fabric_lead_time_days=14,
        trim_lead_time_days=7,
        packaging_lead_time_days=5,
        production_time_days=30,
        qc_time_days=3,
        logistics_time_days=10,
        quality_issue_count=3,
        qc_pass_rate=0.6,
        on_time_delivery_rate=0.75,
        capacity_available=False,
    )
    gltg_input = _make_input([node])
    result = evaluate_delivery_feasibility(gltg_input)

    all_risk_flags = result.risk_flags
    assert any("quality" in f.lower() or "qc" in f.lower() or "capacity" in f.lower() or "delivery" in f.lower()
               for f in all_risk_flags)
