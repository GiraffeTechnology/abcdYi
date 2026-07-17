# Environment Variable Matrix — abcdYi (Stage 1)

## Backend

| Variable | Repository | Reader | Default | Production required | Secret | Obsolete |
|---|---|---|---|---|---|---|
| DATABASE_URL | abcdYi | `src/db/base.py`, `src/db/config.py` | local PG dsn | yes | contains credentials | no |
| SECRET_KEY | abcdYi | `src/db/base.py`; fail-fast guard `api/main.py` startup | placeholder (refused at startup) | yes (>=32 chars, fail-closed) | yes | no |
| ALGORITHM / ACCESS_TOKEN_EXPIRE_MINUTES | abcdYi | `src/db/base.py`, `api/auth.py` | HS256 / 60 | no | no | no |
| GLTG_API_BASE_URL / GLTG_API_TIMEOUT_SECONDS | abcdYi | `src/integrations/gltg_client.py` (+ AIVAN GLTG client) | localhost:8090 / 30 | yes | no | no |
| GLTG_API_VERSION | abcdYi | `src/aivan/integrations/gltg.py` | v1 | no | no | no |
| LLM_PROVIDER / LLM_ENABLE_REAL_CALLS | abcdYi | `src/llm/*` | stub / off (fail-closed) | no | no | no |
| OPENAI_API_KEY / QWEN_API_KEY / DASHSCOPE_API_KEY | abcdYi | `src/llm/*`, QC/GPM | empty | only if provider enabled | yes | no |
| QWEN_MODEL / QWEN_TEXT_MODEL / QWEN_VISION_MODEL / QWEN_BASE_URL | abcdYi | `src/llm/*`, `src/qc/*` | provider defaults | no | no | no |
| QC_ALLOW_EXTERNAL_LLM / QC_ALLOW_CAD_TO_LLM / QC_ALLOW_BOM_TO_LLM | abcdYi | `src/qc/*` | off (fail-closed) | no | no | no |
| GIRAFFE_ENV | abcdYi | provider registries (llm, logistics) | development | yes (gates real providers) | no | no |
| GIRAFFE_DB_MODE / GIRAFFE_DB_URL / GIRAFFE_DB_BASE_URL | abcdYi | BM DB CI harness, `src/gpm/clients/giraffe_db_client.py` | off / unset | per deployment | URL may embed credentials | no |
| GPM_* (RUNTIME_PROFILE, CONTEXT_RETRIEVER, QWEN_MNN_MODEL_PATH, GIRAFFE_DB_*) | abcdYi | `src/gpm/*`, smoke scripts | mock-safe defaults | per deployment | API key: yes | no |
| OPENCLAW_BASE_URL / OPENCLAW_API_KEY / OPENCLAW_MOCK_MODE | abcdYi | `src/openclaw_skill/*`, AIVAN openclaw adapter | mock | per deployment | API key: yes | no |

## AIVAN component (first-party frontend / digital employee)

| Variable group | Reader | Default | Notes |
|---|---|---|---|
| AIVAN_DB_URL | `src/aivan/db/session.py` | `sqlite:///./data/aiven.db` | component-local store; PG dsn in server deployments |
| AIVAN_HOST / AIVAN_PORT | `aivan serve` | 127.0.0.1:8765 | integrated & standalone entry |
| AIVAN_API_KEY / AIVAN_AUTH_SECRET | AIVAN API auth | unset | secret: yes |
| AIVAN_LLM_PROVIDER / AIVAN_LLM_TIMEOUT_SECONDS / AIVAN_STRATEGY_LLM_ENABLED / AIVAN_EVENT_CLASSIFICATION_LLM_ENABLED | `src/aivan/llm/*`, execution | mock / deterministic-off | fail-closed: LLM paths off unless enabled |
| AIVAN_EXTERNAL_MODEL_API_ENABLED / _AUTO_ALLOWED / AIVAN_EXTERNAL_API_CONFIRMATION_REQUIRED | `src/aivan/execution/*` | off / confirmation required | no automatic external LLM calls |
| AIVAN_REQUIRE_HUMAN_APPROVAL | AIVAN execution/safety | true-by-policy | human approval gate |
| AIVAN_EMAIL_SEND_MODE / AIVAN_EMAIL_GATEWAY / AIVAN_EMAIL_ALLOWED_RECIPIENTS / AIVAN_SMTP_* / AIVAN_IMAP_* | `src/aivan/openclaw/email_transport.py` | draft-only | no automatic sending; SMTP/IMAP credentials: secret |
| AIVAN_HIDE_SUPPLIER_IDENTITY_FROM_BUYER / _PRICE_FROM_BUYER | AIVAN sourcing | on | private-domain data boundary |
| AIVAN_BLOCK_CRITICAL_RISK_SUPPLIERS / AIVAN_ENABLE_UNKNOWN_SUPPLIER_RISK_SEARCH / AIVAN_ALLOW_STUB_SUPPLIERS | AIVAN risk/sourcing | fail-closed | |
| AIVAN_DEFAULT_MARGIN_RATE | AIVAN pricing | operator-set | operator-controlled margin |
| AIVAN_ENV / AIVAN_ALIBABA_MODE | AIVAN runtime | development / mock | |

## Removed in Stage 1

| Variable | Where | Reason |
|---|---|---|
| APP_ENV | `.env.example` | read by no code (grep-verified, full tree) |
| LOG_LEVEL | `.env.example` | read by no code |

## Rules verified

- No real secrets committed (placeholders only).
- Mock/live switches explicit and fail-closed (`LLM_ENABLE_REAL_CALLS`,
  `QC_ALLOW_*`, `OPENCLAW_MOCK_MODE`, `GIRAFFE_DB_MODE`, `AIVAN_EXTERNAL_*`,
  `AIVAN_EMAIL_SEND_MODE`).
- Production fails closed: weak `SECRET_KEY` refuses startup; GLTG clients
  never fall back to local calculation; AIVAN drafts require human approval.
- One base-URL variable per service; no duplicate-priority conflicts found.
