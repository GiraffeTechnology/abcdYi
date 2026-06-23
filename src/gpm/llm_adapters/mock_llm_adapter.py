from .local_llm_adapter import LocalLLMAdapter


class MockLLMAdapter(LocalLLMAdapter):
    """Deterministic mock LLM adapter for tests and offline development."""

    def normalize_price_sample(self, requirement: dict, sample: object) -> dict:
        title = ""
        if hasattr(sample, "product_title") and sample.product_title:
            title = sample.product_title
        elif isinstance(sample, dict):
            title = sample.get("product_title", "")

        title_lower = title.lower()

        is_shirt = any(k in title_lower for k in ("shirt", "衬衫"))
        is_cotton = any(k in title_lower for k in ("cotton", "纯棉"))
        is_oem = any(k in title_lower for k in ("oem", "定制"))

        if is_shirt:
            comparability_score = 0.85
            normalized_product_type = "men_cotton_shirt"
            is_comparable = True
            reason = "Sample title matches men's cotton shirt keyword."
        else:
            comparability_score = 0.10
            normalized_product_type = None
            is_comparable = False
            reason = "Sample title does not match target product type."

        if is_shirt and not is_cotton:
            comparability_score = 0.40

        normalized_material = "cotton" if is_cotton else None
        customization_supported = True if is_oem else None

        process_tags = list(requirement.get("process_tags", []))

        return {
            "is_comparable": is_comparable,
            "comparability_score": comparability_score,
            "normalized_product_type": normalized_product_type,
            "normalized_material": normalized_material,
            "normalized_process_tags": process_tags,
            "customization_supported": customization_supported,
            "reason": reason,
        }
