import hashlib
import json
import random
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from iso_templates import camt053, pacs002, pacs008

ROOT = Path(__file__).resolve().parents[1]
SEED_DIR = ROOT / "data" / "seed"
DOCS_DIR = ROOT / "docs"
SEED = 42
LIST_NAME = "SYNTHETIC-WATCHLIST-1"
# "Now" for every detector and test, so results never depend on the real clock.
REFERENCE_NOW = datetime(2026, 11, 20, 12, 0, 0, tzinfo=UTC)

FIRST_NAMES = [
    "Aiden", "Bianca", "Callum", "Dalia", "Elias", "Farah", "Gideon", "Hana", "Idris", "Jonas",
    "Kira", "Leon", "Mira", "Nikolai", "Odette", "Pavel", "Quinn", "Rosa", "Soren", "Talia",
    "Ulrich", "Vera", "Wade", "Ximena", "Yusuf", "Zara", "Anders", "Britta", "Cyrus", "Delphine",
    "Emeka", "Freya", "Gustav", "Helena", "Ivo", "Jada", "Kofi", "Lucia", "Mateo", "Noor",
]
LAST_NAMES = [
    "Abernathy", "Bellweather", "Castellan", "Dunmore", "Eversley", "Fairbairn", "Galloway",
    "Hartwell", "Ingram", "Jessop", "Kingsley", "Lockhart", "Marchetti", "Northcott", "Okafor",
    "Pemberton", "Quartermaine", "Rasmussen", "Satterthwaite", "Thackeray", "Underhill",
    "Vandermeer", "Whitlock", "Yardley", "Zielinski", "Ashcroft", "Brandvold", "Cavendish",
    "Draycott", "Ellsworth", "Fitzgibbon", "Grayson", "Holloway", "Iverson", "Kowalczyk",
    "Lindqvist", "Moorcroft", "Nakamura", "Ostrander", "Prendergast",
]
COMPANY_A = ["Bluepeak", "Cinder", "Driftwood", "Emberline", "Foxglove", "Greystone", "Harborview",
             "Ironbark", "Juniper", "Kestrelwood", "Lakeshore", "Moonridge", "Nettle", "Oakhaven"]
COMPANY_B = ["Trading", "Logistics", "Holdings", "Capital", "Freight", "Imports", "Exports",
             "Partners", "Supplies", "Ventures"]
COMPANY_SUFFIX = ["Ltd", "LLC", "GmbH", "Pte Ltd", "Inc"]
STREETS = ["Harbor St", "Mill Rd", "Cedar Ave", "Union Way", "Bridge Ln", "Orchard Dr",
           "Station Rd", "Market Sq", "Ridge Blvd", "Willow Ct", "Canal St", "Summit Ave"]
CITIES = ["Springfield", "Riverton", "Lakeside", "Hillcrest", "Port Alden", "Eastmere",
          "Northgate", "Cedar Falls", "Stonebridge", "Marlow"]
COUNTRIES = ["US", "GB", "DE", "IN", "AE", "SG", "CA", "AU"]
CURRENCIES = ["USD", "EUR", "GBP"]
BANKS = ["BANK-NOVA", "BANK-ORCHID", "BANK-TIDEWATER", "BANK-ALPINE", "BANK-SUNDIAL"]
SANCTIONED_OTHER = [
    ("Oskar Brennvik", "person"), ("Lazar Dominik", "person"), ("Mirela Quade", "person"),
    ("Halden Maritime Co", "company"), ("Brightwater Exports", "company"),
    ("Irina Salvatore", "person"), ("Qadir Stone Holdings", "company"),
    ("Perrin Valk", "person"), ("Zenova Shipping Ltd", "company"),
]
PAYPAL_TYPES = ("ORDER_CREATED", "CAPTURE_COMPLETED")  # neutral labels, not real PayPal names


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def generate(out_dir: Path | None = None, write_docs: bool = True) -> dict:
    """Build the whole synthetic world and write it to out_dir. Returns the data."""
    rng = random.Random(SEED)
    out_dir = Path(out_dir) if out_dir else SEED_DIR

    def new_uetr() -> str:
        return str(uuid.UUID(int=rng.getrandbits(128), version=4))

    used_addresses: set[str] = set()
    used_phones: set[str] = set()
    addresses: list[dict] = []
    phones: list[dict] = []

    def make_address(label: str | None = None) -> str:
        while True:
            number = rng.randint(1, 989)
            street = rng.choice(STREETS)
            city = rng.choice(CITIES)
            country = rng.choice(COUNTRIES)
            key = f"{number} {street}, {city}, {country}".lower()
            if key not in used_addresses:
                used_addresses.add(key)
                addresses.append({"normalizedAddress": key, "city": city, "country": country})
                return key

    def make_phone() -> str:
        while True:
            number = f"+99-{rng.randint(1000000, 9999999)}"  # +99 is not a real country code
            if number not in used_phones:
                used_phones.add(number)
                phones.append({"number": number})
                return number

    persons: list[dict] = []
    companies: list[dict] = []
    sanctioned: list[dict] = []
    bank_accounts: list[dict] = []
    relationships: list[dict] = []

    def rel(rel_type, from_label, from_key, from_value, to_label, to_key, to_value):
        relationships.append({
            "type": rel_type,
            "from": {"label": from_label, "key": from_key, "value": from_value},
            "to": {"label": to_label, "key": to_key, "value": to_value},
        })

    def add_person(pid, name, dob_year, country, trust, address=None, phone=None) -> str:
        persons.append({"id": pid, "name": name, "kind": "person", "dobYear": dob_year,
                        "country": country, "trustScore": trust})
        rel("REGISTERED_AT", "Party", "id", pid, "Address", "normalizedAddress",
            address or make_address())
        rel("SHARES_PHONE", "Party", "id", pid, "Phone", "number", phone or make_phone())
        add_account(pid)
        return pid

    def add_company(cid, name, country, trust, address=None) -> str:
        companies.append({"id": cid, "name": name, "kind": "company", "country": country,
                          "trustScore": trust})
        rel("REGISTERED_AT", "Party", "id", cid, "Address", "normalizedAddress",
            address or make_address())
        add_account(cid)
        return cid

    def add_account(party_id: str) -> None:
        acc_id = f"BA-{party_id}"
        bank = rng.choice(BANKS)
        bank_accounts.append({"id": acc_id, "bankId": bank,
                              "iban": f"XX00SYNTH{rng.randint(10**9, 10**10 - 1)}"})
        rel("HAS_ACCOUNT", "Party", "id", party_id, "BankAccount", "id", acc_id)

    def add_sanctioned(sid, name, kind, dob_year, country, address=None, phone=None) -> str:
        entry = {"id": sid, "name": name, "kind": kind, "country": country, "listName": LIST_NAME}
        if dob_year:
            entry["dobYear"] = dob_year
        sanctioned.append(entry)
        rel("REGISTERED_AT", "SanctionedEntity", "id", sid, "Address", "normalizedAddress",
            address or make_address())
        if phone:
            rel("SHARES_PHONE", "SanctionedEntity", "id", sid, "Phone", "number", phone)
        return sid

    # ---- watchlist (12 fake entries; SANC-001 is the false-alarm lookalike) ----
    add_sanctioned("SANC-001", "John Doe", "person", 1962, "RU")
    add_sanctioned("SANC-002", "Orlin Freight Group", "company", None, "BY")  # address shared below
    add_sanctioned("SANC-003", "Kestrel Metals JSC", "company", None, "IR")
    for i, (name, kind) in enumerate(SANCTIONED_OTHER, start=4):
        add_sanctioned(f"SANC-{i:03d}", name, kind, 1950 + i if kind == "person" else None,
                       rng.choice(["RU", "IR", "KP", "SY", "BY"]))

    # ---- planted screening cases ----
    # FALSE_ALARM: same name as SANC-001, but different birth year, country, address, history.
    fa_payer = add_person("P-FA-001", "John Doe", 1985, "US", 780)

    # HIDDEN_ADDRESS: payer owns Company A, which shares a registered address with SANC-002.
    shared_address = make_address()
    sanc2_address_rel = next(r for r in relationships
                             if r["from"]["value"] == "SANC-002" and r["type"] == "REGISTERED_AT")
    sanc2_address_rel["to"]["value"] = shared_address
    ha_payer = add_person("P-HA-001", "Marta Voss", 1978, "DE", 610)
    ha_company = add_company(
        "CO-HA-001", "Northwind Trading Ltd", "DE", 640, address=shared_address
    )
    rel("OWNS", "Party", "id", ha_payer, "Party", "id", ha_company)

    # HIDDEN_PHONE: payer shares a phone with a director of sanctioned company SANC-003.
    shared_phone = make_phone()
    hp_payer = add_person("P-HP-001", "Dmitri Hale", 1981, "GB", 575, phone=shared_phone)
    hp_director = add_person("P-HP-002", "Selina Okoro", 1974, "GB", 590, phone=shared_phone)
    rel("DIRECTOR_OF", "Party", "id", hp_director, "SanctionedEntity", "id", "SANC-003")

    # MULE_RING: six different senders pay one receiver inside 24 hours.
    mr_receiver = add_person("P-MR-000", "Lena Crowe", 1990, "US", 520)
    mr_senders = [
        add_person(f"P-MR-{i:03d}", f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
                   rng.randint(1970, 2000), rng.choice(COUNTRIES), rng.randint(420, 560))
        for i in range(1, 7)
    ]

    # ---- background world: 200 persons in total, 40 companies ----
    background_persons: list[str] = []
    used_names: set[str] = {"John Doe", "Marta Voss", "Dmitri Hale", "Selina Okoro", "Lena Crowe"}
    used_names.update(p["name"] for p in persons)
    while len(persons) < 200:
        name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        if name in used_names:
            continue
        used_names.add(name)
        pid = f"P-{len(persons) + 1:04d}"
        add_person(pid, name, rng.randint(1950, 2002), rng.choice(COUNTRIES),
                   rng.randint(300, 900))
        background_persons.append(pid)

    background_companies: list[str] = []
    used_company_names: set[str] = {"Northwind Trading Ltd"}
    while len(companies) < 40:
        name = (f"{rng.choice(COMPANY_A)} {rng.choice(COMPANY_B)} {rng.choice(COMPANY_SUFFIX)}")
        if name in used_company_names:
            continue
        used_company_names.add(name)
        cid = f"CO-{len(companies) + 1:04d}"
        add_company(cid, name, rng.choice(COUNTRIES), rng.randint(300, 900))
        background_companies.append(cid)

    # Background ownership and directors (never touch sanctioned entities).
    for cid in background_companies:
        rel("OWNS", "Party", "id", rng.choice(background_persons), "Party", "id", cid)
        if rng.random() < 0.5:
            rel("DIRECTOR_OF", "Party", "id", rng.choice(background_persons), "Party", "id", cid)
    # Harmless noise: a few background pairs share an address or a phone.
    for _ in range(8):
        a, b = rng.sample(background_persons, 2)
        phone_rel = next(r for r in relationships
                         if r["from"]["value"] == a and r["type"] == "SHARES_PHONE")
        rel("SHARES_PHONE", "Party", "id", b, "Phone", "number", phone_rel["to"]["value"])

    # ---- payments and their records ----
    payments: list[dict] = []
    paypal_events: list[dict] = []
    bank_messages: list[dict] = []
    ledger_entries: list[dict] = []
    party_name = {p["id"]: p["name"] for p in persons + companies}
    counters = {"pay": 0, "event": 0, "msg": 0, "entry": 0, "arrival": 0}
    planted_payments: dict[str, dict] = {}

    def add_message(msg_type, payment, ts, status, xml):
        counters["msg"] += 1
        counters["arrival"] += 1
        bank_messages.append({
            "msgId": f"M-{counters['msg']:06d}", "type": msg_type, "ts": iso(ts), "status": status,
            "uetr": payment["uetr"], "endToEndId": payment["endToEndId"],
            "amount": payment["amount"], "currency": payment["currency"],
            "arrivalSeq": counters["arrival"], "xml": xml,
        })
        return bank_messages[-1]

    def add_entry(payment, side, amount, ts, entry_id=None):
        counters["entry"] += 1
        entry = {
            "entryId": entry_id or f"L-{counters['entry']:06d}", "uetr": payment["uetr"],
            "endToEndId": payment["endToEndId"], "amount": round(amount, 2),
            "currency": payment["currency"], "ts": iso(ts), "side": side,
        }
        ledger_entries.append(entry)
        return entry

    def add_payment(key, payer, payee, created, variant="clean", amount=None, camt=False):
        counters["pay"] += 1
        amt = round(amount if amount is not None else rng.uniform(20, 5000), 2)
        currency = rng.choice(CURRENCIES)
        fee = max(0.5, round(amt * 0.02, 2))
        payment = {
            "uetr": new_uetr(), "endToEndId": f"E2E-{key}", "amount": amt, "currency": currency,
            "feeAmount": fee, "status": "PENDING", "createdAt": iso(created),
            "payerId": payer, "payeeId": payee,
        }
        payments.append(payment)
        planted_payments[key] = payment

        for kind, delta in zip(PAYPAL_TYPES, (0, 60), strict=True):
            counters["event"] += 1
            event_id = f"WH-{counters['event']:06d}"
            paypal_events.append({
                "eventId": event_id, "type": kind, "ts": iso(created + timedelta(seconds=delta)),
                "customId": payment["endToEndId"], "amount": amt, "currency": currency,
                "rawRef": f"synthetic://paypal/{event_id}",
            })

        debtor, creditor = party_name[payer], party_name[payee]
        sent_at = created + timedelta(minutes=2)
        msg_008 = pacs008(f"M-{counters['msg'] + 1:06d}", payment["uetr"], payment["endToEndId"],
                          amt, currency, debtor, creditor, iso(sent_at))
        msg_002_ts = created + timedelta(minutes=4)

        def status_xml():
            return pacs002(f"M-{counters['msg'] + 1:06d}", payment["uetr"],
                           payment["endToEndId"], amt, currency, "ACSC", iso(msg_002_ts))

        if variant == "stuck":  # instruction sent, no reply, nothing booked
            add_message("pacs.008", payment, sent_at, "SENT", msg_008)
            return payment
        if variant == "out_of_order":  # status arrives BEFORE the instruction
            add_message("pacs.002", payment, msg_002_ts, "ACSC", status_xml())
            add_message("pacs.008", payment, sent_at, "SENT",
                        msg_008.replace(f"M-{counters['msg']:06d}", f"M-{counters['msg'] + 1:06d}"))
        else:
            add_message("pacs.008", payment, sent_at, "SENT", msg_008)
            add_message("pacs.002", payment, msg_002_ts, "ACSC", status_xml())

        add_entry(payment, "DEBIT", amt, sent_at)
        if variant == "missing_leg":  # money left, no credit
            return payment
        received = amt - fee - (25.0 if variant == "mismatch" else 0.0)
        credit = add_entry(payment, "CREDIT", received, created + timedelta(minutes=5))
        if variant == "duplicate":  # the same ledger line is delivered twice
            ledger_entries.append(dict(credit))
        if camt:
            add_message("camt.053", payment, created + timedelta(hours=1), "BOOK",
                        camt053(f"M-{counters['msg'] + 1:06d}", payment["uetr"],
                                payment["endToEndId"], received, currency, creditor,
                                iso(created + timedelta(hours=1))))
        return payment

    everyone = background_persons + background_companies
    old_start = REFERENCE_NOW - timedelta(days=40)
    for i in range(400):  # past payments between background parties
        payer, payee = rng.sample(everyone, 2)
        created = old_start + timedelta(seconds=rng.randint(0, 38 * 86400))
        add_payment(f"BG-{i + 1:04d}", payer, payee, created, camt=(i % 10 == 0))

    # history for the three demo payers: a few older payments to clean parties
    for payer, tag in ((fa_payer, "FA"), (ha_payer, "HA"), (hp_payer, "HP")):
        for j in range(3):
            created = old_start + timedelta(seconds=rng.randint(0, 30 * 86400))
            add_payment(f"HIST-{tag}-{j + 1}", payer, rng.choice(background_persons), created)

    recent = REFERENCE_NOW - timedelta(days=1)
    clean_target = background_persons[0]
    add_payment("FA", fa_payer, clean_target, recent, amount=900.0, camt=True)
    add_payment("HA", ha_payer, background_persons[1], recent + timedelta(minutes=10),
                amount=4800.0, camt=True)
    add_payment("HP", hp_payer, background_persons[2], recent + timedelta(minutes=20),
                amount=3100.0, camt=True)
    for i, sender in enumerate(mr_senders, start=1):
        add_payment(f"MR-{i}", sender, mr_receiver,
                    REFERENCE_NOW - timedelta(hours=8) + timedelta(minutes=17 * i),
                    amount=round(200 + 35 * i, 2))
    add_payment("STUCK", background_persons[3], background_persons[4],
                REFERENCE_NOW - timedelta(hours=3), variant="stuck", amount=640.0)
    add_payment("MISSING", background_persons[5], background_persons[6],
                REFERENCE_NOW - timedelta(hours=5), variant="missing_leg", amount=720.0)
    add_payment("DUP", background_persons[7], background_persons[8],
                REFERENCE_NOW - timedelta(hours=6), variant="duplicate", amount=410.0)
    add_payment("MISMATCH", background_persons[9], background_persons[10],
                REFERENCE_NOW - timedelta(hours=7), variant="mismatch", amount=1500.0)
    add_payment("OOO", background_persons[11], background_persons[12],
                REFERENCE_NOW - timedelta(hours=9), variant="out_of_order", amount=530.0)
    for i in range(1, 4):
        add_payment(f"CLEAN-{i}", background_persons[12 + i], background_persons[15 + i],
                    REFERENCE_NOW - timedelta(hours=10 + i), amount=250.0 * i, camt=True)

    def uetr_of(key: str) -> str:
        return planted_payments[key]["uetr"]

    expected_cases = [
        {"caseId": "FALSE_ALARM", "category": "screening", "paymentKey": "FA",
         "paymentUetr": uetr_of("FA"), "partyId": fa_payer,
         "description": "Common name matches a watchlist entry, but birth year, country, "
                        "address and history all differ.",
         "expectedOutcome": "AUTO_CLEARED", "expectedHops": 0,
         "expectedNameVerdict": "DIFFERENT_PERSON", "expectedFindings": []},
        {"caseId": "HIDDEN_ADDRESS", "category": "screening", "paymentKey": "HA",
         "paymentUetr": uetr_of("HA"), "partyId": ha_payer,
         "description": "Clean name. The payer owns a company registered at an address shared "
                        "with a sanctioned company.",
         "expectedOutcome": "HELD", "expectedHops": 3,
         "expectedPathRelationships": ["OWNS", "REGISTERED_AT", "REGISTERED_AT"],
         "expectedFindings": []},
        {"caseId": "HIDDEN_PHONE", "category": "screening", "paymentKey": "HP",
         "paymentUetr": uetr_of("HP"), "partyId": hp_payer,
         "description": "Clean name. The payer shares a phone with a director of a sanctioned "
                        "company.",
         "expectedOutcome": "HELD", "expectedHops": 3,
         "expectedPathRelationships": ["SHARES_PHONE", "SHARES_PHONE", "DIRECTOR_OF"],
         "expectedFindings": []},
        {"caseId": "MULE_RING", "category": "signal", "paymentKey": "MR-1",
         "paymentUetr": uetr_of("MR-1"), "partyId": mr_receiver,
         "description": "Six different senders pay one receiver within 24 hours.",
         "expectedOutcome": "AUTO_CLEARED", "expectedSignal": "MULE_RING",
         "expectedDistinctSenders": 6, "expectedFindings": [],
         "note": "The mule signal only adds to the score. Tune the threshold on this case."},
        {"caseId": "STUCK", "category": "lineage", "paymentKey": "STUCK",
         "paymentUetr": uetr_of("STUCK"), "description":
         "Instruction (pacs.008) sent, no status reply, nothing booked.",
         "expectedOutcome": "AUTO_CLEARED", "expectedFindings": ["STUCK"]},
        {"caseId": "MISSING_LEG", "category": "lineage", "paymentKey": "MISSING",
         "paymentUetr": uetr_of("MISSING"), "description": "Debit booked, credit missing.",
         "expectedOutcome": "AUTO_CLEARED", "expectedFindings": ["MISSING_LEG"]},
        {"caseId": "DUPLICATE", "category": "lineage", "paymentKey": "DUP",
         "paymentUetr": uetr_of("DUP"),
         "description": "The same credit ledger entry is delivered twice (ingestCount 2).",
         "expectedOutcome": "AUTO_CLEARED", "expectedFindings": ["DUPLICATE"]},
        {"caseId": "AMOUNT_MISMATCH", "category": "lineage", "paymentKey": "MISMATCH",
         "paymentUetr": uetr_of("MISMATCH"),
         "description": "Sent minus received is 25.00 more than the declared fee.",
         "expectedOutcome": "AUTO_CLEARED", "expectedFindings": ["AMOUNT_MISMATCH"]},
        {"caseId": "OUT_OF_ORDER", "category": "lineage", "paymentKey": "OOO",
         "paymentUetr": uetr_of("OOO"),
         "description": "The status message (pacs.002) arrives before the instruction.",
         "expectedOutcome": "AUTO_CLEARED", "expectedFindings": [],
         "expectedLinked": True},
        {"caseId": "CLEAN", "category": "lineage", "paymentKey": "CLEAN-1",
         "paymentUetr": uetr_of("CLEAN-1"),
         "otherPaymentUetrs": [uetr_of("CLEAN-2"), uetr_of("CLEAN-3")],
         "description": "Normal payments with a complete chain and no risk links.",
         "expectedOutcome": "AUTO_CLEARED", "expectedFindings": []},
    ]
    expected = {
        "meta": {"seed": SEED, "referenceNow": iso(REFERENCE_NOW), "watchlist": LIST_NAME,
                 "muleWindowHours": 24, "muleMinSenders": 5, "stuckAfterMinutes": 30,
                 "synthetic": True},
        "cases": expected_cases,
        "demoPayments": {"falseAlarm": uetr_of("FA"), "hiddenAddress": uetr_of("HA"),
                         "stuck": uetr_of("STUCK")},
    }

    data = {
        "parties": persons, "companies": companies, "addresses": addresses, "phones": phones,
        "bank_accounts": bank_accounts, "sanctioned": sanctioned, "relationships": relationships,
        "payments": payments, "paypal_events": paypal_events, "bank_messages": bank_messages,
        "ledger_entries": ledger_entries, "expected": expected,
    }
    write_files(data, out_dir, write_docs)
    return data


def write_files(data: dict, out_dir: Path, write_docs: bool) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, content in data.items():
        text = json.dumps(content, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        (out_dir / f"{name}.json").write_text(text, encoding="utf-8")
    (out_dir / "README.txt").write_text(
        "All files in this folder are SYNTHETIC. Names, addresses, phones, accounts and trust\n"
        "scores are invented. The watchlist is fake. No real people, no real sanctions data,\n"
        "no real credit or KYC data. Regenerate with: python generator/generate.py\n",
        encoding="utf-8",
    )
    if write_docs:
        DOCS_DIR.mkdir(parents=True, exist_ok=True)
        (DOCS_DIR / "planted-cases.md").write_text(planted_cases_markdown(data["expected"]),
                                                   encoding="utf-8")


def planted_cases_markdown(expected: dict) -> str:
    lines = [
        "# Planted cases",
        "",
        "Generated by `generator/generate.py` (seed 42). All data is synthetic.",
        f"Reference time for every detector and test: `{expected['meta']['referenceNow']}`.",
        "",
        "| Case | Kind | What is planted | Expected result |",
        "|---|---|---|---|",
    ]
    for case in expected["cases"]:
        result = case["expectedOutcome"]
        if "expectedHops" in case:
            result += f", {case['expectedHops']} hops"
        if case.get("expectedSignal"):
            senders = case["expectedDistinctSenders"]
            result += f", signal {case['expectedSignal']} ({senders} senders)"
        if case["expectedFindings"]:
            result += ", finding " + ", ".join(case["expectedFindings"])
        lines.append(
            f"| {case['caseId']} | {case['category']} | {case['description']} | {result} |"
        )
    lines += ["", "Demo payments (UETR):", ""]
    for name, uetr in expected["demoPayments"].items():
        lines.append(f"- {name}: `{uetr}`")
    return "\n".join(lines) + "\n"


def folder_hash(folder: Path) -> str:
    """SHA-256 over every file in a seed folder (used by the determinism test)."""
    digest = hashlib.sha256()
    for path in sorted(folder.glob("*")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


if __name__ == "__main__":
    result = generate()
    print(f"Wrote {len(result)} files to {SEED_DIR}")
    print(f"Parties {len(result['parties'])}, companies {len(result['companies'])}, "
          f"sanctioned {len(result['sanctioned'])}, payments {len(result['payments'])}")
    print(f"Folder hash: {folder_hash(SEED_DIR)}")