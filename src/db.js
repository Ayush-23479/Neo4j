const { Database } = require("@relate/relate");

// Open the database (single-file .rl persistence mode)
const db = Database.open("./data/corridor_guard.rl");

// Get a read-write connection for operations
const conn = db.connect();

// Execute a read-only openCypher query via the async connection
async function executeCypher(cypher, params = {}) {
  return await conn.queryAsync(cypher, params);
}

// Initialize the schema — idempotent, safe to call multiple times
// Note: conn.query() is synchronous; use conn.queryAsync() for Promise-returning
function initSchema() {
  try {
    // Run each statement separately since Relate may not batch multi-statement well
    conn.query("MERGE (p:Person {name: 'placeholder'})");
    conn.query("MERGE (c:Company {name: 'placeholder'})");
    conn.query("MERGE (a:Address {street: 'placeholder', city: 'placeholder', zip: 'placeholder', country: 'placeholder'})");
    conn.query("MERGE (ph:Phone {number: 'placeholder'})");
    conn.query("MERGE (ba:BankAccount {accountNumber: 'placeholder', bankName: 'placeholder'})");
    conn.query("MERGE (s:SanctionedEntity {name: 'placeholder', program: 'placeholder'})");
    conn.query("MERGE (pm:Payment {id: 'placeholder', status: 'pending'})");
    conn.query("MERGE (d:Decision {verdict: 'pending', evidencePath: '', scoredAt: 0, scoredBy: ''})");
    conn.query("MERGE (sp:SanctionProgram {code: 'placeholder'})");
    console.log("✅ Schema initialized");
  } catch (e) {
    // MERGE is idempotent; errors on first run only if syntax is wrong
    console.log("⚠️ Schema init note:", e.message);
  }
}

// Initialize on module load
initSchema();

/**
 * Person helpers
 */
async function createPerson({ id, name, dob, address, cibilScore, corridor }) {
  return await conn.queryAsync(
    `MERGE (p:Person {id: $id}) SET p.name = $name, p.dob = $dob, p.address = $address, p.cibilScore = $cibilScore, p.corridor = $corridor`,
    { id, name, dob: dob || null, address: address || null, cibilScore, corridor: corridor || null }
  );
}

/**
 * Company helpers
 */
async function createCompany({ id, name, corridor }) {
  return await conn.queryAsync(
    `MERGE (c:Company {id: $id}) SET c.name = $name, c.corridor = $corridor`,
    { id, name, corridor: corridor || null }
  );
}

/**
 * Address helpers
 */
async function createAddress({ id, street, city, zip, country }) {
  return await conn.queryAsync(
    `MERGE (a:Address {id: $id}) SET a.street = $street, a.city = $city, a.zip = $zip, a.country = $country`,
    { id, street: street || null, city: city || null, zip: zip || null, country: country || null }
  );
}

/**
 * Phone helpers
 */
async function createPhone({ id, number }) {
  return await conn.queryAsync(
    `MERGE (ph:Phone {id: $id}) SET ph.number = $number`,
    { id, number: number || null }
  );
}

/**
 * BankAccount helpers
 */
async function createBankAccount({ id, accountNumber, bankName }) {
  return await conn.queryAsync(
    `MERGE (ba:BankAccount {id: $id}) SET ba.accountNumber = $accountNumber, ba.bankName = $bankName`,
    { id, accountNumber: accountNumber || null, bankName: bankName || null }
  );
}

/**
 * SanctionedEntity helpers
 */
async function createSanctionedEntity({ id, name, program, notes }) {
  return await conn.queryAsync(
    `MERGE (s:SanctionedEntity {id: $id}) SET s.name = $name, s.program = $program, s.notes = $notes`,
    { id, name: name || null, program: program || null, notes: notes || null }
  );
}

/**
 * Payment helpers
 */
async function createPayment({ id, sender, recipient, amount, currency, status, timestamp }) {
  return await conn.queryAsync(
    `MERGE (pm:Payment {id: $id}) SET pm.sender = $sender, pm.recipient = $recipient, pm.amount = $amount, pm.currency = $currency, pm.status = $status, pm.timestamp = $timestamp`,
    { id, sender: sender || null, recipient: recipient || null, amount, currency: currency || "USD", status: status || "pending", timestamp: timestamp || null }
  );
}

/**
 * Decision helpers
 */
async function createDecision({ paymentId, verdict, evidencePath, scoredAt, scoredBy, overrideVerdict }) {
  const verdictValue = overrideVerdict || verdict;
  return await conn.queryAsync(
    `MATCH (p:Payment {id: $paymentId}) MERGE (p)-[:SCREENED_AS]->(d:Decision {paymentId: $paymentId}) SET d.verdict = $verdict, d.evidencePath = $evidencePath, d.scoredAt = $scoredAt, d.scoredBy = $scoredBy`,
    { paymentId, verdict: verdictValue, evidencePath: evidencePath || "", scoredAt: scoredAt || Date.now(), scoredBy: scoredBy || "system" }
  );
}

/**
 * SanctionProgram helpers
 */
async function createSanctionProgram({ code, name, description }) {
  return await conn.queryAsync(
    `MERGE (sp:SanctionProgram {code: $code}) SET sp.name = $name, sp.description = $description`,
    { code, name: name || null, description: description || null }
  );
}

/**
 * Relationship helpers
 */
async function createSentFundsTo({ fromId, toId, amount, timestamp }) {
  return await conn.queryAsync(
    `MATCH (from:Person {id: $fromId}), (to:SanctionedEntity {id: $toId}) MERGE (from)-[:SENT_FUNDS_TO {amount: $amount, timestamp: $timestamp}]->(to)`,
    { fromId, toId, amount: amount || 0, timestamp: timestamp || null }
  );
}

async function createOwns({ fromId, toId }) {
  return await conn.queryAsync(
    `MATCH (from:Person {id: $fromId}), (to:Company {id: $toId}) MERGE (from)-[:OWNS]->(to)`,
    { fromId, toId }
  );
}

async function createRegisteredAt({ entityId, addressId }) {
  return await conn.queryAsync(
    `MATCH (e:Company {id: $entityId}), (a:Address {id: $addressId}) MERGE (e)-[:REGISTERED_AT]->(a)`,
    { entityId, addressId }
  );
}

async function createSharesPhone({ personId, phoneId }) {
  return await conn.queryAsync(
    `MATCH (p:Person {id: $personId}), (ph:Phone {id: $phoneId}) MERGE (p)-[:SHARES_PHONE]->(ph)`,
    { personId, phoneId }
  );
}

async function createPayPalEvent({ paymentId, payee, amount, timestamp, transactionId }) {
  return await conn.queryAsync(
    `MERGE (pe:PayPalEvent {id: $paymentId}) SET pe.payee = $payee, pe.amount = $amount, pe.timestamp = $timestamp, pe.transactionId = $transactionId`,
    { paymentId, payee: payee || null, amount: amount || 0, timestamp: timestamp || null, transactionId: transactionId || null }
  );
}

async function createBankMessage({ paymentId, messageType, swiftBic, value }) {
  return await conn.queryAsync(
    `MERGE (bm:BankMessage {id: $paymentId}) SET bm.messageType = $messageType, bm.swiftBic = $swiftBic, bm.value = $value`,
    { paymentId, messageType: messageType || null, swiftBic: swiftBic || null, value: value || 0 }
  );
}

async function createLedgerEntry({ paymentId, entryId, description, amount }) {
  return await conn.queryAsync(
    `MERGE (le:LedgerEntry {id: $paymentId}) SET le.entryId = $entryId, le.description = $description, le.amount = $amount`,
    { paymentId, entryId: entryId || null, description: description || null, amount: amount || 0 }
  );
}

async function createFee({ paymentId, amount, description }) {
  return await conn.queryAsync(
    `MERGE (f:Fee {id: $paymentId}) SET f.amount = $amount, f.description = $description`,
    { paymentId, amount: amount || 0, description: description || null }
  );
}

// Export the conn and db for use by other modules
module.exports = {
  db,
  conn,
  initSchema,
  createPerson,
  createCompany,
  createAddress,
  createPhone,
  createBankAccount,
  createSanctionedEntity,
  createPayment,
  createDecision,
  createSanctionProgram,
  createSentFundsTo,
  createOwns,
  createRegisteredAt,
  createSharesPhone,
  createPayPalEvent,
  createBankMessage,
  createLedgerEntry,
  createFee,
  executeCypher,  // Added for screening engine Cypher playground queries
};