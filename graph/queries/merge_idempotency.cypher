MERGE (i:Idempotency {key: $key})
ON CREATE SET i.resultJson = $resultJson, i.payloadHash = $payloadHash, i.createdAt = $now
RETURN i.key AS key