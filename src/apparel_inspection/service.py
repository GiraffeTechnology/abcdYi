import math

def evaluate_qc_record(qc_record_data: dict, qc_standard: dict) -> dict:
    """
    Compare QC record data against QC standard.
    Returns result, failure_reasons, pass_criteria_met, rework_required.
    """
    failures: list[str] = []
    passed: list[str] = []

    fabric_defects = qc_record_data.get("fabric_defects") or {}
    defect_limits = (qc_standard.get("fabric_defect_limits") or {})
    for defect_type, count in fabric_defects.items():
        limit = defect_limits.get(defect_type)
        _number(count, defect_type)
        _number(limit, defect_type + " limit")
        if count < 0 or limit < 0:
            raise ValueError("QC counts and limits must be nonnegative")
        if count > limit:
            failures.append(f"Fabric defect '{defect_type}': {count} exceeds limit {limit}")
        else:
            passed.append(f"Fabric defect '{defect_type}': within limit")

    # Label compliance
    label_ok = qc_record_data.get("label_compliance")
    if label_ok is False:
        failures.append("Label non-compliance")
    elif label_ok is True:
        passed.append("Label compliance")

    # Packaging compliance
    pkg_ok = qc_record_data.get("packaging_compliance")
    if pkg_ok is False:
        failures.append("Packaging non-compliance")
    elif pkg_ok is True:
        passed.append("Packaging compliance")

    # Size deviation
    size_dev = qc_record_data.get("size_deviation") or {}
    size_limits = qc_standard.get("size_deviation_limits") or {}
    for dim, deviation in size_dev.items():
        limit = size_limits.get(dim)
        _number(deviation, dim)
        _number(limit, dim + " limit")
        if limit < 0: raise ValueError("QC tolerance must be nonnegative")
        if abs(float(deviation)) > limit:
            failures.append(f"Size deviation '{dim}': {deviation} exceeds tolerance {limit}")
        else:
            passed.append(f"Size deviation '{dim}': within tolerance")

    # Color difference
    color_diff = qc_record_data.get("color_difference") or {}
    color_tolerance = qc_standard.get("color_difference_tolerance") or {}
    for channel, value in color_diff.items():
        tolerance = color_tolerance.get(channel)
        _number(value, channel)
        _number(tolerance, channel + " tolerance")
        if tolerance < 0: raise ValueError("QC tolerance must be nonnegative")
        if abs(float(value)) > tolerance:
            failures.append(f"Color difference '{channel}': {value} exceeds tolerance {tolerance}")
        else:
            passed.append(f"Color '{channel}': within tolerance")

    rework_required = len(failures) > 0
    result = "QC_FAILED" if failures else "QC_PASSED"

    return {
        "result": result,
        "failure_reasons": failures,
        "pass_criteria_met": passed,
        "rework_required": rework_required,
    }


def _number(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("QC observation and approved numeric criterion are required: " + field)
