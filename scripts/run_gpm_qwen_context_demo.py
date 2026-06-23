#!/usr/bin/env python
"""GPM Qwen Context Demo.

Demonstrates the full Session C pipeline:
  Session A samples -> InMemoryGPMContextRetriever -> GPMContextBundle
  -> MockQwenRuntime -> QwenSemanticAnalysis -> validated output

Usage: uv run python scripts/run_gpm_qwen_context_demo.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.gpm.models.supplier_price_sample import GPMSupplierPriceSample
from src.gpm.context.in_memory_context_retriever import InMemoryGPMContextRetriever
from src.gpm.qwen.mock_qwen_runtime import MockQwenRuntime
from src.gpm.prompts.qwen_semantic_analysis_prompt import build_qwen_semantic_analysis_prompt
from src.gpm.validators.qwen_output_validator import validate_qwen_output
from src.gpm.validators.context_bundle_validator import validate_context_bundle
from src.gpm.models.qwen_semantic_analysis import QwenSemanticAnalysis


def _make_shirt_sample(i: int) -> GPMSupplierPriceSample:
    sample = GPMSupplierPriceSample(
        id=f"sample_{i:03d}",
        source_platform="1688_mock",
        source_offer_id=f"offer_{i:03d}",
        supplier_id=f"sup_{i:03d}",
        supplier_name=f"Supplier {i}",
        supplier_location="Guangzhou",
        captured_at=datetime.now(timezone.utc),
        observed_at=datetime.now(timezone.utc),
        product_title="Men's 100% Cotton OEM Shirt 衬衫",
        product_url=None,
        image_url=None,
        category_id="apparel",
        category_name="Men's Shirts",
        material="100% cotton",
        process_tags=["oem"],
        customization_supported=True,
        price_min=Decimal("32.0"),
        price_max=Decimal("38.0"),
        price_currency="CNY",
        price_unit="piece",
        moq=Decimal("500"),
        moq_unit="pieces",
        ladder_prices=[],
        sku_attributes={},
        delivery_region="Japan",
        lead_time_text="30-45 days",
        raw_response_id="raw_001",
        created_at=datetime.now(timezone.utc),
    )
    sample.usable_for_benchmark = True
    return sample


def main() -> int:
    requirement = {
        "product_type": "men_cotton_shirt",
        "material": "100% cotton",
        "quantity": 10000,
        "unit": "piece",
        "process_tags": ["oem", "odm"],
        "target_market": "Japan",
    }
    supplier_quote = {
        "price": "38.5",
        "currency": "CNY",
        "unit": "piece",
        "moq": 10000,
    }

    samples = [_make_shirt_sample(i) for i in range(1, 21)]

    retriever = InMemoryGPMContextRetriever(price_samples=samples)
    context = retriever.build_context(
        requirement=requirement,
        supplier_quote=supplier_quote,
        data_mode="mock",
    )

    validate_context_bundle(context)

    runtime = MockQwenRuntime()
    prompt = build_qwen_semantic_analysis_prompt(context)
    raw_output = runtime.generate_json(prompt, schema_name="qwen_semantic_analysis")
    validate_qwen_output(raw_output, context)

    analysis = QwenSemanticAnalysis(**raw_output)
    evidence_ids_valid = all(eid in context.evidence_ids() for eid in analysis.evidence_ids)

    print("GPM QWEN CONTEXT DEMO: PASS")
    print(f"data_mode: {context.data_mode}")
    print(f"runtime: {runtime.runtime_name}")
    print(f"normalized_product_type: {analysis.normalized_product_type}")
    print(f"normalized_material: {analysis.normalized_material}")
    print(f"comparability_score: {analysis.comparability_score}")
    print(f"evidence_ids_valid: {str(evidence_ids_valid).lower()}")
    print("no_external_llm_api: true")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print("GPM QWEN CONTEXT DEMO: FAIL")
        print(f"reason: {exc}")
        sys.exit(1)
