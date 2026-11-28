// Method 4: same amount and currency, created inside the time window ($lo..$hi, ISO UTC
// strings). Only when exactly ONE Payment fits. Confidence 0.5, flagged lowConfidence.
OPTIONAL MATCH (b:BankMessage {msgId: $id}) WHERE $kind = 'BankMessage'
OPTIONAL MATCH (l:LedgerEntry {entryId: $id}) WHERE $kind = 'LedgerEntry'
OPTIONAL MATCH (e:PayPalEvent {eventId: $id}) WHERE $kind = 'PayPalEvent'
WITH coalesce(b, l, e) AS r
MATCH (p:Payment) WHERE r IS NOT NULL AND coalesce(p.stub, false) = false
  AND p.amount = $amount AND p.currency = $currency AND p.createdAt >= $lo AND p.createdAt <= $hi
WITH r, collect(p) AS ps WHERE size(ps) = 1
UNWIND ps AS p
OPTIONAL MATCH (r)-[old:CORRELATES_WITH]->(s:Payment) WHERE coalesce(s.stub, false) = true AND s.uetr <> p.uetr
DELETE old
WITH r, p
MERGE (r)-[c:CORRELATES_WITH]->(p)
SET c.method = 'amount_time', c.confidence = 0.5, c.lowConfidence = true
RETURN p.uetr AS uetr, c.method AS method, c.confidence AS confidence