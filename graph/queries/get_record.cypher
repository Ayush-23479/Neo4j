// One record (BankMessage, LedgerEntry or PayPalEvent) with the keys the matcher needs,
// plus the real (non-stub) Payment it is already linked to, if any.
OPTIONAL MATCH (b:BankMessage {msgId: $id}) WHERE $kind = 'BankMessage'
OPTIONAL MATCH (l:LedgerEntry {entryId: $id}) WHERE $kind = 'LedgerEntry'
OPTIONAL MATCH (e:PayPalEvent {eventId: $id}) WHERE $kind = 'PayPalEvent'
WITH coalesce(b, l, e) AS r
WHERE r IS NOT NULL
OPTIONAL MATCH (r)-[c:CORRELATES_WITH]->(q:Payment) WHERE coalesce(q.stub, false) = false
RETURN r.uetr AS uetr, r.endToEndId AS endToEndId, r.customId AS customId,
  r.amount AS amount, r.currency AS currency, r.ts AS ts,
  q.uetr AS linkedUetr, c.method AS linkedMethod, c.confidence AS linkedConfidence