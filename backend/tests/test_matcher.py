import pytest

from app.detect.matcher import link_records, orphan_count, relink_orphans
from app.graph.client import GraphClient


@pytest.fixture
async def g(tmp_path):
    client = GraphClient(str(tmp_path / "m.rl"))
    yield client
    await client.close()


async def pay(g, uetr, e2e, amount="100.00", created="2026-11-20T10:00:00Z", payer="A", payee="B"):
    await g.run_write(
        "merge_payment",
        {
            "uetr": uetr, "endToEndId": e2e, "amount": float(amount), "currency": "USD",
            "payerId": payer, "payeeId": payee, "createdAt": created, "feeAmount": None,
        },
    )


async def msg(g, msg_id, uetr, e2e, amount=100.0, ts="2026-11-20T10:02:00Z"):
    await g.run_write(
        "merge_bank_message",
        {
            "msgId": msg_id, "type": "pacs.008", "ts": ts, "status": "SENT", "uetr": uetr,
            "endToEndId": e2e, "amount": amount, "currency": "USD", "arrivalSeq": 1, "xml": None,
        },
    )


async def event(g, event_id, custom_id, amount=100.0, ts="2026-11-20T10:01:00Z"):
    await g.run_write(
        "merge_paypal_event",
        {
            "eventId": event_id, "type": "CAPTURE_COMPLETED", "ts": ts, "customId": custom_id,
            "amount": amount, "currency": "USD", "rawRef": None,
        },
    )


async def test_uetr_match_is_1(g):
    await pay(g, "U1", "E1")
    await msg(g, "M1", "U1", "E1")
    r = await link_records(g, "BankMessage", "M1")
    assert (r.paymentUetr, r.method, r.confidence, r.lowConfidence) == ("U1", "uetr", 1.0, False)


async def test_e2e_only_match_is_095(g):
    await pay(g, "U1", "E1")
    await msg(g, "M1", "WRONG-UETR", "E1")  # stub link to WRONG-UETR is replaced
    r = await link_records(g, "BankMessage", "M1")
    assert (r.paymentUetr, r.method, r.confidence) == ("U1", "e2e", 0.95)
    links = await g.run_named(
        "get_record", {"kind": "BankMessage", "id": "M1"}
    )
    assert links[0]["linkedUetr"] == "U1"
    stub_links = await g.run_named("count_orphans", {})
    assert stub_links[0]["n"] == 0


async def test_custom_id_match_is_09(g):
    await pay(g, "U1", "E1")
    await event(g, "W1", "E1")
    r = await link_records(g, "PayPalEvent", "W1")
    assert (r.method, r.confidence, r.lowConfidence) == ("custom_id", 0.9, False)


async def test_amount_time_unique_is_low_confidence(g):
    await pay(g, "U1", "E1", amount="77.00")
    await event(g, "W1", "NOPE", amount=77.0)
    r = await link_records(g, "PayPalEvent", "W1")
    assert (r.paymentUetr, r.method) == ("U1", "amount_time")
    assert (r.confidence, r.lowConfidence) == (0.5, True)


async def test_amount_time_two_candidates_stays_unmatched(g):
    await pay(g, "U1", "E1", amount="50.00", created="2026-11-20T10:00:00Z")
    await pay(g, "U2", "E2", amount="50.00", created="2026-11-20T10:03:00Z")
    await event(g, "W1", "NOPE", amount=50.0)
    r = await link_records(g, "PayPalEvent", "W1")
    assert r.paymentUetr is None and r.method is None
    assert await orphan_count(g) == 1


async def test_amount_time_outside_window_is_unmatched(g):
    await pay(g, "U1", "E1", amount="50.00", created="2026-11-20T09:00:00Z")
    await event(g, "W1", "NOPE", amount=50.0, ts="2026-11-20T10:00:00Z")
    assert (await link_records(g, "PayPalEvent", "W1")).paymentUetr is None


async def test_message_before_payment_is_orphan_then_linked(g):
    await msg(g, "M1", "U9", "E9")
    assert await orphan_count(g) == 1
    assert await relink_orphans(g) == 0
    await pay(g, "U9", "E9")  # the stub is filled in
    assert await relink_orphans(g) == 1
    assert await orphan_count(g) == 0
    r = await link_records(g, "BankMessage", "M1")
    assert (r.paymentUetr, r.method) == ("U9", "uetr")


async def link_count(g) -> int:
    """Count CORRELATES_WITH relationships directly (test only)."""
    import asyncio

    def run():
        row = g._get_conn().execute(
            "MATCH ()-[c:CORRELATES_WITH]->() RETURN count(c) AS n"
        ).fetchone()
        return row["n"]

    return await asyncio.get_running_loop().run_in_executor(g._executor, run)


async def test_rerun_creates_no_duplicate_links(g):
    await pay(g, "U1", "E1")
    await msg(g, "M1", "U1", "E1")
    await event(g, "W1", "E1")
    for _ in range(3):
        await link_records(g, "BankMessage", "M1")
        await link_records(g, "PayPalEvent", "W1")
        await relink_orphans(g)
    assert await link_count(g) == 2


async def test_unknown_record_and_bad_kind(g):
    assert (await link_records(g, "BankMessage", "nope")).paymentUetr is None
    with pytest.raises(ValueError):
        await link_records(g, "Payment", "x")