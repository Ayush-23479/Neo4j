import hashlib
import json
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from pydantic import BaseModel

from app.detect.matcher import relink_orphans
from app.errors import ApiError
from app.graph.client import GraphClient, GraphError
from app.ingest.models import (
    BankMessageIn,
    IngestResult,
    LedgerEntryIn,
    PaymentIn,
    PayPalEventIn,
    iso_utc,
)

logger = logging.getLogger("app.ingest")


def _float(value) -> float | None:
    return None if value is None else float(value)


def _payload_hash(model: BaseModel) -> str:
    canonical = json.dumps(model.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _result(row: dict) -> IngestResult:
    count = int(row["ingestCount"])
    return IngestResult(id=row["id"], created=count == 1, duplicate=count > 1)


async def _once(
    graph: GraphClient,
    scope: str,
    key: str,
    model: BaseModel,
    work: Callable[[], Awaitable[IngestResult]],
) -> IngestResult:
    """Run `work` once per (scope, key). A repeat returns the first result, duplicate=true."""
    full_key = f"{scope}:{key}"
    payload_hash = _payload_hash(model)
    async with graph.write_lock:
        found = await graph.run_named("get_idempotency", {"key": full_key})
        if found:
            if found[0]["payloadHash"] != payload_hash:
                raise ApiError(
                    409, "idempotency_key_reuse", "This Idempotency-Key was used for another body."
                )
            first = json.loads(found[0]["resultJson"])
            return IngestResult(id=first["id"], created=False, duplicate=True)
        result = await work()
        try:  # Task 9: a late record or Payment links itself (we hold write_lock here)
            await relink_orphans(graph)
        except GraphError:
            logger.warning("relink after ingest failed; the record stays unmatched for now")
        await graph.run_write(
            "merge_idempotency",
            {
                "key": full_key,
                "resultJson": result.model_dump_json(),
                "payloadHash": payload_hash,
                "now": iso_utc(datetime.now(UTC)),
            },
        )
        return result


async def ingest_payment(graph: GraphClient, key: str, data: PaymentIn) -> IngestResult:
    async def work() -> IngestResult:
        rows = await graph.run_write(
            "merge_payment",
            {
                "uetr": data.uetr,
                "endToEndId": data.endToEndId,
                "amount": _float(data.amount),
                "currency": data.currency,
                "payerId": data.payerId,
                "payeeId": data.payeeId,
                "createdAt": iso_utc(data.createdAt),
                "feeAmount": _float(data.feeAmount),
            },
        )
        await graph.run_write(
            "link_payment_parties", {"payerId": data.payerId, "payeeId": data.payeeId}
        )
        return _result(rows[0])

    return await _once(graph, "payment", key, data, work)


async def ingest_ledger_entry(graph: GraphClient, key: str, data: LedgerEntryIn) -> IngestResult:
    async def work() -> IngestResult:
        rows = await graph.run_write(
            "merge_ledger_entry",
            {
                "entryId": data.entryId,
                "uetr": data.uetr,
                "endToEndId": data.endToEndId,
                "amount": _float(data.amount),
                "currency": data.currency,
                "ts": iso_utc(data.ts),
                "side": data.side,
            },
        )
        return _result(rows[0])

    return await _once(graph, "ledger", key, data, work)


async def ingest_paypal_event(graph: GraphClient, key: str, data: PayPalEventIn) -> IngestResult:
    async def work() -> IngestResult:
        rows = await graph.run_write(
            "merge_paypal_event",
            {
                "eventId": data.eventId,
                "type": data.type,
                "ts": iso_utc(data.ts),
                "customId": data.customId,
                "amount": _float(data.amount),
                "currency": data.currency,
                "rawRef": data.rawRef,
            },
        )
        return _result(rows[0])

    return await _once(graph, "paypal", key, data, work)


async def ingest_bank_message(graph: GraphClient, key: str, data: BankMessageIn) -> IngestResult:
    async def work() -> IngestResult:
        rows = await graph.run_write(
            "merge_bank_message",
            {
                "msgId": data.msgId,
                "type": data.type,
                "ts": iso_utc(data.ts),
                "status": data.status,
                "uetr": data.uetr,
                "endToEndId": data.endToEndId,
                "amount": _float(data.amount),
                "currency": data.currency,
                "arrivalSeq": data.arrivalSeq,
                "xml": data.xml,
            },
        )
        return _result(rows[0])

    return await _once(graph, "bank_message", key, data, work)