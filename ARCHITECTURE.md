# Architecture & Design Guide

## Phase 1 Complete: Foundation

### What's Built

✅ **Backend FastAPI Skeleton**
- Modular architecture with clean separation of concerns
- Dependency injection ready
- Async/await throughout
- API versioning (v1)

✅ **Plugin Manager**
- Auto-discovery of agents in designated folders
- Manifest validation
- Safe dynamic module loading
- Path allowlisting security
- Hot-reload support

✅ **Agent Registry**
- Central agent lifecycle management
- Health monitoring
- Execution context handling
- Agent discovery and registration

✅ **Log Analysis Agent (Sample)**
- Fully functional first agent
- Multiple log format support
- Pattern detection and analysis
- Remediation suggestions

✅ **Security Module**
- Path validation with allowlisting
- Input sanitization
- RBAC framework (extensible)
- Audit logging for compliance

✅ **Configuration System**
- Environment-based settings
- Type validation with Pydantic
- 12-factor app compliant

✅ **Structured Logging**
- JSON output for log aggregation
- Audit trail support
- Enterprise compliance ready

## Architecture Diagrams

### Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Application                    │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                   API Routes (v1)                      │ │
│  │  /health, /agents, /agents/{id}/execute, /plugins    │ │
│  └────────────┬─────────────────────────────────────────┘ │
│               │                                             │
│  ┌────────────▼─────────────────────────────────────────┐ │
│  │              Agent Registry                          │ │
│  │  - Agent lifecycle management                        │ │
│  │  - Health checks                                     │ │
│  │  - Execution coordination                            │ │
│  └────────────┬─────────────────────────────────────────┘ │
│               │                                             │
│  ┌────────────▼─────────────────────────────────────────┐ │
│  │           Plugin Manager                             │ │
│  │  - Discovery & validation                            │ │
│  │  - Dynamic loading                                   │ │
│  │  - Manifest parsing                                  │ │
│  └────────────┬─────────────────────────────────────────┘ │
│               │                                             │
├───────────────┼──────────────────────────────────────────────┤
│               │                                             │
│  ┌────────────▼──────┐  ┌──────────────────────────────┐  │
│  │  Plugin Agents    │  │   Security & Config          │  │
│  │  ┌──────────────┐ │  │  ┌────────────────────────┐  │  │
│  │  │ Log Analysis │ │  │  │ Path Validator        │  │  │
│  │  │ ServiceNow   │ │  │  │ Input Validator       │  │  │
│  │  │ GitHub       │ │  │  │ RBAC Manager          │  │  │
│  │  │ Terraform    │ │  │  │ Audit Logger          │  │  │
│  │  └──────────────┘ │  │  └────────────────────────┘  │  │
│  └───────────────────┘  └──────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Infrastructure                                       │  │
│  │  - Logging (Structured JSON)                        │  │
│  │  - Error Handling (Custom Exceptions)               │  │
│  │  - Configuration (Pydantic + .env)                  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Agent Execution Flow

```
User Request
    │
    ▼
┌─────────────────────────────────┐
│  API Endpoint                   │
│  /agents/{agent_id}/execute     │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│  Agent Registry                 │
│  - Validate agent exists        │
│  - Check if enabled             │
│  - Log audit event              │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│  Agent Instance                 │
│  1. can_handle(intent)          │
│  2. plan(intent, context)       │
│  3. execute(plan)               │
│  4. summarize(result)           │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│  Return Result                  │
│  - Execution ID                 │
│  - Status                       │
│  - Result Data                  │
│  - Summary                      │
└─────────────────────────────────┘
```

### Security Layers

```
┌──────────────────────────────────────────────┐
│  Layer 1: Input Validation                   │
│  - RequestBody validation (Pydantic)         │
│  - String length checks                      │
│  - Pattern detection                         │
└──────────┬───────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────┐
│  Layer 2: Authentication (JWT Ready)         │
│  - Token validation                          │
│  - User context extraction                   │
└──────────┬───────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────┐
│  Layer 3: Authorization (RBAC)               │
│  - Permission checks                         │
│  - Resource access control                   │
└──────────┬───────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────┐
│  Layer 4: Path Validation                    │
│  - Allowlist checking                        │
│  - Directory traversal prevention            │
│  - Null byte filtering                       │
└──────────┬───────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────┐
│  Layer 5: Audit Logging                      │
│  - Event logging                             │
│  - Compliance tracking                       │
└──────────────────────────────────────────────┘
```

## Design Patterns Used

### 1. **Plugin Architecture**
- Enables extensibility without modifying core
- Dynamic loading and hot-reload
- Manifest-driven discovery

### 2. **Agent Interface (Strategy Pattern)**
All agents implement `IAgent` contract:
```python
class IAgent(ABC):
    def can_handle(intent: str) -> bool
    async def plan(intent: str, context: dict) -> dict
    async def execute(plan: dict) -> dict
    async def summarize(result: dict) -> str
```

### 3. **Registry Pattern**
Central registry for agent lifecycle management:
- Discovery and registration
- Health monitoring
- Execution coordination

### 4. **Dependency Injection**
Ready for enterprise DI frameworks:
- Loose coupling
- Easy testing
- Configuration-driven

### 5. **Clean Architecture**
```
Entities (Domain Models)
    ↑
Use Cases (Services)
    ↑
Interface Adapters (API, Security)
    ↑
Frameworks (FastAPI, Pydantic)
```

### 6. **Error Taxonomy**
Custom exception hierarchy:
```
PlatformException
├── PluginException
├── AgentException
├── SecurityException
├── ValidationException
└── ResourceNotFoundException
```

## Code Organization

### SOLID Principles Applied

**S - Single Responsibility**
- `PluginManager`: Plugin lifecycle only
- `AgentRegistry`: Agent management only
- `PathValidator`: Path validation only

**O - Open/Closed**
- Open for extension (new agents)
- Closed for modification (IAgent interface)

**L - Liskov Substitution**
- All agents implement IAgent interface
- Interchangeable at runtime

**I - Interface Segregation**
- Minimal IAgent interface
- Agents only implement what they need

**D - Dependency Inversion**
- Depend on abstractions (IAgent)
- Not concrete implementations

## Security Model

### Zero Trust
- All inputs validated
- All paths checked
- All actions audited

### Defense in Depth
- Multiple validation layers
- Input + path + permission checks
- Fallback security mechanisms

### Principle of Least Privilege
- Agents have minimum required permissions
- Paths restricted to allow lists
- Users start with minimal access

## Performance Characteristics

| Component | Complexity | Notes |
|-----------|-----------|-------|
| Plugin Discovery | O(n) | Linear scan of directories |
| Agent Registry | O(1) | Hash lookup for agent access |
| Plugin Loading | O(1) | Single module import |
| Path Validation | O(1) | Resolved path comparison |
| Request Processing | O(1) | Fixed overhead |

## Scalability Considerations

### Current Limitations
- Single-threaded plugin loading
- In-memory agent registry
- No distributed execution

### Future Improvements
- Parallel agent initialization
- Distributed registry (Redis)
- Queue-based execution (Celery)
- Load balancing across workers

## Testing Strategy

### Unit Tests
- Individual component testing
- Mock external dependencies
- Focus on business logic

### Integration Tests
- Plugin loading and agent execution
- API endpoint testing
- End-to-end workflows

### Coverage Goal: >80%

```
backend/tests/
├── test_plugin_manager.py
├── test_security.py
├── test_models.py
├── test_api.py
└── fixtures/
    └── sample_logs/
```

## Deployment Architecture

### Development
```
Local FastAPI Dev Server
    └── Plugin Directory: ./agents
```

### Production
```
Docker Container
    └── Uvicorn Workers
        └── Plugin Volume Mount: /agents
```

### Enterprise
```
Kubernetes
    ├── FastAPI Deployment
    ├── ConfigMap (settings)
    ├── PersistentVolume (plugins)
    └── HPA (auto-scaling)
```

## Next Phase Goals

### Phase 2: SLM Integration & Chat
- [ ] llama-cpp-python integration
- [ ] Local model loading
- [ ] Chat endpoint with streaming
- [ ] Session memory management

### Phase 3: Frontend
- [ ] React ChatGPT-style UI
- [ ] WebSocket streaming
- [ ] Session history
- [ ] Agent selector

### Phase 4: Expansion
- [ ] ServiceNow agent
- [ ] GitHub Actions agent
- [ ] Terraform agent
- [ ] Ansible agent

### Phase 5: Enterprise Features
- [ ] Full RBAC with DB
- [ ] OAuth 2.0 integration
- [ ] Multi-tenancy support
- [ ] Audit compliance reports

## Maintenance Guidelines

### Adding New Agents
1. Create folder: `/agents/my_agent`
2. Create `manifest.json` with metadata
3. Implement `IAgent` interface in `main.py`
4. Include tests in `tests/`
5. Document in `README.md`

### Modifying Core Services
- Maintain backward compatibility
- Update version in settings
- Add migration scripts if needed
- Update tests

### Security Updates
- Regular dependency updates
- Security scanning (bandit)
- Code review for security changes
- Audit trail verification

---

**Architecture Version**: 1.0
**Last Updated**: 2024-01-17
**Maintainer**: AI Platform Team
