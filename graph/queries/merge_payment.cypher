// A stub Payment (created by an earlier message) has no amount yet: coalesce fills it in.
// ingestCount: 0 for a stub, 1 for the first real record, more for every repeat.
MERGE (p:Payment {uetr: $uetr})
ON CREATE SET p.endToEndId = $endToEndId, p.amount = $amount, p.currency = $currency,
  p.payerId = $payerId, p.payeeId = $payeeId, p.createdAt = $createdAt,
  p.feeAmount = $feeAmount, p.status = 'PENDING', p.stub = false, p.ingestCount = 1
ON MATCH SET p.endToEndId = coalesce(p.endToEndId, $endToEndId),
  p.amount = coalesce(p.amount, $amount), p.currency = coalesce(p.currency, $currency),
  p.payerId = coalesce(p.payerId, $payerId), p.payeeId = coalesce(p.payeeId, $payeeId),
  p.createdAt = coalesce(p.createdAt, $createdAt),
  p.feeAmount = coalesce(p.feeAmount, $feeAmount), p.status = coalesce(p.status, 'PENDING'),
  p.stub = false, p.ingestCount = coalesce(p.ingestCount, 0) + 1
RETURN p.uetr AS id, p.ingestCount AS ingestCount