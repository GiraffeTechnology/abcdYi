.PHONY: install db-up migrate test api dev clean

install:
	uv sync

db-up:
	docker compose up -d db

migrate:
	uv run alembic upgrade head

test:
	uv run pytest tests/api/ tests/unit/ -v

api:
	uv run uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

dev:
	docker compose up --build

clean:
	docker compose down -v
