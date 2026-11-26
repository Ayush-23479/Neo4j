import pytest
import relate

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
]


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


def test_apply_twice_changes_nothing(conn):
    first = apply_schema(conn)
    second = apply_schema(conn)  # a second start must not raise
    assert first == second
    count = conn.execute("MATCH (n) RETURN count(n) AS c").fetchone()["c"]
    assert count == 0  # the schema creates constraints, never nodes


@pytest.mark.parametrize(("label", "prop"), UNIQUE_KEYS)
def test_duplicate_key_is_refused(conn, label, prop):
    apply_schema(conn)
    conn.execute(f"CREATE (:{label} {{{prop}: 'dup-1'}})")
    with pytest.raises(relate.IntegrityError):
        conn.execute(f"CREATE (:{label} {{{prop}: 'dup-1'}})")
    count = conn.execute(f"MATCH (n:{label} {{{prop}: 'dup-1'}}) RETURN count(n) AS c").fetchone()
    assert count["c"] == 1


def test_person_with_party_label_is_covered(conn):
    apply_schema(conn)
    conn.execute("CREATE (:Party:Person {id: 'p1', name: 'A'})")
    with pytest.raises(relate.IntegrityError):
        conn.execute("CREATE (:Party:Company {id: 'p1', name: 'B'})")