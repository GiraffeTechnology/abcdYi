# Dependency Usage Report — abcdYi (Stage 1)

Classification of every `[project.dependencies]` entry after Stage 1, audited
against the FULL tree: backend (`api/`, `src/*`), the AIVAN component
(`src/aivan`), scripts, tests, CI, and deploy files. Frontend/CLI/plugin/
standalone-process usage counts as usage — "not imported by the backend" is
not a removal criterion.

| Dependency | Class | Evidence / notes |
|---|---|---|
| fastapi | runtime direct | backend `api/` app AND AIVAN web app (`src/aivan/api/main.py`) |
| uvicorn[standard] | runtime direct | backend serve + `aivan serve` |
| pydantic[email] | runtime direct | schemas in both components |
| pydantic-settings | runtime direct | `src/db/base.py` Settings |
| sqlalchemy | runtime direct | backend async ORM + AIVAN sync component store |
| alembic | runtime direct | backend migrations |
| asyncpg | runtime direct | backend async PG driver |
| psycopg2-binary | runtime direct (tooling) | sync driver for Alembic/CI harness — deliberate two-driver split, documented |
| python-jose[cryptography] | runtime direct | backend JWT (`api/auth.py`) |
| cryptography (<43 pin) | runtime direct | jose backend; pin inherited — REVIEW in a later stage |
| passlib[bcrypt] | runtime direct | password hashing |
| python-multipart | runtime direct | backend `OAuth2PasswordRequestForm` login |
| httpx | runtime direct | GLTG/giraffe-db clients (both components) + test client |
| jinja2 | runtime direct | **AIVAN web frontend** — `Jinja2Templates` + `src/aivan/app/templates/` |
| python-dotenv | runtime direct | **AIVAN CLI** env loader (`src/aivan/cli/main.py`) |
| bcrypt (<4 pin) | runtime direct | passlib compatibility pin |

Dev group (`[dependency-groups].dev`): pytest, pytest-asyncio, pytest-cov — dev only.

## Removed in Stage 1

| Dependency | Prior class | Reason (full-tree evidence) |
|---|---|---|
| eval-type-backport | unused (3.9 shim) | never imported; 3.11 baseline restored |
| aiosqlite | unused | AIVAN's store is sync SQLAlchemy over stdlib sqlite3; no async engine, no aiosqlite URL/import anywhere (backend, AIVAN, scripts, tests, CI) |
| structlog | unused | zero imports repo-wide |

## Duplicate / conflicting declarations fixed

- Dev dependencies were declared in BOTH `[project.optional-dependencies].dev`
  and `[dependency-groups].dev` with different httpx floors → consolidated
  into `[dependency-groups].dev` (uv's native mechanism; CI uses `uv sync`).
  httpx remains a runtime dependency.

## Security-flagged (PRD watchlist) status

- `eval-type-backport`, `aiosqlite`, `structlog` removed with evidence above.
- `pydantic-settings`, `passlib`, `bcrypt`, `cryptography`, `alembic`,
  `python-multipart`, `jinja2`, `python-dotenv` kept with evidence above.
- Two PostgreSQL drivers kept with documented reason (async app / sync alembic).
- The stale lock's `gltg` entry (never declared) is gone after the rebuild.
