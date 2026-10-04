"""CAS-persist imported apparel lifecycle records through the selected provider.

A local SQL view is acknowledged only after provider write/readback. Re-import
recovers that view from recorded business facts without conversation context.
"""
from __future__ import annotations
import copy
import math
import hashlib
import json
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import DateTime, Uuid, Boolean, Integer, Float, String, JSON, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool
from src.db.models import (Order, OrderLine, Milestone, ProductionUpdate, ProductionMonitoringPacket,
    ExpediteAlert, QCStandard, QCRecord, QualityIncident, Shipment, ShipmentTrackingEvent,
    SupplierMemoryRecord, ExecutionEvent, UploadedFileMetadata, Participant, User)
from src.db.models.provider_order import ProviderOrderAssociation
from src.db.tenant_scope import get_project_owned
from src.integrations.confirmed_orders import ConfirmedOrderError, ConfirmedOrderProvider

# Foreign-key order; excludes credentials, user tables and unrelated projects.
MODELS = (OrderLine, Milestone, ProductionUpdate, ProductionMonitoringPacket, ExpediteAlert,
          QCStandard, QCRecord, QualityIncident, Shipment, ShipmentTrackingEvent,
          SupplierMemoryRecord, ExecutionEvent, UploadedFileMetadata)
SNAPSHOT_VERSION = "abcdYi.apparel-lifecycle.v1"


def _json(value):
    if isinstance(value, datetime):
        instant = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
        return instant.isoformat().replace("+00:00", "Z")
    if isinstance(value, date): return value.isoformat()
    if isinstance(value, (uuid.UUID, Decimal)): return str(value)
    raise TypeError("Unsupported lifecycle value")


def _row(row):
    return json.loads(json.dumps({c.key: getattr(row, c.key) for c in row.__table__.columns}, default=_json))


def snapshot_hash(snapshot):
    return hashlib.sha256(json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _scope(model, order_id, shipment_ids):
    return model.shipment_id.in_(shipment_ids) if model is ShipmentTrackingEvent else model.order_id == order_id


async def _snapshot(db, order, association):
    await db.refresh(order)
    shipments = list((await db.scalars(select(Shipment.id).where(Shipment.order_id == order.id))).all())
    records = {}
    for model in MODELS:
        rows = (await db.scalars(select(model).where(_scope(model, order.id, shipments)).order_by(model.id))).all()
        records[model.__tablename__] = [_row(row) for row in rows]
        if model is OrderLine:
            for row in records[model.__tablename__]:
                row["attributes"] = _compact_attributes(row["attributes"], association, order)
    return {"schema_version": SNAPSHOT_VERSION, "order": _row(order), "records": records}


def _typed(model, row):
    if not isinstance(row, dict) or set(row) != {c.key for c in model.__table__.columns}:
        raise ConfirmedOrderError("PROVIDER_LIFECYCLE_RECORD_INVALID", 409)
    result = dict(row)
    try:
        for column in model.__table__.columns:
            value = result[column.key]
            if value is None:
                if not column.nullable: raise ValueError("null required field")
            elif isinstance(column.type, Uuid): result[column.key] = uuid.UUID(value)
            elif isinstance(column.type, DateTime): result[column.key] = datetime.fromisoformat(value.replace("Z", "+00:00"))
            elif isinstance(column.type, Boolean):
                if type(value) is not bool: raise ValueError("invalid boolean")
            elif isinstance(column.type, Integer):
                if type(value) is not int: raise ValueError("invalid integer")
            elif isinstance(column.type, Float):
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value): raise ValueError("invalid number")
            elif isinstance(column.type, String):
                if not isinstance(value, str): raise ValueError("invalid text")
            elif isinstance(column.type, JSON) or isinstance(getattr(column.type, "impl", None), JSON):
                if not isinstance(value, (dict, list)): raise ValueError("invalid structured data")
        return result
    except (TypeError, ValueError, AttributeError) as exc:
        raise ConfirmedOrderError("PROVIDER_LIFECYCLE_RECORD_INVALID", 409) from exc


def _confirmed_facts(association):
    try:
        source = association.source_snapshot
        metadata = source["metadata_json"]
        requirement = metadata["confirmed_requirement_snapshot"]["case"]["requirement"]
        option = metadata["confirmed_quote_snapshot"]["metadata_json"]["selected_option"]
        return requirement, option["quote"]["buyer_unit_price"], option["quote"].get("currency") or option["currency"], source["accepted_at"]
    except (KeyError, TypeError) as exc:
        raise ConfirmedOrderError("PROVIDER_CONFIRMED_SNAPSHOT_REQUIRED", 409) from exc


def _requirement_reference(association, order):
    return {"provider_id": association.provider_id, "source_po_id": association.source_po_id,
            "source_snapshot_hash": association.source_snapshot_hash, "form_version_id": str(order.locked_form_version_id)}


def _compact_attributes(attributes, association, order):
    """Replace only the exact deterministic requirement duplicate with its source."""
    requirement, _, _, _ = _confirmed_facts(association)
    if not isinstance(attributes, dict) or attributes.get("form_fields_snapshot") != requirement:
        raise ConfirmedOrderError("PROVIDER_LIFECYCLE_REQUIREMENT_CHANGED", 409)
    result = copy.deepcopy(attributes)
    result.pop("form_fields_snapshot")
    result["confirmed_requirement_source"] = _requirement_reference(association, order)
    return result


def _restore_attributes(attributes, association, order):
    requirement, _, _, _ = _confirmed_facts(association)
    if not isinstance(attributes, dict):
        raise ConfirmedOrderError("PROVIDER_LIFECYCLE_REQUIREMENT_CHANGED", 409)
    result = copy.deepcopy(attributes)
    reference = result.pop("confirmed_requirement_source", None)
    if reference is not None:
        if reference != _requirement_reference(association, order) or "form_fields_snapshot" in result:
            raise ConfirmedOrderError("PROVIDER_LIFECYCLE_REQUIREMENT_CHANGED", 409)
        result["form_fields_snapshot"] = copy.deepcopy(requirement)
    elif result.get("form_fields_snapshot") != requirement:
        raise ConfirmedOrderError("PROVIDER_LIFECYCLE_REQUIREMENT_CHANGED", 409)
    return result


def _time(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if not isinstance(value, datetime):
        raise ConfirmedOrderError("PROVIDER_LIFECYCLE_EVIDENCE_INVALID", 409)
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


async def _validate_business_evidence(db, association, order, values, parsed):
    """A valid hash is integrity evidence, not commercial or QC authorization."""
    requirement, price, currency, accepted_at = _confirmed_facts(association)
    if values["confirmed_at"] is None or _time(values["confirmed_at"]) != _time(accepted_at):
        raise ConfirmedOrderError("PROVIDER_LIFECYCLE_CONFIRMATION_CHANGED", 409)
    lines = parsed[OrderLine]
    if (not lines or sum(row["quantity"] for row in lines) != requirement["quantity"]
            or len({row["line_number"] for row in lines}) != len(lines)):
        raise ConfirmedOrderError("PROVIDER_LIFECYCLE_COMMERCIAL_TERMS_CHANGED", 409)
    for row in lines:
        if (row["quantity"] <= 0 or row["unit"] != "pcs" or row["unit_price"] != price
                or row["currency"] != currency or row["description"] != requirement["product_type"]):
            raise ConfirmedOrderError("PROVIDER_LIFECYCLE_COMMERCIAL_TERMS_CHANGED", 409)
        row["attributes"] = _restore_attributes(row["attributes"], association, order)
    events = parsed[ExecutionEvent]
    if any(not isinstance(event["payload"], dict) for event in events):
        raise ConfirmedOrderError("PROVIDER_LIFECYCLE_EVIDENCE_INVALID", 409)
    by_kind = {}
    for event in events:
        by_kind.setdefault(event["event_type"], []).append(event)
        actor_id = event["triggered_by_user_id"]
        if actor_id is not None:
            actor = await db.get(User, actor_id)
            if actor is None or actor.tenant_id != association.tenant_id:
                raise ConfirmedOrderError("PROVIDER_LIFECYCLE_ACTOR_REQUIRED", 409)
    qc_records = sorted(parsed[QCRecord], key=lambda row: _time(row["inspected_at"] or row["created_at"]))
    status = values["status"]
    advanced = {"QC_PASSED", "READY_TO_SHIP", "SHIPPED", "DELIVERED", "BUYER_SIGNED_OFF"}
    if status != "IN_PRODUCTION" and not any(event["triggered_by_user_id"] is not None for event in by_kind.get("QC_REQUESTED", [])):
        raise ConfirmedOrderError("PROVIDER_LIFECYCLE_QC_EVIDENCE_REQUIRED", 409)
    if status in advanced and (not qc_records or qc_records[-1]["result"] != "QC_PASSED"):
        raise ConfirmedOrderError("PROVIDER_LIFECYCLE_QC_EVIDENCE_REQUIRED", 409)
    if status == "QC_FAILED" and (not qc_records or qc_records[-1]["result"] != "QC_FAILED"):
        raise ConfirmedOrderError("PROVIDER_LIFECYCLE_QC_EVIDENCE_REQUIRED", 409)
    resolution_roles = {"admin", "operator", "approver", "buyer", "quality", "qc", "quality_manager", "production_manager"}
    for record in qc_records:
        result_events = by_kind.get(record["result"], [])
        if not any(event["payload"].get("qc_record_id") == str(record["id"]) and event["triggered_by_user_id"] is not None for event in result_events):
            raise ConfirmedOrderError("PROVIDER_LIFECYCLE_QC_EVIDENCE_REQUIRED", 409)
        if record["result"] == "QC_FAILED" and not (status == "QC_FAILED" and record is qc_records[-1]):
            resolutions = [event for event in by_kind.get("QC_FAILURE_RESOLVED", []) if event["payload"].get("qc_record_id") == str(record["id"])]
            if not any(event["triggered_by_user_id"] is not None
                and event["payload"].get("actor_id") == str(event["triggered_by_user_id"])
                and str(event["payload"].get("actor_role", "")).lower() in resolution_roles
                and event["payload"].get("resolution") == "REWORK"
                and isinstance(event["payload"].get("reason"), str) and event["payload"]["reason"].strip()
                and _time(event["occurred_at"]) >= _time(record["inspected_at"] or record["created_at"])
                for event in resolutions):
                raise ConfirmedOrderError("PROVIDER_LIFECYCLE_QC_RESOLUTION_REQUIRED", 409)
    if status in {"SHIPPED", "DELIVERED", "BUYER_SIGNED_OFF"} and not parsed[Shipment]:
        raise ConfirmedOrderError("PROVIDER_LIFECYCLE_SHIPMENT_REQUIRED", 409)
    if status in {"DELIVERED", "BUYER_SIGNED_OFF"} and not any(
            row["event_type"].upper() in {"DELIVERED", "POD", "PROOF_OF_DELIVERY"} for row in parsed[ShipmentTrackingEvent]):
        raise ConfirmedOrderError("PROVIDER_LIFECYCLE_DELIVERY_REQUIRED", 409)
    if status == "BUYER_SIGNED_OFF":
        if values["buyer_signed_off_at"] is None:
            raise ConfirmedOrderError("PROVIDER_LIFECYCLE_SIGNOFF_REQUIRED", 409)
        signoffs = by_kind.get("BUYER_SIGNED_OFF", [])
        if not any(event["triggered_by_user_id"] is not None
            and event["payload"].get("actor_id") == str(event["triggered_by_user_id"])
            and str(event["payload"].get("actor_role", "")).lower() in {"buyer", "buyer_proxy", "admin"}
            and event["payload"].get("signed_off_at") is not None
            and _time(event["payload"]["signed_off_at"]) == _time(values["buyer_signed_off_at"])
            for event in signoffs):
            raise ConfirmedOrderError("PROVIDER_LIFECYCLE_SIGNOFF_REQUIRED", 409)
    elif values["buyer_signed_off_at"] is not None or parsed[SupplierMemoryRecord]:
        raise ConfirmedOrderError("PROVIDER_LIFECYCLE_SIGNOFF_REQUIRED", 409)


def _envelope_matches(state, association, order):
    return isinstance(state, dict) and all(state.get(k) == v for k, v in {
        "schema_version": "abcdYi.execution.v1", "source_po_id": association.source_po_id,
        "source_quote_id": association.source_quote_id, "source_snapshot_hash": association.source_snapshot_hash,
        "local_order_id": str(order.id), "local_project_id": str(order.project_id),
    }.items()) and isinstance(state.get("projection"), dict) and all(state["projection"].get(k) == v for k, v in {
        "provider_id": association.provider_id, "local_tenant_id": str(association.tenant_id),
    }.items())


async def restore_execution(db, *, association, order, readback):
    """Validate the entire remote graph before refreshing any local record."""
    state = readback.get("state")
    if (not _envelope_matches(state, association, order) or
            readback.get("source_snapshot_hash") != association.source_snapshot_hash or
            readback.get("tenant_id") != association.provider_tenant_id or
            type(readback.get("revision")) is not int or readback["revision"] < association.execution_revision):
        raise ConfirmedOrderError("PROVIDER_LIFECYCLE_IDENTITY_MISMATCH", 409)
    lifecycle = state["projection"].get("lifecycle")
    if lifecycle is None:
        if association.execution_snapshot_hash or readback["revision"] != association.execution_revision:
            raise ConfirmedOrderError("PROVIDER_LIFECYCLE_MISSING", 409)
        return order
    digest = state["projection"].get("lifecycle_hash")
    try:
        valid_hash = isinstance(lifecycle, dict) and snapshot_hash(lifecycle) == digest
    except (TypeError, ValueError):
        valid_hash = False
    if not valid_hash:
        raise ConfirmedOrderError("PROVIDER_LIFECYCLE_HASH_MISMATCH", 409)
    if readback["revision"] == association.execution_revision and association.execution_snapshot_hash:
        if digest != association.execution_snapshot_hash:
            raise ConfirmedOrderError("PROVIDER_LIFECYCLE_REVISION_MISMATCH", 409)
        # Equal provider revision does not prove the local projection is intact.
        try:
            local_matches = snapshot_hash(await _snapshot(db, order, association)) == digest
        except (ConfirmedOrderError, TypeError, ValueError):
            local_matches = False
        if local_matches:
            return order
    if lifecycle.get("schema_version") != SNAPSHOT_VERSION or set(lifecycle) != {"schema_version", "order", "records"}:
        raise ConfirmedOrderError("PROVIDER_LIFECYCLE_SCHEMA_INVALID", 409)
    values = _typed(Order, lifecycle["order"])
    for key in ("id", "project_id", "approved_option_id", "locked_form_version_id", "buyer_participant_id", "order_number"):
        if values[key] != getattr(order, key): raise ConfirmedOrderError("PROVIDER_LIFECYCLE_IDENTITY_MISMATCH", 409)
    if values["status"] not in {"IN_PRODUCTION", "QC_PENDING", "QC_FAILED", "QC_PASSED", "READY_TO_SHIP", "SHIPPED", "DELIVERED", "BUYER_SIGNED_OFF"}:
        raise ConfirmedOrderError("PROVIDER_LIFECYCLE_STATUS_INVALID", 409)
    records = lifecycle.get("records")
    if not isinstance(records, dict) or set(records) != {m.__tablename__ for m in MODELS}:
        raise ConfirmedOrderError("PROVIDER_LIFECYCLE_SCHEMA_INVALID", 409)
    parsed = {}
    for model in MODELS:
        rows = records[model.__tablename__]
        if not isinstance(rows, list): raise ConfirmedOrderError("PROVIDER_LIFECYCLE_RECORD_INVALID", 409)
        parsed[model] = [_typed(model, row) for row in rows]
        ids = [row["id"] for row in parsed[model]]
        if len(ids) != len(set(ids)): raise ConfirmedOrderError("PROVIDER_LIFECYCLE_RECORD_INVALID", 409)
    shipment_ids = {row["id"] for row in parsed[Shipment]}
    model_ids = {model.__tablename__: {row["id"] for row in rows} for model, rows in parsed.items()}
    for model, rows in parsed.items():
        for row in rows:
            if model is ShipmentTrackingEvent:
                if row["shipment_id"] not in shipment_ids: raise ConfirmedOrderError("PROVIDER_LIFECYCLE_SCOPE_MISMATCH", 409)
            elif row.get("order_id") != order.id: raise ConfirmedOrderError("PROVIDER_LIFECYCLE_SCOPE_MISMATCH", 409)
            if row.get("tenant_id", association.tenant_id) != association.tenant_id or row.get("project_id") not in {None, order.project_id}:
                raise ConfirmedOrderError("PROVIDER_LIFECYCLE_SCOPE_MISMATCH", 409)
            existing = await db.get(model, row["id"])
            if existing is not None:
                if model is ShipmentTrackingEvent:
                    shipment = await db.get(Shipment, existing.shipment_id)
                    owner = shipment.order_id if shipment else None
                else: owner = existing.order_id
                if owner != order.id: raise ConfirmedOrderError("PROVIDER_LIFECYCLE_IDENTITY_CONFLICT", 409)
            for column in model.__table__.columns:
                for fk in column.foreign_keys:
                    value = row[column.key]
                    if value is None: continue
                    target = fk.column.table.name
                    if target in model_ids and value not in model_ids[target]:
                        raise ConfirmedOrderError("PROVIDER_LIFECYCLE_REFERENCE_INVALID", 409)
                    if target == "participants":
                        participant = await db.get(Participant, value)
                        if participant is None or participant.tenant_id != association.tenant_id:
                            raise ConfirmedOrderError("PROVIDER_LIFECYCLE_PARTICIPANT_REQUIRED", 409)
    try:
        await _validate_business_evidence(db, association, order, values, parsed)
    except (TypeError, ValueError, KeyError, AttributeError) as exc:
        raise ConfirmedOrderError("PROVIDER_LIFECYCLE_EVIDENCE_INVALID", 409) from exc
    old_shipments = list((await db.scalars(select(Shipment.id).where(Shipment.order_id == order.id))).all())
    for model in reversed(MODELS):
        await db.execute(delete(model).where(_scope(model, order.id, old_shipments)).execution_options(synchronize_session="fetch"))
    for key, value in values.items(): setattr(order, key, value)
    await db.flush()
    for model in MODELS:
        db.add_all([model(**row) for row in parsed[model]])
        await db.flush()
    association.execution_revision = readback["revision"]
    association.execution_snapshot_hash = digest
    return order


async def commit_execution(db: AsyncSession, *, tenant_id: uuid.UUID, user_id: uuid.UUID,
                           order_id: uuid.UUID, provider: ConfirmedOrderProvider | None = None):
    """Provider-backed orders fail closed; standalone SQL orders remain local."""
    try:
        order = await get_project_owned(db, Order, order_id, tenant_id)
        if order is None: raise HTTPException(status_code=404, detail="Order not found")
        association = await db.scalar(select(ProviderOrderAssociation).where(
            ProviderOrderAssociation.order_id == order_id, ProviderOrderAssociation.tenant_id == tenant_id).with_for_update())
        if association is None:
            await db.commit()
            return
        provider = provider or db.info.get("confirmed_order_provider") or ConfirmedOrderProvider(local_tenant_id=str(tenant_id))
        if provider.provider_id != association.provider_id or provider.tenant_id != association.provider_tenant_id:
            raise ConfirmedOrderError("PROVIDER_EXECUTION_IDENTITY_MISMATCH", 409)
        current = await run_in_threadpool(provider.get_execution, association.source_po_id)
        if (current.get("revision") != association.execution_revision or
                not _envelope_matches(current.get("state"), association, order) or
                current.get("source_snapshot_hash") != association.source_snapshot_hash or
                current["state"]["projection"].get("lifecycle_hash") != association.execution_snapshot_hash):
            raise ConfirmedOrderError("PROVIDER_EXECUTION_CONFLICT_REIMPORT", 409)
        await db.flush()
        snapshot = await _snapshot(db, order, association)
        actor = await db.get(User, user_id)
        if actor is None or not actor.is_active or actor.tenant_id != tenant_id:
            raise ConfirmedOrderError("PROVIDER_LIFECYCLE_ACTOR_REQUIRED", 403)
        parsed = {model: [_typed(model, row) for row in snapshot["records"][model.__tablename__]] for model in MODELS}
        try:
            await _validate_business_evidence(db, association, order, _typed(Order, snapshot["order"]), parsed)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            raise ConfirmedOrderError("PROVIDER_LIFECYCLE_EVIDENCE_INVALID", 409) from exc
        digest = snapshot_hash(snapshot)
        if digest == association.execution_snapshot_hash:
            await db.commit()
            return
        state = {**current["state"], "operator_id": str(user_id), "recorded_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                 "projection": {**current["state"]["projection"], "lifecycle": snapshot, "lifecycle_hash": digest}}
        readback = await run_in_threadpool(provider.persist_execution, association.source_po_id, association.execution_revision, state)
        association.execution_revision = readback["revision"]
        association.execution_snapshot_hash = digest
        await db.commit()
    except ConfirmedOrderError as exc:
        await db.rollback()
        raise HTTPException(status_code=exc.status_code, detail={"error": exc.code}) from exc
    except Exception:
        await db.rollback()
        raise


async def refresh_execution(db: AsyncSession, *, tenant_id: uuid.UUID, order_id: uuid.UUID):
    """Reconcile the authoritative provider before an HTTP read or mutation."""
    association = await db.scalar(select(ProviderOrderAssociation).where(
        ProviderOrderAssociation.order_id == order_id, ProviderOrderAssociation.tenant_id == tenant_id).with_for_update())
    if association is None:
        return
    try:
        order = await get_project_owned(db, Order, order_id, tenant_id)
        if order is None:
            raise HTTPException(status_code=404, detail='Order not found')
        provider = db.info.get('confirmed_order_provider') or ConfirmedOrderProvider(local_tenant_id=str(tenant_id))
        if provider.provider_id != association.provider_id or provider.tenant_id != association.provider_tenant_id:
            raise ConfirmedOrderError('PROVIDER_EXECUTION_IDENTITY_MISMATCH',409)
        readback = await run_in_threadpool(provider.get_execution,association.source_po_id)
        await restore_execution(db,association=association,order=order,readback=readback)
        await db.commit()
    except ConfirmedOrderError as exc:
        await db.rollback()
        raise HTTPException(status_code=exc.status_code,detail={'error':exc.code}) from exc
    except Exception:
        await db.rollback()
        raise
