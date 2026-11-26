// Graph schema for Explainable Payment Holds. One statement per line.
// Every statement is idempotent (IF NOT EXISTS), so running it on every start changes nothing.
// Lines starting with // and blank lines are ignored by backend/app/graph/schema.py.
// Person and Company nodes carry two labels: their own and Party (e.g. :Party:Person).

CREATE CONSTRAINT party_id_unique IF NOT EXISTS FOR (n:Party) REQUIRE n.id IS UNIQUE
CREATE CONSTRAINT sanctioned_entity_id_unique IF NOT EXISTS FOR (n:SanctionedEntity) REQUIRE n.id IS UNIQUE
CREATE CONSTRAINT address_normalized_unique IF NOT EXISTS FOR (n:Address) REQUIRE n.normalizedAddress IS UNIQUE
CREATE CONSTRAINT phone_number_unique IF NOT EXISTS FOR (n:Phone) REQUIRE n.number IS UNIQUE
CREATE CONSTRAINT payment_uetr_unique IF NOT EXISTS FOR (n:Payment) REQUIRE n.uetr IS UNIQUE
CREATE CONSTRAINT paypal_event_id_unique IF NOT EXISTS FOR (n:PayPalEvent) REQUIRE n.eventId IS UNIQUE
CREATE CONSTRAINT bank_message_id_unique IF NOT EXISTS FOR (n:BankMessage) REQUIRE n.msgId IS UNIQUE
CREATE CONSTRAINT ledger_entry_id_unique IF NOT EXISTS FOR (n:LedgerEntry) REQUIRE n.entryId IS UNIQUE

// Extra keys that later tasks rely on for "write once" behaviour
CREATE CONSTRAINT bank_account_id_unique IF NOT EXISTS FOR (n:BankAccount) REQUIRE n.id IS UNIQUE
CREATE CONSTRAINT decision_id_unique IF NOT EXISTS FOR (n:Decision) REQUIRE n.id IS UNIQUE
CREATE CONSTRAINT finding_id_unique IF NOT EXISTS FOR (n:Finding) REQUIRE n.id IS UNIQUE
CREATE CONSTRAINT audit_event_id_unique IF NOT EXISTS FOR (n:AuditEvent) REQUIRE n.id IS UNIQUE
CREATE CONSTRAINT idempotency_key_unique IF NOT EXISTS FOR (n:Idempotency) REQUIRE n.key IS UNIQUE