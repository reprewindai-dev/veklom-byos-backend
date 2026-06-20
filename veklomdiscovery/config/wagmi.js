import { http, createConfig, createStorage, cookieStorage } from "wagmi";
import { base, baseSepolia } from "wagmi/chains";
import { baseAccount, injected } from "wagmi/connectors";

const baseRpc = process.env.NEXT_PUBLIC_BASE_MAINNET_RPC || "https://mainnet.base.org";
const baseSepoliaRpc = process.env.NEXT_PUBLIC_BASE_SEPOLIA_RPC || "https://sepolia.base.org";

export const wagmiConfig = createConfig({
  chains: [base, baseSepolia],
  connectors: [
    injected(),
    baseAccount({
      appName: "Veklom Discovery",
    }),
  ],
  storage: createStorage({ storage: cookieStorage }),
  ssr: true,
  transports: {
    [base.id]: http(baseRpc),
    [baseSepolia.id]: http(baseSepoliaRpc),
  },
});
