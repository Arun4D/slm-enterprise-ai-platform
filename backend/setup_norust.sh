#!/usr/bin/env bash
# Local compiler-free setup script for SLM Enterprise AI Platform Backend
# This script ensures that no dependencies are compiled from source, avoiding Rust and C++ requirements.

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "🚀 Starting SLM Enterprise AI Platform Compiler-Free Local Setup..."
echo "================================================================="

# Detect Python version
python_bin="python3"
if ! command -v python3 &>/dev/null; then
    if command -v python &>/dev/null; then
        python_bin="python"
    else
        echo "❌ Python is not installed. Please install Python 3.10+ and try again."
        exit 1
    fi
fi

python_version=$($python_bin -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✓ Detected Python version: $python_version"

# Validate python version >= 3.10
major=$(echo "$python_version" | cut -d'.' -f1)
minor=$(echo "$python_version" | cut -d'.' -f2)
if [ "$major" -lt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -lt 10 ]; }; then
    echo "❌ Python 3.10+ is required. Found Python $python_version."
    exit 1
fi

# Clean up existing virtual environments to avoid state conflicts
if [ -d "venv" ]; then
    echo "🧹 Removing old virtual environment (venv) to prevent dependency conflicts..."
    rm -rf venv
fi

# Create clean virtual environment
echo "📦 Creating a fresh virtual environment..."
$python_bin -m venv venv

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Upgrade packaging tools in virtual environment first
echo "📚 Upgrading pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel

# Install dependencies using binary-only flag to prevent local compilation
echo "📦 Installing core dependencies using binary wheels only..."
echo "   (This prevents pip from attempting to compile packages like pydantic-core or watchfiles from source)"

# Configure proxy if environment variables are set
PROXY_FLAG=""
if [ -n "$http_proxy" ]; then
    PROXY_FLAG="--proxy $http_proxy"
    echo "   Using HTTP proxy: $http_proxy"
elif [ -n "$HTTP_PROXY" ]; then
    PROXY_FLAG="--proxy $HTTP_PROXY"
    echo "   Using HTTP proxy: $HTTP_PROXY"
fi

# Run the installation
# We use --only-binary :all: to force pip to fetch precompiled wheels.
# -e . installs the current package in editable mode.
pip install $PROXY_FLAG --only-binary :all: -e .

# Create the environment configuration file if not exists
if [ ! -f ".env" ]; then
    echo "⚙️  Creating .env configuration file from Linux template..."
    cp .env.linux.example .env
    
    # Update SQLite path and make SLM optional/disabled by default locally if they don't have local weights yet
    # Phi-3 Mini path is kept as default but it won't load if not present, falling back to deterministic mode.
fi

echo "================================================================="
echo "✅ Compiler-free setup completed successfully!"
echo "================================================================="
echo ""
echo "📋 Next steps to start testing locally:"
echo ""
echo "1. Activate virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "2. Run the FastAPI backend:"
echo "   uvicorn app.main:app --reload --host 0.0.0.0 --port 8001"
echo ""
echo "3. Verify local server runtime:"
echo "   curl http://localhost:8001/api/v1/health"
echo ""
echo "💡 Note: The SLM Engine is configured to degrade gracefully and warning logs will inform you"
echo "   that it is using deterministic fallbacks. This is normal and expected when running without"
echo "   heavy local inference compilers."
echo ""
