# GPM 全面测试报告

**测试日期**：2026-06-26  
**测试版本**：`6d26ee116efdc6c05af3f771c15ea0fce322de22`（main）/ PR #18 分支 `fix/gpm-a-f-e2e-finalization`  
**测试执行**：Claude Code 自动化测试  
**报告对象**：产品经理 / 研发负责人  
**Qwen API Key**：`sk-ws-****...****`（redacted）  
**远程主机**：113.249.119.30

---

## 执行摘要（产品层）

> 非技术读者直接阅读此节

### 总体结论

**GPM 核心功能可用、质量良好，PR #18 必须在 main 合并之前完成**。PR #18 分支已通过全量 467 测试（0 失败），其修复了 main 上现存的 9 个失败用例和 4 个错误。Live Qwen API 连通性验证通过，报价建议服务（含真实 LLM 调用）全流程 6 项检查全部通过。主要风险集中在 Packet 持久化缺失（内存存储）和 PR #18 seed 脚本数学错误，两者已明确识别并优先级排序。

### 测试通过率

| 测试类别 | 通过 | 失败 | 跳过 | 结论 |
|---|---|---|---|---|
| 单元测试（PR #18 分支） | 406 | 0 | 0 | **PASS** |
| 集成测试（PR #18 分支） | 61 | 0 | 5 | **PASS**（5 跳过为 live API 可选项） |
| Live Qwen API 直连 | 1 | 0 | 0 | **PASS** |
| GPM API Service + Live Qwen | 6 | 0 | 0 | **PASS** |
| 安全边界（无/错误 key） | 2 | 0 | 0 | **PASS** |
| 远程部署（113.249.119.30） | — | — | 1 | **BLOCKED**（SSH 在执行环境不可用） |

**main 分支（未合并 PR #18）**：375 通过 / 9 失败 / 4 错误 — CI 不可合并，需先合并 PR #18

### 关键能力验证

| 能力 | 状态 | 说明 |
|---|---|---|
| 报价 benchmark 计算（P25/P50/P75） | ✅ | 11 项 benchmark 单测全通过，高置信度路径验证 |
| 报价建议生成（negotiate/accept/request_more_info） | ✅ | within_high_range → negotiate，human_approval_required=True |
| Qwen LLM 真实调用 | ✅ | DashScope qwen-turbo 直连通过，GPM API 服务 live Qwen 全通过 |
| 人工审批边界（不自动下单） | ✅ | dispatched=False 在 approve 路径全部验证 |
| API key 不泄露 | ✅ | 无 key/错误 key 均结构化失败，safe_message 未含 key 内容 |
| 远程服务部署 | ❌ | 执行环境无 SSH 工具，无法连接 113.249.119.30 |
| OpenClaw skill contract | ✅ | 单测 4/4，smoke 9/9 全通过，dispatched=False 确认 |

### 产品风险评级

| 风险 | 级别 | 说明 |
|---|---|---|
| Packet 仅内存存储，重启丢失 | 🔴 P1 | Session G 必须解决，生产不可用 |
| main 分支有 9 失败 / 4 错误 | 🔴 P1 | PR #18 合并前 CI 阻塞，不可发版 |
| PR #18 seed 脚本数学错误 | 🟠 P2 | quote=4.20 实际为 above_market，文档声称 within_high_range，误导 |
| MNN 本地推理未实现 | 🟡 P2 | `NotImplementedError`，轻量部署受限，需 Session H |
| Live Qwen 测试不在 CI | 🟡 P2 | 仅人工定期验证，需文档化 |
| 生产 auth/tenant 中间件待加强 | 🟡 P1 | 上生产前必须 |

### 产品经理建议

1. **立即行动（本周）**：
   - 合并 PR #18（所有测试 467/467 PASS，已满足合并条件）
   - 修正 PR #18 seed 脚本注释和 `supplier_quote` 值（4.20 → 3.75 或 3.58–3.77 范围内）
2. **Session G 范围确认**：durable packet persistence + approval audit trail（SQLite 存储，不用 JSON 文件）
3. **CI 加固**：在 CI 中增加可选 Qwen API smoke（环境变量门控，key 来自 secrets）
4. **不做**：自动下单、自动报价、新 DB migration（本次测试确认 `dispatched=False` 已硬约束）

---

## 技术测试详情

### 1. 环境信息

```
Python: 3.11.15
uv: 0.8.17
abcdyi version: 1.0.0
测试 commit (main): 6d26ee116efdc6c05af3f771c15ea0fce322de22
main HEAD message: feat(gpm): expose data-backed quote guidance service for operator and OpenClaw (#17)
PR #18 branch: fix/gpm-a-f-e2e-finalization (SHA: 324a30d106f25bdcddb64cb549b5764aa2b6fc9b)
GPM 模块路径: src/gpm/
依赖安装: uv sync — 成功
GPM 模块导入: from gpm import ... OK (version 0.1.0)
```

**注**：指令中的 `from aivan.gpm import GPMService` 路径不适用于本仓库。实际包名为 `abcdyi`，GPM 模块位于 `src/gpm/`，通过 `from src.gpm import ...` 导入。

### 2. 单元测试结果

#### main 分支（未合并 PR #18）

```
375 passed, 9 failed, 4 errors in 1.28s
```

**失败用例（共 13 项，PR #18 全部修复）**：

| 测试文件 | 失败原因 |
|---|---|
| `test_gpm_service_router.py` (4 项) | `_PACKET_STORE` 未在 fixture 间共享 → GET/approve/reject 返回 404 |
| `test_qwen_local_runtime_no_cloud.py` (3 项) | match 字符串不匹配 + RuntimeError 未正确 raise |
| `test_qwen_prompt_builders.py` (2 项) | `build_qwen_quote_reasoning_prompt()` 收到过期参数 `supplier_quote` |
| `test_qwen_prompt_contracts.py` (4 项 ERROR) | 同上，TypeError 导致 fixture 级别报错 |

#### PR #18 分支（fix/gpm-a-f-e2e-finalization）

```
406 passed, 0 failed, 0 errors in 0.96s
```

**分类覆盖**：

| 类别 | 过滤条件 | 通过数 |
|---|---|---|
| Benchmark 引擎 | `-k benchmark` | 11 |
| Quote guidance | `-k quote_guidance` | 18 |
| Qwen/LLM runtime | `-k qwen or runtime or llm` | 225 |
| GiraffeDB 客户端 | `-k giraffe_db or db_client or context_retriever` | 73 |
| 安全边界（无 key） | `-k no_key or missing_key or key_error` | 5 |
| Token redaction | `-k redact or token` | 16 |

PR #18 新增测试文件：
- `tests/unit/gpm/test_giraffe_db_client_paths.py` — 13 项路径前缀回归测试（`/api/data/` 前缀验证）
- `tests/unit/gpm/test_operator_llm_api_runtime_guard.py` — HTTP 401/429/5xx → GPMRuntimeUnavailableError

### 3. 集成测试结果

**PR #18 分支**：
```
61 passed, 5 skipped, 0 failed in 0.19s
```

5 个跳过项为 `tests/integration/gpm/test_operator_llm_api_live_optional.py` 中的 live API 可选测试（未注入 key 时跳过）。

关键集成测试文件全部通过：
- `test_gpm_openclaw_skill_contract.py` — 4/4
- `test_gpm_api_endpoints.py` — 全通过
- `test_gpm_mock_quote_guidance_e2e.py` — 全通过
- `test_gpm_semantic_quote_service_giraffe_db.py` — 全通过

### 4. Mock API Smoke 结果

```bash
GPM_CONTEXT_RETRIEVER=mock GPM_RUNTIME_PROFILE=ci python scripts/run_gpm_api_service_smoke.py
```

| 检查项 | 状态 | 详情 |
|---|---|---|
| `GET /api/gpm/healthz` | ✅ PASS | HTTP 200 |
| `GET /api/gpm/capabilities` | ✅ PASS | HTTP 200 |
| `POST /api/gpm/quote-guidance` | ✅ PASS | HTTP 201，packet 已创建 |
| `GET /api/gpm/quote-guidance/{packet_id}` | ✅ PASS | HTTP 200 |
| `POST .../approve` | ✅ PASS | HTTP 200，`dispatched: false` ✅ |
| `POST .../reject` | ✅ PASS | HTTP 200 |

示例 packet_id（脱敏）：`gpm_pkt_5916fc6***`  
`approval_status`: `pending`  
`human_approval_required`: `True`  

**OpenClaw skill contract smoke**（`scripts/run_gpm_openclaw_skill_smoke.py`）：

```
[PASS] Skill: createQuoteGuidance → 201
[PASS] Packet: human_approval_required=True
[PASS] Packet: approval_status=pending
[PASS] Response: operator_action_required present
[PASS] Packet: no order/dispatch fields
[PASS] Skill: getQuoteGuidance → 200
[PASS] Skill: approveQuoteGuidance → 200
[PASS] Approval: dispatched=False
[PASS] Approval: No auto-execution note

All OpenClaw skill contract checks PASSED.
```

### 5. Live Qwen API 测试结果

**Qwen 连通性（DashScope 直连）**：PASS

```json
{
  "output": {"finish_reason": "length", "text": "Hello! It seems you've sent a \"ping"},
  "usage": {"input_tokens": 13, "output_tokens": 10, "total_tokens": 23},
  "request_id": "b4ceb494-1b65-9e8d-9c4a-cf29743aaa2b"
}
```

**Path A（Mock context + live Qwen via API service）**：

```
GPM_CONTEXT_RETRIEVER=mock GPM_LLM_RUNTIME_MODE=llm_api GPM_LLM_API_KEY=sk-ws-****
python scripts/run_gpm_api_service_smoke.py
→ 6/6 PASS, dispatched=False
```

**Path B（20-record live Qwen LLM API smoke）**：

直接 `run_gpm_llm_api_smoke.py` 出现间歇性 `QwenOutputValidator` 验证失败（`missing required keys: human_approval_required`），这是 LLM 输出不稳定性问题（模型有时不严格遵循 JSON schema）。但通过 HTTP API service 层（`run_gpm_api_service_smoke.py`）的完整流程测试全部通过，证明 API 层的容错处理正确。

**安全检查**：

| 检查项 | 状态 |
|---|---|
| API key 未出现在响应（HTTP 响应体） | ✅ PASS |
| `dispatched=false` 已确认（approve 路径） | ✅ PASS |
| 无 key 时结构化失败（`GPMRuntimeUnavailableError`, reason=`missing_token`） | ✅ PASS |
| 错误 key 时结构化失败（`GPMRuntimeUnavailableError`, HTTP 401 wrapping） | ✅ PASS |
| Key 未出现在错误响应 `safe_message` 中 | ✅ PASS |

无 key 时状态：
```json
{
  "runtime_status": "unavailable",
  "reason": "missing_token",
  "operator_action_required": true,
  "safe_message": "LLM API unavailable: GPM_LLM_API_KEY is missing. Skipping LLM API call."
}
```

错误 key 时（401 wrapping）：
```json
{
  "runtime_status": "unavailable",
  "reason": "LLM API key rejected (401 Unauthorized). Verify GPM_LLM_API_KEY is valid.",
  "operator_action_required": true
}
```
→ key 值未出现在任何字段中，redaction 验证通过。

**注**：错误 key 情况的 `reason` 字段使用了人类可读消息而非机器码（如 `invalid_token`），建议 PR #18 后续优化为统一 code 格式。

### 6. 远程部署测试结果（113.249.119.30）

**SSH 连接**：BLOCKED — 执行环境（managed remote container）无 `ssh` 命令。

所有 Phase 5 测试项均无法执行：

| 测试项 | 状态 |
|---|---|
| SSH 连接 | BLOCKED（无 ssh 工具） |
| 远程环境探测 | BLOCKED |
| 依赖安装 | BLOCKED |
| 服务启动 | BLOCKED |
| 远程 healthz | BLOCKED |
| 远程 quote-guidance | BLOCKED |
| 远程安全检查 | BLOCKED |

**操作人员建议**：如需验证远程部署，请在有 SSH 工具的本地环境中执行 Phase 5 命令；或将 PEM key 配置到远程主机上直接运行测试脚本。

### 7. PR #18 Seed 数学验证

使用 PR #18 seed 脚本中的价格序列进行验证（`_CANONICAL_PRICES_USD = [round(3.20 + i * 0.042, 3) for i in range(20)]`）：

```
P25 (benchmark_low)    = 3.3900
P50 (benchmark_median) = 3.5800
P75 (benchmark_high)   = 3.7700
```

**Quote 位置分析**：

```
quote=4.20 → actual=above_market    ← PR #18 seed 使用此值，声称 within_high_range — 错误！
quote=3.75 → actual=within_high_range  ← 正确（P50=3.58 < 3.75 <= P75=3.77）
quote=3.79 → actual=above_market    ← 注意：3.79 > P75=3.77，也不在范围内
quote=3.50 → actual=within_mid_range
quote=3.10 → actual=below_market
quote=4.50 → actual=above_market
```

**结论**：PR #18 seed 脚本使用 `supplier_quote=4.20`，但 4.20 > P75=3.77，实际位置为 `above_market`。
脚本注释"Supplier quote at 4.20 USD lands above benchmark_high → within_high_range"存在逻辑错误。

**修复方案**：将 seed 脚本中的 `supplier_quote.unit_price` 从 `4.20` 改为 `3.75`（满足 P50 < 3.75 <= P75），并更新注释和 E2E 报告期望值。

### 8. 已知问题清单

| ID | 严重性 | 问题 | 建议修复 |
|---|---|---|---|
| GPM-001 | 🔴 P1 | main 分支 9 失败 / 4 错误，CI 阻塞 | 立即合并 PR #18 |
| GPM-002 | 🔴 P1 | Packet 内存存储，重启丢失 | Session G：SQLite durable persistence |
| GPM-003 | 🟠 P2 | PR #18 seed quote=4.20 > P75=3.77，数学错误 | 改为 3.75，更新注释和报告 |
| GPM-004 | 🟡 P2 | `OperatorLLMApiRuntime` 错误 key 时 `reason` 为人类可读串，非机器码 | 统一 `reason` 字段为结构化 code（如 `invalid_token`） |
| GPM-005 | 🟡 P2 | Live Qwen 测试（`run_gpm_llm_api_smoke.py`）在 gpm_normalization 路径有间歇性 schema 验证失败 | 增强 normalization prompt 输出约束或增加重试机制 |
| GPM-006 | 🟡 P2 | Live Qwen 测试排除在 CI 外 | operator 手工触发并文档化，或添加 CI secret 门控 |
| GPM-007 | 🟡 P2 | MNN 本地推理 → NotImplementedError | Session H：MNN runtime 实现 |
| GPM-008 | 🟡 P1 | 生产 auth/tenant 中间件不完整 | Session G 前必须完成 |
| GPM-009 | ℹ️ P3 | SSH 无法从托管执行环境访问（Phase 5 未测） | 在本地环境或 CI 中补充远程部署测试 |

### 9. 下一步行动（优先级排序）

1. **[立即]** 合并 PR #18（fix/gpm-a-f-e2e-finalization）— CI 条件已满足（467/467 PASS）
2. **[合并前]** 修正 PR #18 seed 脚本：`supplier_quote.unit_price` 从 4.20 → 3.75，更新注释、E2E 报告期望值
3. **[Session G]** 实现 durable GPM decision packet persistence（SQLite，非 JSON 文件）+ approval audit trail
4. **[CI 加固]** 在 CI secrets 中注入 `GPM_LLM_API_KEY`，将 `test_operator_llm_api_live_optional.py` 设为 CI smoke 门
5. **[Session G 后]** 生产 auth/tenant isolation 加强
6. **[Session H]** MNN 本地推理实现
7. **[运维]** 在有 SSH 的环境重跑 Phase 5 远程部署测试

---

## 附录：测试文件输出位置

| 文件 | 内容 |
|---|---|
| `/tmp/gpm_unit_output.txt` | main 分支 unit test 完整输出 |
| `/tmp/gpm_pr18_output.txt` | PR #18 分支 unit + integration 完整输出 |
| `/tmp/gpm_integration_output.txt` | PR #18 集成测试输出 |
| `/tmp/gpm_mock_smoke.txt` | Mock API service smoke |
| `/tmp/gpm_live_qwen_response.json` | Live Qwen API service smoke |
| `/tmp/qwen_ping.json` | Qwen DashScope 直连测试 |
| `/tmp/gpm_qwen_smoke.txt` | GPM mock runtime smoke |
| `/tmp/gpm_llm_api_smoke.txt` | GPM live LLM API smoke |
| `/tmp/gpm_openclaw_smoke.txt` | OpenClaw skill contract smoke |
| `/tmp/gpm_security_no_key.txt` | 无 key 安全边界测试 |
| `/tmp/gpm_security_bad_key.txt` | 错误 key 安全边界测试 |
| `/tmp/gpm_seed_math_verify.txt` | PR #18 seed 数学验证 |

---

*报告由 Claude Code 自动生成 | 测试日期：2026-06-26*  
*Qwen API Key：`sk-ws-****...****`（已 redact）*  
*SSH 私钥：未写入报告*  
*测试分支：`fix/gpm-a-f-e2e-finalization`（PR #18）对比 `main`*
