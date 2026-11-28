// Refresh (a:Party)-[:SENT_FUNDS_TO]->(b:Party) from the stored payments:
// total, count and the date of the latest payment. MERGE, so a rerun never duplicates a link.
MATCH (p:Payment)
WHERE p.payerId IS NOT NULL AND p.payeeId IS NOT NULL AND p.amount IS NOT NULL
WITH p.payerId AS a, p.payeeId AS b, sum(p.amount) AS total, count(p) AS n, max(p.createdAt) AS last
MATCH (x:Party {id: a})
MATCH (y:Party {id: b})
MERGE (x)-[r:SENT_FUNDS_TO]->(y)
SET r.total = total, r.count = n, r.lastDate = last
RETURN count(r) AS links