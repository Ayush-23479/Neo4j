#!/usr/bin/env bash
# Task 1 setup for Explainable Payment Holds (FastAPI + React + Docker Compose).
# Run from the ROOT of your repo:   bash task1_setup.sh
# Safe to re-run: it never overwrites a file that already exists.
set -euo pipefail

w() {  # w <path>  (file content comes from the heredoc)
  mkdir -p "$(dirname "$1")"
  if [ -e "$1" ]; then echo "skip (exists): $1"; else cat > "$1"; echo "created: $1"; fi
}

# ---------- folders ----------
for d in backend/app/{api,ingest,screening,detect,decision,audit,graph} backend/tests \
         frontend/src graph/queries generator data docs tests .github/workflows; do
  mkdir -p "$d"
done
for p in app api ingest screening detect decision audit graph; do
  d="backend/app"; [ "$p" != "app" ] && d="backend/app/$p"
  [ -e "$d/__init__.py" ] || { : > "$d/__init__.py"; echo "created: $d/__init__.py"; }
done
touch data/.gitkeep graph/queries/.gitkeep generator/.gitkeep tests/.gitkeep docs/.gitkeep

# ---------- backend ----------
w backend/pyproject.toml <<'EOF'
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "payment-holds-backend"
version = "0.1.0"
description = "Explainable Payment Holds backend (FastAPI)"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115",
  "uvicorn[standard]>=0.30",
  "pydantic>=2.7",
  "httpx>=0.27",
  "defusedxml>=0.7",
  "rapidfuzz>=3.9",
  "slowapi>=0.1.9",
  "PyJWT>=2.8",
  "passlib[bcrypt]>=1.7.4",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.2",
  "pytest-asyncio>=0.23",
  "ruff>=0.5",
  "bandit>=1.7",
  "pip-audit>=2.7",
]

[tool.setuptools.packages.find]
include = ["app*"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
asyncio_mode = "auto"
EOF

w backend/app/main.py <<'EOF'
from fastapi import FastAPI

app = FastAPI(
    title="Explainable Payment Holds",
    description="Synthetic data and PayPal sandbox only.",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
EOF

w backend/tests/test_health.py <<'EOF'
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
EOF

w backend/Dockerfile <<'EOF'
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN useradd --create-home --uid 10001 appuser
WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir .

USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

w backend/.dockerignore <<'EOF'
__pycache__
*.pyc
.pytest_cache
.ruff_cache
tests
EOF

# ---------- frontend (Vite + React + TypeScript) ----------
w frontend/package.json <<'EOF'
{
  "name": "payment-holds-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc --noEmit && vite build",
    "lint": "tsc --noEmit",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "typescript": "^5.5.4",
    "vite": "^5.4.2"
  }
}
EOF

w frontend/index.html <<'EOF'
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Explainable Payment Holds</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
EOF

w frontend/vite.config.ts <<'EOF'
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": { target: "http://localhost:8000", rewrite: (p) => p.replace(/^\/api/, "") } },
  },
});
EOF

w frontend/tsconfig.json <<'EOF'
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noEmit": true,
    "skipLibCheck": true,
    "isolatedModules": true
  },
  "include": ["src", "vite.config.ts"]
}
EOF

w frontend/src/main.tsx <<'EOF'
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
EOF

w frontend/src/App.tsx <<'EOF'
import { useEffect, useState } from "react";

export default function App() {
  const [status, setStatus] = useState("checking...");

  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.json())
      .then((d: { status: string }) => setStatus(d.status))
      .catch(() => setStatus("backend not reachable"));
  }, []);

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", padding: 24 }}>
      <h1>Explainable Payment Holds</h1>
      <p>Backend health: {status}</p>
      <footer>All data is synthetic. PayPal is sandbox only.</footer>
    </main>
  );
}
EOF

w frontend/nginx.conf <<'EOF'
server {
  listen 8080;
  server_name _;
  root /usr/share/nginx/html;
  index index.html;

  location /api/ {
    proxy_pass http://backend:8000/;
    proxy_set_header Host $host;
  }

  location / {
    try_files $uri /index.html;
  }
}
EOF

w frontend/Dockerfile <<'EOF'
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
EOF

w frontend/.dockerignore <<'EOF'
node_modules
dist
EOF

# ---------- compose, env, git, license, readme, make ----------
w docker-compose.yml <<'EOF'
services:
  backend:
    build: ./backend
    env_file: .env
    expose:
      - "8000"          # internal only, not published to the host
    volumes:
      - ./data:/app/data
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request as u; u.urlopen('http://localhost:8000/health')"]
      interval: 10s
      timeout: 3s
      retries: 5

  frontend:
    build: ./frontend
    depends_on:
      - backend
    ports:
      - "3000:8080"     # the only published port

  # Placeholder. Task 2 decides if Relate runs embedded (no service) or as a server.
  # Start it only with:  docker compose --profile server up
  graph:
    image: alpine:3.20
    command: ["sleep", "infinity"]
    profiles: ["server"]
    expose:
      - "7687"
EOF

w .env.example <<'EOF'
# Copy to .env. Fake placeholder values only. Never commit a real .env.
JWT_SECRET=change-me-to-a-long-random-string
JWT_TTL_MINUTES=15
RELATE_MODE=embedded
RELATE_PATH=./data/graph
RELATE_URL=
PAYPAL_BASE_URL=https://api-m.sandbox.paypal.com
PAYPAL_CLIENT_ID=sandbox-client-id-placeholder
PAYPAL_CLIENT_SECRET=sandbox-client-secret-placeholder
PAYPAL_WEBHOOK_ID=sandbox-webhook-id-placeholder
DEMO_MODE=local
RISK_THRESHOLD=50
MULE_MIN_SENDERS=5
MULE_WINDOW_HOURS=24
EOF

w .gitignore <<'EOF'
.env
__pycache__/
*.pyc
.pytest_cache/
.ruff_cache/
.venv/
node_modules/
dist/
*.egg-info/
.DS_Store
EOF

w README.md <<'EOF'
# Explainable Payment Holds

> All data is synthetic. PayPal is sandbox only.

## Use case
TODO (Task 20)

## How it uses Relate
TODO (Task 20)

## Setup
```bash
cp .env.example .env
docker compose up --build
# frontend: http://localhost:3000   health: through the frontend at /api/health
```

## Where the data lives
TODO (Task 20): the Relate store file inside `data/`.

## Synthetic data and sandbox notice
All people, companies, addresses, phones and trust scores are fake. The PayPal side uses the
sandbox with no real money.
EOF

w Makefile <<'EOF'
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
EOF

if [ ! -e LICENSE ]; then
  if curl -fsSL https://www.apache.org/licenses/LICENSE-2.0.txt -o LICENSE; then
    echo "created: LICENSE (Apache-2.0)"
  else
    echo "!! Could not download LICENSE. Add Apache-2.0 text manually (GitHub: Add file > Create > LICENSE)."
  fi
fi

# ---------- CI ----------
w .github/workflows/ci.yml <<'EOF'
name: CI
on:
  push:
  pull_request:

jobs:
  backend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e ".[dev]"
      - run: ruff check .
      - run: pytest
      - run: bandit -r app
      - run: pip-audit

  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - run: npm install
      - run: npm run lint
      - run: npm run build

  gitleaks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
EOF

w .github/workflows/codeql.yml <<'EOF'
name: CodeQL
on:
  push:
    branches: [main]
  pull_request:
  schedule:
    - cron: "0 3 * * 1"

jobs:
  analyze:
    runs-on: ubuntu-latest
    permissions:
      security-events: write
      contents: read
    strategy:
      matrix:
        language: [python, javascript-typescript]
    steps:
      - uses: actions/checkout@v4
      - uses: github/codeql-action/init@v3
        with:
          languages: ${{ matrix.language }}
      - uses: github/codeql-action/analyze@v3
EOF

w .github/dependabot.yml <<'EOF'
version: 2
updates:
  - package-ecosystem: pip
    directory: /backend
    schedule: { interval: weekly }
  - package-ecosystem: npm
    directory: /frontend
    schedule: { interval: weekly }
  - package-ecosystem: docker
    directory: /backend
    schedule: { interval: weekly }
  - package-ecosystem: docker
    directory: /frontend
    schedule: { interval: weekly }
  - package-ecosystem: github-actions
    directory: /
    schedule: { interval: weekly }
EOF

echo
echo "Done. Next:"
echo "  cp .env.example .env"
echo "  (cd backend && python3.12 -m venv .venv && . .venv/bin/activate && pip install -e '.[dev]' && pytest)"
echo "  docker compose up --build      # then open http://localhost:3000"