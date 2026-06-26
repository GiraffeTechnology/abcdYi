"""
Stub tests for GLTG engine date-buffer behaviour.

All tests are marked xfail because the scenarios they cover are not yet
tested by the existing suite.  Remove the xfail marker (and flesh out the
fixture where noted) once the defect is fixed.

Scenarios covered
-----------------
- LT-05a: risk_adjusted buffer is hardcoded to 3 d; no per-call override
- LT-05b: committable buffer is hardcoded to 5 d; no per-call override
- LT-08:  _compute_milestone_delay uses max() instead of sum() across
           independent DELAYED milestones
"""
import pytest
from datetime import date

from gltg.engine import LeadTimeGraphEngine
from gltg.models import ApparelOrderInput, ParticipantNode


def _minimal_order(today: date, milestone_updates: list[dict] | None = None) -> ApparelOrderInput:
    """Single full-data manufacturer node; deadline is one year out."""
    return ApparelOrderInput(
        order_id="order-buf-test",
        required_delivery_date=date(today.year + 1, today.month, today.day),
        quantity=200,
        participant_nodes=[
            ParticipantNode(
                participant_id="mfr-1",
                role="manufacturer",
                fabric_lead_time_days=10,
                trim_lead_time_days=8,
                packaging_lead_time_days=5,
                production_time_days=20,
                qc_time_days=3,
                logistics_time_days=7,
            )
        ],
        dependency_edges=[],
        milestone_updates=milestone_updates or [],
        form_fields={},
        evaluated_at=today,
    )


@pytest.mark.xfail(reason="not yet covered: LT-05 risk_buffer_days is hardcoded to 3; no per-call override exists")
def test_risk_buffer_is_configurable_per_call():
    """
    When the caller passes risk_buffer_days=0 the risk-adjusted date must equal
    most_likely.  Currently LeadTimeGraphEngine.evaluate() accepts no such kwarg
    and the module constant _RISK_ADJ_BUFFER_DAYS=3 is always applied, so this
    test raises TypeError → xfail.
    """
    engine = LeadTimeGraphEngine()
    inp = _minimal_order(date(2026, 1, 1))
    packet = engine.evaluate(inp, risk_buffer_days=0)  # TypeError: unexpected keyword argument
    best = packet.ranked_options[0]
    assert best.risk_adjusted_delivery_date == best.most_likely_delivery_date


@pytest.mark.xfail(reason="not yet covered: LT-05 committable_buffer_days is hardcoded to 5; no per-call override exists")
def test_committable_buffer_is_configurable_per_call():
    """
    When the caller passes committable_buffer_days=0 the committable date must
    equal risk_adjusted.  Same root cause as LT-05a.
    """
    engine = LeadTimeGraphEngine()
    inp = _minimal_order(date(2026, 1, 1))
    packet = engine.evaluate(inp, committable_buffer_days=0)  # TypeError: unexpected keyword argument
    best = packet.ranked_options[0]
    assert best.committable_delivery_date == best.risk_adjusted_delivery_date


@pytest.mark.xfail(
    reason=(
        "not yet covered: LT-08 _compute_milestone_delay takes max() across DELAYED milestones; "
        "independent delays must accumulate via sum()"
    )
)
def test_two_independent_delayed_milestones_accumulate_via_sum():
    """
    Given two independently delayed milestones (fabric +3 d, trim +5 d) the total
    delay applied to most_likely must be 8 d (sum), not 5 d (max).

    With the current max() implementation both packets land on the same date
    (max of single-delay packet == max of two-delay packet == 5 d), so the
    strictly-greater assertion below fails → xfail.

    When LT-08 is fixed to use sum(), pkt_two.most_likely will be 3 d later
    than pkt_one.most_likely and the test turns green.
    """
    today = date(2026, 3, 1)
    engine = LeadTimeGraphEngine()

    pkt_one = engine.evaluate(
        _minimal_order(
            today,
            milestone_updates=[
                {"name": "trim_ready", "status": "DELAYED", "delay_days": 5},
            ],
        )
    )
    pkt_two = engine.evaluate(
        _minimal_order(
            today,
            milestone_updates=[
                {"name": "fabric_ready", "status": "DELAYED", "delay_days": 3},
                {"name": "trim_ready", "status": "DELAYED", "delay_days": 5},
            ],
        )
    )

    # With sum: pkt_two adds 8 d → most_likely 3 d later than pkt_one (5 d).
    # With max (current): both add 5 d → same date → assertion fails.
    assert (
        pkt_two.ranked_options[0].most_likely_delivery_date
        > pkt_one.ranked_options[0].most_likely_delivery_date
    ), "two independent delays must push most_likely further than a single delay of the same maximum"
