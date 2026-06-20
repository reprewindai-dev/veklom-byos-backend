# Veklom Discovery

Production Next.js app for Veklom Discovery, with Base Builder Code attribution, x402 payment-gated mission/race APIs, ACP governance, smart contracts, and same-origin Vercel API routes.

## Revenue Outcome

Veklom Discovery monetizes AI agent game actions through x402-gated mission claims, governed race launches, USDC settlement, and Base Builder Code attribution for Base rewards analytics.

## Run

```bash
npm install
npm run dev
```

Backend:

```bash
pip install -r requirements.txt
uvicorn api.veklom_backend:app --host 0.0.0.0 --port 8000
```

For hosted deployment on Vercel, leave `NEXT_PUBLIC_VEKLOM_API_URL` blank so the frontend uses the same-origin API routes in this app.

## Deployment Status

This repository is ready to deploy to Vercel as the Veklom Discovery web app. The configured recipient identity is `veklom.base.eth` / `0xCC34553b4e6332ffb9C1b61E22436ACA53113D1d`.

The Solidity contracts in `contracts/` are deployment assets. They are not assumed to be live until Foundry deployment completes and the resulting contract addresses are added to environment configuration.

## Visitor Wallet Behavior

The public page does not connect visitors to the Veklom recipient wallet. `veklom.base.eth` is the payment recipient and attribution identity for the app. A visitor must approve their own wallet action through Base MCP or a supported wallet flow before any USDC payment or onchain action can happen.

## Base Builder Code

Set `NEXT_PUBLIC_BASE_BUILDER_CODE=bc_j7x422o5` in Vercel after registering the app on Base.dev. The app generates the ERC-8021 data suffix with `ox/erc8021` and applies it through the shared onchain config.

## Base App Standard Web Setup

The frontend follows Base's standard web app guidance for the Base App: wagmi + viem for wallet state, `@base-org/account` for Base Account connection, React Query for wagmi state, and SIWE for user authentication before paid actions.

Paid x402 mission and race actions are disabled until a visitor connects a wallet and signs in with Ethereum. The Veklom recipient wallet remains `veklom.base.eth`; the connected visitor wallet is passed as the paying user identity to same-origin API routes.

Base App registration for Veklom ID:

```text
NEXT_PUBLIC_BASE_APP_ID=6a20f24cc341f72c2f573eb5
NEXT_PUBLIC_VEKLOM_ID_ADDRESS=0x3a74772e925b54F7dAD7FD95c9Ba30825033f970
```

Veklom Discovery/payapi x402 payment routing remains:

```text
NEXT_PUBLIC_VEKLOM_ADDRESS=0xCC34553b4e6332ffb9C1b61E22436ACA53113D1d
NEXT_PUBLIC_VEKLOM_COM_ADDRESS=0xCC34553b4e6332ffb9C1b61E22436ACA53113D1d
VEKLOM_ADDRESS=0xCC34553b4e6332ffb9C1b61E22436ACA53113D1d
VEKLOM_COM_ADDRESS=0xCC34553b4e6332ffb9C1b61E22436ACA53113D1d
```

API credentials for Veklom ID and the veklom.com Base App must stay server-side. Store them only in the deployment provider environment, never in git:

```text
VEKLOM_ID_API_KEY_ID=
VEKLOM_ID_API_KEY_SECRET=
VEKLOM_COM_BASE_APP_API_KEY_ID=
VEKLOM_COM_BASE_APP_API_KEY_SECRET=
```

## x402 Payments

Paid routes use exact-price x402 on Base mainnet:

```bash
X402_PRICE=$0.01
X402_NETWORK=eip155:8453
CDP_API_KEY_ID=
CDP_API_KEY_SECRET=
NEXT_PUBLIC_BASE_APP_ID=6a20f24cc341f72c2f573eb5
NEXT_PUBLIC_VEKLOM_ADDRESS=0xCC34553b4e6332ffb9C1b61E22436ACA53113D1d
NEXT_PUBLIC_VEKLOM_COM_ADDRESS=0xCC34553b4e6332ffb9C1b61E22436ACA53113D1d
NEXT_PUBLIC_VEKLOM_ID_ADDRESS=0x3a74772e925b54F7dAD7FD95c9Ba30825033f970
VEKLOM_ADDRESS=0xCC34553b4e6332ffb9C1b61E22436ACA53113D1d
VEKLOM_COM_ADDRESS=0xCC34553b4e6332ffb9C1b61E22436ACA53113D1d
VEKLOM_ID_API_KEY_ID=
VEKLOM_ID_API_KEY_SECRET=
VEKLOM_COM_BASE_APP_API_KEY_ID=
VEKLOM_COM_BASE_APP_API_KEY_SECRET=
```

Mission claim and race launch responses are returned only after x402 verifies and settles payment through the configured facilitator.

Without `CDP_API_KEY_ID` and `CDP_API_KEY_SECRET`, local development falls back to the public x402.org testnet facilitator and Base Sepolia. Production Vercel must have CDP keys set for real Base mainnet payments.

## Base App Notifications

Notifications are delivered only inside the Base App to users who pinned Veklom Discovery and enabled notifications. The Base Dashboard API key stays server-side; callers must also pass `VEKLOM_ADMIN_API_KEY` as `x-admin-key` or `Authorization: Bearer`.

```bash
BASE_APP_URL=https://veklomdiscovery.vercel.app
BASE_DASHBOARD_API_KEY=
VEKLOM_ADMIN_API_KEY=
```

Server routes:

```text
GET  /api/base-notifications/users?notification_enabled=true&limit=500
POST /api/base-notifications/status
POST /api/base-notifications/send
```

Base rate limit is 20 notification API requests per minute per IP. Batch sends can include up to 1,000 wallet addresses per request, and Base deduplicates identical notifications within 24 hours.

Canonical docs used:

- https://docs.base.org/llms.txt
- https://docs.base.org/apps/builder-codes/app-developers
- https://docs.base.org/apps/growth/rewards
- https://docs.base.org/apps/technical-guides/base-notifications
