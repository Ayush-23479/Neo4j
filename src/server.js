const express = require("express");
const cors = require("cors");
const path = require("path");
const fs = require("fs");
const { Database } = require("@relate/relate");
const { initSchema, createPerson, createCompany, createAddress, createPhone,
  createBankAccount, createSanctionedEntity, createPayment, createDecision,
  createSanctionProgram, createSentFundsTo, createOwns, createRegisteredAt,
  createSharesPhone, createPayPalEvent, createBankMessage, createLedgerEntry, createFee,
} = require("./db");
const db = Database.open("./data/corridor_guard.rl");
const conn = db.connect();
initSchema();

const app = express();
app.use(cors());
app.use(express.json());

/**
 * GET /api/graph
 * Returns full nodes, edges, and persisted (:Decision) records from ./data/corridor_guard.rl.
 */
app.get("/api/graph", async (req, res) => {
  try {
    // Fetch all nodes and relationships from the Relate DB
    const nodesResult = await db.executeCypher(
      `MATCH (n) RETURN labels(n) AS labels, properties(n) AS properties, id(n) AS nodeId LIMIT 500`
    );
    const relationshipsResult = await db.executeCypher(
      `MATCH ()-[r]->() RETURN type(r) AS type, properties(r) AS properties, id(r) AS relId, startNode AS start, endNode AS end LIMIT 200`
    );

    const decisionsResult = await db.executeCypher(
      `MATCH (p:Payment)-[:SCREENED_AS]->(d:Decision) RETURN d.verdict AS verdict, d.riskScore AS riskScore, d.evidencePath AS evidencePath, d.scoredAt AS scoredAt, p.id AS paymentId LIMIT 100`
    );

    const nodes = [];
    const seen = new Set();

    // Deduplicate and canonicalize nodes
    for (const rec of nodesResult.records) {
      const labels = rec.get("labels") || [];
      const props = rec.get("properties") || {};
      const nid = rec.get("nodeId");

      // Skip placeholder
      if (nid && nid.toString().startsWith("0")) continue;

      const key = `${labels.join(",")}|${nid}`;
      if (seen.has(key)) continue;
      seen.add(key);

      nodes.push({
        id: nid !== undefined ? nid : null,
        labels: labels.length > 0 ? labels : ["Unknown"],
        properties: props,
      });
    }

    const edges = [];
    const edgeSeen = new Set();

    for (const rec of relationshipsResult.records) {
      const type = rec.get("type") || "KNOWS";
      const s = rec.get("start") ? rec.get("start").identity : null;
      const e = rec.get("end") ? rec.get("end").identity : null;
      const props = rec.get("properties") || {};
      const rid = rec.get("relId");

      if (s === null || e === null) continue;
      const key = `${s}|${e}|${type}`;
      if (edgeSeen.has(key)) continue;
      edgeSeen.add(key);

      edges.push({
        id: rid !== undefined ? rid : null,
        type,
        start: s,
        end: e,
        properties: props,
      });
    }

    const decisions = decisionsResult.records.map(r => ({
      verdict: r.get("verdict") || "pending",
      riskScore: r.get("riskScore") || 0,
      evidencePath: r.get("evidencePath") || "",
      scoredAt: r.get("scoredAt") || 0,
      paymentId: r.get("paymentId") || "unknown",
    }));

    res.json({ nodes, edges, decisions });
  } catch (err) {
    console.error("❌ GET /api/graph error:", err);
    res.status(500).json({ error: err.message });
  }
});

/**
 * POST /api/screen
 * Screens a preset or custom cross-border payment live, persists the (:Decision) node
 * to ./data/corridor_guard.rl, and returns the subgraph + JSON proof.
 */
app.post("/api/screen", async (req, res) => {
  try {
    const { paymentId, overrideVerdict } = req.body;

    if (!paymentId) {
      return res.status(400).json({ error: "paymentId is required" });
    }

    // Run the screening engine
    const result = await screeningEngine.screenPayment(paymentId, overrideVerdict);

    // Return the full subgraph + decision
    const subgraphResults = await db.executeCypher(
      `MATCH (p:Payment {id: $pid})-[r]->(n) RETURN p.id AS paymentId, type(r) AS relType, n.id AS nodeId, labels(n) AS labels, properties(n) AS properties
       UNION
       MATCH (p:Payment {id: $pid})<--[r]->(n) RETURN p.id AS paymentId, type(r) AS relType, n.id AS nodeId, labels(n) AS labels, properties(n) AS properties`,
      { pid: paymentId }
    );

    const subgraph = {
      paymentId,
      nodes: [],
      edges: [],
    };

    const seenNodes = new Set();
    const seenEdges = new Set();

    for (const rec of subgraphResults.records) {
      const nodeId = rec.get("nodeId");
      const labelArr = rec.get("labels") || [];
      const prop = rec.get("properties") || {};
      const relType = rec.get("relType") || "";

      if (nodeId && !seenNodes.has(nodeId.toString())) {
        seenNodes.add(nodeId.toString());
        subgraph.nodes.push({
          id: nodeId,
          labels: labelArr.length > 0 ? labelArr : ["Unknown"],
          properties: prop,
        });
      }

      if (relType && nodeId) {
        const s = rec.get("startNode") ? rec.get("startNode").identity : null;
        const e = rec.get("endNode") ? rec.get("endNode").identity : null;
        const key = `${s || ''}|${e || ''}|${relType}`;
        if (!seenEdges.has(key)) {
          seenEdges.add(key);
          subgraph.edges.push({
            type: relType,
            start: s || null,
            end: e || null,
            properties: prop,
          });
        }
      }
    }

    res.json({
      ...result,
      subgraph,
    });
  } catch (err) {
    console.error("❌ POST /api/screen error:", err);
    res.status(500).json({ error: err.message });
  }
});

/**
 * POST /api/review/:paymentId
 * Human-in-the-loop compliance override (APPROVED_RELEASED or CONFIRMED_SAR_BLOCKED)
 * persisted back into (:Decision).
 */
app.post("/api/review/:paymentId", async (req, res) => {
  try {
    const { paymentId } = req.params;
    const { verdict } = req.body; // "APPROVED_RELEASED" or "CONFIRMED_SAR_BLOCKED"

    if (!verdict || (!verdict.includes("APPROVED") && !verdict.includes("SAR"))) {
      return res.status(400).json({ error: "Invalid verdict. Use APPROVED_RELEASED or CONFIRMED_SAR_BLOCKED" });
    }

    // Persist the human override into the existing Decision node
    await db.executeCypher(
      `MATCH (p:Payment {id: $pid})-[r:SCREENED_AS]->(d:Decision) SET d.verdict = $verdict, d.overriddenAt = $ts, d.overriddenBy = "human-compliance"`,
      { pid: paymentId, verdict, ts: Date.now() }
    );

    // Also update the payment status
    await db.executeCypher(
      `MATCH (p:Payment {id: $pid}) SET p.status = $verdict`,
      { pid: paymentId, verdict }
    );

    res.json({
      paymentId,
      verdict,
      message: "Human review override persisted",
    });
  } catch (err) {
    console.error("❌ POST /api/review error:", err);
    res.status(500).json({ error: err.message });
  }
});

/**
 * POST /api/cypher
 * Executes read-only openCypher queries from the UI's Cypher Playground
 * against ./data/corridor_guard.rl.
 */
app.post("/api/cypher", async (req, res) => {
  try {
    const { query } = req.body;

    if (!query || !query.trim().toUpperCase().startsWith("MATCH")) {
      return res.status(400).json({ error: "Query must be a read-only MATCH query starting with MATCH" });
    }

    // Execute as read-only (Relate enforces this in single-file mode)
    const result = await db.executeCypher(query.trim());

    res.json({
      query: query.trim(),
      records: result.records.map(r => r.values),
      columns: result.columns || [],
    });
  } catch (err) {
    console.error("❌ POST /api/cypher error:", err);
    res.status(500).json({ error: err.message });
  }
});

// Serve public/index.html
app.use(express.static("public"));

// Fallback: serve index.html for any route not matched above
app.get("*", (req, res) => {
  const indexPath = path.join(__dirname, "../public/index.html");
  if (fs.existsSync(indexPath)) {
    res.sendFile(indexPath);
  } else {
    res.status(404).send("index.html not found");
  }
});

/**
 * Start server.
 */
const PORT = process.env.PORT || 3000;
app.listen(PORT, async () => {
  console.log(`🚀 CorridorGuard AI server listening on http://localhost:${PORT}`);
  console.log(`📊 API endpoints:`);
  console.log(`   GET  /api/graph`);
  console.log(`   POST /api/screen`);
  console.log(`   POST /api/review/:paymentId`);
  console.log(`   POST /api/cypher`);
  console.log(`🌐 Serving static files from public/`);
});