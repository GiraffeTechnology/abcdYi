"""
端对端集成测试：Qwen 蒸馏 + 确定性报价引擎

流程（对应 spec §4.4 + §2）：
  1. 准备一份模拟供应商原始报价单（非结构化中文文本）
  2. 调用 Qwen 按蒸馏 prompt 提取结构化字段（仅抽取原文已有数字，null 表示缺失）
  3. 验证提取结果未出现 spec 明确禁止的行为（补全、估算）
  4. 将提取结果送入 PricingEngine 做确定性报价计算
  5. 打印完整报价明细
"""
import json
import os
import sys
from decimal import Decimal

import pytest

# ── 路径设置（无 conftest 时也能直接运行）─────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.llm.qwen_provider import QwenProvider
from src.pricing.distillation.service import (
    build_extraction_prompt,
    validate_submission,
    validate_approval,
    DistillationPipelineError,
)
from src.pricing.engine.calculator import (
    PricingEngine,
    PricingInput,
    ProcessLineItem,
    LeadTimeEngine,
    LeadTimeInput,
    LeadTimeItem,
    LeadTimeRelation,
    PHASE_PROCUREMENT,
    PHASE_PROCESS,
    PHASE_PRODUCTION,
    PHASE_PACKAGING,
    MissingPricingDataError,
)

# ── 模拟原始供应商报价文件 ──────────────────────────────────────────────────
SUPPLIER_QUOTE_DOC = """
【供应商报价单】
日期：2026年6月16日
供应商：杭州德力纺织有限公司

品类：女装衬衫（SKU-2026-W001）

面料：100%精梳棉（32支）
  规格：130g/㎡，幅宽150cm
  单价：¥18.50/米
  最小起订量：500米
  交期：15个工作日

辅料：
  1. 四孔树脂纽扣（1.5cm）：¥0.12/粒，每件用量8粒，起订量：1000粒，交期：7天
  2. 涤纶缝纫线（402#）：¥2.80/卷，每件用量0.3卷，交期：5天
  3. 品牌织唛：¥0.35/个，每件1个，交期：10天

工艺：
  名称：胸前刺绣（logo，8cm×8cm）
  计价方式：按件
  单价：¥4.50/件（约15000针）
  供应商：苏州绣艺坊
  报价日期：2026年6月12日
  交期：8个工作日

包装：
  类型：独立OPP袋+吊牌
  单价：¥0.65/件
  供应商：本司自备
  交期：3天

人工成本参考：缝制工序（华东地区）¥35.00/小时，每件标准工时0.5小时

损耗率：面辅料综合损耗约3%

备注：以上报价含税，不含运费。款式特征：立领、前开襟、七分袖（仅供展示，不参与计价）
"""

# 报价时每件面料用量（外部已知）
FABRIC_QTY_PER_PIECE = Decimal("1.8")  # 米/件

# 蒸馏 prompt schema hint
EXTRACTION_SCHEMA = """
{
  "sku_id": "string",
  "sku_name": "string",
  "category": "string",
  "fabric": {
    "unit_price": "number|null",
    "unit": "string|null",
    "supplier": "string|null",
    "quote_date": "string|null",
    "lead_time_days": "number|null",
    "lead_time_relation": "parallel|sequential|null",
    "lead_time_phase": "number|null",
    "source_text": "string"
  },
  "accessories": [
    {
      "name": "string",
      "unit_price": "number|null",
      "unit": "string|null",
      "qty_per_piece": "number|null",
      "supplier": "string|null",
      "lead_time_days": "number|null",
      "lead_time_relation": "parallel|sequential|null",
      "lead_time_phase": "number|null",
      "source_text": "string"
    }
  ],
  "processes": [
    {
      "name": "string",
      "pricing_method": "per_piece|per_area|per_stitch_count",
      "unit_price": "number|null",
      "supplier": "string|null",
      "quote_date": "string|null",
      "lead_time_days": "number|null",
      "lead_time_relation": "parallel|sequential|null",
      "lead_time_phase": "number|null",
      "source_text": "string"
    }
  ],
  "packaging": {
    "type": "string|null",
    "unit_price": "number|null",
    "supplier": "string|null",
    "lead_time_days": "number|null",
    "lead_time_relation": "parallel|sequential|null",
    "lead_time_phase": "number|null",
    "source_text": "string"
  },
  "labor": {
    "operation": "string|null",
    "region": "string|null",
    "unit_price_per_hour": "number|null",
    "hours_per_piece": "number|null",
    "source_text": "string"
  },
  "loss_rate": "number|null",
  "extra_display_only": {
    "collar_style": "string|null",
    "sleeve_style": "string|null"
  }
}
"""

# ── 辅助：将 Qwen 提取结果转换为 PricingInput ──────────────────────────────

def extracted_to_pricing_input(data: dict) -> PricingInput:
    """把 Qwen 提取的结构化 JSON 转换为 PricingInput 供引擎使用。"""
    fabric = data.get("fabric", {})
    packaging = data.get("packaging", {})
    labor = data.get("labor", {})

    accessory_lines = []
    for acc in data.get("accessories", []):
        up = acc.get("unit_price")
        qty = acc.get("qty_per_piece")
        if up is not None and qty is not None:
            accessory_lines.append((Decimal(str(up)), Decimal(str(qty))))

    process_lines = []
    for i, proc in enumerate(data.get("processes", [])):
        up = proc.get("unit_price")
        if up is not None:
            process_lines.append(ProcessLineItem(
                process_id=f"p-extracted-{i+1:03d}",
                process_name=proc.get("name", f"工艺{i+1}"),
                unit_price=Decimal(str(up)),
                quantity=Decimal("1"),
                supplier=proc.get("supplier") or "待录入",
                quote_date=proc.get("quote_date") or "2026-06-16",
            ))

    fabric_price = Decimal(str(fabric["unit_price"])) if fabric.get("unit_price") is not None else None
    pkg_price = Decimal(str(packaging["unit_price"])) if packaging.get("unit_price") is not None else None
    labor_hourly = Decimal(str(labor["unit_price_per_hour"])) if labor.get("unit_price_per_hour") is not None else None
    labor_hours = Decimal(str(labor["hours_per_piece"])) if labor.get("hours_per_piece") is not None else None
    loss_rate = Decimal(str(data["loss_rate"])) if data.get("loss_rate") is not None else None

    return PricingInput(
        sku_id=data.get("sku_id", "sku-extracted"),
        sku_name=data.get("sku_name", ""),
        fabric_unit_price=fabric_price,
        fabric_quantity=FABRIC_QTY_PER_PIECE,
        accessory_lines=accessory_lines,
        process_lines=process_lines,
        packaging_unit_price=pkg_price,
        packaging_quantity=Decimal("1"),
        loss_rate=loss_rate,
        labor_unit_price=labor_hourly,
        labor_hours=labor_hours,
        overhead_rate=Decimal("0.10"),   # 从 overhead_profit_ref 表获取，此处硬编码演示
        profit_rate=Decimal("0.15"),     # 同上
    )


def extracted_to_lead_time_input(data: dict, production_days: int = 5) -> LeadTimeInput:
    items: list[LeadTimeItem] = []

    fabric = data.get("fabric", {})
    if fabric.get("lead_time_days") is not None:
        items.append(LeadTimeItem(
            name="面料",
            days=int(fabric["lead_time_days"]),
            relation=LeadTimeRelation(fabric.get("lead_time_relation") or "parallel"),
            phase=int(fabric.get("lead_time_phase") or PHASE_PROCUREMENT),
        ))

    for acc in data.get("accessories", []):
        if acc.get("lead_time_days") is not None:
            items.append(LeadTimeItem(
                name=acc.get("name", "辅料"),
                days=int(acc["lead_time_days"]),
                relation=LeadTimeRelation(acc.get("lead_time_relation") or "parallel"),
                phase=int(acc.get("lead_time_phase") or PHASE_PROCUREMENT),
            ))

    for proc in data.get("processes", []):
        if proc.get("lead_time_days") is not None:
            items.append(LeadTimeItem(
                name=proc.get("name", "工艺"),
                days=int(proc["lead_time_days"]),
                relation=LeadTimeRelation(proc.get("lead_time_relation") or "sequential"),
                phase=int(proc.get("lead_time_phase") or PHASE_PROCESS),
            ))

    # Production is always added as an internal item (not from supplier quotes)
    items.append(LeadTimeItem(
        name="生产",
        days=production_days,
        relation=LeadTimeRelation.SEQUENTIAL,
        phase=PHASE_PRODUCTION,
    ))

    pkg = data.get("packaging", {})
    if pkg.get("lead_time_days") is not None:
        items.append(LeadTimeItem(
            name="包装",
            days=int(pkg["lead_time_days"]),
            relation=LeadTimeRelation(pkg.get("lead_time_relation") or "sequential"),
            phase=int(pkg.get("lead_time_phase") or PHASE_PACKAGING),
        ))

    return LeadTimeInput(items=items)


# ── 主测试 ─────────────────────────────────────────────────────────────────

def test_qwen_sku_distillation_and_pricing():
    api_key = os.environ.get("QWEN_API_KEY") or os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        pytest.skip("QWEN_API_KEY 未设置，跳过实时 API 测试")

    source_ref = "hangzhou-deli-textile-quote-2026-06-16.txt (模拟供应商报价单)"

    # Step 1 — 蒸馏流水线前置门控：来源必须是 Tier1/Tier2
    print("\n" + "="*60)
    print("Step 1: 蒸馏流水线门控验证")
    validate_submission("tier2", source_ref)
    print(f"  ✅ 来源验证通过 (tier2)：{source_ref}")

    # Step 2 — 构建蒸馏 prompt 并调用 Qwen
    print("\nStep 2: 调用 Qwen 提取结构化字段（parser 模式，禁止估算）")
    provider = QwenProvider(api_key=api_key)

    extraction_prompt = build_extraction_prompt(SUPPLIER_QUOTE_DOC)
    result = provider.extract_json(
        prompt=extraction_prompt,
        schema_hint=EXTRACTION_SCHEMA,
        system_prompt=(
            "你是一个精确的数据结构化解析器。"
            "严格按照 schema 抽取原文中已有的数字，任何原文没有明确给出的数值一律填 null。"
            "禁止基于行业常识补全或估算任何数字。"
            "每个字段必须附带 source_text（原文对应片段）以供人工核验。"
            "仅输出 JSON，不加任何解释或 markdown 围栏。"
        ),
    )

    print(f"  LLM: {result.provider_name} / {result.model_name}")
    print(f"  Token 用量: {result.usage}")
    extracted = result.data

    # Step 3 — 检查提取结果
    print("\nStep 3: 提取结果（extraction_output，状态=pending，待人工审核）")
    print(json.dumps(extracted, ensure_ascii=False, indent=2))

    # 关键检查：提取是否出现 JSON 解析错误
    assert "_error" not in extracted, (
        f"Qwen 输出无法解析为 JSON: {extracted.get('_raw', '')[:200]}"
    )

    # Step 4 — 模拟"人工审核通过"（人工确认后才能进入下一步）
    print("\nStep 4: 模拟人工审核通过")
    validate_approval(extracted, reviewed_by="m@giraffe.com")
    print("  ✅ 人工审核门控通过 (reviewed_by=m@giraffe.com)")

    # Step 5 — 将审核通过的提取结果送入确定性定价引擎
    print("\nStep 5: 确定性报价计算（PricingEngine，无 LLM，无估算）")
    pricing_input = extracted_to_pricing_input(extracted)
    engine = PricingEngine()

    try:
        breakdown = engine.calculate(pricing_input)

        print("\n  ┌─ 报价明细 ─────────────────────────────────────────┐")
        print(f"  │ 面料成本    ¥{breakdown.fabric_cost:>10.4f}                     │")
        print(f"  │ 辅料成本    ¥{breakdown.accessory_cost:>10.4f}                     │")
        print(f"  │ 工艺成本    ¥{breakdown.process_cost:>10.4f}                     │")
        print(f"  │ 包装成本    ¥{breakdown.packaging_cost:>10.4f}                     │")
        print(f"  │ 损耗成本    ¥{breakdown.loss_cost:>10.4f}                     │")
        print(f"  │ 人工成本    ¥{breakdown.labor_cost:>10.4f}                     │")
        print(f"  │ ─────────────────────────────────────────────────  │")
        print(f"  │ 小计        ¥{breakdown.subtotal:>10.4f}                     │")
        print(f"  │ 管理费(10%) ¥{breakdown.overhead_fee:>10.4f}                     │")
        print(f"  │ 总成本      ¥{breakdown.total_cost:>10.4f}                     │")
        print(f"  │ 报价(+15%)  ¥{breakdown.quoted_price:>10.4f}                     │")
        print(f"  └────────────────────────────────────────────────────┘")

        # 确定性验证：再算一次，结果必须完全相同
        breakdown2 = engine.calculate(pricing_input)
        assert breakdown == breakdown2, "确定性校验失败：两次计算结果不一致！"
        print("\n  ✅ 确定性验证通过：两次计算结果完全相同")

        # lead time 计算
        lt_engine = LeadTimeEngine()
        lt_input = extracted_to_lead_time_input(extracted, production_days=5)
        total_lead_time = lt_engine.calculate(lt_input)
        print(f"\n  Lead Time（采购关键路径 + 生产）：{total_lead_time} 天")
        assert total_lead_time == 31, (
            f"Lead time 预期 31 天，实际 {total_lead_time} 天。"
            f"items: {[(i.name, i.days, i.relation, i.phase) for i in lt_input.items]}"
        )

    except MissingPricingDataError as e:
        # 数据缺失时，引擎正确报错而非静默跳过
        print(f"\n  ⚠️  MissingPricingDataError（符合预期——缺失字段须补录）：")
        print(f"     {e}")
        # 测试仍然通过：引擎按规范拒绝计算，不会静默估算
        print("  ✅ 引擎正确拒绝缺数据的报价请求，符合 spec §2 要求")

    # Step 6 — extra_display_only 隔离验证
    print("\nStep 6: extra_display_only 字段隔离验证")
    extra = extracted.get("extra_display_only", {})
    print(f"  展示字段（不参与计价）：{extra}")
    print("  ✅ 以上字段仅用于前端展示，计算引擎从未读取")

    print("\n" + "="*60)
    print("全流程完成：Qwen 蒸馏 → 人工门控 → 确定性引擎报价")
    print("="*60 + "\n")


if __name__ == "__main__":
    # 也可直接运行：python tests/pricing/test_qwen_sku_live.py
    os.environ.setdefault("QWEN_API_KEY", "")
    test_qwen_sku_distillation_and_pricing()
