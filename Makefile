.PHONY: run dev test lint migrate upgrade downgrade shell

# Dev server
dev:
	poetry run fastapi dev app/main.py

# Tests
test:
	poetry run pytest tests/ -v

test-cov:
	poetry run pytest tests/ -v --cov=app --cov-report=term-missing

# Linting
lint:
	poetry run ruff check app/ tests/
	poetry run ruff format --check app/ tests/

format:
	poetry run ruff format app/ tests/

# Database
migrate:
	poetry run alembic revision --autogenerate -m "$(msg)"

upgrade:
	poetry run alembic upgrade head

downgrade:
	poetry run alembic downgrade -1

# Infrastructure
up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

# Python shell
shell:
	poetry run python