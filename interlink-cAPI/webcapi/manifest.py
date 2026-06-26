"""/.well-known/webcapi.json discovery endpoint."""

def get_manifest():
    return {
        "transport": "webcAPI/1.0",
        "pgl_required": True,
        "capabilities": [
             {"name": "github.read", "risk": "low"},
             {"name": "wallet.pay", "risk": "high"}
        ]
    }
