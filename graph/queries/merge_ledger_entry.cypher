// The Payment may not exist yet: make a stub (filled in later) and link by UETR.
MERGE (p:Payment {uetr: $uetr})
ON CREATE SET p.stub = true, p.ingestCount = 0
MERGE (l:LedgerEntry {entryId: $entryId})
ON CREATE SET l.uetr = $uetr, l.endToEndId = $endToEndId, l.amount = $amount,
  l.currency = $currency, l.ts = $ts, l.side = $side, l.ingestCount = 1
ON MATCH SET l.ingestCount = coalesce(l.ingestCount, 0) + 1
MERGE (l)-[:CORRELATES_WITH]->(p)
RETURN l.entryId AS id, l.ingestCount AS ingestCount