"""Unit tests for DeliveryFeasibilityService."""
import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

from gltg.models import (
    DeliveryFeasibilityPacket as GltgPacket,
    DeliveryPath,
    ApparelOrderInput,
    ParticipantNode,
)
from src.services.delivery_feasibility_service import DeliveryFeasibilityService, _path_to_dict, _packet_to_dict


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_path(participant_id: str = None, total_lt: int = 45) -> DeliveryPath:
    return DeliveryPath(
        path_id=str(uuid.uuid4()),
        participant_ids=[participant_id or str(uuid.uuid4())],
        parallel_max_days=14,
        sequential_days=31,
        total_lead_time_days=total_lt,
        earliest_delivery_date=date(2026, 8, 1),
        most_likely_delivery_date=date(2026, 8, 1),
        risk_adjusted_delivery_date=date(2026, 8, 4),
        committable_delivery_date=date(2026, 8, 9),
        critical_path=["FABRIC_SOURCING", "GARMENT_MANUFACTURING"],
        critical_path_days=total_lt,
        is_feasible=True,
        feasibility_reason="All sequential stages have lead time evidence.",
        risk_flags=[],
        missing_evidence=[],
        unit_price=12.5,
        currency="USD",
        rank_score=0.75,
        recommendation_reason="Best overall feasible path",
        confidence="HIGH",
    )


def _make_gltg_packet(paths: list[DeliveryPath] | None = None) -> GltgPacket:
    paths = paths or [_make_path()]
    return GltgPacket(
        order_id=str(uuid.uuid4()),
        status="EVALUATED",
        earliest_delivery_date=date(2026, 8, 1),
        most_likely_delivery_date=date(2026, 8, 1),
        risk_adjusted_delivery_date=date(2026, 8, 4),
        committable_delivery_date=date(2026, 8, 9),
        delivery_feasibility="FEASIBLE",
        days_vs_deadline=-10,
        critical_path=["FABRIC_SOURCING", "GARMENT_MANUFACTURING"],
        critical_path_days=45,
        ranked_options=paths,
        option_count=len(paths),
        risk_flags=[],
        missing_evidence=[],
        explanation="Best feasible path: 45 days total lead time.",
        confidence="HIGH",
    )


# ---------------------------------------------------------------------------
# _path_to_dict / _packet_to_dict
# ---------------------------------------------------------------------------

def test_path_to_dict_serialises_dates():
    path = _make_path()
    d = _path_to_dict(path)

    assert d["risk_adjusted_delivery_date"] == "2026-08-04"
    assert d["committable_delivery_date"] == "2026-08-09"
    assert isinstance(d["critical_path"], list)


def test_path_to_dict_none_dates_remain_none():
    path = _make_path()
    path.earliest_delivery_date = None
    path.risk_adjusted_delivery_date = None
    d = _path_to_dict(path)

    assert d["earliest_delivery_date"] is None
    assert d["risk_adjusted_delivery_date"] is None


def test_packet_to_dict_includes_ranked_options():
    packet = _make_gltg_packet()
    d = _packet_to_dict(packet)

    assert "ranked_options" in d
    assert len(d["ranked_options"]) == 1
    assert d["option_count"] == 1


# ---------------------------------------------------------------------------
# DeliveryFeasibilityService.evaluate — mocked DB + adapter
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_service_evaluate_persists_record_and_emits_event():
    service = DeliveryFeasibilityService()
    order_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()

    mock_order = MagicMock()
    mock_order.id = order_id
    mock_order.project_id = project_id

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=mock_order)
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()

    gltg_packet = _make_gltg_packet()

    with (
        patch("src.services.delivery_feasibility_service.build_gltg_input_from_order", new_callable=AsyncMock) as mock_build,
        patch("src.services.delivery_feasibility_service.evaluate_delivery_feasibility") as mock_eval,
        patch("src.services.delivery_feasibility_service.emit_event", new_callable=AsyncMock) as mock_emit,
    ):
        mock_build.return_value = ApparelOrderInput(order_id=str(order_id))
        mock_eval.return_value = gltg_packet

        record = await service.evaluate(
            db=mock_db,
            order_id=order_id,
            tenant_id=tenant_id,
            project_id=project_id,
            triggered_by_user_id=user_id,
        )

    mock_db.add.assert_called_once()
    mock_emit.assert_called_once()

    _, emit_kwargs = mock_emit.call_args
    assert emit_kwargs["event_type"] == "DELIVERY_FEASIBILITY_EVALUATED"
    assert emit_kwargs["tenant_id"] == tenant_id
    assert emit_kwargs["order_id"] == order_id


@pytest.mark.asyncio
async def test_service_evaluate_raises_404_when_order_not_found():
    from fastapi import HTTPException
    service = DeliveryFeasibilityService()

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc_info:
        await service.evaluate(
            db=mock_db,
            order_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
        )

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_service_evaluate_stores_gltg_feasibility_fields():
    service = DeliveryFeasibilityService()
    order_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    project_id = uuid.uuid4()

    mock_order = MagicMock()
    mock_order.id = order_id
    mock_order.project_id = project_id

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=mock_order)
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()

    no_options_packet = GltgPacket(
        order_id=str(order_id),
        status="INFEASIBLE",
        delivery_feasibility="INFEASIBLE",
        ranked_options=[],
        option_count=0,
        missing_evidence=["production_time_days"],
        explanation="No feasible delivery path.",
        confidence="LOW",
    )

    captured = {}

    def capture_add(obj):
        captured["record"] = obj

    mock_db.add.side_effect = capture_add

    with (
        patch("src.services.delivery_feasibility_service.build_gltg_input_from_order", new_callable=AsyncMock) as mock_build,
        patch("src.services.delivery_feasibility_service.evaluate_delivery_feasibility") as mock_eval,
        patch("src.services.delivery_feasibility_service.emit_event", new_callable=AsyncMock),
    ):
        mock_build.return_value = ApparelOrderInput(order_id=str(order_id))
        mock_eval.return_value = no_options_packet

        await service.evaluate(
            db=mock_db,
            order_id=order_id,
            tenant_id=tenant_id,
            project_id=project_id,
        )

    rec = captured["record"]
    assert rec.delivery_feasibility == "INFEASIBLE"
    assert rec.option_count == 0
    assert rec.confidence == "LOW"
    assert "production_time_days" in rec.missing_evidence_json
