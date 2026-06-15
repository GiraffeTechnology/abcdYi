from datetime import datetime, timezone, timedelta
from src.production_monitoring.delay_predictor import predict_completion_date


def make_milestone(mtype, planned_offset, actual_offset=None, predicted_offset=None, status="PENDING"):
    base = datetime.now(timezone.utc)
    return {
        "milestone_type": mtype,
        "planned_date": base + timedelta(days=planned_offset),
        "actual_date": base + timedelta(days=actual_offset) if actual_offset is not None else None,
        "predicted_date": base + timedelta(days=predicted_offset) if predicted_offset is not None else None,
        "status": status,
        "responsible_participant_id": None,
    }


def test_on_track_when_no_delays():
    milestones = [make_milestone("FABRIC_BOOKING", 10, actual_offset=9, status="COMPLETED")]
    order = {"delivery_deadline": (datetime.now(timezone.utc) + timedelta(days=45)).isoformat()}
    result = predict_completion_date(milestones, order)
    assert result["delay_risk_level"] == "ON_TRACK"


def test_high_risk_when_8_days_late():
    base = datetime.now(timezone.utc)
    deadline = (base + timedelta(days=22)).isoformat()
    milestones = [make_milestone("SEWING", 20, predicted_offset=30)]
    order = {"delivery_deadline": deadline}
    result = predict_completion_date(milestones, order)
    assert result["delay_risk_level"] in ("HIGH", "CRITICAL")
    assert result["expedite_alert_required"] is True


def test_critical_when_more_than_14_days_late():
    milestones = [make_milestone("FINAL_QC", 10, predicted_offset=30)]
    order = {"delivery_deadline": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()}
    result = predict_completion_date(milestones, order)
    assert result["delay_risk_level"] == "CRITICAL"
    assert result["expedite_alert_required"] is True


def test_medium_risk_5_days_late():
    milestones = [make_milestone("SEWING", 10, predicted_offset=20)]
    order = {"delivery_deadline": (datetime.now(timezone.utc) + timedelta(days=15)).isoformat()}
    result = predict_completion_date(milestones, order)
    assert result["delay_risk_level"] in ("MEDIUM", "HIGH", "CRITICAL")


def test_no_milestones_returns_on_track():
    order = {"delivery_deadline": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()}
    result = predict_completion_date([], order)
    assert result["delay_risk_level"] == "ON_TRACK"
    assert result["expedite_alert_required"] is False


def test_low_confidence_when_no_predicted_dates():
    milestones = [make_milestone("FABRIC_BOOKING", 20), make_milestone("SEWING", 30)]
    order = {"delivery_deadline": (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()}
    result = predict_completion_date(milestones, order)
    assert result["confidence"] in ("LOW", "MEDIUM")


def test_delayed_milestones_listed():
    base = datetime.now(timezone.utc)
    milestones = [
        make_milestone("FABRIC_BOOKING", 10, predicted_offset=20),
        make_milestone("SEWING", 30, predicted_offset=45),
    ]
    order = {"delivery_deadline": (base + timedelta(days=60)).isoformat()}
    result = predict_completion_date(milestones, order)
    assert "FABRIC_BOOKING" in result["delayed_milestones"]
    assert "SEWING" in result["delayed_milestones"]
