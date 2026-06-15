from __future__ import annotations
from datetime import date, datetime, timedelta, timezone
from typing import Optional
import uuid as _uuid

from .models import (
    ApparelOrderInput, DeliveryFeasibilityPacket, DeliveryPath, ParticipantNode
)

_RISK_ADJ_BUFFER_DAYS = 3  # days added to most-likely for risk-adjusted
_COMMITTABLE_BUFFER_DAYS = 5  # days added to risk-adjusted for committable


class LeadTimeGraphEngine:
    """
    GLTG — Giraffe Lead-Time Graph engine.

    Constructs a dependency graph from ApparelOrderInput, calculates delivery paths,
    and returns a ranked DeliveryFeasibilityPacket.
    """

    def evaluate(self, order_input: ApparelOrderInput) -> DeliveryFeasibilityPacket:
        evaluated_at = order_input.evaluated_at or datetime.now(timezone.utc)
        today = evaluated_at.date() if isinstance(evaluated_at, datetime) else date.today()

        nodes = order_input.participant_nodes
        if not nodes:
            return self._empty_packet(order_input, "No participant nodes provided.")

        # Group nodes by role
        manufacturers = [n for n in nodes if n.role == "MANUFACTURER"]
        fabric_suppliers = [n for n in nodes if n.role == "FABRIC_SUPPLIER"]
        trim_suppliers = [n for n in nodes if n.role == "TRIM_SUPPLIER"]
        packaging_suppliers = [n for n in nodes if n.role == "PACKAGING_SUPPLIER"]
        qc_inspectors = [n for n in nodes if n.role == "QC_INSPECTOR"]
        logistics_providers = [n for n in nodes if n.role == "LOGISTICS_PROVIDER"]

        # Build candidate paths: one per manufacturer (anchor node)
        # Each path selects the best fabric/trim/packaging/qc/logistics from available nodes
        candidate_paths: list[DeliveryPath] = []

        anchor_nodes = manufacturers if manufacturers else nodes

        for mfr in anchor_nodes:
            path = self._evaluate_path(
                anchor=mfr,
                fabric_suppliers=fabric_suppliers,
                trim_suppliers=trim_suppliers,
                packaging_suppliers=packaging_suppliers,
                qc_inspectors=qc_inspectors,
                logistics_providers=logistics_providers,
                today=today,
                order_input=order_input,
            )
            candidate_paths.append(path)

        # Filter to feasible paths; sort by rank_score desc
        feasible = [p for p in candidate_paths if p.is_feasible]
        ranked = sorted(feasible, key=lambda p: p.rank_score, reverse=True)

        # Also include best infeasible path for explanation if no feasible paths exist
        all_by_rank = sorted(candidate_paths, key=lambda p: p.rank_score, reverse=True)

        required_delivery = order_input.required_delivery_date

        # Overall packet from best feasible option
        best = ranked[0] if ranked else (all_by_rank[0] if all_by_rank else None)

        missing_evidence = list({ev for p in all_by_rank for ev in p.missing_evidence})
        all_risk_flags = list({rf for p in all_by_rank for rf in p.risk_flags})

        if not ranked:
            status = "INFEASIBLE" if candidate_paths else "INCOMPLETE_EVIDENCE"
            explanation = self._build_explanation(None, required_delivery, missing_evidence, ranked_count=0)
            return DeliveryFeasibilityPacket(
                order_id=order_input.order_id,
                status=status,
                required_delivery_date=required_delivery,
                delivery_feasibility="INFEASIBLE",
                ranked_options=[],
                option_count=0,
                risk_flags=all_risk_flags,
                missing_evidence=missing_evidence,
                explanation=explanation,
                confidence="LOW",
            )

        # Assign recommendation reasons to ranked options
        for i, path in enumerate(ranked):
            if i == 0:
                path.recommendation_reason = "Best overall feasible path"
            elif i == 1:
                if path.total_lead_time_days == min(p.total_lead_time_days or 9999 for p in ranked):
                    path.recommendation_reason = "Fastest lead time"
                else:
                    path.recommendation_reason = "Alternative feasible path"
            else:
                path.recommendation_reason = "Alternative feasible path"

        # Delivery feasibility vs deadline
        feasibility_status = "FEASIBLE"
        days_vs_deadline = None
        if required_delivery and best and best.risk_adjusted_delivery_date:
            days_vs_deadline = (best.risk_adjusted_delivery_date - required_delivery).days
            if days_vs_deadline > 7:
                feasibility_status = "INFEASIBLE"
            elif days_vs_deadline > 0:
                feasibility_status = "AT_RISK"

        # Confidence
        confidence = self._compute_confidence(ranked)

        explanation = self._build_explanation(best, required_delivery, missing_evidence, len(ranked))

        return DeliveryFeasibilityPacket(
            order_id=order_input.order_id,
            status="EVALUATED",
            earliest_delivery_date=best.earliest_delivery_date if best else None,
            most_likely_delivery_date=best.most_likely_delivery_date if best else None,
            risk_adjusted_delivery_date=best.risk_adjusted_delivery_date if best else None,
            committable_delivery_date=best.committable_delivery_date if best else None,
            required_delivery_date=required_delivery,
            delivery_feasibility=feasibility_status,
            days_vs_deadline=days_vs_deadline,
            critical_path=best.critical_path if best else [],
            critical_path_days=best.critical_path_days if best else None,
            ranked_options=ranked[:3],  # up to 3 — never faked
            option_count=len(ranked),
            risk_flags=all_risk_flags,
            missing_evidence=missing_evidence,
            explanation=explanation,
            confidence=confidence,
        )

    def _evaluate_path(
        self,
        anchor: ParticipantNode,
        fabric_suppliers: list[ParticipantNode],
        trim_suppliers: list[ParticipantNode],
        packaging_suppliers: list[ParticipantNode],
        qc_inspectors: list[ParticipantNode],
        logistics_providers: list[ParticipantNode],
        today: date,
        order_input: ApparelOrderInput,
    ) -> DeliveryPath:
        path_id = str(_uuid.uuid4())
        participant_ids = [anchor.participant_id]
        missing_evidence: list[str] = []
        risk_flags: list[str] = []
        critical_path: list[str] = []

        # Parallel stage: fabric, trim, packaging (take the max)
        fabric_lt = self._best_lt(fabric_suppliers, "fabric_lead_time_days", anchor.fabric_lead_time_days)
        trim_lt = self._best_lt(trim_suppliers, "trim_lead_time_days", anchor.trim_lead_time_days)
        packaging_lt = self._best_lt(packaging_suppliers, "packaging_lead_time_days", anchor.packaging_lead_time_days)

        if fabric_lt is None:
            missing_evidence.append("fabric_lead_time_days")
        if trim_lt is None:
            missing_evidence.append("trim_lead_time_days")

        parallel_values = [v for v in [fabric_lt, trim_lt, packaging_lt] if v is not None]
        parallel_max = max(parallel_values) if parallel_values else None

        # Identify critical parallel item
        if fabric_lt and fabric_lt == parallel_max:
            critical_path.append("FABRIC_SOURCING")
        elif trim_lt and trim_lt == parallel_max:
            critical_path.append("TRIM_SOURCING")
        elif packaging_lt and packaging_lt == parallel_max:
            critical_path.append("PACKAGING_SOURCING")

        # Sequential stage: production, QC, logistics
        production_lt = anchor.production_time_days
        qc_lt = self._best_lt(qc_inspectors, "qc_time_days", anchor.qc_time_days)
        logistics_lt = self._best_lt(logistics_providers, "logistics_time_days", anchor.logistics_time_days)

        if production_lt is None:
            missing_evidence.append("production_time_days")
        if qc_lt is None:
            missing_evidence.append("qc_time_days")
        if logistics_lt is None:
            missing_evidence.append("logistics_time_days")

        sequential_parts = [production_lt, qc_lt, logistics_lt]
        sequential_sum = sum(v for v in sequential_parts if v is not None)
        has_missing_sequential = any(v is None for v in sequential_parts)

        if production_lt:
            critical_path.append("GARMENT_MANUFACTURING")
        if qc_lt:
            critical_path.append("QC_INSPECTION")
        if logistics_lt:
            critical_path.append("LOGISTICS")

        # Total lead time
        if parallel_max is not None and not has_missing_sequential:
            total_lt = parallel_max + sequential_sum
        elif parallel_max is None and not has_missing_sequential:
            total_lt = sequential_sum
            missing_evidence.append("parallel_supply_lead_time")
        else:
            total_lt = None

        # Risk signals
        if anchor.quality_issue_count >= 2:
            risk_flags.append("Supplier has recurring quality issues")
        if anchor.qc_pass_rate is not None and anchor.qc_pass_rate < 0.8:
            risk_flags.append("Low QC pass rate")
        if anchor.on_time_delivery_rate is not None and anchor.on_time_delivery_rate < 0.9:
            risk_flags.append("Late delivery history")
        if anchor.capacity_available is False:
            risk_flags.append("Capacity not confirmed")

        # Milestone-based updates (reforecasting)
        milestone_delay_days = self._compute_milestone_delay(order_input.milestone_updates)
        effective_lt = (total_lt + milestone_delay_days) if total_lt is not None else None

        # Date calculations
        earliest = (today + timedelta(days=total_lt)) if total_lt is not None else None
        most_likely = (today + timedelta(days=effective_lt)) if effective_lt is not None else None
        risk_adjusted = (most_likely + timedelta(days=_RISK_ADJ_BUFFER_DAYS)) if most_likely else None
        committable = (risk_adjusted + timedelta(days=_COMMITTABLE_BUFFER_DAYS)) if risk_adjusted else None

        # Feasibility: path is feasible if we have at least production + QC + logistics
        is_feasible = production_lt is not None and qc_lt is not None and logistics_lt is not None

        if is_feasible:
            feasibility_reason = "All sequential stages have lead time evidence."
        else:
            feasibility_reason = f"Missing: {', '.join(missing_evidence)}"

        # Rank score: combination of lead time (lower = better) and reliability
        rank_score = 0.0
        if total_lt is not None:
            rank_score += max(0.0, (200 - total_lt) / 200.0) * 0.5
        if anchor.qc_pass_rate is not None:
            rank_score += anchor.qc_pass_rate * 0.3
        if anchor.on_time_delivery_rate is not None:
            rank_score += anchor.on_time_delivery_rate * 0.2
        if not is_feasible:
            rank_score *= 0.1  # penalize infeasible paths

        confidence = "HIGH" if not missing_evidence else ("MEDIUM" if len(missing_evidence) <= 2 else "LOW")

        return DeliveryPath(
            path_id=path_id,
            participant_ids=participant_ids,
            parallel_max_days=parallel_max,
            sequential_days=sequential_sum if not has_missing_sequential else None,
            total_lead_time_days=total_lt,
            earliest_delivery_date=earliest,
            most_likely_delivery_date=most_likely,
            risk_adjusted_delivery_date=risk_adjusted,
            committable_delivery_date=committable,
            critical_path=critical_path,
            critical_path_days=total_lt,
            is_feasible=is_feasible,
            feasibility_reason=feasibility_reason,
            risk_flags=risk_flags,
            missing_evidence=list(set(missing_evidence)),
            unit_price=anchor.unit_price,
            currency=anchor.currency,
            rank_score=rank_score,
            confidence=confidence,
        )

    def _best_lt(
        self,
        suppliers: list[ParticipantNode],
        field_name: str,
        anchor_fallback: Optional[int],
    ) -> Optional[int]:
        """Pick the best (shortest) lead time from available suppliers, or use anchor fallback."""
        values = []
        for s in suppliers:
            v = getattr(s, field_name, None)
            if v is not None:
                values.append(v)
        if values:
            return min(values)
        return anchor_fallback

    def _compute_milestone_delay(self, milestone_updates: list[dict]) -> int:
        """Compute total delay days from delayed milestones."""
        total_delay = 0
        for ms in milestone_updates:
            if ms.get("status") == "DELAYED":
                predicted = ms.get("predicted_date")
                planned = ms.get("planned_date")
                if predicted and planned:
                    try:
                        from datetime import date
                        if isinstance(predicted, str):
                            from datetime import datetime
                            predicted = datetime.fromisoformat(predicted.replace("Z", "+00:00")).date()
                        if isinstance(planned, str):
                            from datetime import datetime
                            planned = datetime.fromisoformat(planned.replace("Z", "+00:00")).date()
                        delay = (predicted - planned).days
                        if delay > 0:
                            total_delay = max(total_delay, delay)
                    except Exception:
                        pass
        return total_delay

    def _compute_confidence(self, ranked: list[DeliveryPath]) -> str:
        if not ranked:
            return "LOW"
        best = ranked[0]
        if not best.missing_evidence and best.total_lead_time_days is not None:
            return "HIGH"
        if len(best.missing_evidence) <= 2:
            return "MEDIUM"
        return "LOW"

    def _build_explanation(
        self,
        best: Optional[DeliveryPath],
        required_delivery: Optional[date],
        missing_evidence: list[str],
        ranked_count: int,
    ) -> str:
        if ranked_count == 0:
            if missing_evidence:
                return (
                    f"No feasible delivery path can currently be confirmed because the following "
                    f"evidence is missing: {', '.join(missing_evidence)}. "
                    f"Obtain lead-time data from suppliers before committing to a delivery date."
                )
            return "No feasible delivery path found. All candidate paths failed feasibility checks."

        if best is None:
            return "Evaluation complete."

        parts = [f"Best feasible path: {best.total_lead_time_days} days total lead time."]
        if best.risk_adjusted_delivery_date and required_delivery:
            delta = (best.risk_adjusted_delivery_date - required_delivery).days
            if delta <= 0:
                parts.append(f"Risk-adjusted delivery date is {abs(delta)} days before the deadline.")
            else:
                parts.append(
                    f"Risk-adjusted delivery date is {delta} days after the deadline — "
                    f"delivery is at risk. Consider expediting or selecting an alternative supplier."
                )
        if missing_evidence:
            parts.append(f"Missing evidence for optimal calculation: {', '.join(missing_evidence)}.")
        if best.risk_flags:
            parts.append(f"Risk flags: {'; '.join(best.risk_flags)}.")
        return " ".join(parts)

    def _empty_packet(self, order_input: ApparelOrderInput, reason: str) -> DeliveryFeasibilityPacket:
        return DeliveryFeasibilityPacket(
            order_id=order_input.order_id,
            status="INCOMPLETE_EVIDENCE",
            required_delivery_date=order_input.required_delivery_date,
            delivery_feasibility="UNKNOWN",
            ranked_options=[],
            option_count=0,
            risk_flags=[],
            missing_evidence=["participant_nodes"],
            explanation=reason,
            confidence="LOW",
        )
