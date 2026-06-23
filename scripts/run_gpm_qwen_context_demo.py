"""GPM Qwen context demo: build a mock context bundle, call mock Qwen runtime, validate, print results."""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

sys.path.insert(0, ".")

from src.gpm.context.in_memory_context_retriever import InMemoryGPMContextRetriever
from src.gpm.models.qwen_semantic_analysis import QwenSemanticAnalysis
from src.gpm.prompts.qwen_semantic_analysis_prompt import build_qwen_semantic_analysis_prompt
from src.gpm.qwen.mock_qwen_runtime import MockQwenRuntime
from src.gpm.validators.context_bundle_validator import ContextBundleValidator, ContextBundleValidationError
from src.gpm.validators.qwen_output_validator import QwenOutputValidator, QwenOutputValidationError


@dataclass
class _MockSample:
    id: str
    product_title: str
    price_min: Decimal
    price_max: Decimal
    price_currency: str = "CNY"
    price_unit: str = "piece"
    moq: Decimal = Decimal("1000")
    moq_unit: str = "piece"
    material: str = "100% cotton"
    source_platform: str = "mock_1688"
    usable_for_benchmark: bool = True
    invalid_reasons: list[str] = field(default_factory=list)
    captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


SAMPLE_TITLES = [
    "men cotton shirt OEM custom",
    "100% cotton shirt men",
    "OEM cotton shirt men Japan export",
    "men shirt 100% cotton",
    "pure cotton shirt OEM custom Japan",
]

REQUIREMENT = {
    "id": "req-demo-001",
    "product": "men's cotton shirt",
    "quantity": 10000,
    "unit": "piece",
    "material": "100% cotton",
    "process_tags": ["cutting", "sewing", "buttoning", "packing"],
    "target_market": "Japan",
}

SUPPLIER_QUOTE = {
    "supplier_id": "supplier_abc",
    "unit_price": 38.5,
    "currency": "CNY",
    "unit": "piece",
    "moq": 1000,
}


def main() -> None:
    samples = [
        _MockSample(
            id=f"ms-{i+1:03d}",
            product_title=title,
            price_min=Decimal(str(28 + i)),
            price_max=Decimal(str(35 + i)),
        )
        for i, title in enumerate(SAMPLE_TITLES)
    ]

    retriever = InMemoryGPMContextRetriever(price_samples=samples)
    bundle = retriever.build_context(
        requirement=REQUIREMENT,
        supplier_quote=SUPPLIER_QUOTE,
        data_mode="mock",
    )

    bundle_validator = ContextBundleValidator()
    try:
        bundle_validator.validate(bundle)
    except ContextBundleValidationError as e:
        print(f"GPM QWEN CONTEXT DEMO: FAIL\nreason: context bundle invalid: {e}")
        sys.exit(1)

    prompt = build_qwen_semantic_analysis_prompt(bundle)

    runtime = MockQwenRuntime()
    raw_output = runtime.generate_json(prompt, schema_name="qwen_semantic_analysis")

    output_validator = QwenOutputValidator()
    try:
        output_validator.validate(raw_output, bundle)
    except QwenOutputValidationError as e:
        print(f"GPM QWEN CONTEXT DEMO: FAIL\nreason: output validation failed: {e}")
        sys.exit(1)

    analysis = QwenSemanticAnalysis(**raw_output)

    evidence_ids_valid = all(eid in bundle.evidence_ids() for eid in analysis.evidence_ids)

    print("GPM QWEN CONTEXT DEMO: PASS")
    print(f"data_mode: {bundle.data_mode}")
    print(f"runtime: {runtime.runtime_name}")
    print(f"normalized_product_type: {analysis.normalized_product_type}")
    print(f"normalized_material: {analysis.normalized_material}")
    print(f"comparability_score: {analysis.comparability_score}")
    print(f"evidence_ids_valid: {str(evidence_ids_valid).lower()}")
    print("no_external_llm_api: true")


if __name__ == "__main__":
    main()
