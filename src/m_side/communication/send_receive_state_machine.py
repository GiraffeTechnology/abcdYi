"""
M-side Send/Receive state machine — tracks the full inquiry-to-delivery flow.
State persisted in a per-project JSON file under data/communication/states/.
"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from src.m_side.m_event_logger import log_m_event

_DATA_DIR = Path("data/communication/states")

MSideSendReceiveState = Literal[
    "WAITING_FOR_BUYER_INQUIRY",
    "BUYER_INQUIRY_RECEIVED",
    "PREPARING_UPSTREAM_INQUIRIES",
    "AWAITING_MAIN_SUPPLIER_SEND_APPROVAL",
    "SENDING_UPSTREAM_INQUIRIES",
    "WAITING_FOR_UPSTREAM_RESPONSES",
    "UPSTREAM_RESPONSES_RECEIVED",
    "PREPARING_UPSTREAM_OPTIONS",
    "AWAITING_OPTION_APPROVAL",
    "GENERATING_BUYER_ROLLUP",
    "AWAITING_ROLLUP_APPROVAL",
    "SENDING_ROLLUP_TO_BUYER",
    "WAITING_FOR_BUYER_CONFIRMATION",
    "ORDER_CONFIRMED",
    "EXECUTION_IN_PROGRESS",
    "LOGISTICS_HANDOVER_PENDING",
    "LOGISTICS_TRACKING_ACTIVE",
    "BUYER_SIGNOFF_PENDING",
    "CLOSED",
    "EXCEPTION",
]

_VALID_TRANSITIONS: dict[str, list[str]] = {
    "WAITING_FOR_BUYER_INQUIRY": ["BUYER_INQUIRY_RECEIVED"],
    "BUYER_INQUIRY_RECEIVED": ["PREPARING_UPSTREAM_INQUIRIES"],
    "PREPARING_UPSTREAM_INQUIRIES": ["AWAITING_MAIN_SUPPLIER_SEND_APPROVAL"],
    "AWAITING_MAIN_SUPPLIER_SEND_APPROVAL": ["SENDING_UPSTREAM_INQUIRIES"],
    "SENDING_UPSTREAM_INQUIRIES": ["WAITING_FOR_UPSTREAM_RESPONSES"],
    "WAITING_FOR_UPSTREAM_RESPONSES": ["UPSTREAM_RESPONSES_RECEIVED"],
    "UPSTREAM_RESPONSES_RECEIVED": ["PREPARING_UPSTREAM_OPTIONS"],
    "PREPARING_UPSTREAM_OPTIONS": ["AWAITING_OPTION_APPROVAL"],
    "AWAITING_OPTION_APPROVAL": ["GENERATING_BUYER_ROLLUP"],
    "GENERATING_BUYER_ROLLUP": ["AWAITING_ROLLUP_APPROVAL"],
    "AWAITING_ROLLUP_APPROVAL": ["SENDING_ROLLUP_TO_BUYER"],
    "SENDING_ROLLUP_TO_BUYER": ["WAITING_FOR_BUYER_CONFIRMATION"],
    "WAITING_FOR_BUYER_CONFIRMATION": ["ORDER_CONFIRMED"],
    "ORDER_CONFIRMED": ["EXECUTION_IN_PROGRESS"],
    "EXECUTION_IN_PROGRESS": ["LOGISTICS_HANDOVER_PENDING", "EXCEPTION"],
    "LOGISTICS_HANDOVER_PENDING": ["LOGISTICS_TRACKING_ACTIVE"],
    "LOGISTICS_TRACKING_ACTIVE": ["BUYER_SIGNOFF_PENDING"],
    "BUYER_SIGNOFF_PENDING": ["CLOSED"],
    "CLOSED": [],
    "EXCEPTION": ["EXECUTION_IN_PROGRESS", "CLOSED"],
}


class SendReceiveStateMachineRecord(BaseModel):
    machine_id: str
    project_id: str
    current_state: str = "WAITING_FOR_BUYER_INQUIRY"
    history: list[dict] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def _path(project_id: str) -> Path:
    return _DATA_DIR / f"{project_id}_srstate.json"


def create_send_receive_machine(project_id: str) -> SendReceiveStateMachineRecord:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    rec = SendReceiveStateMachineRecord(
        machine_id=f"SRM-{uuid.uuid4().hex[:10].upper()}",
        project_id=project_id,
    )
    _path(project_id).write_text(rec.model_dump_json(indent=2), encoding="utf-8")
    return rec


def get_send_receive_machine(project_id: str) -> SendReceiveStateMachineRecord:
    p = _path(project_id)
    if not p.exists():
        return create_send_receive_machine(project_id)
    return SendReceiveStateMachineRecord.model_validate(json.loads(p.read_text(encoding="utf-8")))


def transition_state(project_id: str, new_state: str, reason: str = "") -> SendReceiveStateMachineRecord:
    rec = get_send_receive_machine(project_id)
    old_state = rec.current_state
    allowed = _VALID_TRANSITIONS.get(old_state, [])
    if new_state not in allowed:
        raise ValueError(f"Invalid transition {old_state} → {new_state}. Allowed: {allowed}")
    rec.history.append({"from": old_state, "to": new_state, "reason": reason,
                         "at": datetime.now(timezone.utc).isoformat()})
    rec.current_state = new_state
    rec.updated_at = datetime.now(timezone.utc).isoformat()
    _path(project_id).write_text(rec.model_dump_json(indent=2), encoding="utf-8")
    log_m_event(
        event_type="M_ROLE_SEND_RECEIVE_STATE_CHANGED",
        b_workspace_id=project_id,
        payload={"from_state": old_state, "to_state": new_state, "reason": reason},
    )
    return rec
