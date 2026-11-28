// Method 1: the record carries the Payment UETR. Confidence 1.0.
// A link to a stub Payment (made when the record arrived first) is replaced by the real one.
OPTIONAL MATCH (b:BankMessage {msgId: $id}) WHERE $kind = 'BankMessage'
OPTIONAL MATCH (l:LedgerEntry {entryId: $id}) WHERE $kind = 'LedgerEntry'
OPTIONAL MATCH (e:PayPalEvent {eventId: $id}) WHERE $kind = 'PayPalEvent'
WITH coalesce(b, l, e) AS r
MATCH (p:Payment {uetr: $uetr}) WHERE r IS NOT NULL AND coalesce(p.stub, false) = false
OPTIONAL MATCH (r)-[old:CORRELATES_WITH]->(s:Payment) WHERE coalesce(s.stub, false) = true AND s.uetr <> p.uetr
DELETE old
WITH r, p
MERGE (r)-[c:CORRELATES_WITH]->(p)
SET c.method = 'uetr', c.confidence = 1.0, c.lowConfidence = false
RETURN p.uetr AS uetr, c.method AS method, c.confidence AS confidence