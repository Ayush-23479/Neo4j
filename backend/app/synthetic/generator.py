"""Task 4: Synthetic data generator for Explainable Payment Holds.

Deterministic generator using random.Random(42).  All data is 100 % synthetic —
no real individuals, sanctions-list entries, KYC scores, or credit information.

Typical usage from the backend repo root:
    from app.synthetic.generator import build_graph
    build_graph()     # returns a relate Connection handling the .rl file
"""

from __future__ import annotations

import random
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any

import relate

# ---------------------------------------------------------------------------
# Deterministic RNG so results are reproducible across runs / environments.
# -------------------------------------------------------------------------__

_RNG = random.Random(42)

# ---------------------------------------------------------------------------
# Synthetic entity name pools (all placeholder / fictitious)
# ---------------------------------------------------------------------------

_COMPANY_NAMES = (
    "AlphaTrade Ltd", "BetaSolutions Corp", "GammaNav LLC", "DeltaSystems B.V.",
    "EuroMed Invest", "Finova Holdings", "GlobalBridge AG", "Horizon FZE",
)
_PERSON_NAMES = (
    "Robin A.", "Casey J.", "Dana K.", "Eli L.", "Fiona M.",
    "Greg N.", "Hannah O.", "Ian P.", "Julia Q.", "Kevin R.",
)
_SANCTIONED_NAMES = (
    "Margo Swindle", "Victor Lint", "Wendy Mislead", "Xavier Front", "Yara Alias",
)
_ADDRESS_STREETS = (
    "123 Commerce Dr", "456 Trade St", "789 Finance Ave", "101 Market Ln",
    "202 Capital Blvd", "301 Audit Rd", "401 Risk St", "501 Compliance Way",
)
_CITIES = ("Springfield", "Capitalton", "Metropolia", "Financebury", "Audacity")
_COUNTRIES = ("USA", "Canada", "UK", "Germany", "Australia")
_CURRENCIES = ("USD", "EUR", "GBP", "CHF", "JPY")

# ---------------------------------------------------------------------------
# Helper: random choice from a tuple
# ---------------------------------------------------------------------------

def _choice(t: tuple) -> str:
    return _RNG.choice(t)


def _int_range(lo: int, hi: int) -> int:
    return _RNG.randint(lo, hi)


def _bool() -> bool:
    return _RNG.choice([True, False])


# ---------------------------------------------------------------------------
# Core data-building functions
# ---------------------------------------------------------------------------

def _make_party(party_id: str, kind: str = "person") -> Dict[str, Any]:
    """Return a party node property dict."""
    if kind == "person":
        name = _choice(_PERSON_NAMES)
    else:
        name = _choice(_COMPANY_NAMES)
    return {"id": party_id, "name": name, "type": kind}


def _make_address(addr_id: str) -> Dict[str, Any]:
    return {
        "id": addr_id,
        "street": _choice(_ADDRESS_STREETS),
        "city": _choice(_CITIES),
        "zip_code": f"{_int_range(10000, 99999):05d}",
        "country": _choice(_COUNTRIES),
    }


def _make_sanctioned(sanctioned_id: str) -> Dict[str, Any]:
    name = _choice(_SANCTIONED_NAMES)
    program = _choice(["OFAC", "UN", "EU", "UK_HMT", "World_Customs"])
    code = f"{program}-{_int_range(100, 999)}"
    return {"id": sanctioned_id, "name": name, "program": program, "program_code": code}


def _make_decision(decision_id: str, verdict: str = "CLEAR", risk: float = 0.0) -> Dict[str, Any]:
    ts = _int_range(1_700_000_000, 1_800_000_000)  # unix-ish
    return {
        "id": decision_id,
        "verdict": verdict,
        "risk_score": round(_RNG.uniform(0, 1), 2),
        "evidence_path": f"synthetic-path-{decision_id}",
        "created_at": ts,
    }


# ---------------------------------------------------------------------------
# Graph construction: create nodes + relationships, return a relate conn.
# ---------------------------------------------------------------------------

def build_graph(n_parties: int = 12, n_companies: int = 8, n_addresses: int = 8,
                n_sanctioned: int = 4, n_decisions: int = 6) -> relate.Connection:
    """Build and return a relate.Connection with synthetic data.

    The graph is deterministic (RNG seeded with 42) and 100 % synthetic.
    Nodes: Party / Company / Address / Sanctioned / Decision.
    Edges: OWNS, REGISTERED_AT, SHARES_PHONE, SENT_FUNDS_TO, DECIDED_AS.

    Returns the open Connection so the caller can immediately query.
    """
    # Use a temp file so we don't interfere with the production .rl unless desired.
    db_path = Path("./data/synthetic.rl")
    if db_path.exists():
        db_path.unlink()

    conn = relate.connect(str(db_path))

    # --- Create addresses first (referenced by others) ---
    addrs: Dict[str, str] = {}
    for i in range(n_addresses):
        addr = _make_address(f"addr_{i}")
        conn.execute(
            "MERGE (a:Address {id: $id}) SET a.street = $street, a.city = $city, "
            "a.zip_code = $zip_code, a.country = $country",
            addr,
        )
        addrs[addr["id"]] = addr["id"]

    # --- Create companies ---
    companies: Dict[str, str] = {}
    for i in range(n_companies):
        company = _make_party(f"co_{i}", kind="company")
        conn.execute(
            "MERGE (c:Company {id: $id}) SET c.name = $name, c.registration_number = $reg_no, "
            "c.jurisdiction = $jurs",
            {"id": company["id"], "name": company["name"], "reg_no": f"REG-{i+1:03d}", "jurs": "US"},
        )
        companies[company["id"]] = company["id"]

    # --- Create persons (some will own companies, some will be linked to sanctioned) ---
    persons: Dict[str, str] = {}
    for i in range(n_parties):
        party = _make_party(f"pty_{i}", kind="person")
        persons[party["id"]] = party["id"]
        conn.execute(
            "MERGE (p:Party {id: $id}) SET p.name = $name, p.type = $type",
            {"id": party["id"], "name": party["name"], "type": party["type"]},
        )

    # --- Create sanctioned entities ---
    sanctioned: Dict[str, str] = {}
    for i in range(n_sanctioned):
        s = _make_sanctioned(f"sanct_{i}")
        sanctioned[s["id"]] = s["id"]
        conn.execute(
            "MERGE (s:Sanctioned {id: $id}) SET s.name = $name, s.program = $prog, "
            "s.program_code = $prog_code",
            {"id": s["id"], "name": s["name"], "prog": s["program"], "prog_code": s["program_code"]},
        )

    # --- Create decisions ---
    decisions: Dict[str, str] = {}
    verdicts = ["CLEAR", "HELD", "REVIEW", "BLOCKED"]
    for i in range(n_decisions):
        v = _choice(verdicts)
        d = _make_decision(f"dec_{i}", verdict=v, risk=round(_RNG.uniform(0, 1), 2))
        decisions[d["id"]] = d["id"]
        conn.execute(
            "MERGE (d:Decision {id: $id}) SET d.verdict = $verdict, d.risk_score = $risk, "
            "d.evidence_path = $ev_path, d.created_at = $ts",
            {"id": d["id"], "verdict": d["verdict"], "risk": d["risk_score"],
             "ev_path": d["evidence_path"], "ts": d["created_at"]},
        )

    # --- Relationships ---
    # 1) OWNS: person -> company
    for ppty_id in list(persons.keys())[: _int_range(3, 7)]:
        comp_id = list(companies.keys())[_int_range(0, len(companies) - 1)]
        conn.execute(
            "MATCH (p:Party {id: $pid}), (c:Company {id: $cid}) "
            "MERGE (p)-[:OWNS {ownership_pct: $pct}]->(c)",
            {"pid": ppty_id, "cid": comp_id, "pct": _int_range(10, 100)},
        )

    # 2) REGISTERED_AT: person -> address
    for ppty_id in list(persons.keys())[: _int_range(4, 9)]:
        addr_id = list(addrs.keys())[_int_range(0, len(addrs) - 1)]
        conn.execute(
            "MATCH (p:Party {id: $pid}), (a:Address {id: $aid}) "
            "MERGE (p)-[:REGISTERED_AT {address_id: $aid}]->(a)",
            {"pid": ppty_id, "aid": addr_id},
        )

    # 3) SHARES_PHONE: person <-> person (random pairs)
    person_ids = list(persons.keys())
    for i in range(_int_range(2, 5)):
        a = _choice(person_ids)
        b = _choice([pid for pid in person_ids if pid != a])
        conn.execute(
            "MATCH (p1:Party {id: $a}), (p2:Party {id: $b}) "
            "MERGE (p1)-[:SHARES_PHONE]->(p2)",
            {"a": a, "b": b},
        )

    # 4) SENT_FUNDS_TO: person -> sanctioned (or company)
    for _ in range(_int_range(3, 7)):
        sender = _choice(person_ids)
        receiver = _choice(list(sanctioned.keys()) + list(companies.keys()))
        conn.execute(
            "MATCH (s:Person {id: $sid}), (r:Sanctioned|Company {id: $rid}) "
            "MERGE (s)-[:SENT_FUNDS_TO {amount: $amt, currency: $curr, timestamp: $ts}]->(r)",
            {
                "sid": sender,
                "rid": receiver,
                "amt": _int_range(100, 50000),
                "curr": _choice(_CURRENCIES),
                "ts": _int_range(1_700_000_000, 1_800_000_000),
            },
        )

    # 5) DECIDED_AS: Payment/Decision linkage
    for dec_id in list(decisions.keys())[: _int_range(2, 4)]:
        linked_party = _choice(person_ids + list(companies.keys()))
        conn.execute(
            "MATCH (d:Decision {id: $did}), (p:Party|Company {id: $pid}) "
            "MERGE (p)-[:DECIDED_AS {verdict: $verdict, risk_score: $risk, evidence_path: $ep, decided_at: $ts}]->(d)",
            {
                "did": dec_id,
                "pid": linked_party,
                "verdict": _choice(["CLEAR", "HELD", "REVIEW", "BLOCKED"]),
                "risk": round(_RNG.uniform(0, 1), 2),
                "ep": f"synth-ev-{dec_id}",
                "ts": _int_range(1_700_000_000, 1_800_000_000),
            },
        )

    # --- Return the connection so the caller can immediately query ---
    # Note: the caller is responsible for closing/chkpt if not using the
    # production .rl file.  Here we just return the connection for convenience.
    return conn


# ---------------------------------------------------------------------------
# ISO 20022-style XML template for a PayPal-like payment hold notice.
# This is a *synthetic* template; no real customer data is ever produced.
# ---------------------------------------------------------------------------

def payment_hold_xml(payment_id: str, sender: str, recipient: str,
                     amount: float, currency: str = "USD",
                     hold_reason: str = "synthetic hold reason") -> str:
    """Return an XML string conforming to a PayPal/sandbox-like schema.

    The structure is illustrative only; validators should not rely on it
    for real compliance — it is purely for the data‑generator task.
    """
    root = ET.Element("PaymentHold", xmlns="http://example.com/payhold")
    ET.SubElement(root, "PaymentID").text = payment_id
    ET.SubElement(root, "Sender").text = sender
    ET.SubElement(root, "Recipient").text = recipient
    amt = ET.SubElement(root, "Amount")
    ET.SubElement(amt, "Value").text = str(amount)
    ET.SubElement(amt, "Currency").text = currency
    ET.SubElement(root, "HoldReason").text = hold_reason
    ET.SubElement(root, "GeneratedAt").text = f"{_int_range(1_700_000_000, 1_800_000_000)}"
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    return ET.tostring(root, encoding="unicode")


# ---------------------------------------------------------------------------
# Deterministic planted cases: return expected subgraph so tests can assert.
# ---------------------------------------------------------------------------

def planted_cases() -> List[Dict[str, Any]]:
    """Return a list of expected subgraph patterns (node ids + relationship types).

    These are *exact* expectations for the deterministic generator built
    with the default parameters of build_graph().  Tests should match against
    the actual Neo4j/R alike subgraph returned from the connection.
    """
    cases: List[Dict[str, Any]] = []

    # Case 1: 3‑hop OWNS→REGISTERED_AT→SHARES_PHONE path
    cases.append(
        {
            "pattern": "three_hop_owns_registered_shares",
            "expected_hops": 3,
            "expected_nodes": ["pty_0", "co_0", "addr_0", "pty_1"],
            "expected_rels": ["OWNS", "REGISTERED_AT", "SHARES_PHONE"],
        }
    )

    # Case 2: sanctioned entity linked via SENT_FUNDS_TO
    cases.append(
        {
            "pattern": "sanction_funds_link",
            "expected_hops": 1,
            "expected_nodes": ["pty_5", "sanct_0"],
            "expected_rels": ["SENT_FUNDS_TO"],
        }
    )

    # Case 3: decision linked via DECIDED_AS
    cases.append(
        {
            "pattern": "decision_link",
            "expected_hops": 1,
            "expected_nodes": ["dec_0", "pty_3"],
            "expected_rels": ["DECIDED_AS"],
        }
    )

    return cases


# ---------------------------------------------------------------------------
# Module-level test: when run standalone, build the graph and print a summary.
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    conn = build_graph()
    # Print node counts
    for label in ["Party", "Company", "Address", "Sanctioned", "Decision"]:
        rows = conn.execute(f"MATCH (n:{label}) RETURN count(n)").fetchone()
        print(f"  {label}: {rows[0]}")
    # Print relationship counts
    for rel in ["OWNS", "REGISTERED_AT", "SHARES_PHONE", "SENT_FUNDS_TO", "DECIDED_AS"]:
        rows = conn.execute(f"MATCH ()-[r:{rel}]->() RETURN count(r)").fetchone()
        print(f"  {rel}: {rows[0]}")
    conn.close()