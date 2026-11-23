.RECIPEPREFIX = >

.PHONY: up down test lint seed

up:
> docker compose --build up

down:
> docker compose down

test:
> cd backend && pytest

lint:
> cd backend && ruff check . && cd ../frontend && npm run lint

seed:
> cd backend && python -m app.graph.schema