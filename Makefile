PY ?= backend/.venv/bin/python

.PHONY: up down test lint seed

up:
	docker compose up --build

down:
	docker compose down

test:
	cd backend && pytest

lint:
	cd backend && ruff check . && cd ../frontend && npm run lint

seed:
	$(PY) generator/generate.py
	$(PY) generator/loader.py
