# Dependency Usage Report — abcdYi (Stage 1)

Classification of every `[project.dependencies]` entry after Stage 1.
Legend: runtime-direct = imported by product code; dev-only = tests/CI only.

| Dependency | Class | Evidence / notes |
|---|---|---|
| fastapi | runtime direct | `api/` app |
| uvicorn[standard] | runtime direct | serve entry (Dockerfile, README) |
| pydantic[email] | runtime direct | schemas, EmailStr |
| pydantic-settings | runtime direct | `src/db/base.py` Settings |
| sqlalchemy | runtime direct | ORM + async engine |
| alembic | runtime direct | migrations (`alembic/`) |
| asyncpg | runtime direct | async PG driver (`DATABASE_URL=postgresql+asyncpg://`) |
| psycopg2-binary | runtime direct (tooling) | sync driver for Alembic/CI harness. **Two PG drivers kept deliberately**: asyncpg for the app, psycopg2 for sync migration/verification paths. |
| python-jose[cryptography] | runtime direct | `api/auth.py` JWT |
| cryptography (<43 pin) | runtime direct | jose backend; pin inherited — REVIEW in a later stage |
| passlib[bcrypt] | runtime direct | password hashing |
| python-multipart | runtime direct | `OAuth2PasswordRequestForm` login |
| httpx | runtime direct | GLTG/giraffe-db HTTP clients; also test client |
| bcrypt (<4 pin) | runtime direct | passlib compatibility pin |

Dev group (`[dependency-groups].dev`): pytest, pytest-asyncio, pytest-cov — dev only.

## Removed in Stage 1

| Dependency | Prior class | Reason |
|---|---|---|
| eval-type-backport | unused (3.9 shim) | never imported; 3.11 baseline restored |
| aiosqlite | unused | zero references repo-wide |
| jinja2 | unused | zero references repo-wide |
| python-dotenv | unused after aivan removal | only reader was `src/aivan/cli/main.py` |
| structlog | unused | zero references repo-wide |

## Duplicate / conflicting declarations fixed

- Dev dependencies were declared in BOTH `[project.optional-dependencies].dev`
  and `[dependency-groups].dev` with different httpx floors (>=0.27 vs >=0.28.1).
  Consolidated into `[dependency-groups].dev` only (uv's native mechanism;
  CI uses `uv sync`/`uv add --dev`). httpx stays a runtime dep.

## Security-flagged (PRD watchlist) status

- `eval-type-backport` removed. `pydantic-settings`, `passlib`, `bcrypt`,
  `cryptography`, `alembic`, `python-multipart` kept with evidence above.
- `aiosqlite`, `jinja2`, `python-dotenv`, `structlog` removed.
- `gltg` was present in the stale lockfile only — never a declared dependency;
  gone after lock rebuild.
