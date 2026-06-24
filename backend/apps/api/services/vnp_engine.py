import math
from typing import List, Dict, Any, Optional
import hashlib
import time
import random
from backend.core.web3_client import web3_client

# ============ PROTOCOL PARAMETERS ============
VNP_PARAMS = {
    "k": 3,
    "lambda": 2.0,
    "epochDurationMs": 3_600_000,
    "minSamples": 100,
    "minBondUsdc": 1000,
    "challengeTierA": {"min": 5, "max": 50},
    "challengeTierB": {"min": 100, "max": 5000},
    "consensusWeights": {"kde": 0.5, "historical": 0.3, "shadow": 0.2},
    "reputationDecay": 0.95,
    "reputationWindow": 720,
    "ewmaAlpha": 0.05,
    "platformFeeRate": 0.025,
}

# ============ DEVIATION & PENALTY ============

def compute_deviation(target_p95_ms: float, observed_p95_ms: float, sigma_ms: float, k: float = VNP_PARAMS["k"]) -> dict:
    deviation_ms = abs(observed_p95_ms - target_p95_ms)
    tolerance_ms = k * max(sigma_ms, 0.1)
    excess_ms = max(0.0, deviation_ms - tolerance_ms)
    penalty_usdc = VNP_PARAMS["lambda"] * excess_ms if excess_ms > 0 else 0.0
    return {
        "deviation_ms": deviation_ms,
        "tolerance_ms": tolerance_ms,
        "excess_ms": excess_ms,
        "penalty_usdc": penalty_usdc
    }

def bond_status_from_deviation(d: dict) -> str:
    if d["excess_ms"] == 0 and d["deviation_ms"] < d["tolerance_ms"] * 0.5:
        return "healthy"
    if d["excess_ms"] == 0:
        return "warning"
    if d["penalty_usdc"] < 100:
        return "breaching"
    return "critical"

# ============ STATISTICAL HELPERS ============

def mean(data: List[float]) -> float:
    if not data: return 0.0
    return sum(data) / len(data)

def stddev(data: List[float]) -> float:
    n = len(data)
    if n < 2: return 0.0
    m = mean(data)
    variance = sum((x - m) ** 2 for x in data) / (n - 1)
    return math.sqrt(variance)

def percentile(sorted_data: List[float], p: float) -> float:
    if not sorted_data: return 0.0
    idx = (p / 100.0) * (len(sorted_data) - 1)
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi or hi >= len(sorted_data):
        return sorted_data[lo]
    return sorted_data[lo] + (sorted_data[hi] - sorted_data[lo]) * (idx - lo)

def iqr(data: List[float]) -> float:
    sorted_data = sorted(data)
    return percentile(sorted_data, 75) - percentile(sorted_data, 25)

# ============ KDE CONSENSUS ============

def gaussian_kernel(u: float) -> float:
    return math.exp(-0.5 * u * u) / math.sqrt(2 * math.pi)

def silverman_bandwidth(data: List[float]) -> float:
    n = len(data)
    if n < 2: return 1.0
    s = stddev(data)
    q = iqr(data)
    spread = min(s, q / 1.34) if q > 0 else s
    return 0.9 * max(spread, 0.1) * math.pow(n, -0.2)

def compute_kde(data: List[float], num_points: int = 200) -> dict:
    if not data:
        return {"mode": 0, "bandwidth": 1, "points": [], "density": []}
    if len(data) == 1:
        return {"mode": data[0], "bandwidth": 1, "points": [data[0]], "density": [1.0]}
    
    bandwidth = silverman_bandwidth(data)
    sorted_data = sorted(data)
    margin = bandwidth * 3
    lo = sorted_data[0] - margin
    hi = sorted_data[-1] + margin
    step = (hi - lo) / (num_points - 1) if num_points > 1 else 0

    points = []
    density = []
    max_d = 0.0
    mode_val = 0.0

    for i in range(num_points):
        x = lo + i * step
        points.append(x)
        d = 0.0
        for xi in data:
            d += gaussian_kernel((x - xi) / bandwidth)
        d /= (len(data) * bandwidth)
        density.append(d)
        if d > max_d:
            max_d = d
            mode_val = x

    return {"mode": mode_val, "bandwidth": bandwidth, "points": points, "density": density}

def multi_anchor_consensus(kde_mode: float, historical_anchor: float, shadow_anchor: float) -> float:
    w = VNP_PARAMS["consensusWeights"]
    return (w["kde"] * kde_mode) + (w["historical"] * historical_anchor) + (w["shadow"] * shadow_anchor)

def log_normal_params(p50: float, p95: float) -> dict:
    p50 = max(p50, 0.1)
    p95 = max(p95, p50 * 1.01)
    mu = math.log(p50)
    z_95 = 1.645
    sigma = (math.log(p95) - mu) / z_95
    return {"mu": mu, "sigma": sigma}

def latency_density_curve(p50: float, p95: float) -> dict:
    params = log_normal_params(p50, p95)
    mu, sigma = params["mu"], params["sigma"]
    
    lo = math.exp(mu - 3 * sigma)
    hi = math.exp(mu + 3 * sigma)
    step = (hi - lo) / 99
    points = []
    density = []
    max_d = 0
    mode_idx = 0
    
    for i in range(100):
        x = lo + i * step
        points.append(x)
        if x <= 0:
            density.append(0)
            continue
        d = (1 / (x * sigma * math.sqrt(2 * math.pi))) * math.exp(-((math.log(x) - mu) ** 2) / (2 * sigma ** 2))
        density.append(d)
        if d > max_d:
            max_d = d
            mode_idx = i
            
    return {
        "points": points,
        "density": density,
        "mode": points[mode_idx] if points else p50,
        "variance": math.exp(2*mu + sigma**2) * (math.exp(sigma**2) - 1)
    }

# ============ VERIFIER / SETTLEMENT ============

def current_epoch() -> int:
    return int(time.time() * 1000) // VNP_PARAMS["epochDurationMs"]

def generate_sha() -> str:
    return ''.join(random.choice('0123456789abcdef') for _ in range(64))

VERIFIER_REGIONS = ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1", "ap-northeast-1"]
VERIFIER_ASNS = ["AS16509", "AS15169", "AS13335", "AS24940", "AS14061"]

def verifier_weight(stake: float, reputation: float, diversity_score: float) -> float:
    return stake * math.log(max(reputation, 1) + 1) * diversity_score

def build_verifier_nodes(api_count: int) -> List[dict]:
    nodes = []
    for i, region in enumerate(VERIFIER_REGIONS):
        base_stake = 5000 + i * 1000
        base_rep = 80 + int(api_count * 2.5)
        diversity = 0.7 + i * 0.06
        rep = min(100, base_rep)
        weight = verifier_weight(base_stake, rep, diversity)
        nodes.append({
            "address": f"0x{(0xA1 + i):02x}...{generate_sha()[:8]}",
            "stake": base_stake,
            "reputation": rep,
            "diversity_score": round(diversity, 2),
            "weight": round(weight),
            "region": region,
            "asn": VERIFIER_ASNS[i],
            "measurement_count": 1000 + api_count * 50 + i * 200,
            "accuracy": 95 + min(4, i * 0.8),
            "active": True
        })
    return nodes

def compute_epoch_settlement(api_id: str, name: str, target_p95: float, observed_p95: float, sigma: float, bond_usdc: float, epoch: int) -> dict:
    d = compute_deviation(target_p95, observed_p95, sigma)
    penalty = min(bond_usdc, d["penalty_usdc"])
    
    # If there is a penalty to slash, submit it to the Base Sepolia testnet!
    tx_hash = ""
    if penalty > 0:
        tx_hash = web3_client.slash_bond(api_id, penalty)
        
    return {
        "id": f"stl-{epoch}-{api_id[:8]}",
        "epoch": epoch,
        "apiId": api_id,
        "name": name,
        "observedP95": observed_p95,
        "targetP95": target_p95,
        "penaltyApplied": penalty,
        "newBondBalance": bond_usdc - penalty,
        "txHash": tx_hash,
        "timestamp": time.time() * 1000
    }

def build_provider_bond_view(api: dict) -> dict:
    target_p95 = api.get("p95", 100) * 0.95
    observed_p95 = api.get("p95", 100)
    sigma = observed_p95 * 0.15
    
    # Fetch real bond from Base Sepolia!
    bond_amount = web3_client.get_provider_bond(api.get('id', ''))
        
    d = compute_deviation(target_p95, observed_p95, sigma)
    return {
        "id": f"bond-{api.get('id')}",
        "apiId": api.get('id'),
        "name": api.get("name"),
        "bondAmountUsdc": bond_amount,
        "targetP95Ms": target_p95,
        "observedP95Ms": observed_p95,
        "sigmaMs": sigma,
        "deviation": d,
        "status": bond_status_from_deviation(d),
        "updatedAt": time.time() * 1000
    }
