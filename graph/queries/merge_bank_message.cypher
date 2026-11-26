// The Payment may not exist yet (status message before instruction): stub, link by UETR.
MERGE (p:Payment {uetr: $uetr})
ON CREATE SET p.stub = true, p.ingestCount = 0
MERGE (m:BankMessage {msgId: $msgId})
ON CREATE SET m.type = $type, m.ts = $ts, m.status = $status, m.uetr = $uetr,
  m.endToEndId = $endToEndId, m.amount = $amount, m.currency = $currency,
  m.arrivalSeq = $arrivalSeq, m.xml = $xml, m.ingestCount = 1
ON MATCH SET m.ingestCount = coalesce(m.ingestCount, 0) + 1
MERGE (m)-[:CORRELATES_WITH]->(p)
RETURN m.msgId AS id, m.ingestCount AS ingestCount