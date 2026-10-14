.PHONY: help up down restart logs test lint format typecheck simulate clean

help:
	@echo "Available commands:"
	@echo "  make up          - Start all containers (Kafka, Cassandra, Kafdrop, Engine, UI)"
	@echo "  make down        - Stop all containers"
	@echo "  make restart     - Restart all containers"
	@echo "  make logs        - Follow container logs"
	@echo "  make test        - Run unit tests with pytest"
	@echo "  make lint        - Check code formatting with ruff"
	@echo "  make format      - Format code with ruff"
	@echo "  make typecheck   - Run mypy type checker"
	@echo "  make simulate    - Run synthetic market order generator (15 orders)"
	@echo "  make clean       - Remove cached files and test artifacts"

up:
	docker compose up -d

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f

test:
	python -m pytest tests -v

lint:
	python -m ruff check .

format:
	python -m ruff format .

typecheck:
	python -m mypy backend kafka frontend

simulate:
	python scripts/market_simulator.py --symbol AAPL --count 15 --rate 2.0

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	rm -rf .coverage htmlcov
