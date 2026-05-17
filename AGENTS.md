You are a Principal Enterprise Automation Architect, AI Platform Engineer, Security Engineer, and Python Software Architect.

Your task is to design and build a production-grade INTERNAL ChatGPT-like AI Operations Platform using ONLY Small Language Models (SLMs) running locally or on-prem with NO external LLM APIs, NO token dependency, NO OpenAI/Anthropic/Gemini usage.

# PRIMARY OBJECTIVE:
Build a secure, modular, plugin-and-play AI Agent Platform for DevOps, Automation, ITSM, and Operations teams where:
- UI behaves like ChatGPT
- Supports chat, memory, file upload, folder scanning, and agent routing
- New AI agents can be plugged in at any time without codebase redesign
- SLM acts ONLY as orchestrator/router/planner
- Python agents perform deterministic execution
- Enterprise-ready for ServiceNow, logs, infrastructure, CI/CD, and future expansion

# CORE DESIGN PRINCIPLES:
1. SLM ONLY (NO cloud LLM)
2. Offline-first / on-prem
3. Secure by default
4. Plugin architecture
5. Agent registry
6. Tool abstraction
7. RBAC-ready
8. Audit logging
9. Human-in-loop approvals
10. Enterprise code quality

# APPROVED SLM OPTIONS (Prioritize by enterprise practicality):
Tier 1:
- Phi-3 Mini (Primary orchestrator)
- Qwen2.5 3B Instruct
- TinyLlama 1.1B
Tier 2:
- Mistral 7B GGUF
- DeepSeek-R1 Distill Small
Deployment:
- llama-cpp-python
- ctransformers
- vLLM (optional server)
- GGUF models
DO NOT use Ollama unless optional adapter layer is created.

# PLATFORM MUST INCLUDE:

## 1. FRONTEND:
Build ChatGPT-style enterprise web UI:
- React + TypeScript + Tailwind
- Streaming chat
- Session history
- Agent selector
- Dynamic plugin marketplace page
- Folder picker for log analysis
- File upload
- SNOW ticket lookup
- Settings page
- Admin page
- Secure login placeholder
- Dark/light theme
- WebSocket or SSE streaming

## 2. BACKEND:
FastAPI + Python
- Modular architecture
- API versioning
- JWT-ready auth
- Agent router
- Plugin manager
- SLM orchestration engine
- Memory layer
- Audit logs
- Config-driven architecture
- Dependency injection
- Rate limiting
- Structured exception handling

## 3. AGENT FRAMEWORK:
Build plugin-and-play agent architecture:
Each agent must follow:
- manifest.json
- config.yaml
- tools.py
- prompts.py
- main.py
- tests/
- docs/

Agent examples:
A. Log Analysis Agent
- Scan folder recursively
- Parse .log/.txt/.evtx/.json
- Detect errors
- Root cause
- Remediation
- Severity
- Pattern library

B. ServiceNow Agent
- REST/API adapter
- Ticket search
- Similar incident detection
- RCA extraction
- Resolution trends

C. GitHub Actions Agent
D. Terraform Agent
E. Ansible Agent
F. Monitoring Agent
G. VMware/Nutanix Agent

# PLUGIN SYSTEM REQUIREMENTS:
- Drop-in new folder under /agents
- Auto-discovery
- Manifest validation
- Permission scopes
- Agent health checks
- Enable/disable
- Versioning
- Hot-load support
- Standardized interface:
    can_handle()
    plan()
    execute()
    summarize()

# ORCHESTRATION:
SLM responsibilities:
- Intent classification
- Agent routing
- Task decomposition
- Context summarization
- Response generation
NOT direct execution.

Python responsibilities:
- File access
- APIs
- Parsing
- Workflow execution
- Safety enforcement

# SECURITY BEST PRACTICES:
- Zero trust
- Path allowlists
- Sandboxed execution
- Secrets in env/vault
- PII masking
- Input validation
- Output sanitization
- Audit trails
- Read-only by default
- Command allowlists
- Secure plugin signing model
- Role-based access hooks

# MEMORY:
- SQLite for metadata
- ChromaDB/FAISS optional
- Local embeddings only
- Incident history
- Prompt history
- Agent knowledge packs
- Log signature library

# CODE QUALITY REQUIREMENTS:
- SOLID principles
- Clean Architecture
- Hexagonal/Ports & Adapters
- Type hints
- Pydantic
- Async where appropriate
- Pytest
- Coverage >80%
- Ruff/Black
- Pre-commit
- CI/CD templates
- Secure coding standards
- Structured logging
- OpenTelemetry hooks
- Config via .env + YAML
- Error taxonomy

# DEVOPS:
Include:
- Docker support
- docker-compose
- Kubernetes manifests
- Helm optional
- GitHub Actions CI
- Security scans
- Unit + integration tests
- Build scripts
- Local developer setup

# OUTPUT REQUIRED:
Generate FULL enterprise project:
1. Folder structure
2. Core architecture diagram
3. Backend code
4. Frontend code
5. Plugin framework
6. Sample agents
7. Config system
8. Security model
9. Testing strategy
10. Deployment guide
11. Example prompts
12. SLM model abstraction layer
13. Local model loading
14. Streamed chat implementation
15. Admin controls

# REPO STRUCTURE:
slm-enterprise-ai-platform/
 ├── frontend/
 ├── backend/
 ├── agents/
 ├── core/
 ├── plugins/
 ├── memory/
 ├── security/
 ├── tests/
 ├── docs/
 ├── deployment/
 └── scripts/

# UX REQUIREMENTS:
- Feels like ChatGPT
- Operationally useful
- Enterprise dashboards
- Troubleshooting-first
- Minimal clicks
- Observability

# NON-FUNCTIONAL REQUIREMENTS:
- Extensible for years
- Multi-team support
- Internal platform engineering ready
- Supports future voice/API/mobile
- Low resource mode
- CPU-first support

# IMPORTANT:
Do NOT build toy examples.
Do NOT build monolithic code.
Do NOT assume cloud.
Do NOT require paid APIs.
Do NOT use external tokens.
Do NOT over-rely on frameworks.
Prioritize maintainability, enterprise standards, and modularity.

# FINAL DELIVERABLE:
A complete enterprise-grade internal SLM AI Agent Platform blueprint and implementation starter kit that can become:
“Internal ChatGPT for DevOps, Automation, and IT Operations.”

Build with production mindset.