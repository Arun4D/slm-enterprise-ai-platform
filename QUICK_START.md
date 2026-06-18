# Quick Reference Guide

## 🚀 Start Development in 5 Minutes

```bash
cd backend
./setup_dev.sh
source venv/bin/activate
uvicorn app.main:app --reload
```

Visit: http://localhost:8001/docs

## 📁 Where to Find Things

| Task | Location |
|------|----------|
| Add new agent | Create folder in `/agents/` |
| Add API endpoint | `backend/app/api/routes.py` |
| Modify settings | `backend/.env` |
| Add security rule | `backend/app/security/__init__.py` |
| Update logging | `backend/app/core/logging_config.py` |
| Add model | `backend/app/models/__init__.py` |
| Write tests | `backend/tests/test_*.py` or `agents/*/tests/` |

## 🔧 Common Commands

### Setup
```bash
# Install dependencies
pip install -e ".[dev]"

# Format code
black app/ tests/

# Lint
ruff check app/

# Type check
mypy app/
```

### Testing
```bash
# Run all tests
pytest -v

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test
pytest tests/test_security.py::test_path_validator_rejects_traversal -v
```

### Running
```bash
# Development (auto-reload)
uvicorn app.main:app --reload

# Production (4 workers)
uvicorn app.main:app --workers 4 --host 0.0.0.0 --port 8001
```

## 🏗️ Create New Agent (Step-by-Step)

### 1. Create Directory Structure
```bash
mkdir -p agents/my_agent/{tools,tests}
cd agents/my_agent
```

### 2. Create manifest.json
```json
{
  "name": "my_agent",
  "version": "1.0.0",
  "description": "My custom agent",
  "author": "Your Name",
  "entry_point": "main.py",
  "agent_class": "MyAgent",
  "capabilities": ["capability1", "capability2"],
  "permission_scope": ["file:read"]
}
```

### 3. Create config.yaml
```yaml
name: my_agent
version: 1.0.0
# Agent-specific configuration
```

### 4. Create main.py
```python
from app.services.plugin_manager import IAgent

class MyAgent(IAgent):
    def can_handle(self, intent: str) -> bool:
        return "keyword" in intent.lower()
    
    async def plan(self, intent: str, context: dict) -> dict:
        return {"steps": [...]}
    
    async def execute(self, plan: dict) -> dict:
        return {"result": "success"}
    
    async def summarize(self, result: dict) -> str:
        return "Summary of results"
```

### 5. Create prompts.py
```python
SYSTEM_PROMPT = "Your agent's system prompt"
```

### 6. Create tools/__init__.py
```python
# Tools for your agent
```

### 7. Create tests/test_my_agent.py
```python
import pytest

@pytest.mark.asyncio
async def test_my_agent_can_handle():
    from main import MyAgent
    agent = MyAgent()
    assert agent.can_handle("keyword")
```

### 8. Run and Test
```bash
pytest tests/ -v
```

## 🔐 Security Best Practices

### Path Validation
```python
from app.security import path_validator

# Always validate user-provided paths
safe_path = path_validator.sanitize_path(user_input)
```

### Input Validation
```python
from app.security import InputValidator

# Validate agent inputs
validated = InputValidator.validate_agent_input(data)
```

### RBAC Check
```python
from app.security import rbac_manager

rbac_manager.check_permission(user_role, "agent:execute")
```

### Audit Logging
```python
from app.core.logging_config import log_audit_event

log_audit_event(
    event_type="agent_execute",
    actor="user123",
    resource="my_agent",
    action="execute",
    result="success"
)
```

## 📊 API Quick Reference

### List Agents
```bash
curl http://localhost:8001/api/v1/agents
```

### Get Agent Details
```bash
curl http://localhost:8001/api/v1/agents/log_analysis_agent
```

### Execute Agent
```bash
curl -X POST http://localhost:8001/api/v1/agents/log_analysis_agent/execute \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "log_analysis_agent",
    "input_data": {
      "log_folder_path": "/var/log"
    }
  }'
```

### Health Check
```bash
curl http://localhost:8001/api/v1/health
```

### Interactive API Docs
```
http://localhost:8001/docs
```

## 🐛 Troubleshooting

### Agent Not Loading
**Problem**: Agent doesn't appear in `/agents` list

**Solution**:
1. Check agent folder structure (manifest.json exists?)
2. Check manifest.json validation: `json manifest.json`
3. Check logs: `grep -i error logs/`
4. Verify entry_point and agent_class match your code

### Import Errors
**Problem**: `ModuleNotFoundError` when loading agent

**Solution**:
1. Check all required files exist (main.py, config.yaml, tools.py, prompts.py)
2. Verify `sys.path` doesn't have conflicts
3. Check Python version: `python --version` (need 3.10+)
4. Reinstall dependencies: `pip install -e ".[dev]"`

### Path Validation Errors
**Problem**: `SecurityException: Path access denied`

**Solution**:
1. Check allowed paths in `.env`:
   ```
   PLUGIN_ALLOWED_PATHS=["/agents","/your/custom/path"]
   ```
2. Use absolute paths
3. Ensure path exists and is readable

### Tests Failing
**Problem**: `pytest` shows failures

**Solution**:
```bash
# Check test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run with verbose output
pytest -vv -s

# Check imports
python -c "import app; print(app.__file__)"

# Run single test
pytest tests/test_security.py::test_path_validator_safe_path -vv
```

## 💾 Environment Variables

### Development (.env)
```
ENVIRONMENT=development
DEBUG=true
CORS_ORIGINS=["http://localhost:3000"]
SLM_MODEL_PATH=/models/qwen2.5-coder-1.5b-instruct-gguf/model.gguf
SLM_MODEL_THREADS=4
PLUGIN_AUTO_DISCOVERY=true
AUDIT_LOGGING_ENABLED=true
LOG_LEVEL=DEBUG
LOG_FORMAT=json
```

### Production Recommendations
```
ENVIRONMENT=production
DEBUG=false
JWT_SECRET_KEY=<strong-random-key>
PLUGIN_TRUSTED_SOURCES=internal
AGENT_EXECUTION_TIMEOUT_SECONDS=300
AGENT_MEMORY_LIMIT_MB=512
```

## 📚 File Templates

### New Agent Manifest
See: `agents/log_analysis_agent/manifest.json`

### New API Route
See: `backend/app/api/routes.py`

### New Security Check
See: `backend/app/security/__init__.py`

### New Model/Schema
See: `backend/app/models/__init__.py`

### New Test
See: `backend/tests/test_plugin_manager.py`

## 🔄 Common Workflows

### Add Agent to Allowlist
Edit `.env`:
```
PLUGIN_ALLOWED_PATHS=["/agents","/custom/agents","/opt/agents"]
```

### Enable Debug Logging
Edit `.env`:
```
DEBUG=true
LOG_LEVEL=DEBUG
LOG_FORMAT=console
```

### Disable Plugin Auto-Discovery
Edit `.env`:
```
PLUGIN_AUTO_DISCOVERY=false
```

Then manually load:
```python
from app.services.plugin_manager import PluginManager

pm = PluginManager()
await pm.load_plugin("/agents/my_agent")
```

### Add Custom Permission
Edit `backend/app/security/__init__.py`:
```python
self.roles = {
    "admin": [..., "my_permission:action"],
}
```

## 🎯 Performance Tips

- Use async/await for I/O operations
- Cache agent instances in registry
- Limit log file size in agent config
- Use path validation to fail fast
- Monitor response times in production

## 📖 Further Reading

- `backend/README.md` - Backend setup and architecture
- `ARCHITECTURE.md` - Detailed architecture and design patterns
- `agents/log_analysis_agent/README.md` - Agent development guide
- `AGENTS.md` - Original specification and requirements

---

**Last Updated**: 2024-01-17
**Version**: 1.0.0
