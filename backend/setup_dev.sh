#!/bin/bash
# Development setup script for SLM Enterprise AI Platform Backend

set -e

echo "🚀 Setting up SLM Enterprise AI Platform Backend..."

# Check Python version
python_version=$(python --version | cut -d' ' -f2 | cut -d'.' -f1,2)
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    echo "✓ Python $python_version detected"
else
    echo "✗ Python $required_version+ required, found $python_version"
    exit 1
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
source venv/bin/activate || . venv/Scripts/activate

# Upgrade pip
echo "📚 Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install dependencies
echo "📦 Installing dependencies..."
pip install -e ".[dev]"

# Setup pre-commit hooks
echo "🔐 Setting up pre-commit hooks..."
pre-commit install 2>/dev/null || true

# Create .env if not exists
if [ ! -f ".env" ]; then
    echo "⚙️  Creating .env file from Linux template..."
    cp .env.linux.example .env
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "  1. Edit .env with your configuration"
echo "  2. Run: uvicorn app.main:app --reload"
echo "  3. Visit: http://localhost:8001/docs"
echo ""
