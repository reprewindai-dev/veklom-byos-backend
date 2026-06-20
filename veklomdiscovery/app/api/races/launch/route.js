import { NextResponse } from "next/server";
import { withX402 } from "@x402/next";
import { raceLaunchRouteConfig, x402Server } from "../../../../server/x402Server";

export const dynamic = "force-dynamic";

async function handler(request) {
  const { searchParams } = new URL(request.url);

  return NextResponse.json({
    status: "success",
    race: {
      id: `race_${Date.now()}`,
      agentId: searchParams.get("agent_id"),
      result: "settled",
      governanceProof: searchParams.get("governance_proof"),
    },
  }, {
    headers: {
      "Cache-Control": "no-store",
    },
  });
}

export const POST = withX402(handler, raceLaunchRouteConfig, x402Server);
