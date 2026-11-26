import httpx
import pytest
from httpx import ASGITransport

from app.main import app

UETR = "11111111-2222-4333-8444-555555555555"
PAYMENT = {
    "uetr": UETR,
    "endToEndId": "E2E-T1",
    "amount": "125.50",
    "currency": "USD",
    "payerId": "P-1",
    "payeeId": "P-2",
    "createdAt": "2026-11-20T10:00:00Z",
}
MESSAGE = {
    "msgId": "M-T1",
    "type": "pacs.002",
    "ts": "2026-11-20T10:04:00Z",
    "status": "ACSC",
    "uetr": UETR,
    "endToEndId": "E2E-T1",
    "amount": "125.50",
    "currency": "USD",
}
LEDGER = {
    "entryId": "L-T1",
    "uetr": UETR,
    "endToEndId": "E2E-T1",
    "amount": "123.00",
    "currency": "USD",
    "ts": "2026-11-20T10:05:00Z",
    "side": "CREDIT",
}
EVENT = {
    "eventId": "WH-T1",
    "type": "CAPTURE_COMPLETED",
    "ts": "2026-11-20T10:00:30Z",
    "customId": "E2E-T1",
    "amount": "125.50",
    "currency": "USD",
}


@pytest.fixture
async def api(app_env):
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


def key(value: str) -> dict:
    return {"Idempotency-Key": value}


async def count(uetr: str) -> int:
    rows = await app.state.graph.run_named("count_payments_by_uetr", {"uetr": uetr})
    return rows[0]["c"]


async def test_same_payment_five_times_one_node(api):
    replies = []
    for _ in range(5):
        replies.append(await api.post("/ingest/payment", json=PAYMENT, headers=key("pay-1")))
    assert all(r.status_code == 200 for r in replies)
    first, *repeats = [r.json() for r in replies]
    assert first == {"id": UETR, "created": True, "duplicate": False}
    assert len(repeats) == 4
    assert all(r == repeats[0] for r in repeats)
    assert repeats[0] == {"id": UETR, "created": False, "duplicate": True}
    assert await count(UETR) == 1


async def test_new_key_same_payment_still_one_node(api):
    await api.post("/ingest/payment", json=PAYMENT, headers=key("pay-a"))
    again = await api.post("/ingest/payment", json=PAYMENT, headers=key("pay-b"))
    assert again.json()["duplicate"] is True
    assert await count(UETR) == 1


async def test_key_reused_for_other_body_is_409(api):
    await api.post("/ingest/payment", json=PAYMENT, headers=key("pay-x"))
    other = {**PAYMENT, "amount": "999.00"}
    r = await api.post("/ingest/payment", json=other, headers=key("pay-x"))
    assert r.status_code == 409 and r.json()["error"] == "idempotency_key_reuse"


async def test_missing_idempotency_key_is_400(api):
    r = await api.post("/ingest/payment", json=PAYMENT)
    assert r.status_code == 400
    assert r.json()["error"] == "idempotency_key_required"
    assert await count(UETR) == 0


async def test_negative_amount_is_422(api):
    r = await api.post("/ingest/payment", json={**PAYMENT, "amount": "-5"}, headers=key("k"))
    assert r.status_code == 422
    r = await api.post("/ingest/payment", json={**PAYMENT, "currency": "usd"}, headers=key("k2"))
    assert r.status_code == 422
    r = await api.post("/ingest/payment", json={**PAYMENT, "extra": 1}, headers=key("k3"))
    assert r.status_code == 422


async def test_status_message_before_payment_is_linked(api):
    r = await api.post("/ingest/bank-message", json=MESSAGE, headers=key("msg-1"))
    assert r.status_code == 200 and r.json()["created"] is True
    stub = (await app.state.graph.run_named("get_payment", {"uetr": UETR}))[0]
    assert stub["stub"] is True and stub["amount"] is None

    await api.post("/ingest/payment", json=PAYMENT, headers=key("pay-1"))
    filled = (await app.state.graph.run_named("get_payment", {"uetr": UETR}))[0]
    assert filled["stub"] is False
    assert filled["amount"] == 125.5 and filled["payerId"] == "P-1"
    assert await count(UETR) == 1
    links = await app.state.graph.run_named("get_payment_links", {"uetr": UETR})
    assert [row["labels"] for row in links] == [["BankMessage"]]


async def test_ledger_entry_before_payment_makes_stub_and_link(api):
    await api.post("/ingest/ledger-entry", json=LEDGER, headers=key("led-1"))
    again = await api.post("/ingest/ledger-entry", json=LEDGER, headers=key("led-2"))
    assert again.json()["duplicate"] is True
    assert await count(UETR) == 1
    links = await app.state.graph.run_named("get_payment_links", {"uetr": UETR})
    assert [row["labels"] for row in links] == [["LedgerEntry"]]


async def test_paypal_event_idempotent(api):
    first = await api.post("/ingest/paypal-event", json=EVENT, headers=key("ev-1"))
    second = await api.post("/ingest/paypal-event", json=EVENT, headers=key("ev-1"))
    assert first.json()["created"] is True
    assert second.json() == {"id": "WH-T1", "created": False, "duplicate": True}


async def test_concurrent_same_key_creates_one(api):
    import asyncio

    replies = await asyncio.gather(
        *(api.post("/ingest/payment", json=PAYMENT, headers=key("race")) for _ in range(8))
    )
    assert sorted(r.json()["duplicate"] for r in replies) == [False] + [True] * 7
    assert await count(UETR) == 1


async def test_request_body_is_not_logged(api, caplog):
    import logging

    with caplog.at_level(logging.DEBUG):
        await api.post("/ingest/payment", json=PAYMENT, headers=key("log-1"))
    assert "125.5" not in caplog.text and "P-1" not in caplog.text