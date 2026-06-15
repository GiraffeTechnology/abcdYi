from datetime import datetime, timezone


def predict_completion_date(milestones: list[dict], order_details: dict) -> dict:
    """
    Predict order completion date based on current milestone states.
    """
    now = datetime.now(timezone.utc)

    # Parse standard completion date from delivery_deadline
    deadline_raw = order_details.get("delivery_deadline")
    standard_completion = None
    if deadline_raw:
        try:
            if isinstance(deadline_raw, str):
                dt = datetime.fromisoformat(deadline_raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                standard_completion = dt
            elif isinstance(deadline_raw, datetime):
                standard_completion = deadline_raw
        except (ValueError, TypeError):
            pass

    # Find predicted completion from remaining milestones
    predicted_dates = []
    delayed_milestones = []
    responsible_participant_id = None
    has_predicted_dates = 0
    total_remaining = 0

    for ms in milestones:
        if ms.get("status") == "COMPLETED":
            continue
        total_remaining += 1

        planned = ms.get("planned_date")
        predicted = ms.get("predicted_date")
        candidate = predicted or planned

        if predicted:
            has_predicted_dates += 1

        if candidate:
            predicted_dates.append(candidate)
            if planned and candidate > planned:
                delayed_milestones.append(ms.get("milestone_type", "UNKNOWN"))
                if not responsible_participant_id:
                    responsible_participant_id = ms.get("responsible_participant_id")

    predicted_completion = max(predicted_dates) if predicted_dates else None
    delay_days = None
    if predicted_completion and standard_completion:
        if predicted_completion.tzinfo is None:
            predicted_completion = predicted_completion.replace(tzinfo=timezone.utc)
        if standard_completion.tzinfo is None:
            standard_completion = standard_completion.replace(tzinfo=timezone.utc)
        delay_days = (predicted_completion - standard_completion).days

    # Risk level
    if delay_days is None or delay_days <= 0:
        risk_level = "ON_TRACK"
    elif delay_days <= 3:
        risk_level = "LOW"
    elif delay_days <= 7:
        risk_level = "MEDIUM"
    elif delay_days <= 14:
        risk_level = "HIGH"
    else:
        risk_level = "CRITICAL"

    expedite_required = risk_level in ("HIGH", "CRITICAL")

    # Confidence based on predicted_dates coverage
    if total_remaining == 0:
        confidence = "HIGH"
    elif has_predicted_dates == 0:
        confidence = "LOW"
    elif has_predicted_dates / total_remaining >= 0.7:
        confidence = "HIGH"
    else:
        confidence = "MEDIUM"

    recommended_action = {
        "ON_TRACK": "No action required. Continue monitoring.",
        "LOW": "Minor delay detected. Monitor closely.",
        "MEDIUM": "Moderate delay risk. Contact responsible participant.",
        "HIGH": "High delay risk. Expedite alert recommended.",
        "CRITICAL": "Critical delay. Immediate expedite alert required.",
    }.get(risk_level, "Monitor situation.")

    return {
        "standard_completion_date": standard_completion,
        "predicted_completion_date": predicted_completion,
        "delay_days": delay_days,
        "delay_risk_level": risk_level,
        "delayed_milestones": delayed_milestones,
        "responsible_participant_id": responsible_participant_id,
        "recommended_action": recommended_action,
        "expedite_alert_required": expedite_required,
        "confidence": confidence,
    }
