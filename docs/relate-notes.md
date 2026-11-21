# Relate notes (Task 2)

Only things that were tested or read from official pages. Update the "Your Docker run" rows yourself.

## Verified

| Question | Answer | Evidence |
|---|---|---|
| Python package | `pip install relate-db`, then `import relate` | PyPI page for relate-db |
| Open a single-file graph | `relate.connect("./data/probe.rl")` (path ending `.rl`) | probe.py output |
| Query with parameters | `conn.execute("... $name ...", {"name": "A"})`, rows via `.data()` | probe.py |
| Mixed three-hop path | `-[:OWNS\|REGISTERED_AT\|SHARES_PHONE*1..3]-` works, 3 hops returned | probe.py, test_probe.py |
| Unique constraints | `CREATE CONSTRAINT x IF NOT EXISTS FOR (n:Party) REQUIRE n.id IS UNIQUE` works, duplicate raises `relate.IntegrityError` | test_probe.py |
| Data survives reopen | yes | test_probe.py |
| Two processes, same file | second process fails: `OperationalError: storage locked` | test_probe.py |
| Thread safety | Connections are thread-affine: using one from another thread raises `ProgrammingError`. Fix: one dedicated worker thread owns the connection | probe_api.py run (found the error) |
| Hostile parameter | stays plain text, graph unchanged | test_probe.py |

## Decisions

- Mode: **embedded** (library inside FastAPI), file `.rl`.
- API runs with **one worker** (`uvicorn` without `--workers`). Tests use their own temp file.
- One connection owned by ONE dedicated worker thread (`ThreadPoolExecutor(max_workers=1)`); every call is sent to it. A normal thread pool or a lock is not enough.

## Not verified (test before relying on it)

- Traversal depth, graph size and expression memory limits: the CLI flags named in the hackathon
  material (`--max-traversal-depth` etc.) are not on `relate.connect(...)`. Depth is capped in the
  query itself (`*1..3`). Check the Relate docs for any Python setting.
- Query timeout: the Python call has no timeout argument. Task 5 enforces one from outside.
- Server mode (Bolt/HTTP): not needed, embedded works.
- Read-only MCP: `relate serve` is described by Neo4j. It needs the CLI and a second reader, which
  the file lock may block while the API holds the file. Test in Task 15.

## Your Docker run (fill in)

| Check | Result |
|---|---|
| `relate-db` installs in the backend image | |
| POST /probe/write then `docker compose restart backend` then GET /probe/read | |
