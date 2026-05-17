# LICENSE_ACTIVATION.md — Buyer License Activation

## Overview

Veklom BYOS Backend uses a license key system to activate your purchased instance. Each license key is:

- Tied to your deployment domain or server fingerprint
- Cryptographically signed (RSA)
- Validated at startup and periodically at runtime

---

## Activation Steps

### 1. Receive Your License Key

After purchase, you will receive a license key in the format:

```
VKLM-XXXX-XXXX-XXXX-XXXX
```

### 2. Set Environment Variable

Add to your `.env.production`:

```env
LICENSE_KEY=VKLM-XXXX-XXXX-XXXX-XXXX
LICENSE_SERVER_URL=https://license.veklom.com
```

### 3. Activate via API

After starting the server, activate:

```bash
curl -X POST https://your-domain.com/api/v1/license/activate \
  -H 'Content-Type: application/json' \
  -d '{"license_key": "VKLM-XXXX-XXXX-XXXX-XXXX", "domain": "your-domain.com"}'
```

Expected response:
```json
{
  "activated": true,
  "plan": "enterprise",
  "expires": "2027-05-17T00:00:00Z",
  "features": ["ai_exec", "compliance", "audit", "marketplace", "pipelines"]
}
```

### 4. Verify Activation

```bash
curl https://your-domain.com/api/v1/license/status
```

---

## License Plans

| Plan | Workspaces | AI Requests/mo | Compliance | Marketplace | Support |
|------|------------|---------------|------------|-------------|---------|
| Starter | 1 | 50,000 | Basic | No | Email |
| Pro | 5 | 500,000 | Full | Yes | Priority |
| Enterprise | Unlimited | Unlimited | Full + Custom | Yes | Dedicated |

---

## Offline / Air-Gapped Activation

For air-gapped environments (no internet access from your server):

1. Contact support with your server fingerprint: `python scripts/get_fingerprint.py`
2. Receive an offline license blob
3. Set `LICENSE_OFFLINE_BLOB=<blob>` in environment
4. Set `LICENSE_SERVER_URL=offline`

---

## License Renewal

Licenses auto-renew if `LICENSE_SERVER_URL` is reachable. For manual renewal, repeat the activation step with your renewed key.

---

## Support

License issues: support@veklom.com  
Emergency: Include your license key and server fingerprint in all support requests.
