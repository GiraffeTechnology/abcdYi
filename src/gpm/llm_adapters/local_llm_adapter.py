class LocalLLMAdapter:
    """Base interface for local LLM adapters used in GPM pricing normalization."""

    def normalize_price_sample(self, requirement: dict, sample: object) -> dict:
        """
        Normalize a supplier price sample against a buyer requirement.

        Returns a dict with keys:
            is_comparable, comparability_score, normalized_product_type,
            normalized_material, normalized_process_tags,
            customization_supported, reason
        """
        raise NotImplementedError
