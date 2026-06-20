import { NextResponse } from "next/server";
import { withX402 } from "@x402/next";
import { missionClaimRouteConfig, x402Server } from "../../../../server/x402Server";

export const dynamic = "force-dynamic";

async function handler(request) {
  const { searchParams } = new URL(request.url);

  return NextResponse.json({
    status: "success",
    mission: searchParams.get("mission_id") || "mission_1",
    reward: { usdc: 0.5, xp: 100 },
    payment: {
      verified: true,
      settled: true,
      txHash: searchParams.get("tx_hash"),
    },
  }, {
    headers: {
      "Cache-Control": "no-store",
    },
  });
}

export const POST = withX402(handler, missionClaimRouteConfig, x402Server);
