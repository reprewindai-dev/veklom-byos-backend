# Veklom Discovery Integration Guide

## Objective

Veklom Discovery is a governed AI game platform built around X402 micropayments, ACP governance gates, Base MCP wallet execution, and onchain attribution. The configured recipient identity is `veklom.base.eth` / `0x3a74772e925b54F7dAD7FD95c9Ba30825033f970`.

Veklom.com and Veklom Discovery share the production x402 payment wallet:

- Shared Veklom.com/Discovery wallet: `0x3a74772e925b54F7dAD7FD95c9Ba30825033f970`

Veklom ID is registered separately for Base App identity metadata:

- Base App ID: `6a20f24cc341f72c2f573eb5`
- Veklom ID wallet: `0x3a74772e925b54F7dAD7FD95c9Ba30825033f970`

This repository is deployment-ready. It does not assume the web app, backend, or contracts are already deployed unless their live URLs and deployed contract addresses are configured.

## System Components

| Component | Location | Purpose |
| --- | --- | --- |
| Next.js app | `app/`, `components/` | Veklom Discovery web UI and Base attribution config |
| Base MCP plugin | `docs/veklom-base-mcp-plugin.md` | Agent instructions for wallet detection, X402 payments, and governed actions |
| FastAPI backend | `api/veklom_backend.py` | User profile, missions, X402 402 middleware, races, governance proofs |
| Contracts | `contracts/VeklomContracts.sol` | Registry, payment vault, reputation ledger, governance gate |
| Foundry deploy script | `script/VeklomDeploy.s.sol` | Contract deployment asset for Base and expansion chains |

## Execution Flow

### Mission Claim

1. Base MCP calls `get_wallets` and confirms the user's address.
2. Client reads missions from `{VEKLOM_API_BASE}/api/missions/daily?address={address}`.
3. Client prepares a `0.01 USDC` Base transfer to `0x3a74772e925b54F7dAD7FD95c9Ba30825033f970`.
4. Base MCP executes `send_calls` and appends the ERC-8021 Builder Code suffix when configured.
5. User approves in Base Account.
6. Client posts `/api/missions/claim` with `X-Payment-Proof` and the confirmed transaction hash.
7. Backend credits mission rewards and increases trust score.

### Governed Race

1. Base MCP detects wallet address.
2. Client reads the user's agent from `/api/user/{address}`.
3. Client verifies action gates with `/api/governance/verify/{agentId}?action=race&amount=0.1&user_address={address}`.
4. If gates pass, client executes required X402 payment.
5. Client posts `/api/races/launch` with the governance proof and payment proof.
6. Backend records race result and agent earnings.

## Interfaces / APIs

Default hosted API base:

```bash
https://veklomdiscovery.vercel.app
```

Local API base:

```bash
http://localhost:8000
```

Core endpoints:

```text
GET  /health
GET  /api/user/{address}
GET  /api/missions/daily?address={address}
GET  /api/agent/{agent_id}
GET  /api/governance/verify/{agent_id}?action=race&amount=0.1&user_address={address}
GET  /api/prepare/race-launch?user_address={address}&agent_id={agent_id}&policy=balanced
POST /api/missions/claim?user_address={address}&mission_id={mission_id}&tx_hash={tx_hash}
POST /api/races/launch?user_address={address}&agent_id={agent_id}&governance_proof={proofHash}
POST /api/x402/verify
POST /api/x402/batch-settle
POST /api/proofs/store
```

Protected endpoints require:

```http
X-Payment-Proof: veklom:x402:<mission-or-action-id>:<txHash>
```

## State & Data Handling

Current backend state is in-memory and suitable for local validation only. Production deployment needs persistent storage before live financial use:

- PostgreSQL for users, missions, agents, payments, races, proofs, and settlement batches
- IPFS provider for immutable proof payloads
- Onchain contract addresses after deployment
- Monitoring for X402 payment success rate, governance gate failure rate, mission completion rate, and race payout distribution

## Base Builder Code Attribution

Set this environment variable after registering the app on Base.dev:

```bash
NEXT_PUBLIC_BASE_BUILDER_CODE=bc_j7x422o5
```

The frontend uses `ox/erc8021` to generate the Builder Code data suffix. Supported clients can append this suffix to transaction calldata through `dataSuffix`.

## Environment

```bash
NEXT_PUBLIC_BASE_BUILDER_CODE=bc_your_builder_code
NEXT_PUBLIC_BASE_APP_ID=6a20f24cc341f72c2f573eb5
NEXT_PUBLIC_VEKLOM_API_URL=
NEXT_PUBLIC_VEKLOM_BACKEND_SERVICE=veklomdiscovery
NEXT_PUBLIC_VEKLOM_ADDRESS=0x3a74772e925b54F7dAD7FD95c9Ba30825033f970
NEXT_PUBLIC_VEKLOM_COM_ADDRESS=0x3a74772e925b54F7dAD7FD95c9Ba30825033f970
NEXT_PUBLIC_VEKLOM_ID_ADDRESS=0x3a74772e925b54F7dAD7FD95c9Ba30825033f970

VEKLOM_ADDRESS=0x3a74772e925b54F7dAD7FD95c9Ba30825033f970
VEKLOM_COM_ADDRESS=0x3a74772e925b54F7dAD7FD95c9Ba30825033f970
VEKLOM_ENS=veklom.base.eth
VEKLOM_ID_API_KEY_ID=
VEKLOM_ID_API_KEY_SECRET=
VEKLOM_COM_BASE_APP_API_KEY_ID=
VEKLOM_COM_BASE_APP_API_KEY_SECRET=
ALLOWED_ORIGINS=https://veklom-id.vercel.app,http://localhost:3000

BASE_MAINNET_RPC=https://mainnet.base.org
BASE_SEPOLIA_RPC=https://sepolia.base.org
BASE_USDC=0x833589fCD6eDb6E08f4c7C32D4f71b3228cdeC9F

PRIVATE_KEY=
ETHERSCAN_API_KEY=
```

## Failure & Degradation Rules

- Do not claim USDC was paid unless Base MCP returns a confirmed transaction hash.
- Do not claim contracts are deployed until deployed addresses are configured.
- If the backend is unavailable, disable live claims and race settlement.
- If governance verification fails, block the race and surface the failed gate reason.
- If `NEXT_PUBLIC_BASE_BUILDER_CODE` is missing, continue payments without Builder Code attribution and report attribution as inactive.

## Deployment Notes

### Vercel Web App

```bash
npm install
npm run build
```

Deploy this repo to Vercel as the Veklom Discovery web app. Leave `NEXT_PUBLIC_VEKLOM_API_URL` blank so the frontend uses the same-origin Vercel API routes.

### FastAPI Backend

```bash
pip install -r requirements.txt
uvicorn api.veklom_backend:app --host 0.0.0.0 --port 8000
```

### Contracts

Deploy contracts only from a funded deployer wallet:

```bash
forge script script/VeklomDeploy.s.sol:VeklomDeploy \
  --rpc-url $BASE_SEPOLIA_RPC \
  --account deployer \
  --broadcast --verify
```

After deployment, add contract addresses to app and backend configuration.

## Constraints

- Payment recipient for this Discovery app is `0x3a74772e925b54F7dAD7FD95c9Ba30825033f970`.
- Live financial claims require confirmed onchain transactions.
- Base MCP onboarding is mandatory before Veklom actions.
- Veklom Discovery and Veklom ID must remain separate products with separate deployment targets and wallet configuration.
