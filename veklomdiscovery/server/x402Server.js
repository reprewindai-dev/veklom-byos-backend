import { HTTPFacilitatorClient, x402ResourceServer } from "@x402/core/server";
import { ExactEvmScheme } from "@x402/evm/exact/server";
import { createFacilitatorConfig } from "@coinbase/x402";

export const X402_RECIPIENT =
  process.env.VEKLOM_ADDRESS || "0xCC34553b4e6332ffb9C1b61E22436ACA53113D1d";

const hasCdpCredentials = Boolean(process.env.CDP_API_KEY_ID && process.env.CDP_API_KEY_SECRET);

export const X402_NETWORK =
  process.env.X402_NETWORK || (hasCdpCredentials ? "eip155:8453" : "eip155:84532");
export const X402_PRICE = process.env.X402_PRICE || "$0.01";
const facilitatorConfig = hasCdpCredentials
  ? createFacilitatorConfig(process.env.CDP_API_KEY_ID, process.env.CDP_API_KEY_SECRET)
  : { url: "https://x402.org/facilitator" };

const facilitatorClient = new HTTPFacilitatorClient(facilitatorConfig);

export const x402Server = new x402ResourceServer(facilitatorClient).register(
  "eip155:*",
  new ExactEvmScheme()
);

export const missionClaimRouteConfig = {
  accepts: {
    scheme: "exact",
    price: X402_PRICE,
    network: X402_NETWORK,
    payTo: X402_RECIPIENT,
  },
  description: "Claim a Veklom Discovery daily mission reward",
  mimeType: "application/json",
};

export const raceLaunchRouteConfig = {
  accepts: {
    scheme: "exact",
    price: X402_PRICE,
    network: X402_NETWORK,
    payTo: X402_RECIPIENT,
  },
  description: "Launch a governed Veklom Discovery agent race",
  mimeType: "application/json",
};
