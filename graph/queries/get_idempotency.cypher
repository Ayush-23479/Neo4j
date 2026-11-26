MATCH (i:Idempotency {key: $key})
RETURN i.resultJson AS resultJson, i.payloadHash AS payloadHash