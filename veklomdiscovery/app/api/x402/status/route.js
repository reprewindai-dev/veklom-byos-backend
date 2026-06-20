import { NextResponse } from "next/server";
import {
  X402_NETWORK,
  X402_PRICE,
  X402_RECIPIENT,
  missionClaimRouteConfig,
  raceLaunchRouteConfig,
} from "../../../../server/x402Server";

export const dynamic = "force-dynamic";

export async function GET() {
  return NextResponse.json({
    service: "veklomdiscovery",
    commit: process.env.VERCEL_GIT_COMMIT_SHA || "local",
    recipient: X402_RECIPIENT,
    network: X402_NETWORK,
    price: X402_PRICE,
    asset: "0x833589fCD6eDb6E08f4c7C32D4f71b3228cdeC9F",
    builderCode: process.env.NEXT_PUBLIC_BASE_BUILDER_CODE || null,
    routes: {
      missionClaim: missionClaimRouteConfig,
      raceLaunch: raceLaunchRouteConfig,
    },
  }, {
    headers: {
      "Cache-Control": "no-store",
    },
  });
}
