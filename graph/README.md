# Graph data dictionary (Task 3)

One Relate store file (`RELATE_PATH`, default `./data/graph.rl`). Schema: `graph/schema.cypher`
(idempotent, applied at API startup and by the loader). All data is synthetic.

## Nodes

| Label | Unique key | Other properties |
|---|---|---|
| Party (+ `Person` or `Company`) | `id` | name, kind, dobYear (persons), country, trustScore |
| Address | `normalizedAddress` | city, country |
| Phone | `number` | |
| BankAccount | `id` | bankId, iban |
| SanctionedEntity | `id` | name, kind, dobYear, country, listName |
| Payment | `uetr` | endToEndId, amount, currency, feeAmount, status, createdAt, payerId, payeeId |
| PayPalEvent | `eventId` | type, ts, customId (= endToEndId), amount, currency, rawRef |
| BankMessage | `msgId` | type (pacs.008 / pacs.002 / camt.053), ts, status, uetr, endToEndId, amount, currency, arrivalSeq, xml |
| LedgerEntry | `entryId` | uetr, endToEndId, amount, currency, ts, side (DEBIT/CREDIT), ingestCount |
| Decision, Finding, AuditEvent | `id` | written by later tasks |
| Idempotency | `key` | resultJson, payloadHash, createdAt (first result per Idempotency-Key, Task 6) |
| Bank, Fee | | created by lineage tasks |

`Party:Person` and `Party:Company` share one `id` space, so one Party constraint covers both.

## Relationships

Hop relationships (the three-hop screening walk may follow only these):
`OWNS`, `DIRECTOR_OF`, `REGISTERED_AT`, `SHARES_PHONE`, `SENT_FUNDS_TO`.

Not hops (never followed by the screening walk): `SAME_AS_CANDIDATE`, `SCREENED_AS`,
`CORRELATES_WITH`, `SENT_THROUGH`, `NEXT_HOP`, `SETTLED_AS`, `CHARGED`, `FLAGGED_BY`, `EVIDENCE`,
`HAS_ACCOUNT`.

Ingestion (Task 6) links every LedgerEntry and BankMessage to its Payment by UETR with
`CORRELATES_WITH`. If the Payment has not arrived yet, a stub `Payment {stub: true}` is created and
filled in later (`stub` becomes false), so out-of-order messages are never rejected.

The loader writes OWNS, DIRECTOR_OF, REGISTERED_AT, SHARES_PHONE, HAS_ACCOUNT and SENT_FUNDS_TO
(payer to payee, one per payment). Lineage links (CORRELATES_WITH, SENT_THROUGH, SETTLED_AS ...)
are created by the ingest and detect tasks, not by the loader.

## Rules

- Unique constraints refuse duplicate keys (`relate.IntegrityError`).
- A ledger line delivered twice is ONE LedgerEntry with `ingestCount` 2 (planted case DUPLICATE).
- Statuses: Payment `AUTO_CLEARED / HELD / RELEASED / REJECTED`; Finding `STUCK / MISSING_LEG /
  DUPLICATE / AMOUNT_MISMATCH`.

## Seed data

`python generator/generate.py` writes `data/seed/*.json` and `docs/planted-cases.md`
(seed 42, same files every run). `python generator/loader.py` rebuilds the store from them.