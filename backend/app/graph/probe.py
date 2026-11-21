"""Task 2 probe: run with `python -m app.graph.probe` from the backend folder."""
import os
import subprocess
import sys
import time

import relate

PATH = os.getenv("PROBE_PATH", "./data/probe.rl")

THREE_HOP = """
MATCH p = (s:Party {name: $name})-[:OWNS|REGISTERED_AT|SHARES_PHONE*1..3]-(x:Sanctioned)
RETURN [n IN nodes(p) | n.name] AS pathNodes,
       [r IN relationships(p) | type(r)] AS pathRelationships,
       length(p) AS hops
ORDER BY hops LIMIT 5
"""


def ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 2)


def main() -> None:
    print("relate version:", getattr(relate, "__version__", "unknown"))
    print("threadsafety:", relate.threadsafety, "(1 = share the module, not connections)")

    conn = relate.connect(PATH)
    conn.execute("MERGE (:Probe {id: $id})", {"id": "p1"})
    conn.execute(
        "MERGE (a:Party {name:'A'}) MERGE (b:Company {name:'B'}) MERGE (c:Address {name:'C'}) "
        "MERGE (d:Sanctioned {name:'D'}) "
        "MERGE (a)-[:OWNS]->(b) MERGE (b)-[:REGISTERED_AT]->(c) MERGE (d)-[:REGISTERED_AT]->(c)"
    )
    t = time.perf_counter()
    rows = [r.data() for r in conn.execute(THREE_HOP, {"name": "A"})]
    print("three-hop result:", rows, f"({ms(t)} ms)")
    assert rows and rows[0]["hops"] == 3, "expected one 3-hop path"

    for stmt in (
        "CREATE CONSTRAINT probe_party_id IF NOT EXISTS FOR (n:ProbeParty) REQUIRE n.id IS UNIQUE",
    ):
        conn.execute(stmt)
        print("constraint ok:", stmt)
    conn.execute("MERGE (:ProbeParty {id: 'x'})")
    try:
        conn.execute("CREATE (:ProbeParty {id: 'x'})")
        print("duplicate was ALLOWED (bad)")
    except relate.IntegrityError as e:
        print("duplicate refused (good):", str(e)[:80])

    conn.close()
    conn = relate.connect(PATH)
    still = [r.data() for r in conn.execute("MATCH (n:Probe) RETURN n.id AS id")]
    print("after reopen:", still)
    assert still, "node did not survive reopen"

    # Two processes: second one opens the same file while this one holds it.
    code = f"import relate; relate.connect({PATH!r})"
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=30)
    if r.returncode == 0:
        print("second process CAN open the same file")
    else:
        print("second process FAILED to open it:", r.stderr.strip().splitlines()[-1])
    conn.close()


if __name__ == "__main__":
    main()
