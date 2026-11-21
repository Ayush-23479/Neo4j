const { Database } = require("@relate/relate");
const path = require("path");
const { initSchema, createPerson, createCompany, createAddress, createPhone,
  createBankAccount, createSanctionedEntity, createPayment, createDecision,
  createSanctionProgram, createSentFundsTo, createOwns, createRegisteredAt,
  createSharesPhone, createPayPalEvent, createBankMessage, createLedgerEntry, createFee,
} = require("./db");

const SCENARIOS = [
  {
    id: "TXN-101",
    verdict: "AUTO-CLEAR",
    name: "John Doe",
    program: "DEFAULT",
    cibilScore: 785,
    dob: "1994-05-12",
    salaryHistoryClean: true,
    hopsToSanctioned: 0,
    paypalPayee: "johndoe@example.com",
    paypalAmount: 200.00,
    bankMessageSwift: "EXAMPLEUS33",
    bankMessageValue: 1000.00,
  },
  {
    id: "TXN-204",
    verdict: "FROZEN_HUMAN_REVIEW",
    name: "Jane Smith",
    program: "OFAC-991",
    cibilScore: 620,
    dob: "1988-03-15",
    hasMuleLayering: true,
    skimmedFee: 450,
    sentAmount: 10000,
    settledAmount: 9550,
    paypalPayee: "janesmith@example.com",
    paypalAmount: 4500.00,
    bankMessageSwift: "EXAMPLEUS33",
    bankMessageValue: 10000.00,
  },
  {
    id: "TXN-309",
    verdict: "FROZEN_HUMAN_REVIEW",
    name: "Alex Rivera",
    program: "DEFAULT",
    cibilScore: 540,
    dob: "1985-07-22",
    hasMuleLayering: true,
    missingAckBankB: true,
    paypalPayee: "alexrivera@example.com",
    paypalAmount: 3000.00,
    bankMessageSwift: "EXAMPLEUS33",
    bankMessageValue: 3000.00,
  },
  {
    id: "TXN-412",
    verdict: "FROZEN_HUMAN_REVIEW",
    name: "Viktor Krol",
    program: "OFAC-772",
    cibilScore: 510,
    dob: "1982-11-03",
    directHitHop: 1,
    paypalPayee: "viktorkrol@example.com",
    paypalAmount: 500.00,
    bankMessageSwift: "EXAMPLEUS33",
    bankMessageValue: 500.00,
  },
];

async function seed() {
  console.log("🌱 Seeding corridor_guard.rl...");
  await initSchema();

  for (const s of SCENARIOS) {
    // 1. Create Person
    await createPerson({
      id: s.id,
      name: s.name,
      dob: s.dob,
      address: `${String(Math.floor(Math.random() * 999) + 1)} Test St, Springfield, IL, US`,
      cibilScore: s.cibilScore,
      corridor: "cross-border-payments",
    });

    // 2. Create SanctionedEntity
    await createSanctionedEntity({
      id: `${s.id}-sanctioned`,
      name: s.name,
      program: s.program,
      notes: s.verdict === "AUTO-CLEAR" ? "Clean watchlist name, no criminal links" : `Flagged for ${s.verdict}`,
    });

    // 3. Create SanctionProgram
    await createSanctionProgram({
      code: s.program,
      name: s.program,
      description: `Hackathon sanction program: ${s.program}`,
    });

    // 4. Create Payment
    const amount = s.verdict === "AUTO-CLEAR" ? 98.50 : s.paypalAmount || 500.00;
    await createPayment({
      id: s.id,
      sender: s.name,
      recipient: s.verdict === "AUTO-CLEAR" ? "Legacy Payee" : "Mule Account",
      amount: amount,
      currency: "USD",
      status: s.verdict,
      timestamp: new Date().toISOString(),
    });

    // 5. Create Decision
    const evidencePath = `scored-by:system@${new Date().toISOString()}`;
    await createDecision({
      paymentId: s.id,
      verdict: s.verdict,
      evidencePath,
      scoredAt: Date.now(),
      scoredBy: "seed-script",
    });

    // 6. Create P2P credit edges (SENT_FUNDS_TO) for layering scenarios
    if (s.verdict === "FROZEN_HUMAN_REVIEW" && s.hasMuleLayering) {
      // Create 3 upstream accounts sharing phone with flagged actor
      for (let i = 1; i <= 3; i++) {
        const upstreamPerson = `${s.id}-mule-${i}`;
        await createPerson({
          id: upstreamPerson,
          name: `${s.name}-Mule-${i}`,
          dob: new Date().toISOString().split("T")[0],
          address: `${String(Math.floor(Math.random() * 999) + 1)} Upstream St, Springfield, IL, US`,
          cibilScore: 400 + i * 50,
          corridor: "cross-border-payments",
        });
        await createSentFundsTo({ fromId: upstreamPerson, toId: s.id, amount: 500 + i * 100, timestamp: new Date().toISOString() });
        await createSharesPhone({ personId: s.id, phoneId: `${upstreamPerson}-phone` });
        // Also create the mule as a Person with Phone
        await createPhone({ id: `${upstreamPerson}-phone`, number: `555-010${i}` });
      }
    }

    // 7. For TXN-309: missing pac.002 acknowledgment at Correspondent Bank B
    if (s.id === "TXN-309" && s.missingAckBankB) {
      await createBankMessage({
        paymentId: `${s.id}-bankmsg`,
        messageType: "pac.002",
        swiftBic: "CorrespBankBXXX",
        value: amount,
      });
    }

    // 8. For TXN-204: Shell Corp + fee skimming
    if (s.id === "TXN-204") {
      await createCompany({
        id: `${s.id}-shell`,
        name: "Shell Corp LLC",
        corridor: "cross-border-payments",
      });
      await createRegisteredAt({ entityId: `${s.id}-shell`, addressId: `${s.id}-addr` });
      await createOwns({ fromId: s.id, toId: `${s.id}-shell` });
      await createFee({ paymentId: s.id, amount: s.skimmedFee, description: "Intermediary skim fee" });
      await createSentFundsTo({ fromId: s.id, toId: `${s.id}-sanctioned`, amount: s.sentAmount, timestamp: new Date().toISOString() });
      // Create the address for shell corp
      await createAddress({ id: `${s.id}-addr`, street: "999 Bad St", city: "Springfield", zip: "62701", country: "US" });
    }

    // 9. For TXN-412: direct 1-hop watchlist hit
    if (s.id === "TXN-412") {
      await createSentFundsTo({ fromId: s.id, toId: `${s.id}-sanctioned`, amount: s.paypalAmount || 500.00, timestamp: new Date().toISOString() });
    }

    console.log(`  ✅ Seeded ${s.id}: ${s.verdict}`);
  }

  console.log("✅ Seed complete. 4 demo cases loaded with all entities, relationships, and decisions.");
  console.log("   Run `node src/server.js` to start the Express backend.");
}

seed().catch(err => {
  console.error("❌ Seed failed:", err);
  process.exit(1);
});