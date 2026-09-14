.PHONY: lint typecheck test test-single all

all: lint typecheck test

lint:
	uv run ruff check .
	uv run ruff format --check .

typecheck:
	uv run mypy src/

test:
	uv run pytest tests/ -v --cov=src/ --cov-report=term-missing

test-single:
	uv run pytest $(TEST_PATH) -v

test-coverage:
	uv run pytest tests/ -v --cov=src/ --cov-report=html
