MATCH (p:Payment {uetr: $uetr})
RETURN count(p) AS c