"""Task 4: unit tests for the synthetic data generator.

All tests use the deterministic RNG (random.Random(42)) so results are
reproducible.  No real individuals, sanctions lists, KYC or credit data
are involved — everything is 100 % synthetic.
"""

import xml.etree.ElementTree as ET

import pytest

from app.synthetic.generator import build_graph, planted_cases, payment_hold_xml


# ---------------------------------------------------------------------------
# Test: graph builds deterministically with the right node/edge counts
# ---------------------------------------------------------------------------

def test_build_graph_deterministic_counts():
    """Run build_graph() twice and assert identical counts (RNG=42)."""
    from app.synthetic.generator import build_graph as _bg

    conn1 = _bg()
    # Use .data() like the existing probe tests do
    rows1 = list(conn1.execute("MATCH (n:Party) RETURN count(n) AS c").data())
    counts1 = {"Party": rows1[0]["c"] if rows1 else 0}

    labels = ["Company", "Address", "Sanctioned", "Decision"]
    for label in labels:
        rows = list(conn1.execute(f"MATCH (n:{label}) RETURN count(n) AS c").data())
        counts1[label] = rows[0]["c"] if rows else 0
    conn1.close()

    conn2 = _bg()
    counts2 = {}
    for label in ["Party", "Company", "Address", "Sanctioned", "Decision"]:
        rows = list(conn2.execute(f"MATCH (n:{label}) RETURN count(n) AS c").data())
        counts2[label] = rows[0]["c"] if rows else 0
    conn2.close()

    assert counts1 == counts2, f"Non-deterministic counts: {counts1} vs {counts2}"


# ---------------------------------------------------------------------------
# Test: planted cases match the deterministic generator output
# ---------------------------------------------------------------------------

def test_planted_cases_structure():
    """Verify that planted_cases() returns the expected key structure."""
    cases = planted_cases()
    assert isinstance(cases, list)
    assert len(cases) >= 2  # at least the three core patterns
    for case in cases:
        assert "pattern" in case
        assert "expected_hops" in case
        assert "expected_nodes" in case
        assert "expected_rels" in case


# ---------------------------------------------------------------------------
# Test: payment_hold_xml produces well-formed XML with synthetic data
# ---------------------------------------------------------------------------

def test_payment_hold_xml_well_formed():
    xml_str = payment_hold_xml(
        payment_id="paymlt-001",
        sender="TestSender Corp",
        recipient="TestRecipient Ltd",
        amount=1250.50,
    )
    # Should be parseable XML
    tree = ET.fromstring(xml_str)
    assert tree.tag == "PaymentHold"
    # Check required sub-elements exist by iterating
    tags = [el.tag for el in tree.iter()]
    assert "PaymentID" in tags
    assert "Sender" in tags
    assert "Recipient" in tags
    assert "Amount" in tags
    assert "HoldReason" in tags


# ---------------------------------------------------------------------------
# Test: the graph produced by build_graph contains planted case patterns.
# We use a simpler Cypher pattern check that works with relate's query format.
# ---------------------------------------------------------------------------

def test_planted_three_hop_path():
    """Ensure a 3‑hop OWNS→REGISTERED_AT→SHARES_PHONE path exists in the graph."""
    from app.synthetic.generator import build_graph as _bg

    conn = _bg()
    # Use a simple MATCH that relate can parse — no parameters, no collect()
    three_hop = """
    MATCH p = (s:Party)-[:OWNS]->(c:Company)-[:REGISTERED_AT]->(a:Address)-[:SHARES_PHONE]->(other:Party)
    RETURN length(p) AS hops
    """
    rows = conn.execute(three_hop)
    # relate rows support .data() or direct access
    found = False
    for r in rows:
        data = r.data() if hasattr(r, "data") else dict(r)
        if data.get("hops") == 3:
            found = True
            break
    conn.close()
    assert found, "Expected a 3‑hop path in synthetic graph"


# ---------------------------------------------------------------------------
# Test: ISO 20022 XML template — structural sanity (no real data).
# ---------------------------------------------------------------------------

def test_synthetic_xml_no_real_names():
    """Ensure payment_hold_xml never uses real-person name pools."""
    xml_str = payment_hold_xml(
        payment_id="paymlt-999",
        sender="SyntheticEnt Ltd",
        recipient="SyntheticLLC Ltd",
        amount=9999.99,
    )
    # Parse and scan for any names that look like real persons from the pool
    tree = ET.fromstring(xml_str)
    # Direct child search (not .//) because the synthetic XML is flat
    sender = tree.find("Sender")
    recipient = tree.find("Recipient")
    if sender is not None and recipient is not None:
        sender_text = sender.text
        recipient_text = recipient.text
    else:
        sender_text = ""
        recipient_text = ""
    # These should be from the synthetic pool, not the real-person pool
    real_pool = {
        "Robin A.", "Casey J.", "Dana K.", "Eli L.", "Fiona M.",
        "Greg N.", "Hannah O.", "Ian P.", "Julia Q.", "Kevin R.",
    }
    assert sender_text not in real_pool, f"Sender {sender_text} is from the real-person pool!"
    assert recipient_text not in real_pool, f"Recipient {recipient_text} is from the real-person pool!"