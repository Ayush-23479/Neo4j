from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import BaseModel

from app.graph.client import GraphClient

logger = logging.getLogger("app.matcher")

RecordKind = Literal["PayPalEvent", "BankMessage", "LedgerEntry"]
Method = Literal["uetr", "e2e", "custom_id", "amount_time"]

KINDS: tuple[str, ...] = ("PayPalEvent", "BankMessage", "LedgerEntry")
CONF_UETR = 1.0
CONF_E2E = 0.95
CONF_CUSTOM_ID = 0.9
CONF_AMOUNT_TIME = 0.5
LOW_CONFIDENCE_BELOW = 0.9
WINDOW = timedelta(minutes=10)
MAX_ORPHANS = 10_000


class MatchResult(BaseModel):
    paymentUetr: str | None = None  # noqa: N815
    method: Method | None = None
    confidence: float = 0.0
    lowConfidence: bool = False  # noqa: N815


def _window(ts: str) -> tuple[str, str] | None:
    """ISO UTC bounds (ts - 10 min, ts + 10 min), or None when ts is not a usable time."""
    try:
        moment = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    return (
        (moment - WINDOW).astimezone(UTC).strftime(fmt),
        (moment + WINDOW).astimezone(UTC).strftime(fmt),
    )


def _result(row: dict) -> MatchResult:
    confidence = float(row["confidence"])
    return MatchResult(
        paymentUetr=row["uetr"],
        method=row["method"],
        confidence=confidence,
        lowConfidence=confidence < LOW_CONFIDENCE_BELOW,
    )


async def link_records(client: GraphClient, record_kind: str, record_id: str) -> MatchResult:
    """Try to link one record. Returns the existing match if it already has one."""
    if record_kind not in KINDS:
        raise ValueError(f"record_kind must be one of {KINDS}")
    base = {"kind": record_kind, "id": record_id}
    rows = await client.run_named("get_record", base)
    if not rows:
        return MatchResult()
    rec = rows[0]

    if rec["linkedUetr"] and rec["linkedMethod"]:
        confidence = float(rec["linkedConfidence"] or 0.0)
        return MatchResult(
            paymentUetr=rec["linkedUetr"],
            method=rec["linkedMethod"],
            confidence=confidence,
            lowConfidence=confidence < LOW_CONFIDENCE_BELOW,
        )

    attempts: list[tuple[str, dict]] = []
    if rec["uetr"]:
        attempts.append(("link_by_uetr", {**base, "uetr": rec["uetr"]}))
    if rec["endToEndId"]:
        attempts.append(("link_by_e2e", {**base, "e2e": rec["endToEndId"]}))
    if rec["customId"]:
        attempts.append(("link_by_custom_id", {**base, "customId": rec["customId"]}))
    bounds = _window(rec["ts"]) if rec["ts"] else None
    if bounds and rec["amount"] is not None and rec["currency"]:
        attempts.append(
            (
                "link_by_amount_time",
                {
                    **base,
                    "amount": rec["amount"],
                    "currency": rec["currency"],
                    "lo": bounds[0],
                    "hi": bounds[1],
                },
            )
        )
    for query, params in attempts:
        found = await client.run_write(query, params)
        if found:
            return _result(found[0])
    return MatchResult()


async def relink_orphans(client: GraphClient) -> int:
    """Retry every unmatched record. Returns how many got linked."""
    orphans = await client.run_named("list_orphans", {}, limit=MAX_ORPHANS)
    linked = 0
    for orphan in orphans:
        if (await link_records(client, orphan["kind"], orphan["id"])).paymentUetr:
            linked += 1
    if linked:
        logger.info("relinked %d previously unmatched records", linked)
    return linked


async def orphan_count(client: GraphClient) -> int:
    rows = await client.run_named("count_orphans", {})
    return int(rows[0]["n"]) if rows else 0