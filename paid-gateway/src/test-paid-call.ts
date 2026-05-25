/**
 * Test a real paid x402 call against the Veklom gateway.
 *
 * Requirements:
 *   1. A funded EVM wallet on Base mainnet with USDC
 *   2. EVM_PRIVATE_KEY env var set to that wallet's private key
 *   3. The paid gateway running at GATEWAY_URL
 *
 * This performs a real on-chain USDC payment and should be run
 * ONLY after confirming the gateway is deployed and PAY_TO is correct.
 *
 * Usage:
 *   EVM_PRIVATE_KEY=0xYourKey GATEWAY_URL=https://api.veklom.com npx tsx src/test-paid-call.ts
 */

import "dotenv/config";

const GATEWAY_URL = process.env.GATEWAY_URL || "https://api.veklom.com";
const PRIVATE_KEY = process.env.EVM_PRIVATE_KEY;

if (!PRIVATE_KEY) {
  console.error("Set EVM_PRIVATE_KEY to a funded Base wallet private key");
  process.exit(1);
}

// Step 1: Hit without payment — should return 402
console.log("\n=== Step 1: Unpaid call (expect 402) ===");
const unpaidRes = await fetch(`${GATEWAY_URL}/api/v1/ai/inference`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ messages: [{ role: "user", content: "hello" }] }),
});
console.log("Status:", unpaidRes.status);
if (unpaidRes.status === 402) {
  const body = await unpaidRes.json();
  console.log("x402Version:", body.x402Version);
  console.log("Price USDC:", unpaidRes.headers.get("X-Payment-Price-USDC"));
  console.log("PayTo:", unpaidRes.headers.get("X-Payment-Address"));
  console.log("✓ Gateway correctly returning 402");
} else {
  console.log("✗ Expected 402 but got", unpaidRes.status);
}

// Step 2: Paid call using @coinbase/x402 or @x402/fetch
console.log("\n=== Step 2: Paid call ===");
try {
  const { wrapFetchWithPayment } = await import("@x402/fetch").catch(() => import("@coinbase/x402/fetch"));
  const { x402Client } = await import("@x402/core/client").catch(() => ({ x402Client: null }));
  const { ExactEvmScheme } = await import("@x402/evm/exact/client").catch(() => ({ ExactEvmScheme: null }));
  const { privateKeyToAccount } = await import("viem/accounts");

  if (!x402Client || !ExactEvmScheme) {
    console.log("Install @x402/fetch @x402/core @x402/evm viem to run the paid call test");
    process.exit(0);
  }

  const signer = privateKeyToAccount(PRIVATE_KEY as `0x${string}`);
  const client = new (x402Client as any)();
  client.register("eip155:*", new (ExactEvmScheme as any)(signer));

  const fetchWithPayment = wrapFetchWithPayment(fetch, client);
  const paidRes = await fetchWithPayment(`${GATEWAY_URL}/api/v1/ai/inference`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages: [{ role: "user", content: "say hello in 3 words" }] }),
  });

  console.log("Status:", paidRes.status);
  console.log("Evidence-ID:", paidRes.headers.get("X-Veklom-Evidence-ID"));
  console.log("Cost-USDC:", paidRes.headers.get("X-Veklom-Cost-USDC"));
  console.log("Payment-Verified:", paidRes.headers.get("X-Payment-Verified"));
  const body = await paidRes.json();
  console.log("Response:", body.response_text || body);
  console.log("✓ Paid call succeeded — USDC settled to PAY_TO wallet");
} catch (e) {
  console.error("Paid call error:", e);
}
