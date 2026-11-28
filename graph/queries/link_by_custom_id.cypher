// Method 3: PayPal custom_id equal to the endToEndId of exactly one real Payment. Confidence 0.9.
OPTIONAL MATCH (b:BankMessage {msgId: $id}) WHERE $kind = 'BankMessage'
OPTIONAL MATCH (l:LedgerEntry {entryId: $id}) WHERE $kind = 'LedgerEntry'
OPTIONAL MATCH (e:PayPalEvent {eventId: $id}) WHERE $kind = 'PayPalEvent'
WITH coalesce(b, l, e) AS r
MATCH (p:Payment {endToEndId: $customId}) WHERE r IS NOT NULL AND coalesce(p.stub, false) = false
WITH r, collect(p) AS ps WHERE size(ps) = 1
UNWIND ps AS p
OPTIONAL MATCH (r)-[old:CORRELATES_WITH]->(s:Payment) WHERE coalesce(s.stub, false) = true AND s.uetr <> p.uetr
DELETE old
WITH r, p
MERGE (r)-[c:CORRELATES_WITH]->(p)
SET c.method = 'custom_id', c.confidence = 0.9, c.lowConfidence = false
RETURN p.uetr AS uetr, c.method AS method, c.confidence AS confidence