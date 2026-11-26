from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Id = Annotated[str, StringConstraints(min_length=1, max_length=64, strip_whitespace=True)]
Currency = Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]
Money = Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2)]
Fee = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)]


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


def iso_utc(value: datetime) -> str:
    """Store timestamps the same way the seed data does: 2026-11-20T12:00:00Z."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class PaymentIn(_In):
    uetr: Id
    endToEndId: Id  # noqa: N815 (matches the graph property name)
    amount: Money
    currency: Currency
    payerId: Id  # noqa: N815
    payeeId: Id  # noqa: N815
    createdAt: datetime  # noqa: N815
    feeAmount: Fee | None = None  # noqa: N815


class LedgerEntryIn(_In):
    entryId: Id  # noqa: N815
    uetr: Id
    endToEndId: Id  # noqa: N815
    amount: Money
    currency: Currency
    ts: datetime
    side: Literal["DEBIT", "CREDIT"]


class PayPalEventIn(_In):
    eventId: Id  # noqa: N815
    type: Annotated[str, StringConstraints(min_length=1, max_length=64)]
    ts: datetime
    customId: Id  # noqa: N815
    amount: Money
    currency: Currency
    rawRef: Annotated[str, StringConstraints(max_length=256)] | None = None  # noqa: N815


class BankMessageIn(_In):
    msgId: Id  # noqa: N815
    type: Literal["pacs.008", "pacs.002", "camt.053"]
    ts: datetime
    status: Annotated[str, StringConstraints(max_length=16)] | None = None
    uetr: Id
    endToEndId: Id  # noqa: N815
    amount: Money
    currency: Currency
    arrivalSeq: int | None = Field(default=None, ge=0)  # noqa: N815
    xml: Annotated[str, StringConstraints(max_length=262_144)] | None = None


class IngestResult(BaseModel):
    id: str
    created: bool
    duplicate: bool