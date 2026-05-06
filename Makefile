# =============================================================================
# Mallah Backend — Make targets for everyday workflows
# =============================================================================

.PHONY: help install dev migrate makemigration test lint format \
        up down logs shell deploy backup

help:
	@echo "Mallah Backend — common targets"
	@echo ""
	@echo "  install         Install Python deps + pre-commit"
	@echo "  dev             Run API locally (requires postgres + redis up)"
	@echo "  test            Run tests"
	@echo "  lint            Ruff check"
	@echo "  format          Ruff format"
	@echo "  migrate         Apply DB migrations"
	@echo "  makemigration   Generate a new migration (M=\"message\")"
	@echo "  up              docker compose up -d"
	@echo "  down            docker compose down"
	@echo "  logs            Tail API logs"
	@echo "  shell           psql shell into the running DB"
	@echo "  backup          Run a one-off pg_dump"
	@echo "  deploy          Build + push + restart prod stack"

install:
	pip install --upgrade pip
	pip install -e ".[dev]"
	pre-commit install || true

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest -v --cov=app --cov-report=term-missing

lint:
	ruff check app tests

format:
	ruff format app tests
	ruff check --fix app tests

migrate:
	alembic upgrade head

makemigration:
	@if [ -z "$(M)" ]; then echo "Usage: make makemigration M=\"add foo table\""; exit 1; fi
	alembic revision --autogenerate -m "$(M)"

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f api

shell:
	docker compose exec postgres psql -U mallah -d mallah

backup:
	@mkdir -p backups
	docker compose exec -T postgres pg_dump -U mallah mallah | gzip > backups/mallah-$(shell date +%Y%m%d-%H%M%S).sql.gz
	@echo "Backup written to backups/"

deploy:
	@echo "Production deploy"
	docker compose pull
	docker compose up -d --build
	docker compose exec api alembic upgrade head
	@echo "Deploy complete"
