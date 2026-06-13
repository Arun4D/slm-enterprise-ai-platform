# Backend: SLM Enterprise AI Platform

FastAPI-based backend for the SLM Enterprise AI Operations Platform.

## Architecture

### Core Components

1. **Plugin Manager** (`app/services/plugin_manager.py`)
   - Dynamic plugin discovery and loading
   - Manifest validation
   - Safe module importing
   - Hot-reload support
   - Path allowlisting for security

2. **Agent Registry** (`app/services/agent_registry.py`)
   - Central agent lifecycle management
   - Health monitoring
   - Execution context handling
   - Agent discovery and registration

3. **Security Module** (`app/security/__init__.py`)
   - Path validation with allowlisting
   - Input sanitization
   - RBAC framework (ready for enterprise integration)
   - Defense-in-depth security model

4. **Configuration** (`app/core/config.py`)
   - Environment-based settings
   - 12-factor app compliant
   - Type-validated with Pydantic

5. **Structured Logging** (`app/core/logging_config.py`)
   - JSON output for log aggregation
   - Audit trail support
   - Enterprise compliance ready

## API Endpoints (v1)

### Health & Status
- `GET /api/v1/health` - Platform health check

### Agent Management
- `GET /api/v1/agents` - List all agents
- `GET /api/v1/agents/{agent_id}` - Get agent details
- `POST /api/v1/agents/{agent_id}/execute` - Execute agent

### Plugin Management
- `GET /api/v1/plugins` - List loaded plugins

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py          # API endpoints
│   ├── core/
│   │   ├── config.py          # Settings management
│   │   ├── exceptions.py      # Error taxonomy
│   │   └── logging_config.py  # Structured logging
│   ├── models/
│   │   └── __init__.py        # Pydantic models
│   ├── security/
│   │   └── __init__.py        # RBAC, validation, path security
│   ├── services/
│   │   ├── plugin_manager.py  # Plugin lifecycle
│   │   └── agent_registry.py  # Agent management
│   ├── __init__.py
│   └── main.py                # FastAPI app factory
├── tests/
│   ├── test_plugin_manager.py
│   ├── test_security.py
│   └── ...
├── .env.example               # Generic environment template
├── .env.linux.example         # Linux/macOS development template
├── .env.windows.example       # Windows development template
├── pyproject.toml             # Dependencies & config
└── README.md
```

## Setup & Development

### Prerequisites
- Python 3.10+
- Virtual environment

### Installation

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

pip install -e ".[dev]"
```

`llama-cpp-python` is intentionally not installed by the `dev` extra because it may
compile native C++ code on Windows and fail with CMake errors when a compatible
wheel or compiler toolchain is unavailable.

For local GGUF inference, install it explicitly after the backend is working:

```powershell
# Windows PowerShell
pip install --only-binary=:all: llama-cpp-python
```

If pip cannot find a wheel for your Python/Windows combination, use Python
3.10-3.12 x64 or install Visual Studio Build Tools with the C++ workload and
CMake, then run:

```powershell
pip install -e ".[dev-local-slm]"
```

### Environment Configuration

```bash
cp .env.linux.example .env
# Edit .env with your settings
```

On Windows:

```powershell
Copy-Item .env.windows.example .env
# Edit .env with your settings
```

### Running the Application

```bash
# Development with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 4
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_security.py -v
```

### Code Quality

```bash
# Format code
black app/ tests/

# Lint
ruff check app/ tests/

# Type checking
mypy app/

# Pre-commit hooks
pre-commit install
pre-commit run --all-files
```

## Security Features

### Path Allowlisting
All file access is validated against a whitelist of allowed directories:
```python
from app.security import path_validator

# Raises SecurityException if path is outside allowed directories
safe_path = path_validator.sanitize_path("/agents/log_analysis_agent")
```

### Input Validation
Prevents injection attacks:
```python
from app.security import InputValidator

# Validates agent input for dangerous patterns
validated = InputValidator.validate_agent_input(agent_input)
```

### RBAC Framework
Ready for enterprise integration:
```python
from app.security import rbac_manager

rbac_manager.check_permission("admin", "agent:execute")
```

### Audit Logging
Compliance tracking:
```python
from app.core.logging_config import log_audit_event

log_audit_event(
    event_type="agent_execute",
    actor="user123",
    resource="log_analysis_agent",
    action="execute",
    result="success",
)
```

## Agent Interface Contract

All agents must implement `IAgent`:

```python
class IAgent(ABC):
    @abstractmethod
    def can_handle(self, intent: str) -> bool:
        """Check if agent can handle the intent"""
        pass
    
    @abstractmethod
    async def plan(self, intent: str, context: dict) -> dict:
        """Create execution plan"""
        pass
    
    @abstractmethod
    async def execute(self, plan: dict) -> dict:
        """Execute the plan"""
        pass
    
    @abstractmethod
    async def summarize(self, result: dict) -> str:
        """Summarize execution result"""
        pass
```

## Configuration

### Settings (Environment Variables)

```
# FastAPI
ENVIRONMENT=development
DEBUG=true
CORS_ORIGINS=["http://localhost:3000"]

# SLM Model
SLM_MODEL_PATH=/models/qwen2.5-1.5b-instruct-gguf/model.gguf
SLM_MODEL_CONTEXT_SIZE=2048
SLM_MODEL_THREADS=4

# Security
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256

# Plugins
PLUGIN_AUTO_DISCOVERY=true
PLUGIN_ALLOWED_PATHS=["/agents","/plugins"]

# Agent Constraints
AGENT_EXECUTION_TIMEOUT_SECONDS=300
```

On Windows, prefer forward slashes or escaped backslashes in `.env`:

```powershell
SLM_MODEL_PATH=C:/arun/workspace/qwen2.5-1.5b-instruct-gguf/model.gguf
# or
SLM_MODEL_PATH=C:\\arun\\workspace\\qwen2.5-1.5b-instruct-gguf\\model.gguf
```

You can also point `SLM_MODEL_PATH` at the model directory; the backend will
look for `model.gguf` inside it.

## Error Handling

Structured error taxonomy:

```python
from app.core.exceptions import (
    PlatformException,
    PluginException,
    AgentException,
    SecurityException,
    ValidationException,
    ResourceNotFoundException,
)
```

All exceptions include:
- `error_code`: Machine-readable error identifier
- `status_code`: HTTP status code
- `message`: User-friendly message
- `details`: Additional context

## Next Steps

1. **Implement SLM Integration**: Add llama-cpp-python for local model loading
2. **Add Chat Memory**: Implement conversation history with SQLite/ChromaDB
3. **Build Frontend**: React UI with WebSocket streaming
4. **Add Authentication**: JWT token validation and user context
5. **Expand Agents**: ServiceNow, GitHub Actions, Terraform agents
6. **Add Observability**: OpenTelemetry instrumentation

## Code Quality Standards

- **SOLID Principles**: Applied throughout
- **Type Hints**: Comprehensive type coverage
- **Testing**: Pytest with >80% coverage target
- **Linting**: Ruff strict mode
- **Formatting**: Black for consistency
- **Async**: Used for I/O-bound operations
- **Error Handling**: Custom exception hierarchy
- **Logging**: Structured JSON output

## Deployment

### Docker

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY pyproject.toml .
RUN pip install -e .

COPY app app/
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

### Kubernetes

See `deployment/` folder for K8s manifests.

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Python Async](https://docs.python.org/3/library/asyncio.html)
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)

---

**Status**: Phase 1 Complete ✓
**Coverage**: Plugin Manager, Agent Registry, Security, Log Analysis Agent
**Next**: Phase 2 - SLM Integration & Chat Interface
