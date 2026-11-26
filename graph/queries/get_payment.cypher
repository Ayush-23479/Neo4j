MATCH (p:Payment {uetr: $uetr})
RETURN p.uetr AS uetr, p.stub AS stub, p.amount AS amount, p.currency AS currency,
       p.payerId AS payerId, p.payeeId AS payeeId, p.status AS status,
       p.ingestCount AS ingestCount