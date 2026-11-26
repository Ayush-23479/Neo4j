# Named queries

Rule: every query the API runs is a file in this folder, run by name through `GraphClient`
(`run_named` for reads, `run_write` for writes) with `$parameters` only.

- File name: lowercase letters, digits and underscore, ending in `.cypher` (`ping.cypher`).
- One statement per file. Lines starting with `//` are comments.
- Never build query text from input. Route code can only pass a name and a dict of parameters.
- Writes use `MERGE` on the unique key, with `ON CREATE SET` / `ON MATCH SET`.

| File | Used by | What it does |
|---|---|---|
| ping.cypher | /health | Proves the graph answers |
| merge_payment.cypher | ingest | Create or fill a Payment (fills a stub, counts repeats) |
| merge_ledger_entry.cypher | ingest | Create a LedgerEntry, stub Payment, link by UETR |
| merge_paypal_event.cypher | ingest | Create a PayPalEvent |
| merge_bank_message.cypher | ingest | Create a BankMessage, stub Payment, link by UETR |
| link_payment_parties.cypher | ingest | Payer -SENT_FUNDS_TO-> payee, when both Parties exist |
| get_idempotency.cypher / merge_idempotency.cypher | ingest | Remember the first result per key |
| get_payment.cypher, get_payment_links.cypher, count_payments_by_uetr.cypher | ingest, tests | Read back a payment and what points at it |