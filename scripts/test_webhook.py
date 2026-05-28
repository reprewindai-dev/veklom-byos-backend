#!/usr/bin/env python3
"""Test webhook HMAC validation and idempotency."""

import hmac
import hashlib
import json
import requests
import time

WEBHOOK_SECRET = "73d751b745aeb7c485f0b18f811314fcabb3c3aa06cb6226e25d974a5e7705d1"
WEBHOOK_URL = "http://localhost:8088/api/v1/webhook/payment"

def generate_signature(payload: str, secret: str) -> str:
    """Generate HMAC-SHA256 signature."""
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()

def test_valid_hmac():
    """Test valid webhook HMAC returns 200."""
    payload = json.dumps({
        "order_id": "test_order_001",
        "amount": 100.0,
        "status": "confirmed"
    })
    
    signature = generate_signature(payload, WEBHOOK_SECRET)
    
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": f"sha256={signature}",
        "X-Idempotency-Key": "test_key_001"
    }
    
    response = requests.post(WEBHOOK_URL, json=json.loads(payload), headers=headers)
    print(f"Valid HMAC test: {response.status_code} - {response.text}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

def test_invalid_hmac():
    """Test invalid webhook HMAC returns 401."""
    payload = json.dumps({
        "order_id": "test_order_002",
        "amount": 100.0,
        "status": "confirmed"
    })
    
    headers = {
        "Content-Type": "application/json",
        "X-Signature": "sha256=invalid_signature",
        "X-Idempotency-Key": "test_key_002"
    }
    
    response = requests.post(WEBHOOK_URL, data=payload, headers=headers)
    print(f"Invalid HMAC test: {response.status_code} - {response.text}")
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"

def test_idempotency_replay():
    """Test same X-Idempotency-Key + same body returns safe 200."""
    payload = json.dumps({
        "order_id": "test_order_003",
        "amount": 100.0,
        "status": "confirmed"
    })
    
    signature = generate_signature(payload, WEBHOOK_SECRET)
    
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": f"sha256={signature}",
        "X-Idempotency-Key": "test_key_003"
    }
    
    # First request
    response1 = requests.post(WEBHOOK_URL, json=json.loads(payload), headers=headers)
    print(f"First request: {response1.status_code}")
    
    # Second request with same key and body
    response2 = requests.post(WEBHOOK_URL, json=json.loads(payload), headers=headers)
    print(f"Replay test: {response2.status_code} - {response2.text}")
    assert response2.status_code == 200, f"Expected 200 for replay, got {response2.status_code}"
    assert "idempotent" in response2.json().get("message", ""), "Expected idempotent message"

def test_idempotency_conflict():
    """Test same X-Idempotency-Key + different body returns 409."""
    payload1 = json.dumps({
        "order_id": "test_order_004",
        "amount": 100.0,
        "status": "confirmed"
    })
    
    payload2 = json.dumps({
        "order_id": "test_order_004",
        "amount": 200.0,  # Different amount
        "status": "confirmed"
    })
    
    signature1 = generate_signature(payload1, WEBHOOK_SECRET)
    signature2 = generate_signature(payload2, WEBHOOK_SECRET)
    
    headers1 = {
        "Content-Type": "application/json",
        "X-Signature": f"sha256={signature1}",
        "X-Idempotency-Key": "test_key_004"
    }
    
    headers2 = {
        "Content-Type": "application/json",
        "X-Signature": f"sha256={signature2}",
        "X-Idempotency-Key": "test_key_004"
    }
    
    # First request
    response1 = requests.post(WEBHOOK_URL, json=json.loads(payload1), headers=headers1)
    print(f"First request: {response1.status_code}")
    
    # Second request with same key but different body
    response2 = requests.post(WEBHOOK_URL, json=json.loads(payload2), headers=headers2)
    print(f"Conflict test: {response2.status_code} - {response2.text}")
    assert response2.status_code == 409, f"Expected 409 for conflict, got {response2.status_code}"

if __name__ == "__main__":
    print("Testing webhook HMAC validation and idempotency...")
    print()
    
    try:
        test_valid_hmac()
        print("✓ Valid HMAC test passed")
    except AssertionError as e:
        print(f"✗ Valid HMAC test failed: {e}")
    
    print()
    
    try:
        test_invalid_hmac()
        print("✓ Invalid HMAC test passed")
    except AssertionError as e:
        print(f"✗ Invalid HMAC test failed: {e}")
    
    print()
    
    try:
        test_idempotency_replay()
        print("✓ Idempotency replay test passed")
    except AssertionError as e:
        print(f"✗ Idempotency replay test failed: {e}")
    
    print()
    
    try:
        test_idempotency_conflict()
        print("✓ Idempotency conflict test passed")
    except AssertionError as e:
        print(f"✗ Idempotency conflict test failed: {e}")
