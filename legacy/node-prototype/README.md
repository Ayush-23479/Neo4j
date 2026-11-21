# Explainable Payment Holds

> **All data is synthetic. PayPal is sandbox only. No real money, people or watchlists.**

A screening and tracking layer for cross-border payments, built on one Relate graph. It decides
whether a payment looks risky, keeps the proof (a graph path), and shows where the payment is now.

## Use case

TODO (Task 20): one paragraph on explainable payment holds, the two checks (name check and
three-hop graph walk) and the lineage half ("where is my money?").

## How it uses Relate

TODO (Task 20): single-file or server mode, why, and what the graph models.

## Tech stack

| Part | Tool |
|---|---|
| Backend | FastAPI (Python 3.12), Pydantic |
| Graph | Relate by Neo4j |
| Frontend | React, Vite, TypeScript |
| Run | Docker Compose |
| Payments | PayPal sandbox only |

## Project structure

```
backend/        FastAPI app (app/api, ingest, screening, detect, decision, audit, graph) + tests
frontend/       React + Vite + TypeScript
graph/          Graph schema and named queries (graph/queries)
generator/      Synthetic data generator
data/           Relate store file and seed data
docs/           Notes, threat model, test report
tests/          End-to-end tests
.github/        CI, CodeQL, Dependabot
```

## Prerequisites

- Docker Desktop (running), for the one-command setup
- Python 3.12 and Node 20+, only if you run the parts without Docker

## 1. Setup (once)

```bash
cp .env.example .env
```

The values in `.env.example` are fake placeholders. Never commit your real `.env`.

## 2. Run everything with Docker (recommended)

Start Docker Desktop first and wait until it says "Engine running". Then:

```bash
docker compose up --build
```

- App: http://localhost:3000 (shows "Backend health: ok")
- Health check through the app: http://localhost:3000/api/health
- Only the frontend port is published. The backend port stays inside Docker.

Stop it:

```bash
docker compose down
```

Run in the background and read logs:

```bash
docker compose up --build -d
docker compose logs -f backend
```

Rebuild one service after a code change:

```bash
docker compose up --build backend
```

Optional graph service (placeholder until Task 2 decides embedded or server mode):

```bash
docker compose --profile server up --build
```

## 3. Run without Docker (for development)

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

- Health: http://localhost:8000/health
- API docs: http://localhost:8000/docs

### Frontend (second terminal)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Requests to `/api` are proxied to the backend on port 8000.

## 4. Tests and checks

Backend tests:

```bash
cd backend
source .venv/bin/activate
pytest
```

Lint and security scans:

```bash
cd backend
ruff check .
bandit -r app
pip-audit
```

Frontend:

```bash
cd frontend
npm run lint
npm run build
```

Shortcuts from the repo root (need `make`):

| Command | What it does |
|---|---|
| `make up` | `docker compose up --build` |
| `make down` | `docker compose down` |
| `make test` | backend tests |
| `make lint` | ruff and frontend lint |

## Environment variables

Defined in `.env.example`. Names only here, values live in `.env`.

| Variable | Meaning |
|---|---|
| `JWT_SECRET`, `JWT_TTL_MINUTES` | Login token secret and lifetime |
| `RELATE_MODE`, `RELATE_PATH`, `RELATE_URL` | How the backend reaches Relate (embedded or server) |
| `PAYPAL_BASE_URL`, `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_WEBHOOK_ID` | PayPal sandbox only |
| `DEMO_MODE` | `local` for development |
| `RISK_THRESHOLD`, `MULE_MIN_SENDERS`, `MULE_WINDOW_HOURS` | Screening settings (starting values, tuned later) |

## CI

On every push GitHub Actions runs ruff, pytest, Bandit, pip-audit, the frontend lint and build,
gitleaks and CodeQL. Dependabot opens weekly update pull requests.

## Troubleshooting

| Problem | Fix |
|---|---|
| `failed to connect to the docker API ... docker.sock` | Docker Desktop is not running. Open it, wait for "Engine running", try again. |
| `no such service: #` | You pasted a line with a `# comment` into zsh. Run the command without the comment. |
| Port 3000 is already in use | Change `"3000:8080"` in `docker-compose.yml`, or stop the other app. |
| `python3.12: command not found` | Use `python3` if it is 3.12 or newer, or `brew install python@3.12`. |
| Frontend shows "backend not reachable" | Backend is not running. Start Docker, or run uvicorn as in section 3. |
| `ModuleNotFoundError: app` when running pytest | Run it from the `backend` folder. |

## Where the data lives

TODO (Task 20): the committed Relate store file inside `data/`, with its real name.

## Synthetic data and sandbox notice

All people, companies, addresses, phones and trust scores are fake. The bank and ledger sides are
simulated in ISO 20022 style. Only the PayPal side is real, and only in the sandbox.

## License

Apache-2.0. See `LICENSE`.