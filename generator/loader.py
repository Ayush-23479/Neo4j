import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

import relate

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.graph.schema import read_statements

ROOT = Path(__file__).resolve().parents[1]
SEED_DIR = ROOT / "data" / "seed"
BATCH = 500
ALLOWED_LABELS = {"Party", "Address", "Phone", "BankAccount", "SanctionedEntity"}
ALLOWED_RELS = {"OWNS", "DIRECTOR_OF", "REGISTERED_AT", "SHARES_PHONE", "HAS_ACCOUNT",
                "SENT_FUNDS_TO"}


def store_path() -> Path:
    raw = os.getenv("RELATE_PATH", "./data/graph.rl")
    path = Path(raw)
    if not path.is_absolute():
        path = ROOT / path
    if path.suffix != ".rl":
        raise SystemExit(f"RELATE_PATH must end in .rl, got {raw}")
    return path


def read(name: str):
    return json.loads((SEED_DIR / f"{name}.json").read_text(encoding="utf-8"))


def run_batches(conn, query: str, rows: list[dict]) -> None:
    for i in range(0, len(rows), BATCH):
        conn.execute(query, {"rows": rows[i:i + BATCH]})


def load_nodes(conn, label_expr: str, key: str, rows: list[dict]) -> None:
    query = (f"UNWIND $rows AS row MERGE (n:{label_expr} {{{key}: row.{key}}}) "
             "SET n += row")
    run_batches(conn, query, rows)


def load_relationships(conn, rels: list[dict]) -> None:
    groups: dict[tuple, list[dict]] = {}
    for r in rels:
        g = (r["type"], r["from"]["label"], r["from"]["key"], r["to"]["label"], r["to"]["key"])
        groups.setdefault(g, []).append({"f": r["from"]["value"], "t": r["to"]["value"]})
    for (rtype, fl, fk, tl, tk), rows in groups.items():
        if rtype not in ALLOWED_RELS or fl not in ALLOWED_LABELS or tl not in ALLOWED_LABELS:
            raise SystemExit(f"Unexpected relationship in seed: {rtype} {fl}->{tl}")
        query = (f"UNWIND $rows AS row MATCH (a:{fl} {{{fk}: row.f}}) "
                 f"MATCH (b:{tl} {{{tk}: row.t}}) MERGE (a)-[:{rtype}]->(b)")
        run_batches(conn, query, rows)


def load_seed(conn) -> dict[str, int]:
    """Write every seed file into the open connection. Returns node counts by label."""
    for statement in read_statements():
        conn.execute(statement)
    load_nodes(conn, "Party:Person", "id", [dict_clean(p) for p in read("parties")])
    load_nodes(conn, "Party:Company", "id", [dict_clean(p) for p in read("companies")])
    load_nodes(conn, "SanctionedEntity", "id", [dict_clean(p) for p in read("sanctioned")])
    load_nodes(conn, "Address", "normalizedAddress", read("addresses"))
    load_nodes(conn, "Phone", "number", read("phones"))
    load_nodes(conn, "BankAccount", "id", read("bank_accounts"))
    load_nodes(conn, "Payment", "uetr", read("payments"))
    load_nodes(conn, "PayPalEvent", "eventId", read("paypal_events"))
    load_nodes(conn, "BankMessage", "msgId", read("bank_messages"))

    # A ledger line delivered twice is ONE node with ingestCount 2 (the DUPLICATE planted case).
    raw = read("ledger_entries")
    seen = Counter(e["entryId"] for e in raw)
    unique = {e["entryId"]: e for e in raw}
    entries = [{**e, "ingestCount": seen[eid]} for eid, e in unique.items()]
    load_nodes(conn, "LedgerEntry", "entryId", entries)

    rels = read("relationships")
    load_relationships(conn, rels)
    payer_links = [
        {"type": "SENT_FUNDS_TO", "from": {"label": "Party", "key": "id", "value": p["payerId"]},
         "to": {"label": "Party", "key": "id", "value": p["payeeId"]}}
        for p in read("payments")
    ]
    load_relationships(conn, payer_links)
    return counts(conn)


def dict_clean(row: dict) -> dict:
    return {k: v for k, v in row.items() if v is not None}


def counts(conn) -> dict[str, int]:
    out = {}
    for label in ("Party", "SanctionedEntity", "Address", "Phone", "BankAccount", "Payment",
                  "PayPalEvent", "BankMessage", "LedgerEntry"):
        row = conn.execute(f"MATCH (n:{label}) RETURN count(n) AS c").fetchone()
        out[label] = row["c"]
    return out


def main() -> None:
    keep = "--keep" in sys.argv
    if not SEED_DIR.exists():
        raise SystemExit("No data/seed folder. Run: python generator/generate.py")
    path = store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not keep:
        for f in path.parent.glob(path.name + "*"):
            f.unlink()
    start = time.perf_counter()
    try:
        conn = relate.connect(str(path))
    except Exception as exc:
        if "locked" in str(exc).lower():
            raise SystemExit("The graph file is in use. Stop the backend first "
                             "(docker compose down), then run this again.") from exc
        raise
    try:
        result = load_seed(conn)
    finally:
        conn.close()
    print(f"Loaded {path} in {time.perf_counter() - start:.1f}s")
    for label, count in result.items():
        print(f"  {label}: {count}")


if __name__ == "__main__":
    main()