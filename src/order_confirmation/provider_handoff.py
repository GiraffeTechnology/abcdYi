"""Import a provider-confirmed apparel PO into the existing execution model.

The selected provider remains authoritative for the confirmed source and import
association. The existing execution database owns subsequent local lifecycle
records. Import replay never resets or reconstructs progressed lifecycle data.
"""
from __future__ import annotations

import copy
import math
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from src.db.models.decision import DecisionOption, DecisionPacket
from src.db.models.dynamic_form import DynamicOrderForm, DynamicOrderFormVersion
from src.db.models.order import Order, OrderLine
from src.db.models.participant import Participant, ParticipantRole
from src.db.models.production import Milestone
from src.db.models.project import Project
from src.db.models.provider_order import ProviderOrderAssociation
from src.db.models.tenant import Tenant
from src.execution_graph.writer import emit_event
from src.integrations.confirmed_orders import ConfirmedOrderError, ConfirmedOrderProvider, require_id
from src.milestones.constants import ORDERED_MILESTONES


def _human_authorization(metadata: dict) -> None:
    authorization = metadata.get("human_authorization")
    if not isinstance(authorization, dict) or any(not isinstance(authorization.get(key), str) or not authorization[key].strip()
            for key in ("actor_id", "actor_role", "authorization_basis")):
        raise ConfirmedOrderError("CONFIRMED_HUMAN_AUTHORIZATION_REQUIRED", 409)
    if authorization["actor_role"] not in {"approver", "buyer", "operator", "admin", "procurement", "sales"}:
        raise ConfirmedOrderError("CONFIRMED_HUMAN_AUTHORIZATION_REQUIRED", 409)


def _source(order: dict) -> tuple[dict, dict, datetime]:
    for key in ("selected_quote_id", "procurement_case_id", "rfq_id", "buyer_id", "supplier_id"):
        require_id(order.get(key))
    metadata = order.get("metadata_json")
    if not isinstance(metadata, dict) or metadata.get("source_system") != "aivan":
        raise ConfirmedOrderError("AIVAN_CONFIRMED_SOURCE_REQUIRED", 409)
    _human_authorization(metadata)
    require_id(metadata.get("aivan_project_id"))
    require_id(metadata.get("selected_option_id"))
    snapshot = metadata.get("confirmed_requirement_snapshot")
    quote = metadata.get("confirmed_quote_snapshot")
    if not isinstance(snapshot, dict) or not isinstance(quote, dict):
        raise ConfirmedOrderError("CONFIRMED_SOURCE_SNAPSHOT_REQUIRED", 409)
    if any(not isinstance(snapshot.get(part), dict) for part in ("case", "rfq")):
        raise ConfirmedOrderError("CONFIRMED_REQUIREMENT_MISMATCH", 409)
    requirements = [snapshot[part].get("requirement") for part in ("case", "rfq")]
    if any(not isinstance(item, dict) for item in requirements) or requirements[0] != requirements[1]:
        raise ConfirmedOrderError("CONFIRMED_REQUIREMENT_MISMATCH", 409)
    requirement = requirements[0]
    if not isinstance(requirement.get("category"), str) or requirement["category"].lower() not in {"apparel", "textile", "textiles", "garment", "garments"}:
        raise ConfirmedOrderError("APPAREL_TEXTILE_REQUIREMENT_REQUIRED", 409)
    # Aivan preserves the detected source language after canonicalization.
    # That provenance tag is not a content-language assertion. The selected
    # provider's canonical-English write boundary still validates business text.
    if (type(requirement.get("quantity")) is not int or requirement["quantity"] <= 0
            or not isinstance(requirement.get("product_type"), str) or not requirement["product_type"].strip()):
        raise ConfirmedOrderError("CANONICAL_CONFIRMED_REQUIREMENT_REQUIRED", 409)
    if quote.get("quote_id") != order.get("selected_quote_id") or any(quote.get(key) != order.get(key)
            for key in ("procurement_case_id", "rfq_id", "supplier_id")):
        raise ConfirmedOrderError("CONFIRMED_QUOTE_SCOPE_MISMATCH", 409)
    if quote.get("quote_status") != "confirmed" or quote.get("verification_status") != "operator_confirmed":
        raise ConfirmedOrderError("CONFIRMED_QUOTE_REQUIRED", 409)
    quote_metadata = quote.get("metadata_json")
    if not isinstance(quote_metadata, dict):
        raise ConfirmedOrderError("CONFIRMED_QUOTE_REQUIRED", 409)
    _human_authorization(quote_metadata)
    option = quote_metadata.get("selected_option")
    if not isinstance(option, dict) or option.get("option_id") != metadata.get("selected_option_id") or option.get("supplier_id") != order.get("supplier_id"):
        raise ConfirmedOrderError("CONFIRMED_OPTION_MISMATCH", 409)
    price = option.get("quote")
    if not isinstance(price, dict):
        raise ConfirmedOrderError("CONFIRMED_PRICE_REQUIRED", 409)
    if "quantity" in price and (type(price["quantity"]) is not int or price["quantity"] != requirement["quantity"]):
        raise ConfirmedOrderError("CONFIRMED_QUANTITY_MISMATCH", 409)
    unit_price = price.get("buyer_unit_price")
    currency = price.get("currency") or option.get("currency")
    if (not isinstance(unit_price, (int, float)) or isinstance(unit_price, bool) or not math.isfinite(unit_price)
            or unit_price <= 0 or not isinstance(currency, str) or len(currency) != 3 or not currency.isascii() or not currency.isalpha()):
        raise ConfirmedOrderError("CONFIRMED_PRICE_REQUIRED", 409)
    try:
        confirmed_at = datetime.fromisoformat(order["accepted_at"].replace("Z", "+00:00"))
        # The provider's DB timestamp is UTC; SQLite may omit its timezone suffix.
        if confirmed_at.tzinfo is None:
            confirmed_at = confirmed_at.replace(tzinfo=timezone.utc)
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise ConfirmedOrderError("CONFIRMATION_TIME_REQUIRED", 409) from exc
    return copy.deepcopy(requirement), {**copy.deepcopy(option), "currency": currency}, confirmed_at


def _identities(provider: ConfirmedOrderProvider, tenant_id: uuid.UUID, po_id: str) -> dict[str, uuid.UUID]:
    prefix = f"abcdYi:{provider.provider_id}:{provider.tenant_id}:{tenant_id}:{po_id}"
    return {name: uuid.uuid5(uuid.NAMESPACE_URL, f"{prefix}:{name}")
            for name in ("project", "order", "form", "form_version", "packet", "option", "buyer", "supplier")}


async def import_confirmed_order(db: AsyncSession, *, tenant_id: uuid.UUID, user_id: uuid.UUID,
                                 po_id: str, provider: ConfirmedOrderProvider) -> Order:
    po_id = require_id(po_id)
    # Serialize imports in one local tenant; provider CAS also coordinates
    # independent executors. No commercial action is performed by this import.
    tenant = await db.scalar(select(Tenant).where(Tenant.id == tenant_id).with_for_update())
    if tenant is None:
        raise ConfirmedOrderError("TENANT_NOT_FOUND", 404)
    source = await run_in_threadpool(provider.get_order, po_id)
    requirement, selected, confirmed_at = _source(source)
    ids = _identities(provider, tenant_id, po_id)
    existing = await db.get(ProviderOrderAssociation, ids["order"])
    if existing and (existing.tenant_id != tenant_id or existing.source_snapshot_hash != source["source_snapshot_hash"]
                     or existing.provider_tenant_id != provider.tenant_id):
        raise ConfirmedOrderError("CONFIRMED_SOURCE_CHANGED", 409)
    state = {
        "schema_version": "abcdYi.execution.v1", "source_po_id": po_id,
        "source_quote_id": source["selected_quote_id"], "source_snapshot_hash": source["source_snapshot_hash"],
        "local_order_id": str(ids["order"]), "local_project_id": str(ids["project"]),
        "operator_id": str(user_id), "recorded_at": confirmed_at.isoformat(),
        "projection": {"kind": "This record links a confirmed order to apparel production.", "local_tenant_id": str(tenant_id),
                       "provider_id": provider.provider_id},
    }
    readback = await run_in_threadpool(provider.associate, po_id, state)
    persisted = readback.get("state")
    if (readback.get("source_snapshot_hash") != source["source_snapshot_hash"]
            or readback.get("revision", 0) < 1 or not isinstance(persisted, dict)
            or any(persisted.get(key) != state[key] for key in (
                "schema_version", "source_po_id", "source_quote_id", "source_snapshot_hash", "local_order_id", "local_project_id", "projection"))):
        raise ConfirmedOrderError("PROVIDER_ASSOCIATION_NOT_VERIFIED", 409)
    if existing:
        order = await db.get(Order, existing.order_id)
        if order is None:
            raise ConfirmedOrderError("EXECUTION_RECORD_MISSING", 409)
        return order
    if await db.get(Order, ids["order"]) or await db.get(Project, ids["project"]):
        raise ConfirmedOrderError("EXECUTION_IDENTITY_CONFLICT", 409)
    # A fresh local database can recover the initial handoff from the provider.
    # We deliberately do not claim restoration of later execution events.
    project = Project(id=ids["project"], tenant_id=tenant_id, title=f"Confirmed apparel order {po_id}",
                      created_by=user_id, category=requirement["category"], quantity=requirement["quantity"],
                      metadata_json={"provider_id": provider.provider_id, "source_po_id": po_id,
                                     "aivan_project_id": source["metadata_json"].get("aivan_project_id")})
    db.add(project)
    await db.flush()
    for role, key, source_key in (("BUYER", "buyer", "buyer_id"), ("MANUFACTURER", "supplier", "supplier_id")):
        db.add(Participant(id=ids[key], tenant_id=tenant_id, name=require_id(source[source_key])))
        await db.flush()
        db.add(ParticipantRole(participant_id=ids[key], role_name=role))
    db.add(DynamicOrderForm(id=ids["form"], project_id=ids["project"], current_version=1, is_locked=True))
    await db.flush()
    db.add(DynamicOrderFormVersion(id=ids["form_version"], form_id=ids["form"], version_number=1,
                                  fields=requirement, human_confirmed_fields=requirement, created_by=user_id))
    db.add(DecisionPacket(id=ids["packet"], project_id=ids["project"], human_approval_status="APPROVED",
                          recommended_option_id=ids["option"], comparison_summary="Imported provider-confirmed Aivan quotation."))
    await db.flush()
    db.add(DecisionOption(id=ids["option"], packet_id=ids["packet"], option_index=1,
                          supplier_combination={"manufacturer": str(ids["supplier"])},
                          unit_price=selected["quote"]["buyer_unit_price"], currency=selected["currency"],
                          evidence={"provider_id": provider.provider_id, "source_quote_id": source["selected_quote_id"],
                                    "source_snapshot_hash": source["source_snapshot_hash"], "selected_option": selected}))
    await db.flush()
    order = Order(id=ids["order"], project_id=ids["project"], approved_option_id=ids["option"],
                  locked_form_version_id=ids["form_version"], status="IN_PRODUCTION",
                  buyer_participant_id=ids["buyer"], confirmed_at=confirmed_at,
                  order_number=f"PO-{ids['order']}")
    db.add(order)
    await db.flush()
    db.add(OrderLine(order_id=order.id, line_number=1, description=requirement["product_type"],
                     quantity=requirement["quantity"], unit="pcs", unit_price=selected["quote"]["buyer_unit_price"],
                     currency=selected["currency"], attributes={"form_fields_snapshot": requirement}))
    for milestone in ORDERED_MILESTONES:
        db.add(Milestone(order_id=order.id, milestone_type=milestone, status="PENDING",
                         notes="No execution date has been recorded for this imported order."))
    # Exclude provider execution metadata, so later association changes do not
    # turn the frozen confirmation evidence into a mutable record.
    snapshot = copy.deepcopy(source)
    snapshot["metadata_json"].pop("abcdyi_execution", None)
    db.add(ProviderOrderAssociation(order_id=order.id, tenant_id=tenant_id, provider_id=provider.provider_id,
                                   provider_tenant_id=provider.tenant_id, source_po_id=po_id,
                                   source_quote_id=source["selected_quote_id"], source_snapshot_hash=source["source_snapshot_hash"],
                                   source_snapshot=snapshot))
    await emit_event(db, "PROVIDER_CONFIRMED_ORDER_IMPORTED", {
        "provider_id": provider.provider_id, "provider_tenant_id": provider.tenant_id, "source_po_id": po_id,
        "source_quote_id": source["selected_quote_id"], "source_snapshot_hash": source["source_snapshot_hash"],
        "confirmation": source["metadata_json"]["human_authorization"], "confirmed_at": confirmed_at.isoformat(),
        "provider_readback_verified": True,
    }, tenant_id=tenant_id, project_id=order.project_id, order_id=order.id, triggered_by_user_id=user_id)
    return order
