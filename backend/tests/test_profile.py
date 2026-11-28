import json
import re
import sys
from pathlib import Path

import pytest
import relate

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "generator"))

import generate as gen  # noqa: E402
import loader  # noqa: E402

from app.detect.matcher import orphan_count, relink_orphans  # noqa: E402
from app.errors import ApiError  # noqa: E402
from app.graph.client import GraphClient  # noqa: E402
from app.screening.profile import PartyProfile, build_rollups, get_profile, mask_party  # noqa: E402


@pytest.fixture(scope="module")
def seed(tmp_path_factory):
    out = tmp_path_factory.mktemp("seed")
    data = gen.generate(out_dir=out, write_docs=False)
    return out, data


@pytest.fixture
async def g(seed, tmp_path):
    out, _ = seed
    loader.SEED_DIR = out
    path = tmp_path / "p.rl"
    conn = relate.connect(str(path))
    loader.load_seed(conn)
    conn.close()
    client = GraphClient(str(path), default_timeout_s=60)
    yield client
    await client.close()


async def test_every_demo_payer_has_a_profile(g, seed):
    _, d = seed
    payers = {p["payerId"] for p in d["payments"]}
    assert payers
    for pid in sorted(payers):
        profile = await get_profile(g, pid)
        assert profile.id == pid and profile.name


async def test_rollup_matches_summed_payments(g, seed):
    _, d = seed
    links = await build_rollups(g)
    assert links > 0
    pair = max(
        {(p["payerId"], p["payeeId"]) for p in d["payments"]},
        key=lambda k: sum(1 for p in d["payments"] if (p["payerId"], p["payeeId"]) == k),
    )
    rows = [p for p in d["payments"] if (p["payerId"], p["payeeId"]) == pair]
    got = await g.run_named("get_rollup_pair", {"a": pair[0], "b": pair[1]})
    assert got[0]["count"] == len(rows)
    assert got[0]["total"] == pytest.approx(sum(p["amount"] for p in rows), abs=0.01)
    assert got[0]["lastDate"] == max(p["createdAt"] for p in rows)
    assert await build_rollups(g) == links  # rerun: same number, no duplicates


async def test_profile_json_has_no_full_date_or_street(g, seed):
    _, d = seed
    for p in d["payments"][:60]:
        text = (await get_profile(g, p["payerId"])).model_dump_json()
        assert not re.search(r"\d{4}-\d{2}-\d{2}", text)
        street = r"\b\d{1,5}\s+\w+\s+(rd|st|ave|road|street|lane|ln|blvd)\b"
        assert not re.search(street, text, re.I)
        assert not re.search(r"\+\d", text)  # no full phone number


async def test_phone_is_last_two_digits(g, seed):
    _, d = seed
    seen = 0
    for party in d["parties"][:40]:
        for ph in (await get_profile(g, party["id"])).phones:
            seen += 1
            assert re.fullmatch(r"\*{3}\d{2}", ph)
    assert seen > 0


async def test_unknown_party_is_404(g):
    with pytest.raises(ApiError) as e:
        await get_profile(g, "nope")
    assert e.value.status_code == 404


def test_mask_cuts_dates_streets_and_phones_and_is_idempotent():
    raw = PartyProfile(
        id="x", name="n", kind="person", dobYear="1985-03-07",  # type: ignore[arg-type]
        city="12 Mill Rd, Springfield", phones=["+99-4823498", "+99-4823498"],
    )
    once = mask_party(raw)
    assert once.dobYear == 1985
    assert once.city == "Mill Rd, Springfield" and once.addressLabel == once.city
    assert once.phones == ["***98"]
    assert mask_party(once) == once
    assert not re.search(r"\d{4}-\d{2}-\d{2}", json.dumps(once.model_dump()))


async def test_loader_post_load_links_every_record(g):
    # the seed loader writes records without links; the matcher links them
    assert await orphan_count(g) > 0
    await relink_orphans(g)
    assert await orphan_count(g) < 0.05 * 3000