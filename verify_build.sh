#!/usr/bin/env bash
# Build verification script for Phase 1 completion
# Verifies all files have been created correctly

set -e

PROJECT_ROOT="/home/arun/Workspace/arun4d_github/slm-enterprise-ai-platform"
BACKEND_DIR="$PROJECT_ROOT/backend"
AGENTS_DIR="$PROJECT_ROOT/agents"

echo "🔍 SLM Enterprise AI Platform - Phase 1 Build Verification"
echo "=========================================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $1"
        return 0
    else
        echo -e "${RED}✗${NC} $1"
        return 1
    fi
}

check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} $1/"
        return 0
    else
        echo -e "${RED}✗${NC} $1/"
        return 1
    fi
}

# Project documentation
echo "📄 Documentation Files:"
check_file "$PROJECT_ROOT/README.md"
check_file "$PROJECT_ROOT/AGENTS.md"
check_file "$PROJECT_ROOT/ARCHITECTURE.md"
check_file "$PROJECT_ROOT/PHASE_1_COMPLETE.md"
check_file "$PROJECT_ROOT/QUICK_START.md"
echo ""

# Backend structure
echo "📦 Backend Directory Structure:"
check_dir "$BACKEND_DIR"
check_dir "$BACKEND_DIR/app"
check_dir "$BACKEND_DIR/app/api"
check_dir "$BACKEND_DIR/app/core"
check_dir "$BACKEND_DIR/app/models"
check_dir "$BACKEND_DIR/app/security"
check_dir "$BACKEND_DIR/app/services"
check_dir "$BACKEND_DIR/tests"
echo ""

# Backend files
echo "📝 Backend Python Files:"
check_file "$BACKEND_DIR/app/__init__.py"
check_file "$BACKEND_DIR/app/main.py"
check_file "$BACKEND_DIR/app/api/__init__.py"
check_file "$BACKEND_DIR/app/api/routes.py"
check_file "$BACKEND_DIR/app/core/__init__.py"
check_file "$BACKEND_DIR/app/core/config.py"
check_file "$BACKEND_DIR/app/core/exceptions.py"
check_file "$BACKEND_DIR/app/core/logging_config.py"
check_file "$BACKEND_DIR/app/models/__init__.py"
check_file "$BACKEND_DIR/app/security/__init__.py"
check_file "$BACKEND_DIR/app/services/__init__.py"
check_file "$BACKEND_DIR/app/services/plugin_manager.py"
check_file "$BACKEND_DIR/app/services/agent_registry.py"
check_file "$BACKEND_DIR/tests/__init__.py"
check_file "$BACKEND_DIR/tests/test_plugin_manager.py"
check_file "$BACKEND_DIR/tests/test_security.py"
echo ""

# Backend configuration
echo "⚙️  Backend Configuration Files:"
check_file "$BACKEND_DIR/pyproject.toml"
check_file "$BACKEND_DIR/.env.example"
check_file "$BACKEND_DIR/.env.linux.example"
check_file "$BACKEND_DIR/.env.windows.example"
check_file "$BACKEND_DIR/setup_dev.sh"
check_file "$BACKEND_DIR/README.md"
echo ""

# Agent structure
echo "🤖 Agent Directory Structure:"
check_dir "$AGENTS_DIR"
check_dir "$AGENTS_DIR/log_analysis_agent"
check_dir "$AGENTS_DIR/log_analysis_agent/tools"
check_dir "$AGENTS_DIR/log_analysis_agent/tests"
echo ""

# Agent files
echo "🔧 Log Analysis Agent Files:"
check_file "$AGENTS_DIR/log_analysis_agent/manifest.json"
check_file "$AGENTS_DIR/log_analysis_agent/config.yaml"
check_file "$AGENTS_DIR/log_analysis_agent/main.py"
check_file "$AGENTS_DIR/log_analysis_agent/prompts.py"
check_file "$AGENTS_DIR/log_analysis_agent/tools/__init__.py"
check_file "$AGENTS_DIR/log_analysis_agent/tools/log_parser.py"
check_file "$AGENTS_DIR/log_analysis_agent/tests/__init__.py"
check_file "$AGENTS_DIR/log_analysis_agent/tests/test_log_parser.py"
check_file "$AGENTS_DIR/log_analysis_agent/README.md"
echo ""

# Count files
echo "📊 Build Statistics:"
PYTHON_FILES=$(find "$PROJECT_ROOT" -name "*.py" | wc -l)
CONFIG_FILES=$(find "$PROJECT_ROOT" -name "*.json" -o -name "*.yaml" -o -name "*.toml" | wc -l)
DOC_FILES=$(find "$PROJECT_ROOT" -name "*.md" | wc -l)
echo "Python files: $PYTHON_FILES"
echo "Configuration files: $CONFIG_FILES"
echo "Documentation files: $DOC_FILES"
echo ""

# File sizes
echo "📏 File Sizes:"
echo "Backend:"
du -sh "$BACKEND_DIR" 2>/dev/null || echo "N/A"
echo "Agents:"
du -sh "$AGENTS_DIR" 2>/dev/null || echo "N/A"
echo ""

echo "✅ Phase 1 Build Verification Complete!"
echo ""
echo "Next steps:"
echo "1. cd backend"
echo "2. ./setup_dev.sh"
echo "3. source venv/bin/activate"
echo "4. uvicorn app.main:app --reload"
echo ""
