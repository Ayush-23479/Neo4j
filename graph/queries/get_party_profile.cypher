MATCH (p:Party {id: $partyId})
OPTIONAL MATCH (p)-[:REGISTERED_AT]->(a:Address)
WITH p, collect(DISTINCT a.city) AS cities
OPTIONAL MATCH (p)-[:SHARES_PHONE]->(ph:Phone)
WITH p, cities, collect(DISTINCT ph.number) AS phones
RETURN p.id AS id, p.name AS name, p.kind AS kind, p.dobYear AS dobYear, p.country AS country, p.trustScore AS trustScore, cities AS cities, phones AS phones
