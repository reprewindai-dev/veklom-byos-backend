import os
import sys
import httpx
import json

BASE_URL = os.environ.get("VEKLOM_API_URL", "http://localhost:8088")
TREASURY = "0xCC34553b4e6332ffb9C1b61E22436ACA53113D1d"

def check_payment_required():
    print(f"[*] Testing {BASE_URL}/api/v1/x402/search without payment proof...")
    resp = httpx.post(f"{BASE_URL}/api/v1/x402/search")
    
    if resp.status_code == 402:
        print("  [OK] Received 402 Payment Required.")
        headers = resp.headers
        print("  Headers:")
        print(f"    X-Payment-Required: {headers.get('X-Payment-Required')}")
        print(f"    X-Payment-Price-USDC: {headers.get('X-Payment-Price-USDC')}")
        print(f"    X-Payment-Address: {headers.get('X-Payment-Address')}")
        print(f"    X-Payment-Challenge-ID: {headers.get('X-Payment-Challenge-ID')}")
    else:
        print(f"  [FAIL] Expected 402, got {resp.status_code}")
        print(resp.text)
        sys.exit(1)

def verify_with_proof(tx_hash: str):
    print(f"\n[*] Submitting {tx_hash} to /api/v1/x402/search...")
    resp = httpx.post(
        f"{BASE_URL}/api/v1/x402/search",
        headers={"X-Payment-Proof": tx_hash}
    )
    
    if resp.status_code == 200:
        print("  [OK] Payment Accepted! 200 OK.")
        data = resp.json()
        print("  Response:", json.dumps(data, indent=2))
        
        headers = resp.headers
        print("  Receipt Headers:")
        print(f"    X-Veklom-Receipt-ID: {headers.get('X-Veklom-Receipt-ID')}")
        print(f"    X-Veklom-Evidence-ID: {headers.get('X-Veklom-Evidence-ID')}")
        print(f"    X-Veklom-Cost-USDC: {headers.get('X-Veklom-Cost-USDC')}")
    else:
        print(f"  [FAIL] Payment rejected. Status {resp.status_code}")
        try:
            print(json.dumps(resp.json(), indent=2))
        except:
            print(resp.text)

if __name__ == "__main__":
    check_payment_required()
    
    if len(sys.argv) > 1:
        tx_hash = sys.argv[1]
        verify_with_proof(tx_hash)
    else:
        print("\n[!] To test with a real Base USDC transaction, run:")
        print(f"    python scratch/x402_transactions.py <tx_hash>")
        print(f"    Make sure the transaction sends 0.10 USDC to {TREASURY}")
