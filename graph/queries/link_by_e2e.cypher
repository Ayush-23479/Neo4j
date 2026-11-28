// Method 2: end-to-end id equal to exactly one real Payment. Confidence 0.95.
OPTIONAL MATCH (b:BankMessage {msgId: $id}) WHERE $kind = 'BankMessage'
OPTIONAL MATCH (l:LedgerEntry {entryId: $id}) WHERE $kind = 'LedgerEntry'
OPTIONAL MATCH (e:PayPalEvent {eventId: $id}) WHERE $kind = 'PayPalEvent'
WITH coalesce(b, l, e) AS r
MATCH (p:Payment {endToEndId: $e2e}) WHERE r IS NOT NULL AND coalesce(p.stub, false) = false
WITH r, collect(p) AS ps WHERE size(ps) = 1
UNWIND ps AS p
OPTIONAL MATCH (r)-[old:CORRELATES_WITH]->(s:Payment) WHERE coalesce(s.stub, false) = true AND s.uetr <> p.uetr
DELETE old
WITH r, p
MERGE (r)-[c:CORRELATES_WITH]->(p)
SET c.method = 'e2e', c.confidence = 0.95, c.lowConfidence = false
RETURN p.uetr AS uetr, c.method AS method, c.confidence AS confidence