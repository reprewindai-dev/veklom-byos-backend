#!/bin/bash

# Phase 0A Governance Gateway Build Script

echo "🔧 Building Phase 0A Governance Gateway"

# Check if Rust is installed
if ! command -v cargo &> /dev/null; then
    echo "❌ Rust is not installed. Please install Rust first:"
    echo "   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
    exit 1
fi

echo "✅ Rust found: $(cargo --version)"

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template"
    cp .env.example .env
    echo "⚠️  Please edit .env file with your backend URLs"
fi

# Build the project
echo "🏗️  Building governance-gateway..."
cargo build --release

if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
    echo ""
    echo "🚀 To run the gateway:"
    echo "   cargo run --release"
    echo ""
    echo "🧪 To test the gateway:"
    echo "   chmod +x test_phase0a.sh"
    echo "   ./test_phase0a.sh"
    echo ""
    echo "📋 Make sure your backend services are running on the configured URLs"
else
    echo "❌ Build failed!"
    exit 1
fi
