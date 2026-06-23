from __future__ import annotations

import json
import re


class MockQwenRuntime:
    """Deterministic mock Qwen runtime for tests.

    No external API calls. No DashScope. No cloud inference.
    Produces schema-locked JSON based on keyword matching in the prompt.
    """

    runtime_name: str = "mock_qwen"

    def generate_json(
        self, prompt: str, schema_name: str, max_tokens: int = 1024
    ) -> dict:
        prompt_lower = prompt.lower()

        evidence_ids = self._extract_evidence_ids(prompt)

        is_shirt = any(k in prompt_lower for k in ("shirt", "衬衫"))
        is_cotton = any(k in prompt_lower for k in ("cotton", "棉", "纯棉"))
        is_oem = any(k in prompt_lower for k in ("oem", "odm", "custom", "定制"))

        process_tags: list[str] = []
        if is_oem:
            process_tags.append("oem")
        if "odm" in prompt_lower:
            if "odm" not in process_tags:
                process_tags.append("odm")

        if is_shirt and is_cotton:
            comparability_score = 0.85
            normalized_product_type = "men_cotton_shirt"
            normalized_material = "cotton"
            is_comparable = True
            confidence = "high"
            reason = "Product type and material match men's cotton shirt requirement."
        elif is_shirt:
            comparability_score = 0.40
            normalized_product_type = "men_cotton_shirt"
            normalized_material = None
            is_comparable = True
            confidence = "medium"
            reason = "Product type matches but material not confirmed as cotton."
        else:
            comparability_score = 0.10
            normalized_product_type = "unknown"
            normalized_material = None
            is_comparable = False
            confidence = "low"
            reason = "Product type does not match requirement."

        return {
            "normalized_product_type": normalized_product_type,
            "normalized_material": normalized_material,
            "normalized_process_tags": process_tags,
            "is_comparable": is_comparable,
            "comparability_score": comparability_score,
            "detected_mismatch_flags": [],
            "evidence_ids": evidence_ids,
            "reason": reason,
            "confidence": confidence,
        }

    def _extract_evidence_ids(self, prompt: str) -> list[str]:
        match = re.search(r'Available evidence_ids:\s*(\[[^\]]*\])', prompt)
        if match:
            try:
                return json.loads(match.group(1))
            except (json.JSONDecodeError, ValueError):
                pass
        return re.findall(r'"(ev_[^"]+)"', prompt)
