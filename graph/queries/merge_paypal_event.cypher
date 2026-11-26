MERGE (e:PayPalEvent {eventId: $eventId})
ON CREATE SET e.type = $type, e.ts = $ts, e.customId = $customId, e.amount = $amount,
  e.currency = $currency, e.rawRef = $rawRef, e.ingestCount = 1
ON MATCH SET e.ingestCount = coalesce(e.ingestCount, 0) + 1
RETURN e.eventId AS id, e.ingestCount AS ingestCount