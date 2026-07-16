# Environment Variable Matrix — abcdYi (Stage 1)

| Variable | Repository | Reader | Default | Production required | Secret | Obsolete |
|---|---|---|---|---|---|---|
| DATABASE_URL | abcdYi | `src/db/base.py`, `src/db/config.py` | local PG dsn | yes | contains credentials | no |
| SECRET_KEY | abcdYi | `src/db/base.py`; fail-fast guard `api/main.py` startup | placeholder (refused at startup) | yes (>=32 chars, fail-closed) | yes | no |
| ALGORITHM | abcdYi | `src/db/base.py`, `api/auth.py` | HS256 | no | no | no |
| ACCESS_TOKEN_EXPIRE_MINUTES | abcdYi | `src/db/base.py`, `api/auth.py` | 60 | no | no | no |
| GLTG_API_BASE_URL | abcdYi | `src/integrations/gltg_client.py` | http://localhost:8090 | yes | no | no |
| GLTG_API_TIMEOUT_SECONDS | abcdYi | `src/integrations/gltg_client.py` | 30 | no | no | no |
| LLM_PROVIDER | abcdYi | `src/llm/__init__.py`, provider_registry | stub | no | no | no |
| LLM_ENABLE_REAL_CALLS | abcdYi | `src/llm/*` | off (fail-closed) | no | no | no |
| OPENAI_API_KEY | abcdYi | `src/llm/openai_provider.py` | empty | only if provider enabled | yes | no |
| QWEN_API_KEY / DASHSCOPE_API_KEY | abcdYi | `src/llm/*`, QC/GPM smoke scripts | empty | only if provider enabled | yes | no |
| QWEN_MODEL / QWEN_TEXT_MODEL / QWEN_VISION_MODEL / QWEN_BASE_URL | abcdYi | `src/llm/*`, `src/qc/*` | provider defaults | no | no | no |
| QC_ALLOW_EXTERNAL_LLM / QC_ALLOW_CAD_TO_LLM / QC_ALLOW_BOM_TO_LLM | abcdYi | `src/qc/*` | off (fail-closed) | no | no | no |
| GIRAFFE_ENV | abcdYi | `src/llm/provider_registry.py`, provider_config, logistics provider_config | development | yes (production gates real providers) | no | no |
| GIRAFFE_DB_MODE / GIRAFFE_DB_URL / GIRAFFE_DB_BASE_URL | abcdYi | BM DB CI harness (`bm_db_adapter.py`, `run_bm_e2e_with_db.py`), `src/gpm/clients/giraffe_db_client.py` | off / unset | per deployment | URL may embed credentials | no |
| GPM_RUNTIME_PROFILE / GPM_CONTEXT_RETRIEVER / GPM_QWEN_MNN_MODEL_PATH | abcdYi | `src/gpm/*` | mock-safe defaults | per deployment | no | no |
| GPM_GIRAFFE_DB_BASE_URL / GPM_GIRAFFE_DB_API_KEY / GPM_GIRAFFE_DB_TENANT_ID (+ PROJECT/RFQ ids in smoke scripts) | abcdYi | `src/gpm/clients/giraffe_db_client.py`, smoke scripts | unset | per deployment | API key: yes | no |
| OPENCLAW_BASE_URL / OPENCLAW_API_KEY / OPENCLAW_MOCK_MODE | abcdYi | `src/openclaw_skill/*` | mock | per deployment | API key: yes | no |
| SECRET rotation / others | — | — | — | — | — | — |

## Removed in Stage 1

| Variable | Where | Reason |
|---|---|---|
| APP_ENV | `.env.example` | read by no code (grep-verified) |
| LOG_LEVEL | `.env.example` | read by no code |
| AIVAN_* (AIVAN_API_KEY, AIVAN_AUTH_SECRET, AIVAN_SMTP_*, AIVAN_LLM_*) | code readers deleted with `src/aivan` | embed removed; the TypeScript OpenClaw plugin reads `AIVAN_API_KEY` in its own process (kept there) |

## Rules verified

- No real secrets committed (`.env.example` placeholders only).
- Mock/live switches are explicit and fail-closed (`LLM_ENABLE_REAL_CALLS`,
  `QC_ALLOW_*`, `OPENCLAW_MOCK_MODE`, `GIRAFFE_DB_MODE`).
- Production fails closed: weak `SECRET_KEY` refuses startup; GLTG client
  never falls back to local calculation.
- One base-URL variable per service (GLTG_API_BASE_URL, GIRAFFE_DB_BASE_URL,
  OPENCLAW_BASE_URL, QWEN_BASE_URL) — no duplicate-priority conflicts found.
