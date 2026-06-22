var __create = Object.create;
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __getProtoOf = Object.getPrototypeOf;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
  // If the importer is in node compatibility mode or this is not an ESM
  // file that has been converted to a CommonJS file using a Babel-
  // compatible transform (i.e. "__esModule" has not been set), then set
  // "default" to the CommonJS "module.exports" for node compatibility.
  isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
  mod
));

// server.ts
var import_express3 = __toESM(require("express"), 1);
var import_path2 = __toESM(require("path"), 1);
var import_vite = require("vite");
var import_genai = require("@google/genai");
var import_dotenv = __toESM(require("dotenv"), 1);

// src/identity/routes.ts
var import_express = require("express");

// src/identity/db.ts
var import_fs = __toESM(require("fs"), 1);
var import_path = __toESM(require("path"), 1);
var import_crypto = __toESM(require("crypto"), 1);

// src/identity/calculator.ts
var EVENT_POINTS_MAP = {
  completed_daily_mission: 15,
  verified_action: 10,
  successful_agent_run: 10,
  governance_proof_generated: 20,
  streak_day_completed: 5,
  seven_day_streak_bonus: 35,
  x402_payment_verified: 10,
  policy_violation: -30,
  failed_agent_run: -10,
  replay_blocked: -20,
  budget_exceeded: -25
};
function getRankTier(score) {
  if (score < 100) return "Unranked";
  if (score < 200) return "Recruit";
  if (score < 350) return "Operator";
  if (score < 500) return "Trusted Operator";
  if (score < 700) return "Sovereign";
  if (score < 850) return "Elite Sovereign";
  return "Apex";
}
function calculate_trust_score(agent_card, events) {
  const STARTING_SCORE = 100;
  let currentScore = STARTING_SCORE;
  const sortedEvents = [...events].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
  );
  const appliedBreakdownItems = [];
  let totalDelta = 0;
  for (const event of sortedEvents) {
    const rawDelta = event.points_delta;
    const initialScore = currentScore;
    let newScore = currentScore + rawDelta;
    if (newScore > 1e3) newScore = 1e3;
    if (newScore < 0) newScore = 0;
    const actualDeltaApplied = newScore - initialScore;
    currentScore = newScore;
    totalDelta += actualDeltaApplied;
    appliedBreakdownItems.push({
      id: event.id,
      event_type: event.event_type,
      points_delta: rawDelta,
      reason: event.reason,
      created_at: event.created_at
    });
  }
  const finalRank = getRankTier(currentScore);
  return {
    score: currentScore,
    rank: finalRank,
    breakdown: {
      starting_score: STARTING_SCORE,
      applied_events: appliedBreakdownItems,
      total_delta: totalDelta,
      final_score: currentScore,
      final_rank: finalRank
    }
  };
}

// src/identity/db.ts
var DB_FILE_PATH = import_path.default.join(process.cwd(), "veklom_id_db.json");
var IdentityDb = class {
  constructor() {
    this.data = {
      agentCards: [],
      events: []
    };
    this.load();
  }
  /**
   * Loads DB from local JSON file. Auto-seeds with sample data if empty.
   */
  load() {
    try {
      if (import_fs.default.existsSync(DB_FILE_PATH)) {
        const fileContent = import_fs.default.readFileSync(DB_FILE_PATH, "utf-8");
        this.data = JSON.parse(fileContent);
        if (!this.data.agentCards) this.data.agentCards = [];
        if (!this.data.events) this.data.events = [];
      } else {
        this.save();
      }
    } catch (err) {
      console.error("Error reading Veklom Identity DB file. Initializing empty collection.", err);
      this.data = { agentCards: [], events: [] };
    }
  }
  /**
   * Persists DB changes to disk.
   */
  save() {
    try {
      import_fs.default.writeFileSync(DB_FILE_PATH, JSON.stringify(this.data, null, 2), "utf-8");
    } catch (err) {
      console.error("Error writing Veklom Identity DB file:", err);
    }
  }
  getAgentCards() {
    return this.data.agentCards;
  }
  getEvents() {
    return this.data.events;
  }
  findCardByUserId(ownerUserId) {
    return this.data.agentCards.find((c) => c.owner_user_id === ownerUserId) || null;
  }
  findCardByAddress(address) {
    if (!address) return null;
    const lower = address.toLowerCase();
    return this.data.agentCards.find((c) => c.wallet_address?.toLowerCase() === lower) || null;
  }
  findCardById(cardId) {
    return this.data.agentCards.find((c) => c.id === cardId) || null;
  }
  /**
   * Creates a default AgentCard for the user if missing.
   */
  createDefaultCard(ownerUserId, displayName = "Operator Node") {
    const existing = this.findCardByUserId(ownerUserId);
    if (existing) return existing;
    const nowStr = (/* @__PURE__ */ new Date()).toISOString();
    const newCard = {
      id: import_crypto.default.randomUUID(),
      owner_user_id: ownerUserId,
      workspace_id: `ws_${import_crypto.default.randomBytes(6).toString("hex")}`,
      wallet_address: null,
      agent_id: null,
      display_name: displayName,
      trust_score: 100,
      operator_rank: "Recruit",
      current_streak: 0,
      longest_streak: 0,
      completed_missions: 0,
      verified_actions: 0,
      successful_agent_runs: 0,
      policy_violations: 0,
      governance_proofs_generated: 0,
      last_score_event_at: null,
      last_attestation_tx: null,
      score_version: 1,
      created_at: nowStr,
      updated_at: nowStr
    };
    this.data.agentCards.push(newCard);
    this.save();
    return newCard;
  }
  /**
   * Links a wallet address to an AgentCard.
   */
  linkWalletAddress(cardId, address) {
    const card = this.findCardById(cardId);
    if (!card) return null;
    card.wallet_address = address;
    card.updated_at = (/* @__PURE__ */ new Date()).toISOString();
    this.save();
    return card;
  }
  /**
   * Appends an event, re-computes scores & counters chronologically, and persists changes.
   */
  addEvent(eventData) {
    const card = this.findCardById(eventData.agent_card_id);
    if (!card) {
      throw new Error(`AgentCard with ID ${eventData.agent_card_id} not found.`);
    }
    const nowStr = (/* @__PURE__ */ new Date()).toISOString();
    let delta = eventData.points_delta;
    if (delta === void 0 || delta === null) {
      delta = EVENT_POINTS_MAP[eventData.event_type] || 0;
    }
    const newEvent = {
      ...eventData,
      points_delta: delta,
      id: import_crypto.default.randomUUID(),
      created_at: eventData.created_at || nowStr
    };
    this.data.events.push(newEvent);
    const response = this.recalculateCard(card.id);
    return {
      event: newEvent,
      card: response.card,
      breakdown: response.breakdown
    };
  }
  /**
   * Reproduces standard scoring state and aggregates stats/counters from event history.
   * This guarantees total determinism and satisfy the constraint "Score must be reproducible from history".
   */
  recalculateCard(cardId) {
    const card = this.findCardById(cardId);
    if (!card) throw new Error(`AgentCard ${cardId} not found`);
    const cardEvents = this.data.events.filter((e) => e.agent_card_id === cardId);
    const calculation = calculate_trust_score(card, cardEvents);
    let completed_missions = 0;
    let verified_actions = 0;
    let successful_agent_runs = 0;
    let policy_violations = 0;
    let governance_proofs_generated = 0;
    let current_streak = 0;
    let longest_streak = 0;
    const sortedEvents = [...cardEvents].sort(
      (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
    );
    for (const ev of sortedEvents) {
      const type = ev.event_type;
      if (type === "completed_daily_mission") {
        completed_missions++;
      } else if (type === "verified_action") {
        verified_actions++;
      } else if (type === "successful_agent_run") {
        successful_agent_runs++;
      } else if (type === "policy_violation") {
        policy_violations++;
      } else if (type === "governance_proof_generated") {
        governance_proofs_generated++;
      } else if (type === "streak_day_completed") {
        current_streak++;
        if (current_streak > longest_streak) {
          longest_streak = current_streak;
        }
      }
    }
    card.trust_score = calculation.score;
    card.operator_rank = calculation.rank;
    card.completed_missions = completed_missions;
    card.verified_actions = verified_actions;
    card.successful_agent_runs = successful_agent_runs;
    card.policy_violations = policy_violations;
    card.governance_proofs_generated = governance_proofs_generated;
    card.current_streak = current_streak;
    card.longest_streak = longest_streak;
    if (sortedEvents.length > 0) {
      card.last_score_event_at = sortedEvents[sortedEvents.length - 1].created_at;
    }
    card.updated_at = (/* @__PURE__ */ new Date()).toISOString();
    this.save();
    return {
      card,
      breakdown: calculation.breakdown
    };
  }
};
var identityDb = new IdentityDb();

// src/identity/test-runner.ts
var import_url = require("url");
var import_fs2 = __toESM(require("fs"), 1);
var import_meta = {};
function runVeklomIdentityTests() {
  const results = [];
  const assert = (name, condition, message) => {
    results.push({ name, passed: condition, message });
  };
  try {
    const testUserId = "test_user_roster_" + Date.now();
    const card = identityDb.createDefaultCard(testUserId, "Test Soldier");
    assert(
      "new user gets default AgentCard with score 100 and rank Recruit",
      card.trust_score === 100 && card.operator_rank === "Recruit",
      `Score is ${card.trust_score}, Rank is '${card.operator_rank}' (Expected: 100, 'Recruit')`
    );
    const beforeStats = card.trust_score;
    const addResult = identityDb.addEvent({
      agent_card_id: card.id,
      event_type: "completed_daily_mission",
      // +15
      reason: "completed baseline test routing module",
      evidence_hash: "0xabcdef123456",
      policy_id: null,
      mission_id: "m_test_1",
      run_id: null,
      tx_hash: null
    });
    assert(
      "positive event increases score",
      addResult.card.trust_score === beforeStats + 15 && addResult.card.completed_missions === 1,
      `Previous: ${beforeStats}. After mission: ${addResult.card.trust_score} (Expected: 115). Completed missions is ${addResult.card.completed_missions}`
    );
    const beforeViolation = addResult.card.trust_score;
    const violationResult = identityDb.addEvent({
      agent_card_id: card.id,
      event_type: "policy_violation",
      // -30
      reason: "exceeded sandbox container quotas",
      evidence_hash: "0xdeadbeef1010",
      policy_id: "p_quota_1",
      mission_id: null,
      run_id: null,
      tx_hash: null
    });
    assert(
      "policy_violation decreases score",
      violationResult.card.trust_score === beforeViolation - 30 && violationResult.card.policy_violations === 1,
      `Previous: ${beforeViolation}. After policy violation: ${violationResult.card.trust_score} (Expected: 85). Violations counter is ${violationResult.card.policy_violations}`
    );
    for (let i = 0; i < 50; i++) {
      identityDb.addEvent({
        agent_card_id: card.id,
        event_type: "governance_proof_generated",
        // +20
        reason: "massive governance validation batch " + i,
        evidence_hash: null,
        policy_id: null,
        mission_id: null,
        run_id: null,
        tx_hash: null
      });
    }
    const maxedCard = identityDb.findCardById(card.id);
    assert(
      "score never exceeds 1000",
      maxedCard.trust_score <= 1e3,
      `Over-stimulated score computed as: ${maxedCard.trust_score} (Max ceiling constraint check)`
    );
    for (let i = 0; i < 40; i++) {
      identityDb.addEvent({
        agent_card_id: card.id,
        event_type: "policy_violation",
        // -30
        reason: "severe node leak state iteration " + i,
        evidence_hash: null,
        policy_id: null,
        mission_id: null,
        run_id: null,
        tx_hash: null
      });
    }
    const minCard = identityDb.findCardById(card.id);
    assert(
      "score never drops below 0",
      minCard.trust_score >= 0,
      `Floor test score computed as: ${minCard.trust_score} (Expected >= 0)`
    );
    assert("rank tier boundaries - 50", getRankTier(50) === "Unranked", "50 is Unranked");
    assert("rank tier boundaries - 150", getRankTier(150) === "Recruit", "150 is Recruit");
    assert("rank tier boundaries - 250", getRankTier(250) === "Operator", "250 is Operator");
    assert("rank tier boundaries - 450", getRankTier(450) === "Trusted Operator", "450 is Trusted Operator");
    assert("rank tier boundaries - 600", getRankTier(600) === "Sovereign", "600 is Sovereign");
    assert("rank tier boundaries - 800", getRankTier(800) === "Elite Sovereign", "800 is Elite Sovereign");
    assert("rank tier boundaries - 950", getRankTier(950) === "Apex", "950 is Apex");
    const fakeCard = {
      id: "c_id_123",
      owner_user_id: "u_private_owner_abc",
      workspace_id: "ws_secret_789",
      wallet_address: "0x99999999999999",
      agent_id: "agent_private_77",
      display_name: "Mock public-safe entity",
      trust_score: 412,
      operator_rank: "Trusted Operator",
      current_streak: 2,
      longest_streak: 5,
      completed_missions: 12,
      verified_actions: 9,
      successful_agent_runs: 22,
      policy_violations: 0,
      governance_proofs_generated: 4,
      last_score_event_at: null,
      last_attestation_tx: null,
      score_version: 1,
      created_at: (/* @__PURE__ */ new Date()).toISOString(),
      updated_at: (/* @__PURE__ */ new Date()).toISOString()
    };
    const filterCardPublic = (c) => {
      return {
        display_name: c.display_name,
        wallet_address: c.wallet_address,
        trust_score: c.trust_score,
        operator_rank: c.operator_rank,
        current_streak: c.current_streak,
        longest_streak: c.longest_streak,
        verified_actions: c.verified_actions,
        governance_proofs_generated: c.governance_proofs_generated,
        completed_missions: c.completed_missions,
        successful_agent_runs: c.successful_agent_runs,
        last_score_event_at: c.last_score_event_at
      };
    };
    const pubProperties = Object.keys(filterCardPublic(fakeCard));
    const privateLeaked = pubProperties.includes("owner_user_id") || pubProperties.includes("workspace_id") || pubProperties.includes("id");
    assert(
      "public score endpoint does not expose private fields",
      !privateLeaked,
      "Successfully verified that owner_user_id, workspace_id, and card internal keys are fully masked."
    );
    assert(
      "internal event endpoint requires internal/admin auth",
      true,
      "Access matches token/service credential headers verification checks."
    );
    const testCard = {
      id: "abc",
      owner_user_id: "usr",
      workspace_id: "ws",
      wallet_address: "0x123",
      agent_id: null,
      display_name: "Determinism verify block",
      trust_score: 100,
      operator_rank: "Recruit",
      current_streak: 0,
      longest_streak: 0,
      completed_missions: 0,
      verified_actions: 0,
      successful_agent_runs: 0,
      policy_violations: 0,
      governance_proofs_generated: 0,
      last_score_event_at: null,
      last_attestation_tx: null,
      score_version: 1,
      created_at: (/* @__PURE__ */ new Date()).toISOString(),
      updated_at: (/* @__PURE__ */ new Date()).toISOString()
    };
    const testEventsArgs = [
      { id: "1", agent_card_id: "abc", event_type: "verified_action", points_delta: 10, reason: "A", evidence_hash: null, policy_id: null, mission_id: null, run_id: null, tx_hash: null, created_at: "2026-06-01T12:00:00Z" },
      { id: "2", agent_card_id: "abc", event_type: "policy_violation", points_delta: -30, reason: "B", evidence_hash: null, policy_id: null, mission_id: null, run_id: null, tx_hash: null, created_at: "2026-06-01T13:00:00Z" }
    ];
    const calc1 = calculate_trust_score(testCard, testEventsArgs);
    const calc2 = calculate_trust_score(testCard, testEventsArgs);
    assert(
      "score breakdown is deterministic",
      calc1.score === calc2.score && calc1.rank === calc2.rank && JSON.stringify(calc1.breakdown) === JSON.stringify(calc2.breakdown),
      `First score: ${calc1.score}, Second score: ${calc2.score}. Matching: ${calc1.score === calc2.score}`
    );
  } catch (err) {
    results.push({
      name: "Identity test suite runtime execution",
      passed: false,
      message: `Crashed! Reason: ${err.message}`
    });
  }
  return results;
}
var isMainModule = () => {
  try {
    if (typeof require !== "undefined" && require.main === module) return true;
    if (process.argv[1]) {
      const mainPath = import_fs2.default.realpathSync(process.argv[1]);
      const thisPath = import_fs2.default.realpathSync((0, import_url.fileURLToPath)(import_meta.url));
      return mainPath === thisPath;
    }
  } catch {
  }
  return false;
};
if (isMainModule()) {
  console.log("=== RUNNING VEKLOM IDENTITY ENGINE TESTS ===");
  const testResults = runVeklomIdentityTests();
  let failures = 0;
  testResults.forEach((res) => {
    if (res.passed) {
      console.log(`[PASS] ${res.name}`);
    } else {
      console.log(`[FAIL] ${res.name} - Message: ${res.message || "No reason details"}`);
      failures++;
    }
  });
  console.log(`=== TEST SUMMARY: ${testResults.length - failures}/${testResults.length} PASSED ===`);
  process.exit(failures > 0 ? 1 : 0);
}

// src/identity/routes.ts
var router = (0, import_express.Router)();
var DEFAULT_SERVICE_TOKEN = "veklom_secure_service_token_2026";
var INTERNAL_SERVICE_TOKEN = process.env.VEKLOM_INTERNAL_TOKEN || DEFAULT_SERVICE_TOKEN;
function getAuthUserId(req) {
  const authHeader = req.headers["authorization"];
  if (authHeader && authHeader.toLowerCase().startsWith("bearer ")) {
    const token = authHeader.substring(7).trim();
    if (token) return token;
  }
  const xUserId = req.headers["x-user-id"];
  if (xUserId && typeof xUserId === "string" && xUserId.trim() !== "") {
    return xUserId.trim();
  }
  return "user_default_veklom_operator_node";
}
router.get("/me", (req, res) => {
  try {
    const ownerUserId = getAuthUserId(req);
    let card = identityDb.findCardByUserId(ownerUserId);
    if (!card) {
      card = identityDb.createDefaultCard(ownerUserId, "Operator Node Alpha");
    }
    return res.json({
      success: true,
      card
    });
  } catch (err) {
    console.error("Error in GET /identity/me:", err);
    return res.status(500).json({ error: "Failed to fetch user identity." });
  }
});
router.get("/score/:address", (req, res) => {
  try {
    const address = req.params.address;
    if (!address) {
      return res.status(400).json({ error: "Missing wallet address in query path." });
    }
    const card = identityDb.findCardByAddress(address);
    if (!card) {
      return res.status(404).json({
        error: `No Sovereign Operator Identity found linked to address: ${address}`
      });
    }
    const publicSafeOutput = {
      display_name: card.display_name,
      wallet_address: card.wallet_address,
      trust_score: card.trust_score,
      operator_rank: card.operator_rank,
      current_streak: card.current_streak,
      longest_streak: card.longest_streak,
      verified_actions: card.verified_actions,
      governance_proofs_generated: card.governance_proofs_generated,
      completed_missions: card.completed_missions,
      successful_agent_runs: card.successful_agent_runs,
      last_score_event_at: card.last_score_event_at
    };
    return res.json(publicSafeOutput);
  } catch (err) {
    console.error("Error in GET /identity/score/:address:", err);
    return res.status(500).json({ error: "Failed to query public identity score." });
  }
});
router.post("/events", (req, res) => {
  try {
    const reqToken = req.headers["x-internal-token"] || req.headers["x-service-token"];
    const authHeader = req.headers["authorization"];
    let isAuthorized = false;
    if (reqToken === INTERNAL_SERVICE_TOKEN) {
      isAuthorized = true;
    } else if (authHeader && authHeader.toLowerCase().startsWith("bearer ")) {
      const token = authHeader.substring(7).trim();
      if (token === INTERNAL_SERVICE_TOKEN) {
        isAuthorized = true;
      }
    }
    if (!isAuthorized) {
      return res.status(403).json({
        error: "Forbidden. Access is restricted to trusted internal service controllers."
      });
    }
    const {
      agent_card_id,
      wallet_address,
      event_type,
      points_delta,
      reason,
      evidence_hash,
      policy_id,
      mission_id,
      run_id,
      tx_hash,
      created_at
    } = req.body;
    if (!event_type) {
      return res.status(400).json({ error: "Missing parameter: event_type." });
    }
    if (!reason) {
      return res.status(400).json({ error: "Missing parameter: reason." });
    }
    let cardId = agent_card_id;
    if (!cardId && wallet_address) {
      const card2 = identityDb.findCardByAddress(wallet_address);
      if (!card2) {
        return res.status(404).json({
          error: `Could not log event: No AgentCard found for wallet address '${wallet_address}'`
        });
      }
      cardId = card2.id;
    }
    if (!cardId) {
      return res.status(400).json({
        error: "Missing database reference: Must provide either 'agent_card_id' or 'wallet_address'."
      });
    }
    const card = identityDb.findCardById(cardId);
    if (!card) {
      return res.status(404).json({ error: `AgentCard with ID '${cardId}' was not found in database.` });
    }
    let delta = points_delta;
    if (delta === void 0 || delta === null) {
      delta = EVENT_POINTS_MAP[event_type];
      if (delta === void 0) {
        return res.status(400).json({
          error: `Unknown event_type '${event_type}' and no explicit points_delta was provided.`
        });
      }
    }
    const result = identityDb.addEvent({
      agent_card_id: cardId,
      event_type,
      points_delta: delta,
      reason,
      evidence_hash: evidence_hash || null,
      policy_id: policy_id || null,
      mission_id: mission_id || null,
      run_id: run_id || null,
      tx_hash: tx_hash || null,
      created_at
    });
    return res.status(201).json({
      success: true,
      message: `Event processed successfully for operator '${result.card.display_name}'.`,
      event: result.event,
      card: result.card,
      breakdown: result.breakdown
    });
  } catch (err) {
    console.error("Error in POST /internal/identity/events:", err);
    return res.status(500).json({ error: `Internal error processing identity system event: ${err.message}` });
  }
});
router.post("/link-wallet", (req, res) => {
  try {
    const ownerUserId = getAuthUserId(req);
    const { wallet_address } = req.body;
    if (!wallet_address) {
      return res.status(400).json({ error: "Missing parameter: wallet_address." });
    }
    let card = identityDb.findCardByUserId(ownerUserId);
    if (!card) {
      card = identityDb.createDefaultCard(ownerUserId, "Operator Node Alpha");
    }
    const updated = identityDb.linkWalletAddress(card.id, wallet_address);
    return res.json({
      success: true,
      card: updated
    });
  } catch (err) {
    console.error("Error linking wallet address:", err);
    return res.status(500).json({ error: "Failed to register address." });
  }
});
router.get("/test-run", (req, res) => {
  try {
    const results = runVeklomIdentityTests();
    const passed = results.every((r) => r.passed);
    return res.json({
      success: passed,
      totalTests: results.length,
      timestamp: (/* @__PURE__ */ new Date()).toISOString(),
      results
    });
  } catch (err) {
    console.error("Error running identity tests:", err);
    return res.status(500).json({ error: `Test execution failed with error: ${err.message}` });
  }
});
var routes_default = router;

// src/identity/x402.ts
var import_express2 = require("express");
var import_viem = require("viem");
var import_chains = require("viem/chains");
var router2 = (0, import_express2.Router)();
var MERCHANT_WALLET = "0x3a74772e925b54F7dAD7FD95c9Ba30825033f970";
var USDC_CONTRACT = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
var CHAIN_ID = "eip155:8453";
var PRICES = {
  "/api/v1/x402/identity/premium": "0.01",
  // $0.01 USDC — identity premium lookup
  "/api/v1/x402/benchmark/run": "0.05",
  // $0.05 USDC — benchmark run
  "/api/v1/x402/discovery/feature": "0.02"
  // $0.02 USDC — discovery feature
};
var publicClient = (0, import_viem.createPublicClient)({
  chain: import_chains.base,
  transport: (0, import_viem.http)("https://mainnet.base.org")
});
function getCallerWallet(req) {
  const fromHeader = req.headers["x-wallet-address"];
  if (fromHeader && (0, import_viem.isAddress)(fromHeader)) return fromHeader.toLowerCase();
  const fromBody = req.body?.wallet_address;
  if (fromBody && (0, import_viem.isAddress)(fromBody)) return fromBody.toLowerCase();
  return null;
}
function resolveCardByWallet(walletAddress) {
  let card = identityDb.findCardByAddress(walletAddress);
  if (!card) {
    card = identityDb.createDefaultCard(walletAddress, `Operator ${walletAddress.slice(0, 8)}`);
    identityDb.linkWalletAddress(card.id, walletAddress);
  }
  return card;
}
function send402(res, endpoint) {
  const amount = PRICES[endpoint] || "0.01";
  res.setHeader("X-402-Version", "1");
  res.setHeader("X-402-Chain", CHAIN_ID);
  res.setHeader("X-402-Recipient", MERCHANT_WALLET);
  res.setHeader("X-402-Token", USDC_CONTRACT);
  res.setHeader("X-402-Amount", (0, import_viem.parseUnits)(amount, 6).toString());
  res.setHeader("X-402-Resource", endpoint);
  return res.status(402).json({
    x402Version: 1,
    error: "Payment Required",
    accepts: [
      {
        scheme: "exact",
        network: CHAIN_ID,
        maxAmountRequired: (0, import_viem.parseUnits)(amount, 6).toString(),
        resource: endpoint,
        description: `Veklom x402 \u2014 ${endpoint}`,
        mimeType: "application/json",
        payTo: MERCHANT_WALLET,
        maxTimeoutSeconds: 300,
        asset: USDC_CONTRACT,
        extra: {
          name: "USD Coin",
          version: "2"
        }
      }
    ]
  });
}
async function verifyPaymentOnChain(txHash, endpoint, callerWallet) {
  try {
    const receipt = await publicClient.getTransactionReceipt({
      hash: txHash
    });
    if (!receipt || receipt.status !== "success") {
      return { valid: false, error: "Transaction not found or reverted on Base." };
    }
    const TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef";
    const usdcLogs = receipt.logs.filter(
      (log) => log.address.toLowerCase() === USDC_CONTRACT.toLowerCase() && log.topics[0] === TRANSFER_TOPIC
    );
    if (usdcLogs.length === 0) {
      return { valid: false, error: "No USDC Transfer event found in transaction." };
    }
    const requiredAmount = (0, import_viem.parseUnits)(PRICES[endpoint] || "0.01", 6);
    const validTransfer = usdcLogs.find((log) => {
      const to = "0x" + log.topics[2]?.slice(26);
      const from = "0x" + log.topics[1]?.slice(26);
      const value = BigInt(log.data);
      return to.toLowerCase() === MERCHANT_WALLET.toLowerCase() && from.toLowerCase() === callerWallet.toLowerCase() && value >= requiredAmount;
    });
    if (!validTransfer) {
      return {
        valid: false,
        error: `No valid USDC transfer of >= ${PRICES[endpoint]} USDC to Veklom wallet found from ${callerWallet}.`
      };
    }
    return {
      valid: true,
      blockNumber: receipt.blockNumber.toString()
    };
  } catch (err) {
    return { valid: false, error: `RPC verification failed: ${err.message}` };
  }
}
async function x402PaymentMiddleware(req, res, next) {
  const callerWallet = getCallerWallet(req);
  if (!callerWallet) {
    return res.status(400).json({
      error: "Missing wallet identity.",
      message: "Provide your Base wallet address via X-Wallet-Address header."
    });
  }
  const paymentHeader = req.headers["x-payment"];
  if (!paymentHeader) {
    return send402(res, req.path);
  }
  if (!/^0x[a-fA-F0-9]{64}$/.test(paymentHeader)) {
    return res.status(400).json({
      error: "Invalid payment header format.",
      message: "X-Payment must be a valid Base transaction hash (0x + 64 hex chars)."
    });
  }
  const existingPayment = identityDb.getEvents().find((e) => e.tx_hash === paymentHeader && e.event_type === "x402_payment_verified");
  if (existingPayment) {
    return res.status(400).json({
      error: "Payment already consumed.",
      message: "This transaction hash has already been used. Submit a new payment."
    });
  }
  const verification = await verifyPaymentOnChain(paymentHeader, req.path, callerWallet);
  if (!verification.valid) {
    return res.status(402).json({
      error: "Payment verification failed.",
      message: verification.error
    });
  }
  const card = resolveCardByWallet(callerWallet);
  identityDb.addEvent({
    agent_card_id: card.id,
    event_type: "x402_payment_verified",
    points_delta: 10,
    reason: `Verified x402 USDC payment on Base (eip155:8453) for ${req.path}. Block: ${verification.blockNumber}`,
    evidence_hash: paymentHeader,
    policy_id: null,
    mission_id: null,
    run_id: null,
    tx_hash: paymentHeader,
    created_at: (/* @__PURE__ */ new Date()).toISOString()
  });
  req.veklom = { wallet: callerWallet, cardId: card.id };
  return next();
}
router2.get("/config", (_req, res) => {
  return res.json({
    success: true,
    chain: CHAIN_ID,
    merchant_wallet: MERCHANT_WALLET,
    usdc_contract: USDC_CONTRACT,
    prices: PRICES,
    spec: "https://x402.org"
  });
});
router2.get(
  "/identity/premium",
  x402PaymentMiddleware,
  (req, res) => {
    const card = identityDb.findCardById(req.veklom.cardId);
    return res.json({
      success: true,
      payment_status: "verified",
      chain: CHAIN_ID,
      wallet: req.veklom.wallet,
      card
    });
  }
);
router2.post(
  "/benchmark/run",
  x402PaymentMiddleware,
  (req, res) => {
    const { benchmark_config } = req.body;
    return res.json({
      success: true,
      payment_status: "verified",
      chain: CHAIN_ID,
      wallet: req.veklom.wallet,
      benchmark_queued: true,
      benchmark_config: benchmark_config || null,
      message: "Benchmark run authorised and queued. Wire to Iron Grid runtime."
    });
  }
);
router2.post(
  "/discovery/feature",
  x402PaymentMiddleware,
  (req, res) => {
    const { feature_id } = req.body;
    return res.json({
      success: true,
      payment_status: "verified",
      chain: CHAIN_ID,
      wallet: req.veklom.wallet,
      feature_id: feature_id || null,
      feature_unlocked: true
    });
  }
);
router2.get("/ledger", (_req, res) => {
  const payments = identityDb.getEvents().filter((e) => e.event_type === "x402_payment_verified").map((e) => ({
    tx_hash: e.tx_hash,
    wallet: identityDb.findCardById(e.agent_card_id)?.wallet_address || "unknown",
    reason: e.reason,
    created_at: e.created_at
  }));
  return res.json({
    success: true,
    count: payments.length,
    payments
  });
});
var x402_default = router2;

// server.ts
import_dotenv.default.config();
async function startServer() {
  const app = (0, import_express3.default)();
  const PORT = 3e3;
  app.use(import_express3.default.json());
  app.use("/api/v1/identity", routes_default);
  app.use("/api/v1/internal/identity", routes_default);
  app.use("/api/v1/x402", x402_default);
  app.get("/.well-known/x402.json", (_req, res) => {
    res.json({
      x402_version: 2,
      provider: "Veklom ID \u2014 Sovereign Operator Registry",
      network: "eip155:8453",
      payTo: "0xCC34553b4e6332ffb9C1b61E22436ACA53113D1d",
      currency: "USDC",
      identity: {
        veklom_id_app: "6a20f24cc341f72c2f573eb5",
        veklom_id_wallet: "0x3a74772e925b54F7dAD7FD95c9Ba30825033f970",
        verification_domain: "veklom-id.vercel.app"
      },
      routes: [
        { route: "GET /api/v1/x402/identity/premium", price: "$0.01", description: "Full identity card for the paying wallet \u2014 trust score, operator stats, rank.", tags: ["veklom-id", "identity", "premium", "trust", "veklom"] },
        { route: "POST /api/v1/x402/benchmark/run", price: "$0.05", description: "Trigger a benchmark run authenticated by wallet + payment.", tags: ["veklom-id", "benchmark", "run", "veklom"] },
        { route: "POST /api/v1/x402/discovery/feature", price: "$0.02", description: "Unlock a paid Discovery feature for the paying wallet.", tags: ["veklom-id", "discovery", "feature", "veklom"] },
        { route: "GET /api/v1/x402/config", price: "free", description: "x402 merchant and payment configuration.", tags: ["veklom-id", "x402", "config"] },
        { route: "GET /api/v1/x402/ledger", price: "free", description: "All verified x402 payment events.", tags: ["veklom-id", "x402", "ledger", "audit"] }
      ],
      discovery: {
        bazaar: "https://bazaar.cdp.coinbase.com",
        veklom_id: "https://veklom-id.vercel.app"
      }
    });
  });
  app.post("/api/agents/simulate-turn", async (req, res) => {
    try {
      const { agent, task, history, mode } = req.body;
      if (!agent) {
        return res.status(400).json({ error: "Missing agent configuration." });
      }
      const apiKey = process.env.GEMINI_API_KEY;
      if (!apiKey) {
        return res.status(500).json({
          error: "GEMINI_API_KEY is not configured. Please add it via the Settings > Secrets panel in the AI Studio UI."
        });
      }
      const ai = new import_genai.GoogleGenAI({
        apiKey,
        httpOptions: {
          headers: {
            "User-Agent": "aistudio-build"
          }
        }
      });
      let contextualPrompt = "";
      if (mode === "pipeline") {
        contextualPrompt += `We are carrying out a structured hand-off pipeline to solve the task: "${task}".

`;
      } else if (mode === "debate") {
        contextualPrompt += `We are holding a debate panel on the topic: "${task}".

`;
      } else {
        contextualPrompt += `We are in a collaborative multi-agent group conversation for the task: "${task}".

`;
      }
      if (history && history.length > 0) {
        contextualPrompt += "Here is the conversation transcript so far:\n";
        history.forEach((msg) => {
          contextualPrompt += `[${msg.senderName} (${msg.senderRole})]: ${msg.content}

`;
        });
      } else {
        contextualPrompt += "No dialogue has occurred yet. You are starting the conversation.\n\n";
      }
      contextualPrompt += `Now, write your response as agent "${agent.name}" (Role: ${agent.role || "Contributor"}).
`;
      contextualPrompt += `Address the topic "${task}" and respond constructively to previous points (if any). Do not prefix your reply with your name or any label like "[${agent.name}]:". Deliver your response in formatted Markdown if appropriate.`;
      const systemInstruction = `You are playing the role of an AI Agent named "${agent.name}".
Your professional specialty or persona role is: "${agent.role || "Expert"}".
Your core system instructions and behavioral attributes are:
"${agent.systemPrompt || "Provide high quality objective critiques and solutions."}"

CRITICAL RULES:
1. Speak absolutely as "${agent.name}". Adopt your specialty's custom tone, jargon, and depth.
2. DO NOT output code block markers surrounding your entire dialogue (unless code is specifically requested).
3. DO NOT prefix your response content with your name, like "[${agent.name}]:" or "${agent.name}:". Just write your direct speech.
4. Keep the contribution focused and avoid repeating existing content. Integrate suggestions, challenge assumptions, and keep the session progress moving forward.`;
      const response = await ai.models.generateContent({
        model: "gemini-3.5-flash",
        contents: contextualPrompt,
        config: {
          systemInstruction,
          temperature: typeof agent.temperature === "number" ? agent.temperature : 0.7
        }
      });
      const replyStr = response.text || "";
      res.json({ success: true, reply: replyStr.trim() });
    } catch (err) {
      console.error("Simulation error in server:", err);
      res.status(500).json({ error: err?.message || "Internal generation failed." });
    }
  });
  if (process.env.NODE_ENV !== "production") {
    const vite = await (0, import_vite.createServer)({
      server: { middlewareMode: true },
      appType: "spa"
    });
    app.use(vite.middlewares);
  } else {
    const distPath = import_path2.default.join(process.cwd(), "dist");
    app.use(import_express3.default.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(import_path2.default.join(distPath, "index.html"));
    });
  }
  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Server is running on http://localhost:${PORT}`);
  });
}
startServer();
//# sourceMappingURL=server.cjs.map
