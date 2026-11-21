.RECIPEPREFIX = >
.PHONY: up down test lint

up:
> docker compose up --build

down:
> docker compose down

test:
> cd backend && pytest

lint:
> cd backend && ruff check . && cd ../frontend && npm run lint
