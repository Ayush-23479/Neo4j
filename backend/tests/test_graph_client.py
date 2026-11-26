import asyncio

import pytest
import relate

from app.graph.client import GraphClient, GraphTimeout, QueryNotAllowed


@pytest.fixture
def queries(tmp_path):
    d = tmp_path / "queries"
    d.mkdir()
    (d / "create_item.cypher").write_text("CREATE (:Item {name: $name})")
    (d / "count_items.cypher").write_text("MATCH (n:Item) RETURN count(n) AS c")
    (d / "list_items.cypher").write_text("MATCH (n:Item) RETURN n.name AS name ORDER BY name")
    (d / "get_item.cypher").write_text("MATCH (n:Item {name: $name}) RETURN n.name AS name")
    return d


@pytest.fixture
async def client(tmp_path, queries):
    c = GraphClient(str(tmp_path / "t.rl"), query_dir=queries)
    yield c
    await c.close()


async def test_hostile_parameter_is_plain_text(client):
    evil = "x' }) DETACH DELETE (n) //"
    await client.run_write("create_item", {"name": "safe"})
    await client.run_write("create_item", {"name": evil})
    assert (await client.run_named("count_items", {}))[0]["c"] == 2
    assert await client.run_named("get_item", {"name": evil}) == [{"name": evil}]
    assert (await client.run_named("count_items", {}))[0]["c"] == 2


@pytest.mark.parametrize("name", ["nope", "../etc/passwd", "Bad-Name", "a b", "", "x.cypher"])
async def test_unknown_or_badly_named_query_refused(client, name):
    with pytest.raises(QueryNotAllowed):
        await client.run_named(name, {})


async def test_raw_query_text_is_not_a_name(client):
    with pytest.raises(QueryNotAllowed):
        await client.run_named("MATCH (n) DETACH DELETE n", {})


async def test_row_limit_cuts_results(client):
    for i in range(10):
        await client.run_write("create_item", {"name": f"item-{i:02d}"})
    assert len(await client.run_named("list_items", {}, limit=3)) == 3
    assert len(await client.run_named("list_items", {})) == 10


async def test_many_asyncio_tasks_at_once(client):
    await asyncio.gather(*(client.run_write("create_item", {"name": f"n{i}"}) for i in range(25)))
    results = await asyncio.gather(*(client.run_named("count_items", {}) for _ in range(25)))
    assert all(r[0]["c"] == 25 for r in results)


async def test_timeout_raises_graph_timeout(client, monkeypatch):
    import time

    def slow(self, text, params, limit):
        time.sleep(0.5)
        return []

    monkeypatch.setattr(GraphClient, "_blocking_run", slow)
    with pytest.raises(GraphTimeout):
        await client.run_named("count_items", {}, timeout_s=0.05)


async def test_data_survives_close_and_reopen(tmp_path, queries):
    path = str(tmp_path / "persist.rl")
    first = GraphClient(path, query_dir=queries)
    await first.run_write("create_item", {"name": "kept"})
    await first.close()
    conn = relate.connect(path)  # same file, only after the first client closed it
    assert [r.data() for r in conn.execute("MATCH (n:Item) RETURN n.name AS name")] == [
        {"name": "kept"}
    ]
    conn.close()