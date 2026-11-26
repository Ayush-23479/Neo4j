MATCH (x)-[:CORRELATES_WITH]->(p:Payment {uetr: $uetr})
RETURN labels(x) AS labels, p.stub AS stub