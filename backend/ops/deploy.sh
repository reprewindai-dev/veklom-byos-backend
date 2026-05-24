#!/bin/bash
# Deployment script for Veklom BYOS Backend
# This script handles deployment to Coolify/Hetzner

set -e

echo "Veklom BYOS Backend Deployment"
echo "================================"

# Check if running on server
if [ -z "$COOLIFY_APP_ID" ]; then
    echo "Not running on Coolify. Skipping deployment."
    exit 0
fi

# Pull latest code
echo "Pulling latest code..."
git pull origin main

# Build Docker image
echo "Building Docker image..."
docker build -t veklom-local:latest .

# Stop and remove existing container
echo "Stopping existing container..."
docker stop n13gp1nhrcdp0hvazvbnlxru-213557155694 || true
docker rm n13gp1nhrcdp0hvazvbnlxru-213557155694 || true

# Start new container
echo "Starting new container..."
docker run -d \
  --name n13gp1nhrcdp0hvazvbnlxru-213557155694 \
  --network coolify \
  --env-file /data/coolify/applications/n13gp1nhrcdp0hvazvbnlxru/.env \
  --restart unless-stopped \
  -p 8088:8088 \
  veklom-local:latest

# Wait for container to start
echo "Waiting for container to start..."
sleep 5

# Health check
echo "Running health check..."
curl -s http://localhost:8088/health

echo ""
echo "Deployment complete!"
