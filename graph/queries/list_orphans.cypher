// Records that are not matched to a real Payment yet (oldest first). Pass a limit.
MATCH (r) WHERE r:PayPalEvent OR r:BankMessage OR r:LedgerEntry
OPTIONAL MATCH (r)-[c:CORRELATES_WITH]->(:Payment) WHERE c.method IS NOT NULL
WITH r, count(c) AS matched WHERE matched = 0
RETURN CASE WHEN r:PayPalEvent THEN 'PayPalEvent' WHEN r:BankMessage THEN 'BankMessage' ELSE 'LedgerEntry' END AS kind,
  coalesce(r.eventId, r.msgId, r.entryId) AS id, r.ts AS ts
ORDER BY ts