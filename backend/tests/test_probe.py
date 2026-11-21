import subprocess
import sys

import pytest
import relate

THREE_HOP = """
MATCH p = (s:Party {name: $name})-[:OWNS|REGISTERED_AT|SHARES_PHONE*1..3]-(x:Sanctioned)
RETURN [n IN nodes(p) | n.name] AS pathNodes,
       [r IN relationships(p) | type(r)] AS pathRelationships,
       length(p) AS hops
ORDER BY hops LIMIT 5
"""


def seed(conn):
    conn.execute(
        "CREATE (a:Party {name:'A'})-[:OWNS]->(b:Company {name:'B'})"
        "-[:REGISTERED_AT]->(c:Address {name:'C'})<-[:REGISTERED_AT]-(d:Sanctioned {name:'D'})"
    )


def test_node_survives_reopen(tmp_path):
    path = str(tmp_path / "t.rl")
    conn = relate.connect(path)
    conn.execute("CREATE (:Probe {id: $id})", {"id": "p1"})
    conn.close()
    conn = relate.connect(path)
    rows = [r.data() for r in conn.execute("MATCH (n:Probe) RETURN n.id AS id")]
    assert rows == [{"id": "p1"}]


def test_three_hop_mixed_types(tmp_path):
    conn = relate.connect(str(tmp_path / "t.rl"))
    seed(conn)
    rows = [r.data() for r in conn.execute(THREE_HOP, {"name": "A"})]
    assert len(rows) == 1
    assert rows[0]["hops"] == 3
    assert rows[0]["pathNodes"] == ["A", "B", "C", "D"]


def test_hostile_parameter_is_just_text(tmp_path):
    conn = relate.connect(str(tmp_path / "t.rl"))
    seed(conn)
    evil = "x' }) DETACH DELETE (n) //"
    assert list(conn.execute(THREE_HOP, {"name": evil})) == []
    assert conn.execute("MATCH (n) RETURN count(n) AS c").fetchone()["c"] == 4


def test_unique_constraint_refuses_duplicate(tmp_path):
    conn = relate.connect(str(tmp_path / "t.rl"))
    conn.execute("CREATE CONSTRAINT c1 IF NOT EXISTS FOR (n:Party) REQUIRE n.id IS UNIQUE")
    conn.execute("CREATE (:Party {id: 'x'})")
    with pytest.raises(relate.IntegrityError):
        conn.execute("CREATE (:Party {id: 'x'})")


def test_second_process_cannot_open_same_file(tmp_path):
    """Documents what we found: one process per file, so the API runs with ONE worker."""
    path = str(tmp_path / "t.rl")
    conn = relate.connect(path)
    conn.execute("CREATE (:Probe {id: 'p1'})")
    code = f"import relate; relate.connect({path!r})"
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=30)
    assert r.returncode != 0
    assert "locked" in r.stderr
    conn.close()
