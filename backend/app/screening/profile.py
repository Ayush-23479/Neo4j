from __future__ import annotations

import re

from pydantic import BaseModel, field_validator

from app.errors import ApiError
from app.graph.client import GraphClient

_MASKED_PHONE = re.compile(r"^\*{3}\d{2}$")


class PartyProfile(BaseModel):
    id: str
    name: str
    kind: str
    dobYear: int | None = None  # noqa: N815
    country: str | None = None
    city: str | None = None
    trustScore: int | None = None  # noqa: N815
    phones: list[str] = []
    addressLabel: str | None = None  # noqa: N815

    @field_validator("dobYear", mode="before")
    @classmethod
    def _year_only(cls, value):
        """A full date (2026-01-31) or a datetime is cut down to its year."""
        if isinstance(value, str) and len(value) >= 4 and value[:4].isdigit():
            return int(value[:4])
        if hasattr(value, "year"):
            return value.year
        return value


def _mask_phone(number: str) -> str:
    if _MASKED_PHONE.fullmatch(number):
        return number
    digits = re.sub(r"\D", "", number)
    return f"***{digits[-2:]}" if len(digits) >= 2 else "***"


def mask_party(profile: PartyProfile) -> PartyProfile:
    """Year only, city only, phone as last 2 digits. Safe to call twice."""
    city = profile.city
    if city and re.search(r"\d", city):  # a city never has a house number; drop it if it does
        city = re.sub(r"\d+", "", city).strip(" ,") or None
    return profile.model_copy(
        update={
            "city": city,
            "addressLabel": city,
            "phones": sorted({_mask_phone(p) for p in profile.phones}),
        }
    )


async def get_profile(client: GraphClient, party_id: str) -> PartyProfile:
    rows = await client.run_named("get_party_profile", {"partyId": party_id})
    if not rows:
        raise ApiError(404, "party_not_found", "No such party.")
    row = rows[0]
    cities = sorted(c for c in (row.get("cities") or []) if c)
    profile = PartyProfile(
        id=row["id"],
        name=row["name"] or "",
        kind=row["kind"] or "",
        dobYear=row["dobYear"],
        country=row["country"],
        city=cities[0] if cities else None,
        trustScore=row["trustScore"],
        phones=[p for p in (row.get("phones") or []) if p],
    )
    return mask_party(profile)


async def build_rollups(client: GraphClient) -> int:
    """Create or refresh SENT_FUNDS_TO {total, count, lastDate}. Returns the link count."""
    rows = await client.run_write("rollup_sent_funds", {}, timeout_s=60)
    return int(rows[0]["links"]) if rows else 0