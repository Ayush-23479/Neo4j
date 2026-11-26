import pytest
import relate

from app.graph.client import GraphClient
from app.graph.schema import apply_schema, read_statements

# (label, property) pairs that must be unique, from graph/schema.cypher
UNIQUE_KEYS = [
    ("Party", "id"),
    ("SanctionedEntity", "id"),
    ("Address", "normalizedAddress"),
    ("Phone", "number"),
    ("Payment", "uetr"),
    ("PayPalEvent", "eventId"),
    ("BankMessage", "msgId"),
    ("LedgerEntry", "entryId"),
    ("BankAccount", "id"),
    ("Decision", "id"),
    ("Finding", "id"),
    ("AuditEvent", "id"),
    ("Idempotency", "key"),
]


class DirectClient:
    """Runs schema statements on a plain connection (same thread as the test)."""

    def __init__(self, conn):
        self.conn = conn

    async def run_schema(self, statements):
        for statement in statements:
            self.conn.execute(statement)


@pytest.fixture
def conn(tmp_path):
    connection = relate.connect(str(tmp_path / "schema_test.rl"))
    yield connection
    connection.close()


def test_schema_file_has_statements():
    statements = read_statements()
    assert len(statements) >= len(UNIQUE_KEYS)
    assert all(s.startswith("CREATE CONSTRAINT") for s in statements)
    assert all("IF NOT EXISTS" in s for s in statements)


async def test_apply_twice_through_graph_client(tmp_path):
    client = GraphClient(str(tmp_path / "s.rl"), query_dir=tmp_path)
    try:
        first = await apply_schema(client)
        second = await apply_schema(client)  # a second start must not raise
        assert first == second == len(UNIQUE_KEYS)
    finally:
        await client.close()


async def test_apply_twice_creates_no_nodes(conn):
    client = DirectClient(conn)
    await apply_schema(client)
    await apply_schema(client)
    count = conn.execute("MATCH (n) RETURN count(n) AS c").fetchone()["c"]
    assert count == 0  # the schema creates constraints, never nodes


@pytest.mark.parametrize(("label", "prop"), UNIQUE_KEYS)
async def test_duplicate_key_is_refused(conn, label, prop):
    await apply_schema(DirectClient(conn))
    conn.execute(f"CREATE (:{label} {{{prop}: 'dup-1'}})")
    with pytest.raises(relate.IntegrityError):
        conn.execute(f"CREATE (:{label} {{{prop}: 'dup-1'}})")
    count = conn.execute(f"MATCH (n:{label} {{{prop}: 'dup-1'}}) RETURN count(n) AS c").fetchone()
    assert count["c"] == 1


async def test_person_with_party_label_is_covered(conn):
    await apply_schema(DirectClient(conn))
    conn.execute("CREATE (:Party:Person {id: 'p1', name: 'A'})")
    with pytest.raises(relate.IntegrityError):
        conn.execute("CREATE (:Party:Company {id: 'p1', name: 'B'})")