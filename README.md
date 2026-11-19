# CorridorGuard AI

![Relate by Neo4j Hackathon 2026](https://images.unsplash.com/photo-1558655169-3e56b641180e?w=800&fit=crop&q=80)

## One-line pitch
An embedded cross-border sanctions screening system that leverages Relate's single-file openCypher engine to detect financial crime networks through fuzzy name matching, 3-hop graph traversal, and deterministic risk scoring — all within a solitary `.rl` file for offline auditability and rapid deployment.

## Use case

CorridorGuard AI solves the critical problem of detecting illicit money movement across borders in real time. Financial institutions must screen transactions against global sanctions watchlists, but face challenges with:

- **Fuzzy name matching**: Detecting near-matches on watchlist names (e.g., "John Doe" vs "Jon Doe")
- **Hidden network detection**: Uncovering criminal networks layered through corporate structures, P2P mules, and intermediary fees
- **Multi-protocol ingestion**: Normalizing PayPal, SWIFT ISO 20022 `pac.008` and `pac.002` events into a unified graph
- **Human-in-the-loop compliance**: Allowing compliance officers to override decisions and file Suspicious Activity Reports (SARs)

The relationships that matter most are: `OWNS` (corporate control), `REGISTERED_AT` (address registration), `SHARES_PHONE` (mule coordination), `SENT_FUNDS_TO` (payment flow), and `SCREENED_AS` (decision audit trail).

## How it uses Relate

| Aspect | Detail |
|---|---|
| **Mode: single file** | `./data/corridor_guard.rl` — embedded, zero-server execution |
| **Why this mode** | Zero-server embedded execution, deterministic sub-millisecond 3-hop traversals, offline regulator auditability, and direct MCP/agent compatibility |
| **What the graph models** | All 9 node labels and 9 relationship types: `(:Person)`, `(:Company)`, `(:Address)`, `(:Phone)`, `(:BankAccount)`, `(:SanctionedEntity)`, `(:Payment)`, `(:Decision)`, `(:SanctionProgram)`, plus `(:PayPalEvent)`, `(:BankMessage)`, `(:LedgerEntry)`, and `(:Fee)` |

## Setup and run

```bash
# 1. Install dependencies
npm install

# 2. Seed the database with 4 pre-loaded demo cases
node src/seed.js

# 3. Start the Express backend
npm start
```

The server will be available at `http://localhost:3000`.

### CLI inspection

Inspect persisted decisions directly via the Relate CLI:

```bash
relate --database ./data/corridor_guard.rl --read-only \
  "MATCH (p:Payment)-[:SCREENED_AS]->(d:Decision) RETURN p.id, d.verdict, d.riskScore, d.evidencePath"
```

### API endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/graph` | `GET` | Returns full nodes, edges, and persisted `:Decision` records |
| `/api/screen` | `POST` | Screen a transaction (`{paymentId}`) and persist the `:Decision` node |
| `/api/review/:paymentId` | `POST` | Human-in-the-loop override: `{verdict: "APPROVED_RELEASED"}` or `{verdict: "CONFIRMED_SAR_BLOCKED"}` |
| `/api/cypher` | `POST` | Execute read-only openCypher queries from the UI playground |

## Pre-loaded demo cases

| Transaction | Name | Verdict | Key Features |
|---|---|---|---|
| **TXN-101** | John Doe | `AUTO-CLEAR` | 98% watchlist similarity, clean DOB (`1994-05-12`), CIBIL (`785`), no hops to sanctioned targets, clean `pac.008 -> pac.002` settlement |
| **TXN-204** | Jane Smith | `FROZEN_HUMAN_REVIEW` | 0% direct name match, 3-hop link (`Jane Smith -[:OWNS]-> Shell Corp LLC -[:REGISTERED_AT]-> 999 Bad St <-[:REGISTERED_AT]- Bad Co Holdings [OFAC-991]`), $450 skimmed fee (`$10000` sent vs `$9550` settled) |
| **TXN-309** | Alex Rivera | `FROZEN_HUMAN_REVIEW` | Split P2P mule credit layering (3 upstream accounts sharing `[:SHARES_PHONE]` with a flagged actor), missing `pac.002` acknowledgment at Correspondent Bank B |
| **TXN-412** | Viktor Krol | `FROZEN_HUMAN_REVIEW` | Direct `1-hop` watchlist hit (`OFAC-772`) + low CIBIL/trust score (`510`) |

## Repository structure

```
corridorguardai/
├── data/
│   └── corridor_guard.rl          # Persisted Relate database
├── public/
│   └── index.html                 # Interactive frontend UI
├── src/
│   ├── db.js                      # Relate DB opening & parameterized openCypher helpers
│   ├── seed.js                    # Idempotent seeding with MERGE (4 demo cases + entities/relationships)
│   ├── screeningEngine.js         # 5-stage pipeline: ingestion, KYC enrichment, fuzzy scoring, 3-hop audit, deterministic scoring
│   └── server.js                  # Express server serving public/index.html + API endpoints
├── package.json
└── README.md
```# corridorguardai
