"""
Stub test for LT-09: reliability fields not populated by gltg_adapter.

build_gltg_input_from_order constructs ParticipantNode objects from RFQ
responses but never copies qc_pass_rate, on_time_delivery_rate, or
quality_issue_count from the participant's ParticipantProfile.

Because the engine weights these fields at 50 % of rank_score (0.3 + 0.2),
all ranking runs with zero reliability contribution, permanently biasing
selection toward speed regardless of quality history.

Mark the test xfail until the adapter is fixed.  Once the adapter maps the
profile fields onto the node, remove the xfail and supply a real async DB
fixture (see comment inside).
"""
import pytest
import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

from gltg.models import ApparelOrderInput, ParticipantNode


@pytest.mark.xfail(
    reason=(
        "not yet covered: LT-09 build_gltg_input_from_order does not map "
        "ParticipantProfile.qc_pass_rate / on_time_delivery_rate / quality_issue_count "
        "onto ParticipantNode"
    )
)
async def test_adapter_maps_reliability_fields_from_participant_profile():
    """
    The adapter must copy reliability metrics from ParticipantProfile onto the
    constructed ParticipantNode so the engine can include them in rank_score.

    Test plan when implemented
    --------------------------
    1. Insert a ParticipantProfile with qc_pass_rate=0.97, on_time_delivery_rate=0.92,
       quality_issue_count=2 into a test DB (use the async_db fixture from conftest).
    2. Call ``build_gltg_input_from_order(db, order, rfq_id=...)``.
    3. Assert the resulting ParticipantNode carries those values.

    Currently the adapter hardcodes these to None (the dataclass default), so
    the assertions below will fail → xfail.
    """
    from src.lead_time.gltg_adapter import build_gltg_input_from_order

    # Lightweight mock — replace with a real async_db fixture once LT-09 is fixed.
    db = AsyncMock()
    order = MagicMock()
    order.id = uuid.uuid4()
    order.required_delivery_date = date(2026, 12, 31)
    order.quantity = 500

    profile = MagicMock()
    profile.qc_pass_rate = 0.97
    profile.on_time_delivery_rate = 0.92
    profile.quality_issue_count = 2

    lead_time_pkt = MagicMock()
    lead_time_pkt.role = "manufacturer"
    lead_time_pkt.fabric_lead_time_days = 15
    lead_time_pkt.trim_lead_time_days = 10
    lead_time_pkt.packaging_lead_time_days = 7
    lead_time_pkt.production_time_days = 20
    lead_time_pkt.qc_time_days = 3
    lead_time_pkt.logistics_time_days = 5

    rfq_resp = MagicMock()
    rfq_resp.participant_id = uuid.uuid4()
    rfq_resp.participant = MagicMock()
    rfq_resp.participant.profile = profile
    rfq_resp.lead_time_packet = lead_time_pkt

    # Patch the adapter's internal DB-load helpers at the module level.
    # Adjust the patch targets if the adapter uses different helper names.
    with (
        patch("src.lead_time.gltg_adapter._load_rfq_responses", new=AsyncMock(return_value=[rfq_resp])),
        patch("src.lead_time.gltg_adapter._load_form_fields", new=AsyncMock(return_value={})),
        patch("src.lead_time.gltg_adapter._load_milestone_updates", new=AsyncMock(return_value=[])),
    ):
        gltg_input = await build_gltg_input_from_order(db, order, rfq_id=uuid.uuid4())

    assert len(gltg_input.participant_nodes) == 1
    node = gltg_input.participant_nodes[0]

    assert node.qc_pass_rate == pytest.approx(0.97), (
        "qc_pass_rate must be copied from ParticipantProfile; currently None"
    )
    assert node.on_time_delivery_rate == pytest.approx(0.92), (
        "on_time_delivery_rate must be copied from ParticipantProfile; currently None"
    )
    assert node.quality_issue_count == 2, (
        "quality_issue_count must be copied from ParticipantProfile; currently None"
    )
