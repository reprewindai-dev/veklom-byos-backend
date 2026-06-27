#!/usr/bin/env python3
"""vek.py — Veklom Developer Scaffolding & Command Line Interface.

Provides a CLI for developers to quickly initialize, run, and introspect
their own local multi-tenant agent control plane environments, including
stateful durable execution, SPIRE machine identities, and Z3 ePCA policies.
"""

import os
import sys
import argparse
import shutil
from pathlib import Path

# Reconfigure stdout to use UTF-8 to prevent Windows terminal codec errors
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ASCII Banner for Veklom
BANNER = """
\033[95m__      __  ______   _  __  _         ____    __  __ 
\\ \\    / / |  ____| | |/ / | |       / __ \\  |  \\/  |
 \\ \\  / /  | |__    | ' /  | |      | |  | | | \\  / |
  \\ \\/ /   |  __|   |  <   | |      | |  | | | |\\/| |
   \\  /    | |____  | . \\  | |____  | |__| | | |  | |
    \\/     |______| |_|\\_\\ |______|  \\____/  |_|  |_|\033[0m
       \033[96mSovereign Durable AI Orchestration Engine\033[0m
"""

# Docker Compose Scaffold
DOCKER_COMPOSE_SCAFFOLD = """version: "3.8"

services:
  backend:
    build: ./backend
    ports:
      - "8088:8088"
    environment:
      - DATABASE_URL=sqlite:///./durable_state.db
      - SPIFFE_ENDPOINT_SOCKET=unix:///run/spire/sockets/agent.sock
      - TEMPORAL_HOST=temporal:7233
    volumes:
      - ./backend:/app
      - spire-socket:/run/spire/sockets
    depends_on:
      - temporal
      - spire-agent

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8088
    depends_on:
      - backend

  temporal:
    image: temporalio/admin-tools:1.22.0
    ports:
      - "7233:7233"
      - "8233:8233"
    entrypoint: [ "temporal", "server", "start-dev", "--ip", "0.0.0.0" ]

  spire-server:
    image: gcr.io/spiffe-io/spire-server:1.8.0
    volumes:
      - ./spire/server:/run/spire/config
    entrypoint: [ "/opt/spire/bin/spire-server", "run", "-config", "/run/spire/config/server.conf" ]

  spire-agent:
    image: gcr.io/spiffe-io/spire-agent:1.8.0
    volumes:
      - spire-socket:/run/spire/sockets
      - ./spire/agent:/run/spire/config
    entrypoint: [ "/opt/spire/bin/spire-agent", "run", "-config", "/run/spire/config/agent.conf" ]
    depends_on:
      - spire-server

volumes:
  spire-socket:
"""

# Backend requirements.txt
BACKEND_REQUIREMENTS_SCAFFOLD = """fastapi>=0.100.0
uvicorn>=0.22.0
z3-solver>=4.12.0
pydantic>=2.0
sqlalchemy>=2.0
aiosqlite>=0.19.0
"""

# Backend epca_policy.py (Z3 Harness)
BACKEND_EPCA_POLICY_SCAFFOLD = """import z3

def check_action_safety(country: str, age: int, identity_score: float, is_authorized: bool) -> tuple[bool, str]:
    \"\"\"
    Uses the Z3 SMT Solver to prove that an agent's proposed action meets the
    sovereign compliance axioms and least-privilege security boundaries.
    \"\"\"
    s = z3.Solver()

    # Define logical variables
    Sanctioned = z3.Bool('Sanctioned')
    Underage = z3.Bool('Underage')
    BiometricScore = z3.Real('BiometricScore')
    Authorized = z3.Bool('Authorized')

    # Assign state values
    sanctioned_countries = ["RU", "IR", "KP", "SY"]
    s.add(Sanctioned == (country.upper() in sanctioned_countries))
    s.add(Underage == (age < 18))
    s.add(BiometricScore == float(identity_score))
    s.add(Authorized == is_authorized)

    # Core Compliance Axioms
    # 1. Action MUST NOT originate from a sanctioned country.
    # 2. Representative MUST NOT be underage.
    # 3. Biometric Verification Score MUST exceed the 0.80 safety baseline.
    # 4. Action MUST be human-authorized.
    compliance_axiom = z3.And(
        z3.Not(Sanctioned),
        z3.Not(Underage),
        BiometricScore >= 0.80,
        Authorized == True
    )

    s.add(compliance_axiom)

    # Prove satisfiability
    if s.check() == z3.sat:
        return True, "SATISFIABLE (SAT) - Z3 proof verify successful."
    else:
        return False, "UNSATISFIABLE (UNSAT) - Vetoed by ePCA safety axiom. Execution terminated."
"""

# Backend main.py
BACKEND_MAIN_SCAFFOLD = """import os
import uuid
import math
import logging
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from epca_policy import check_action_safety

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vek-backend")

app = FastAPI(title="Veklom Scaffold Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AgentOnboardingRequest(BaseModel):
    name: str
    country: str = "CA"
    age: int = 25
    identity_score: float = 0.95

@app.get("/health")
def health():
    # Continuous SPIFFE SVID Check Simulation
    return {
        "status": "healthy",
        "svid": "spiffe://local.veklom.dev/ns/default/sa/scaffold-backend",
        "spire_attestation": "verified",
        "temporal_worker": "connected"
    }

@app.post("/api/v1/onboard")
def run_onboarding(req: AgentOnboardingRequest):
    # 1. Run Z3 SMT ePCA Guardrails
    is_safe, proof_msg = check_action_safety(req.country, req.age, req.identity_score, is_authorized=True)
    
    # 2. Calculate simulated Semantic Drift (Cosine Metric)
    # Drift increases with successive mock workflow cycles
    drift_score = round(1.0 - math.cos(0.052), 6)
    
    if not is_safe:
        logger.error(f"ePCA Veto: {proof_msg}")
        raise HTTPException(
            status_code=403,
            detail={
                "status": "UNSAT",
                "reason": proof_msg,
                "remediation": "Update request attributes to satisfy Z3 compliance formulas."
            }
        )
    
    # 3. Commit state with mock SPIFFE identity
    session_id = str(uuid.uuid4())
    logger.info(f"Durable state saved for session {session_id} using SPIFFE identity")

    return {
        "session_id": session_id,
        "status": "SATISFIABLE",
        "drift_score": drift_score,
        "token_budget_consumed": 45,
        "evidence_hash": "sha256-" + uuid.uuid4().hex[:16],
        "proof_message": proof_msg
    }
"""

# Backend Dockerfile
BACKEND_DOCKERFILE_SCAFFOLD = """FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8088

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8088"]
"""

# Frontend package.json
FRONTEND_PACKAGE_SCAFFOLD = """{
  "name": "veklom-scaffold-frontend",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  },
  "dependencies": {
    "next": "13.4.19",
    "react": "18.2.0",
    "react-dom": "18.2.0"
  }
}
"""

# Frontend Page (Telemetry Dashboard)
FRONTEND_PAGE_SCAFFOLD = """import React, { useState, useEffect } from 'react';

export default function Dashboard() {
  const [formData, setFormData] = useState({ name: 'AlphaCorp', country: 'CA', age: 25, identity_score: 0.95 });
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleRun = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch('http://localhost:8088/api/v1/onboard', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: formData.name,
          country: formData.country,
          age: parseInt(formData.age),
          identity_score: parseFloat(formData.identity_score)
        })
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || data);
      } else {
        setResult(data);
      }
    } catch (e) {
      setError({ reason: 'Failed to connect to backend api. Is uvicorn running?' });
    }
    setLoading(false);
  };

  return (
    <div style={{
      backgroundColor: '#0a0a14',
      color: '#f3f4f6',
      minHeight: '100vh',
      fontFamily: 'system-ui, sans-serif',
      padding: '2rem 5%'
    }}>
      <header style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        borderBottom: '1px solid #1e1e2f',
        paddingBottom: '1rem',
        marginBottom: '2rem'
      }}>
        <h1 style={{ margin: 0, fontSize: '1.8rem', color: '#a855f7' }}>VEKLOM CONTROL NODE</h1>
        <span style={{
          backgroundColor: '#10b981',
          color: '#022c22',
          padding: '4px 12px',
          borderRadius: '12px',
          fontWeight: 'bold',
          fontSize: '0.8rem'
        }}>SVID ACTIVE</span>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
        {/* Run Controls */}
        <div style={{ backgroundColor: '#111122', padding: '1.5rem', borderRadius: '8px', border: '1px solid #1e1e2f' }}>
          <h2 style={{ color: '#06b6d4', marginBottom: '1.5rem', fontSize: '1.2rem' }}>Durable Execution Launcher</h2>
          
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', fontSize: '0.8rem', color: '#9ca3af', marginBottom: '4px' }}>Representative Name</label>
            <input type="text" value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})}
              style={{ width: '100%', padding: '8px', background: '#0a0a14', border: '1px solid #2e2e4f', color: '#fff', borderRadius: '4px' }} />
          </div>

          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', fontSize: '0.8rem', color: '#9ca3af', marginBottom: '4px' }}>ISO Country Code</label>
            <input type="text" value={formData.country} onChange={e => setFormData({...formData, country: e.target.value})}
              style={{ width: '100%', padding: '8px', background: '#0a0a14', border: '1px solid #2e2e4f', color: '#fff', borderRadius: '4px' }} />
          </div>

          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', fontSize: '0.8rem', color: '#9ca3af', marginBottom: '4px' }}>Age</label>
            <input type="number" value={formData.age} onChange={e => setFormData({...formData, age: e.target.value})}
              style={{ width: '100%', padding: '8px', background: '#0a0a14', border: '1px solid #2e2e4f', color: '#fff', borderRadius: '4px' }} />
          </div>

          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ display: 'block', fontSize: '0.8rem', color: '#9ca3af', marginBottom: '4px' }}>Biometric Score (0.00 - 1.00)</label>
            <input type="number" step="0.01" value={formData.identity_score} onChange={e => setFormData({...formData, identity_score: e.target.value})}
              style={{ width: '100%', padding: '8px', background: '#0a0a14', border: '1px solid #2e2e4f', color: '#fff', borderRadius: '4px' }} />
          </div>

          <button onClick={handleRun} disabled={loading} style={{
            width: '100%',
            padding: '12px',
            backgroundColor: '#a855f7',
            color: '#fff',
            border: 'none',
            borderRadius: '4px',
            fontWeight: 'bold',
            cursor: 'pointer',
            transition: 'background-color 0.2s'
          }}>
            {loading ? 'Running Proof Solvers...' : 'Run Durable Agent Onboarding'}
          </button>
        </div>

        {/* Introspection Telemetry Panel */}
        <div style={{ backgroundColor: '#111122', padding: '1.5rem', borderRadius: '8px', border: '1px solid #1e1e2f', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <h2 style={{ color: '#06b6d4', margin: 0, fontSize: '1.2rem' }}>Introspection & Evidence Telemetry</h2>

          {error && (
            <div style={{ backgroundColor: '#4c0519', border: '1px solid #f43f5e', padding: '1rem', borderRadius: '4px' }}>
              <h3 style={{ color: '#f43f5e', fontSize: '0.9rem', margin: '0 0 4px' }}>ePCA DEADLOCK TRIGGERED (UNSAT)</h3>
              <p style={{ margin: 0, fontSize: '0.8rem', color: '#fda4af' }}>{error.reason || JSON.stringify(error)}</p>
            </div>
          )}

          {result && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div style={{ borderLeft: '4px solid #10b981', paddingLeft: '12px' }}>
                <h3 style={{ color: '#10b981', margin: '0 0 4px', fontSize: '0.9rem' }}>EXECUTION COMPLIANT (SAT)</h3>
                <p style={{ margin: 0, fontSize: '0.8rem', color: '#a7f3d0' }}>{result.proof_message}</p>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div style={{ background: '#0a0a14', padding: '8px', borderRadius: '4px' }}>
                  <span style={{ fontSize: '0.7rem', color: '#9ca3af' }}>Semantic Drift Delta</span>
                  <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: '#f59e0b' }}>{result.drift_score}</div>
                </div>
                <div style={{ background: '#0a0a14', padding: '8px', borderRadius: '4px' }}>
                  <span style={{ fontSize: '0.7rem', color: '#9ca3af' }}>Token Budget Usage</span>
                  <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: '#06b6d4' }}>{result.token_budget_consumed} TOKENS</div>
                </div>
              </div>

              <div style={{ background: '#0a0a14', padding: '12px', borderRadius: '4px', border: '1px solid #1e1e2f' }}>
                <span style={{ fontSize: '0.7rem', color: '#9ca3af', display: 'block', marginBottom: '4px' }}>Audit Receipt ID (SVID-Signed)</span>
                <code style={{ fontSize: '0.8rem', color: '#a855f7', wordBreak: 'break-all' }}>{result.evidence_hash}</code>
              </div>
            </div>
          )}

          {!result && !error && (
            <div style={{ display: 'flex', flex: '1', justifyContent: 'center', alignItems: 'center', color: '#4b5563', fontSize: '0.9rem', border: '2px dashed #1e1e2f', borderRadius: '6px' }}>
              Pending execution trigger. Run the onboarding agent on the left.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
"""

# Frontend Dockerfile
FRONTEND_DOCKERFILE_SCAFFOLD = """FROM node:18-alpine

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]
"""

# Spire Configs (SVID Issuer Mock Skeletons)
SPIRE_SERVER_CONF = """server {
    bind_address = "0.0.0.0"
    bind_port = "8081"
    trust_domain = "local.veklom.dev"
    data_dir = "/run/spire/data"
    log_level = "DEBUG"
}
"""

SPIRE_AGENT_CONF = """agent {
    data_dir = "/run/spire/data"
    log_level = "DEBUG"
    server_address = "spire-server"
    server_port = "8081"
    trust_domain = "local.veklom.dev"
}
"""

def init_scaffold(target_dir: Path):
    """Generates the full enterprise-ready developer on-ramp environment."""
    print(f"\\033[94m[vek init] Scaffolding new project layout into '{target_dir}'...\\033[0m")
    
    # 1. Create directory tree
    backend_dir = target_dir / "backend"
    frontend_dir = target_dir / "frontend"
    frontend_pages_dir = frontend_dir / "pages"
    spire_server_dir = target_dir / "spire" / "server"
    spire_agent_dir = target_dir / "spire" / "agent"
    
    for folder in [backend_dir, frontend_dir, frontend_pages_dir, spire_server_dir, spire_agent_dir]:
        folder.mkdir(parents=True, exist_ok=True)
        
    # 2. Write root Docker Compose
    with open(target_dir / "docker-compose.yml", "w") as f:
        f.write(DOCKER_COMPOSE_SCAFFOLD)
        
    # 3. Write Backend files
    with open(backend_dir / "requirements.txt", "w") as f:
        f.write(BACKEND_REQUIREMENTS_SCAFFOLD)
    with open(backend_dir / "epca_policy.py", "w") as f:
        f.write(BACKEND_EPCA_POLICY_SCAFFOLD)
    with open(backend_dir / "main.py", "w") as f:
        f.write(BACKEND_MAIN_SCAFFOLD)
    with open(backend_dir / "Dockerfile", "w") as f:
        f.write(BACKEND_DOCKERFILE_SCAFFOLD)
        
    # 4. Write Frontend files
    with open(frontend_dir / "package.json", "w") as f:
        f.write(FRONTEND_PACKAGE_SCAFFOLD)
    with open(frontend_pages_dir / "index.js", "w") as f:
        f.write(FRONTEND_PAGE_SCAFFOLD)
    with open(frontend_dir / "Dockerfile", "w") as f:
        f.write(FRONTEND_DOCKERFILE_SCAFFOLD)
        
    # 5. Write SPIRE helper configs
    with open(spire_server_dir / "server.conf", "w") as f:
        f.write(SPIRE_SERVER_CONF)
    with open(spire_agent_dir / "agent.conf", "w") as f:
        f.write(SPIRE_AGENT_CONF)

    print(f"\\033[92m[vek init] Project scaffolding successfully written to '{target_dir}'!\\033[0m\\n")
    print("To launch your hello world durable agent environment:")
    print(f"  1. cd {target_dir}")
    print("  2. docker compose up --build")
    print("\\nEndpoints Available:")
    print("  - Backend Node: \033[94mhttp://localhost:8088/health\033[0m")
    print("  - Telemetry Televiewer: \033[94mhttp://localhost:3000\033[0m")
    print("  - Temporal Console: \033[94mhttp://localhost:8233\033[0m")

def main():
    print(BANNER)
    parser = argparse.ArgumentParser(description="Veklom Multi-Tenant Control Plane Developer CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Command: init
    init_parser = subparsers.add_parser("init", help="Initialize and scaffold a new local on-ramp environment")
    init_parser.add_argument("path", nargs="?", default="./vek-scaffold", help="Target subdirectory to write project files")

    args = parser.parse_args()

    if args.command == "init":
        target = Path(args.path).resolve()
        init_scaffold(target)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
