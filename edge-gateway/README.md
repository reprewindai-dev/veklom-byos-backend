# Edge Gateway - Phase 0B

The Edge MCP (Ingress/Execution Gateway) that verifies Execution Authorization Tokens (EATs) and performs tightly-scoped side effects for Veklom's governed runtime.

## Architecture

The Edge Gateway implements Phase 0B of the Veklom governance specification:

- **EAT Verification Module**: Verifies signed tokens from Inside MCP
- **x402 Merchant Module**: Handles payment challenges and verification
- **Execution Engine**: Performs scoped HTTP requests with timeout and retry logic
- **Rate Limiting**: Prevents abuse and enforces usage limits

## Phase 0B Features

### 0B.1 Edge MCP Service Skeleton
- Rust service with modular architecture
- HTTP API endpoints for execution and x402 flows
- Health check endpoint
- Comprehensive error handling

### 0B.2 EAT Verification
- Signature verification using backend public key
- Expiration time validation
- Replay protection (EAT ID and nonce)
- Scope enforcement (URL, method, domain)

### 0B.3 x402 Merchant Ingress
- Single paid endpoint: `/api/v1/premium/analysis`
- Payment challenge generation
- Facilitator-based payment verification
- Payment reference tracking

### 0B.4 Execution Engine
- HTTP request execution with timeout
- Size limits for responses
- Retry logic with exponential backoff
- Domain whitelist enforcement

### 0B.5 Security Controls
- Rate limiting per client
- No internal agent spend capability
- Comprehensive audit logging
- Fail-closed security defaults

## Configuration

Environment variables:

```bash
# Backend connection
BACKEND_URL=http://localhost:8080

# Gateway settings
EDGE_GATEWAY_PORT=8081
RUST_LOG=debug

# x402 Configuration
X402_FACILITATOR_URL=https://api.x402.org
BASE_NETWORK_URL=https://base-goerli.public.blastapi.io
PAYMENT_TOKEN_ADDRESS=0x07865c6E87B9F70255377e024ace6630C1Eaa37F
SUPPORTED_TOKENS=USDC,USDT,ETH
MAX_PAYMENT_AMOUNT=100.0
X402_FACILITATOR_API_KEY=your_api_key

# Execution Configuration
MAX_EXECUTION_TIME_SECONDS=120
MAX_RESPONSE_SIZE_BYTES=10485760
ALLOWED_DOMAINS=api.example.com,api.veklom.com
RATE_LIMIT_PER_MINUTE=60
```

## API Endpoints

### Health Check
```
GET /health
```

Returns service health status and component operational status.

### Execution with EAT
```
POST /execute
Content-Type: application/json

{
  "eat": {
    "eat_id": "eat_1234567890abcdef",
    "agent_id": "agent_12345",
    "authority_run_id": "run_abcdef12",
    "tool_name": "http_request",
    "resource_scope": {
      "url": "https://api.example.com/data",
      "method": "GET",
      "max_amount": 0.0,
      "domain": "api.example.com"
    },
    "workspace_id": "workspace_67890",
    "issued_at": "2024-01-01T12:00:00Z",
    "expires_at": "2024-01-01T12:02:00Z",
    "nonce": "nonce1234567890",
    "constraints": {
      "max_retries": 3,
      "timeout_seconds": 30,
      "requires_x402": false,
      "allowed_methods": ["GET"]
    },
    "signature": "sig_sha256_hash"
  },
  "target_url": "https://api.example.com/data",
  "method": "GET",
  "headers": {},
  "body": null,
  "timeout_seconds": 30
}
```

### x402 Payment Challenge
```
POST /x402/challenge
Content-Type: application/json

{
  "endpoint": "/api/v1/premium/analysis",
  "workspace_id": "workspace_67890"
}
```

### x402 Payment Verification
```
POST /x402/verify
Content-Type: application/json

{
  "payment_reference": "pay_1234567890abcdef",
  "transaction_hash": "0x123...",
  "amount": "5.0",
  "currency": "USDC",
  "payer_address": "0xabc...",
  "timestamp": "2024-01-01T12:00:00Z",
  "signature": "payment_signature"
}
```

## Security Model

### Trust Contract Enforcement
- **EAT Verification**: All privileged actions require valid signed tokens
- **Scope Enforcement**: Actions limited to token-specified URLs/methods
- **Replay Protection**: Tokens and payment references tracked to prevent reuse
- **Fail-Closed**: Reject when verification services unavailable

### x402 Payment Flow
1. Client requests paid endpoint
2. Edge returns 402 with payment challenge
3. Client pays via x402 and gets proof
4. Client retries with payment proof
5. Edge verifies via facilitator
6. Edge executes request and returns result

### Explicit Constraints
- **No Money Movement**: Edge cannot initiate payments, only verify incoming
- **Domain Whitelist**: Only allowed domains can be accessed
- **Size Limits**: Response size and execution time bounded
- **Rate Limiting**: Per-client request rate limits enforced

## Integration with Inside MCP

### Communication Flow
1. Inside MCP verifies identity and policy
2. Inside MCP mints EAT for allowed actions
3. Inside MCP sends EAT + request to Edge MCP
4. Edge MCP verifies EAT and enforces scope
5. Edge MCP executes action and returns receipt
6. Inside MCP logs execution result

### Secure Channel
- Internal network communication
- mTLS or private network recommended
- No direct external access to Inside MCP

## Building and Running

```bash
# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Build
cargo build --release

# Run
cargo run --release

# Or with custom environment
RUST_LOG=info EDGE_GATEWAY_PORT=8081 cargo run
```

## Testing

```bash
# Run unit tests
cargo test

# Test health endpoint
curl -X GET http://localhost:8081/health

# Test x402 challenge
curl -X POST http://localhost:8081/x402/challenge \
  -H "Content-Type: application/json" \
  -d '{"endpoint": "/api/v1/premium/analysis", "workspace_id": "test"}'
```

## Deployment

### Docker Deployment
```dockerfile
FROM rust:1.70 as builder
WORKDIR /app
COPY . .
RUN cargo build --release

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app/target/release/edge-gateway /usr/local/bin/
EXPOSE 8081
CMD ["edge-gateway"]
```

### Kubernetes Deployment
- Deploy behind Traefik/Cloudflare for edge access
- Use internal service for Inside MCP communication
- Configure rate limiting and monitoring
- Enable mTLS for internal communication

## Monitoring and Observability

### Health Checks
- `/health` endpoint for service health
- Component status tracking
- Dependency health monitoring

### Metrics
- Request rate and response times
- EAT verification success/failure rates
- x402 payment verification metrics
- Error rates and types

### Logging
- Structured JSON logging
- Request tracing with correlation IDs
- Security event logging
- Performance metrics

## Security Considerations

- **Token Security**: Private keys never exposed to Edge MCP
- **Network Security**: Internal network only for sensitive operations
- **Input Validation**: All inputs validated and sanitized
- **Error Handling**: No sensitive information in error responses
- **Audit Trail**: All actions logged with full context

## Phase 0B Acceptance Criteria

- [x] Edge MCP service skeleton created
- [x] EAT verification implemented
- [x] x402 merchant flow for single paid endpoint
- [x] Execution engine with scope enforcement
- [x] No internal agent spend capability
- [x] Comprehensive error handling
- [x] Security controls and rate limiting
- [x] Integration with Inside MCP via EATs

## Next Steps

The Edge Gateway is ready for Phase 0B deployment and testing. Next phases will include:
- Additional paid endpoints
- Advanced execution adapters (webhooks, browser sessions)
- Enhanced monitoring and observability
- Multi-region deployment support
