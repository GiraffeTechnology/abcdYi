.PHONY: install db-up migrate test test-unit test-integration api dev clean validate docker-validate

install:
	uv sync

db-up:
	docker compose up -d db

migrate:
	uv run alembic upgrade head

test-unit:
	uv run pytest tests/unit/ -v -m "not integration"

test-integration:
	uv run pytest tests/integration/ -v

test:
	uv run pytest tests/unit/ tests/integration/ -v

api:
	uv run uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

dev:
	docker compose up --build

clean:
	docker compose down -v

validate:
	./scripts/run_clean_db_validation.sh

docker-validate:
	docker compose down -v
	docker compose build
	docker compose up -d db
	docker compose run --rm migrate
	docker compose up -d api
	sleep 5
	curl -f http://localhost:8000/health
	uv run pytest tests/unit/ -v -m "not integration"
	uv run pytest tests/integration/ -v
