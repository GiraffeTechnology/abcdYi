from __future__ import annotations

import os
from typing import Any

from src.gpm.clients.giraffe_db_client import GiraffeDBClientError
from src.gpm.models.gpm_quote_guidance_packet import GPMQuoteGuidancePacket
from src.gpm.qwen.gpm_runtime_unavailable_error import GPMRuntimeUnavailableError
from src.gpm.qwen.qwen_runtime_config import QwenRuntimeConfig
from src.gpm.services.gpm_semantic_quote_service import GPMSemanticQuoteService

_PACKET_STORE: dict[str, GPMQuoteGuidancePacket] = {}


class GPMQuoteGuidanceApiService:
    def __init__(
        self,
        runtime_config: QwenRuntimeConfig,
        context_retriever: Any,
    ) -> None:
        self._runtime_config = runtime_config
        # GPMSemanticQuoteService resolves QwenLocalRuntime from env at call time
        self._svc = GPMSemanticQuoteService(context_retriever=context_retriever)

    def generate_quote_guidance(
        self,
        *,
        tenant_id: str | None,
        project_id: str | None,
        rfq_id: str | None,
        supplier_response_id: str | None,
        evidence_ids: list[str],
        include_private_data: bool,
        runtime_mode: str | None,
    ) -> dict[str, Any]:
        context_retriever_name = os.getenv("GPM_CONTEXT_RETRIEVER", "mock")
        try:
            result = self._svc.run(
                tenant_id=tenant_id,
                project_id=project_id,
                rfq_id=rfq_id,
                supplier_response_id=supplier_response_id,
                include_private_data=include_private_data,
                runtime_mode=runtime_mode,
                evidence_ids=evidence_ids,
            )
        except GPMRuntimeUnavailableError as exc:
            return {
                "status": "runtime_unavailable",
                "packet": None,
                "error": exc.safe_message or str(exc.reason),
                "operator_action_required": exc.operator_action_required,
            }
        except ValueError as exc:
            return {
                "status": "insufficient_data",
                "packet": None,
                "error": str(exc),
                "operator_action_required": False,
            }
        except (GiraffeDBClientError, RuntimeError) as exc:
            return {
                "status": "context_unavailable",
                "packet": None,
                "error": str(exc),
                "operator_action_required": True,
            }

        risk_flags = result.get("risk_flags") or []
        benchmark_snapshot = result.get("benchmark_snapshot") or {}

        negotiation_points = [str(f) for f in risk_flags]
        buyer_quote_options = [
            {
                "option_id": "opt_accept",
                "label": "Accept supplier quote",
                "position": result.get("supplier_quote_position", ""),
                "recommendation": result.get("accept_recommendation", ""),
            }
        ]

        packet = GPMQuoteGuidancePacket.create(
            tenant_id=tenant_id,
            project_id=project_id,
            rfq_id=rfq_id,
            supplier_response_id=supplier_response_id,
            context_bundle_id=result.get("context_bundle_id"),
            evidence_ids=result.get("evidence_ids") or evidence_ids,
            supplier_quote_position=result.get("supplier_quote_position", ""),
            recommendation=result.get("accept_recommendation", ""),
            benchmark_range=benchmark_snapshot,
            negotiation_points=negotiation_points,
            buyer_quote_options=buyer_quote_options,
            runtime_profile=self._runtime_config.runtime_profile,
            runtime_mode=result.get("runtime_mode", self._runtime_config.runtime_mode),
            context_retriever=context_retriever_name,
            data_mode="private" if include_private_data else "public",
            operator_action_required=True,
        )

        _PACKET_STORE[packet.packet_id] = packet

        return {
            "status": "ok",
            "packet": packet,
            "error": None,
            "operator_action_required": True,
        }

    def get_packet(self, packet_id: str) -> GPMQuoteGuidancePacket | None:
        return _PACKET_STORE.get(packet_id)

    def list_packets(self) -> list[GPMQuoteGuidancePacket]:
        return list(_PACKET_STORE.values())
