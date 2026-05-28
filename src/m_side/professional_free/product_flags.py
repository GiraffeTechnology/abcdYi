"""
Professional Free product feature flags.
Enterprise CAP features are explicitly disabled.
"""

PROFESSIONAL_FREE_FEATURES: dict[str, bool] = {
    "cad_requirement_packet": True,
    "machinacheck_embedded_mock": True,
    "cad_cnc_parameter_matching": True,
    "machine_profile_matching": True,
    "supplier_response_rollup": True,
    "role_switching_upstream_inquiry": True,
    "basic_audit_log": True,
    # Enterprise CAP — explicitly disabled in Professional Free
    "file_encryption": False,
    "dynamic_watermark": False,
    "secure_viewer": False,
    "no_download_room": False,
    "vpc_deployment": False,
    "enterprise_cap": False,
}


def is_feature_enabled(feature: str) -> bool:
    return PROFESSIONAL_FREE_FEATURES.get(feature, False)


def assert_enterprise_cap_disabled() -> None:
    enterprise_features = [
        "file_encryption",
        "dynamic_watermark",
        "secure_viewer",
        "no_download_room",
        "vpc_deployment",
        "enterprise_cap",
    ]
    for feature in enterprise_features:
        if PROFESSIONAL_FREE_FEATURES.get(feature, False):
            raise AssertionError(
                f"Enterprise CAP feature '{feature}' must be disabled in Professional Free."
            )
