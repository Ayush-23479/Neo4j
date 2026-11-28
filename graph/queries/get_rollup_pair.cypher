// The SENT_FUNDS_TO roll-up for one payer/payee pair.
MATCH (:Party {id: $a})-[r:SENT_FUNDS_TO]->(:Party {id: $b})
RETURN r.total AS total, r.count AS count, r.lastDate AS lastDate