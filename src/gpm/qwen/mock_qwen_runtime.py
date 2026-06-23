from __future__ import annotations

import json
import re


class MockQwenRuntime:
    """Deterministic mock Qwen runtime for offline tests."""

    runtime_name = "mock_qwen"

    def generate_json(self, prompt: str, schema_name: str, max_tokens: int = 1024) -> dict:
        prompt_lower = prompt.lower()

        is_shirt = bool(re.search(r"shirt|衬衫", prompt_lower))
        is_cotton = bool(re.search(r"cotton|棉|纯棉", prompt_lower))
        is_custom = bool(re.search(r"oem|odm|custom|定制", prompt_lower))

        if is_shirt and is_cotton:
            comparability_score = 0.85
            normalized_product_type = "men_cotton_shirt"
            normalized_material = "cotton"
            is_comparable = True
            confidence = "high"
            reason = "Product title matches men's cotton shirt with material and process evidence."
        elif is_shirt:
            comparability_score = 0.40
            normalized_product_type = "men_cotton_shirt"
            normalized_material = None
            is_comparable = True
            confidence = "medium"
            reason = "Product title matches shirt but material evidence weak."
        else:
            comparability_score = 0.10
            normalized_product_type = "unknown"
            normalized_material = None
            is_comparable = False
            confidence = "low"
            reason = "Product type does not match target requirement."

        process_tags: list[str] = []
        if is_custom:
            process_tags.append("oem_odm")
        if "cutting" in prompt_lower:
            process_tags.append("cutting")
        if "sewing" in prompt_lower:
            process_tags.append("sewing")

        # Extract evidence IDs from prompt
        evidence_ids: list[str] = re.findall(r'"id":\s*"(ev_[^"]+)"', prompt)
        if not evidence_ids:
            evidence_ids = re.findall(r'ev_[a-zA-Z0-9_-]+', prompt)

        return {
            "normalized_product_type": normalized_product_type,
            "normalized_material": normalized_material,
            "normalized_process_tags": process_tags,
            "is_comparable": is_comparable,
            "comparability_score": comparability_score,
            "detected_mismatch_flags": [],
            "evidence_ids": evidence_ids[:5],
            "reason": reason,
            "confidence": confidence,
        }
