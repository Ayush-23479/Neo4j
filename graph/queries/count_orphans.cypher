// How many records are not matched to a real Payment yet.
MATCH (r) WHERE r:PayPalEvent OR r:BankMessage OR r:LedgerEntry
OPTIONAL MATCH (r)-[c:CORRELATES_WITH]->(:Payment) WHERE c.method IS NOT NULL
WITH r, count(c) AS matched WHERE matched = 0
RETURN count(r) AS n