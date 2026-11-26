import json
import sys
from pathlib import Path

import pytest
import relate

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "generator"))

import generate as gen  # noqa: E402
import loader  # noqa: E402

HOPS = """
MATCH p = (s:Party {id: $partyId})
      -[:OWNS|DIRECTOR_OF|REGISTERED_AT|SHARES_PHONE*1..3]-(x:SanctionedEntity)
RETURN [r IN relationships(p) | type(r)] AS rels, length(p) AS hops
ORDER BY hops LIMIT 5
"""


@pytest.fixture(scope="module")
def seed(tmp_path_factory):
    out = tmp_path_factory.mktemp("seed")
    data = gen.generate(out_dir=out, write_docs=False)
    return out, data


@pytest.fixture(scope="module")
def graph(seed, tmp_path_factory):
    out, _ = seed
    loader.SEED_DIR = out
    conn = relate.connect(str(tmp_path_factory.mktemp("g") / "t.rl"))
    loader.load_seed(conn)
    yield conn
    conn.close()


def test_same_seed_same_files(seed, tmp_path):
    out, _ = seed
    again = tmp_path / "again"
    gen.generate(out_dir=again, write_docs=False)
    assert gen.folder_hash(out) == gen.folder_hash(again)


def test_sizes(seed):
    _, d = seed
    assert len(d["parties"]) == 200
    assert len(d["companies"]) == 40
    assert len(d["sanctioned"]) == 12
    assert len(d["payments"]) >= 400


def test_data_is_marked_synthetic(seed):
    out, d = seed
    assert "SYNTHETIC" in (out / "README.txt").read_text()
    assert all(s["listName"] == "SYNTHETIC-WATCHLIST-1" for s in d["sanctioned"])
    assert all(p["number"].startswith("+99-") for p in d["phones"])


def test_expected_has_every_case(seed):
    _, d = seed
    ids = {c["caseId"] for c in d["expected"]["cases"]}
    assert {"FALSE_ALARM", "HIDDEN_ADDRESS", "HIDDEN_PHONE", "MULE_RING", "STUCK", "MISSING_LEG",
            "DUPLICATE", "AMOUNT_MISMATCH", "OUT_OF_ORDER", "CLEAN"} <= ids
    json.dumps(d["expected"])


def test_every_payment_has_paypal_events_and_pacs008(seed):
    _, d = seed
    events = {e["customId"] for e in d["paypal_events"]}
    msgs = {m["uetr"] for m in d["bank_messages"] if m["type"] == "pacs.008"}
    assert all(p["endToEndId"] in events and p["uetr"] in msgs for p in d["payments"])


def test_xml_carries_the_key_fields(seed):
    _, d = seed
    pacs = next(m for m in d["bank_messages"] if m["type"] == "pacs.008")
    assert "pacs.008" in pacs["xml"] and pacs["uetr"] in pacs["xml"]
    assert pacs["endToEndId"] in pacs["xml"]


def test_counts_in_graph(graph):
    c = loader.counts(graph)
    assert c["Party"] == 240 and c["SanctionedEntity"] == 12


def test_false_alarm_has_no_path(seed, graph):
    _, d = seed
    case = next(c for c in d["expected"]["cases"] if c["caseId"] == "FALSE_ALARM")
    assert list(graph.execute(HOPS, {"partyId": case["partyId"]})) == []


@pytest.mark.parametrize("case_id", ["HIDDEN_ADDRESS", "HIDDEN_PHONE"])
def test_hidden_paths_are_three_hops(seed, graph, case_id):
    _, d = seed
    case = next(c for c in d["expected"]["cases"] if c["caseId"] == case_id)
    rows = [r.data() for r in graph.execute(HOPS, {"partyId": case["partyId"]})]
    assert rows and rows[0]["hops"] == 3
    assert sorted(rows[0]["rels"]) == sorted(case["expectedPathRelationships"])


def test_mule_receiver_has_six_senders(seed, graph):
    _, d = seed
    case = next(c for c in d["expected"]["cases"] if c["caseId"] == "MULE_RING")
    row = graph.execute(
        "MATCH (s:Party)-[:SENT_FUNDS_TO]->(r:Party {id: $id}) RETURN count(DISTINCT s) AS c",
        {"id": case["partyId"]},
    ).fetchone()
    assert row["c"] == 6


def test_duplicate_ledger_entry_counted_twice(seed, graph):
    _, d = seed
    case = next(c for c in d["expected"]["cases"] if c["caseId"] == "DUPLICATE")
    rows = graph.execute(
        "MATCH (l:LedgerEntry {uetr: $u, side: 'CREDIT'}) RETURN l.ingestCount AS n",
        {"u": case["paymentUetr"]},
    )
    assert [r["n"] for r in rows] == [2]


def test_loader_is_repeatable(seed, graph):
    before = loader.counts(graph)
    loader.load_seed(graph)
    assert loader.counts(graph) == before