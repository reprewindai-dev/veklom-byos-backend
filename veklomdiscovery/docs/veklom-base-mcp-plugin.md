# Veklom Discovery Plugin for Base MCP

## Required Onboarding

Before calling any Veklom endpoint, complete the Base MCP onboarding flow:

1. Call `get_wallets` to detect the user's wallet.
2. Present wallet status and payment disclaimer.
3. Use the detected wallet address for every Veklom action.

The user's wallet address is required for mission claims, race launches, policy updates, and account reads.

## Product

Veklom Discovery is a governed AI game platform with autonomous agents, X402 payment rails, and decentralized reputation. Users can access missions, race agents, claim USDC drops, and verify actions through governance gates.

Configured identity:

- ENS: `veklom.base.eth`
- Recipient: `0x3a74772e925b54F7dAD7FD95c9Ba30825033f970`
- Backend service: `veklomdiscovery`
- Default API base: `https://veklomdiscovery.vercel.app`
- Supported chains: Base mainnet `8453`, Base Sepolia `84532`, zkSync Era `324`, Unichain `130`, Monad `10143`

## Read Endpoints

Use `VEKLOM_API_BASE` when configured. Otherwise use `https://veklomdiscovery.vercel.app`.

### Get User Profile

`GET {VEKLOM_API_BASE}/api/user/{address}`

Response:

```json
{
  "address": "0x...",
  "trustScore": 500,
  "level": 1,
  "completedMissions": 0,
  "totalEarned": 0,
  "agent": {
    "id": "agent_0x...",
    "name": "Genesis",
    "level": 1,
    "policy": "balanced",
    "trustScore": 500
  }
}
```

### Get Daily Missions

`GET {VEKLOM_API_BASE}/api/missions/daily?address={address}`

Response:

```json
{
  "missions": [
    {
      "id": "mission_1",
      "title": "First Claim",
      "description": "Claim your daily USDC drop",
      "reward": { "usdc": 0.5, "xp": 100 },
      "completed": false
    }
  ]
}
```

### Get Agent Stats

`GET {VEKLOM_API_BASE}/api/agent/{agentId}`

### Get Governance Proof

`GET {VEKLOM_API_BASE}/api/governance/verify/{agentId}?action={actionType}&amount={amountUSDC}&user_address={address}`

Response:

```json
{
  "approved": true,
  "reason": "All governance gates passed",
  "gates": {
    "agentActive": true,
    "budgetOk": true,
    "policyMatch": true,
    "trustScoreOk": true
  },
  "proofHash": "0x..."
}
```

## Prepare Endpoints

### Prepare Mission Claim

`GET {VEKLOM_API_BASE}/api/prepare/mission-claim?user_address={address}&mission_id={missionId}`

Include `X-Payment-Proof` only after payment confirmation. For prepayment discovery, use the returned HTTP 402 payment instructions from protected endpoints or hardcoded mission payment parameters.

Payment parameters:

```json
{
  "recipient": "0x3a74772e925b54F7dAD7FD95c9Ba30825033f970",
  "amount": "0.01",
  "asset": "USDC",
  "chain": 8453
}
```

### Prepare Agent Race Launch

`GET {VEKLOM_API_BASE}/api/prepare/race-launch?user_address={address}&agent_id={agentId}&policy={policy}`

### Prepare Agent Policy Update

Policy update support is a planned backend route. Until that endpoint exists, do not claim policy updates are persisted. Read the current policy from `/api/agent/{agentId}` and use governance verification to explain whether the requested policy would be acceptable.

## Base MCP `send_calls` Mapping

### Mission Claim With X402 Payment

After reading mission details, construct a Base USDC transfer call:

```json
{
  "chain": "base",
  "calls": [
    {
      "to": "0x833589fCD6eDb6E08f4c7C32D4f71b3228cdeC9F",
      "value": "0x0",
      "data": "<ABI-encoded transfer(0x3a74772e925b54F7dAD7FD95c9Ba30825033f970, 10000)>"
    }
  ],
  "capabilities": {
    "dataSuffix": {
      "value": "0x62635f6a37783432326f350b0080218021802180218021802180218021",
      "optional": true
    }
  }
}
```

The transfer must go to `0x3a74772e925b54F7dAD7FD95c9Ba30825033f970` (`veklom.base.eth`). `10000` is `0.01 USDC` with six decimals.

## Orchestration Patterns

### Claim a Daily Mission

1. `get_wallets()` -> detected user address.
2. `GET /api/missions/daily?address={address}` -> mission list.
3. Build Base USDC transfer with recipient `veklom.base.eth`.
4. Call `send_calls(chain="base", calls=[USDC transfer], capabilities.dataSuffix optional)`.
5. User approves in Base Account.
6. `get_request_status(requestId)` -> confirmed `txHash`.
7. `POST /api/missions/claim?user_address={address}&mission_id={missionId}&tx_hash={txHash}` with `X-Payment-Proof: veklom:x402:{missionId}:{txHash}`.

### Launch Governed Agent Race

1. `get_wallets()` -> detected user address.
2. `GET /api/user/{address}` -> get agent ID.
3. `GET /api/governance/verify/{agentId}?action=race&amount=0.1&user_address={address}`.
4. If approved, execute the required X402 payment via `send_calls`.
5. `POST /api/races/launch?user_address={address}&agent_id={agentId}&governance_proof={proofHash}` with `X-Payment-Proof`.
6. Poll `/api/agent/{agentId}` for updated stats.

## Reference Addresses

- USDC on Base: `0x833589fCD6eDb6E08f4c7C32D4f71b3228cdeC9F`
- WETH on Base: `0x4200000000000000000000000000000000000006`
- Veklom recipient: `0x3a74772e925b54F7dAD7FD95c9Ba30825033f970`
- Veklom Payment Vault: `TBD after Base deployment`
- Veklom Agent Registry: `TBD after Base deployment`

## Failure Handling

If the backend cannot be reached:

- Report that live claims and live race settlement are unavailable.
- Fall back only to read-only local explanation.
- Do not represent simulated rewards as paid USDC.
- Ask the user to retry after backend availability is restored.

## Related

- Base MCP Quickstart
- X402 Payment Protocol
- ACP Agent Control Protocol
- `veklom.base.eth`
