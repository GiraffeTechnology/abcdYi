import pytest
from src.gpm.models.gpm_quote_guidance_packet import GPMQuoteGuidancePacket


def _make(**overrides) -> GPMQuoteGuidancePacket:
    defaults = dict(
        supplier_quote_position="above_benchmark",
        recommendation="negotiate",
        benchmark_range={"confidence": "high", "comparable_sample_count": 5},
        negotiation_points=["price too high"],
        buyer_quote_options=[{"option_id": "opt_accept", "label": "Accept"}],
        runtime_profile="ci",
        runtime_mode="mock",
        context_retriever="mock",
        data_mode="public",
    )
    defaults.update(overrides)
    return GPMQuoteGuidancePacket.create(**defaults)


def test_create_sets_packet_id():
    p = _make()
    assert p.packet_id.startswith("gpm_pkt_")


def test_human_approval_required_always_true():
    p = _make()
    assert p.human_approval_required is True


def test_cannot_construct_with_human_approval_required_false():
    with pytest.raises(ValueError, match="human_approval_required"):
        GPMQuoteGuidancePacket(
            packet_id="x", tenant_id=None, project_id=None, rfq_id=None,
            supplier_response_id=None, context_bundle_id=None, evidence_ids=[],
            supplier_quote_position="", recommendation="", benchmark_range={},
            negotiation_points=[], buyer_quote_options=[],
            runtime_profile="ci", runtime_mode="mock", context_retriever="mock",
            data_mode="public", human_approval_required=False,
            operator_action_required=True, approval_status="pending",
            audit_ref=None, created_at="2026-01-01T00:00:00+00:00",
        )


def test_invalid_approval_status_raises():
    with pytest.raises(ValueError, match="approval_status"):
        GPMQuoteGuidancePacket(
            packet_id="x", tenant_id=None, project_id=None, rfq_id=None,
            supplier_response_id=None, context_bundle_id=None, evidence_ids=[],
            supplier_quote_position="", recommendation="", benchmark_range={},
            negotiation_points=[], buyer_quote_options=[],
            runtime_profile="ci", runtime_mode="mock", context_retriever="mock",
            data_mode="public", human_approval_required=True,
            operator_action_required=True, approval_status="bad_status",
            audit_ref=None, created_at="2026-01-01T00:00:00+00:00",
        )


def test_initial_approval_status_is_pending():
    assert _make().approval_status == "pending"


def test_to_dict_roundtrip():
    p = _make(tenant_id="t1", project_id="p1", rfq_id="r1")
    d = p.to_dict()
    assert d["packet_id"] == p.packet_id
    assert d["human_approval_required"] is True
    assert d["approval_status"] == "pending"
    assert d["tenant_id"] == "t1"


def test_unique_packet_ids():
    ids = {_make().packet_id for _ in range(10)}
    assert len(ids) == 10
