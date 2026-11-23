"""Task 3: Graph schema and constraints for Explainable Payment Holds.

Defines node labels, relationship types, property names, and idempotent
initialization statements for the Relate single-file database (.rl).

DO NOT modify probe.py, probe_api.py, or test_probe.py. This module is
intended to be imported on app startup (see main.py targeted update).
"""

from __future__ import annotations

RELATE_PATH: str = "./data/graph"  # used by main.py startup hook

# ---------------------------------------------------------------------------
# Node labels and their canonical property names
# ---------------------------------------------------------------------------

NODE_LABELS = {
    "Party": {"id", "name", "type"},  # abstract base for natural/legal persons
    "Company": {"id", "name", "registration_number", "jurisdiction"},
    "Address": {"id", "street", "city", "zip_code", "country"},
    "Sanctioned": {"id", "name", "program", "program_code"},  # sanction-list entry
    "Probe": {"id", "created_at"},  # internal tracing node
    "Decision": {"id", "verdict", "risk_score", "created_at", "evidence_path"},
}

# ---------------------------------------------------------------------------
# Relationship types and their canonical property names
# ---------------------------------------------------------------------------

RELATIONSHIP_TYPES = {
    "OWNS": {"ownership_pct"},  # optional percentage
    "REGISTERED_AT": {"address_id"},  # foreign key to Address.id
    "SHARES_PHONE": set(),  # simple link; no extra properties currently
    "SENT_FUNDS_TO": {"amount", "currency", "timestamp"},
    "DECIDED_AS": {"verdict", "risk_score", "evidence_path", "decided_at"},
}

# ---------------------------------------------------------------------------
# Constraints (idempotent IF NOT EXISTS where Relate supports it;
# otherwise best-effort CREATE CONSTRAINT guard)
# ---------------------------------------------------------------------------

CONSTRAINT_STATEMENTS = [
    # Party-level uniqueness (used by seeded synthetic data)
    "CREATE CONSTRAINT party_id IF NOT EXISTS FOR (n:Party) REQUIRE n.id IS UNIQUE",
    # Sanctioned name uniqueness within the graph
    "CREATE INDEX IF NOT EXISTS FOR (n:Sanctioned) ON (n.name)",
    # Probe tracing node — one per run
    "CREATE INDEX IF NOT EXISTS FOR (n:Probe) ON (n.id)",
]

# ---------------------------------------------------------------------------
# Idempotent schema-initialisation statements.
# Each statement is safe to re-run; MERGE guards against duplicates.
# ---------------------------------------------------------------------------

SCHEMA_INIT_STATEMENTS = [
    # Ensure all required node labels can be created via MERGE
    "MERGE (p:Party {id: $id}) SET p.name = $name, p.type = $type",
    "MERGE (c:Company {id: $id}) SET c.name = $name, c.registration_number = $reg_no, c.jurisdiction = $jurs",
    "MERGE (a:Address {id: $id}) SET a.street = $street, a.city = $city, a.zip_code = $zip, a.country = $coun",
    "MERGE (s:Sanctioned {id: $id}) SET s.name = $name, s.program = $prog, s.program_code = $prog_code",
    "MERGE (d:Decision {id: $id}) SET d.verdict = $verdict, d.risk_score = $risk, d.evidence_path = $ev_path, d.created_at = $ts",
    # Indexes that speed up the three-hop traversal used by the probe
    "ADD INDEX IF NOT EXISTS FOR (n:Party) ON (n.id)",
    "ADD INDEX IF NOT EXISTS FOR (n:Sanctioned) ON (n.name)",
    "ADD INDEX IF NOT EXISTS FOR (n:Probe) ON (n.id)",
]

# ---------------------------------------------------------------------------
# Helper: produce a single init-call string that the app can pipe to Relate.
# ---------------------------------------------------------------------------

def init_sql() -> str:
    """Return a semi-colon separated string of init statements."""
    return " ; ".join(SCHEMA_INIT_STATEMENTS)


# ---------------------------------------------------------------------------
# Constraint-guard: run each constraint statement once; ignore if already
# present.  The "IF NOT EXISTS" syntax in Relate will raise no error if the
# constraint already exists; for older versions we catch and ignore.
# ---------------------------------------------------------------------------

def apply_constraints(conn) -> None:
    """Execute every constraint statement; swallow expected errors."""
    for stmt in CONSTRAINT_STATEMENTS:
        try:
            conn.execute(stmt)
        except Exception:  # broad — we only want init to succeed
            pass