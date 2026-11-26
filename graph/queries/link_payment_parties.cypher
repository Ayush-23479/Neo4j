MATCH (a:Party {id: $payerId})
MATCH (b:Party {id: $payeeId})
MERGE (a)-[:SENT_FUNDS_TO]->(b)
RETURN a.id AS payerId