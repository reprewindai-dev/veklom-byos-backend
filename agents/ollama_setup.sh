#!/usr/bin/env bash
# =============================================================================
# Veklom Ollama Setup Script
# Run this once on your Hetzner server to install and configure Ollama
# as the sovereign inference engine for all Veklom agents.
# =============================================================================

set -euo pipefail

echo "================================================================"
echo " VEKLOM SOVEREIGN AI — OLLAMA SETUP"
echo "================================================================"

# 1. Install Ollama
echo "[1/5] Installing Ollama..."
curl -fsSL https://ollama.com/install.sh | sh
echo "Ollama installed."

# 2. Start Ollama service
echo "[2/5] Starting Ollama service..."
systemctl enable ollama || true
systemctl start ollama || ollama serve &
sleep 3
echo "Ollama running at http://localhost:11434"

# 3. Pull core models
echo "[3/5] Pulling sovereign models..."

# Primary — best reasoning for tool use
echo "  Pulling llama3 (primary model)..."
ollama pull llama3

# Fast fallback — lower RAM, quick responses
echo "  Pulling mistral (fast fallback)..."
ollama pull mistral

# Lightweight for edge/low-resource tasks
echo "  Pulling phi3 (lightweight)..."
ollama pull phi3

echo "Core models ready."

# 4. Verify Ollama is working
echo "[4/5] Verifying Ollama API..."
RESPONSE=$(curl -s http://localhost:11434/api/tags)
echo "  Available models: $RESPONSE" | head -c 300
echo ""

# 5. Print env vars to add to Coolify / .env
echo "[5/5] Add these to your .env or Coolify secrets:"
echo ""
echo "  OLLAMA_BASE_URL=http://localhost:11434"
echo "  OLLAMA_MODEL=llama3"
echo "  VEKLOM_AGENT_PROVIDER=ollama"
echo ""
echo "================================================================"
echo " SETUP COMPLETE — Veklom Sovereign Agent ready to run"
echo "================================================================"
echo ""
echo "Run the agent:"
echo "  python agents/agent_ollama.py"
echo "  python agents/agent_router.py"
echo ""
echo "Run with custom goal:"
echo "  python agents/agent_ollama.py 'Check all vendor balances and flag any below 10 USD'"
