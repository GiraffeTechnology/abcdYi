FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
COPY gpm/ ./gpm/

RUN pip install uv && uv pip install --system fastapi uvicorn sqlalchemy asyncpg pydantic pydantic-settings alembic psycopg2-binary

CMD ["uvicorn", "gpm.main:app", "--host", "0.0.0.0", "--port", "8001"]
