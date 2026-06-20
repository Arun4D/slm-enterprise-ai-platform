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
- Parse runner pipeline execution logs
- Detect non-zero exit codes
- Suggest dynamic node allocations
- Identify package build failures
- Direct CI/CD runner repairs
- **Code Generation**: Generate secure, highly optimized GitHub Actions CI/CD workflows and configurations to fast-track developer setup
- **Code Validation**: Validate pasted chat text, local files, or uploaded workflow YAML/logs for trigger coverage, runner definitions, action pinning, least-privilege `permissions`, inline secret risk, dependency-cache usage, and non-reproducible build commands
- Generated workflows MUST be deterministic Python template outputs reviewed by the agent guardrail engine; the local SLM may route/plan/summarize only and MUST NOT directly execute or invent CI/CD commands
- Validation inputs MUST support both browser file uploads and pasted text in chat

D. Terraform Agent
- Validate Terraform plans and plan files
- Scan static security configurations
- Enforce strict public ingress port guardrails
- Audit resource tag completeness
- Provide cloud safety mitigations
- **Code Generation**: Generate secure, compliant HCL resource blocks (such as encrypted VPCs or secure instances with standard tags) to fast-track infrastructure development
- **Code Validation**: Validate pasted chat text, local files, or uploaded `.tf`/plan content for public admin ingress, plaintext HTTP exposure, encryption defaults, required tags, provider secret leakage, and resource/module structure
- Generated HCL MUST use approved deterministic Python templates with secure defaults; the local SLM may route/plan/summarize only and MUST NOT directly provision infrastructure
- Validation inputs MUST support both browser file uploads and pasted text in chat

E. Ansible Agent
- Parse playbooks and task attributes
- Validate YAML syntactic configurations
- Review package module installations over raw shell
- Scan dry-run ping connectivity status
- Trace inventory nodes latency
- **Code Generation**: Generate modular, idempotent YAML playbooks (such as system updates or Nginx webservers) to fast-track host provisioning
- **Code Validation**: Validate pasted chat text, local files, or uploaded playbooks/inventory snippets for play targets, task sections, raw shell/command usage, package state declarations, explicit privilege escalation, inline secret risk, and named tasks
- Generated playbooks MUST use deterministic Python templates and Ansible built-in modules; the local SLM may route/plan/summarize only and MUST NOT directly execute playbooks
- Validation inputs MUST support both browser file uploads and pasted text in chat

F. Monitoring Agent
- Fetch virtualization resource metrics
- Monitor VM CPU and Memory limits
- Audit storage allocation bounds
- Consolidate active site reliability alerts
- Synthesize virtual container mitigations

G. VMware Agent
- Scan physical VMware ESXi cluster nodes and virtual center structures
- Map active SSD and SATA datastore allocations
- Verify vCPU allocations and RAM overcommit levels
- Execute VM storage migrations (vMotion workflows)
- **Operational Q&A**: Resolve natural language questions regarding physical host server count, cluster usage/utilization, CPU/Memory profiles, and virtual networks

H. Nutanix Agent
- Audit hyperconverged infrastructure (HCI) storage pools and tiers
- Verify replication resiliency factor compliance (RF2 vs RF3)
- Scans virtual machine overcommits and CPU limits
- Audit Nutanix hypervisor configurations using Prism Central API
- **Operational Q&A**: Resolve natural language questions regarding node counts, storage capacity usage, CPU/Memory configurations, and virtual switches/backplanes


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


# COMPANY STANDARDS COMPLIANCE & CUSTOMIZATION ENGINE:
Both Terraform and Ansible agents feature a configuration-driven **Company Standards Customization Engine** that allows DevOps and security teams to align code generation and validation rules to strict enterprise policies.

## 1. Terraform Agent Customization
Configured in [config.yaml](file:///home/arun/Workspace/arun4d_github/slm-enterprise-ai-platform/agents/terraform_agent/config.yaml) under `company_standards`:
- **Enforced Tags**: Validates that S3 buckets, EC2 instances, resource groups, databases, and vnets contain all required company tags (e.g. `Environment`, `Owner`, `Project`, `ManagedBy`).
- **Dynamic Tag Generation**: Replaces template tag definitions dynamically using a regex-based post-processor wrapper (`_post_process_tags`), ensuring all generated HCL is automatically tagged.
- **Port Ingress Limits**: Prohibits public administrative access on ports `22` and `3389` from `0.0.0.0/0`.
- **Encryption Policies**: Demands storage volume and block device encryption (`encrypted = true`).
- **TLS Version Enforcement**: Checks and flags plaintext port `80` listener access without redirection or minimal TLS version `1.2`.

## 2. Ansible Agent Customization
Configured in [config.yaml](file:///home/arun/Workspace/arun4d_github/slm-enterprise-ai-platform/agents/ansible_agent/config.yaml) under `company_standards`:
- **Task Naming Policy**: Requires every task to have a descriptive `name:` for clean logs and execution logs audits.
- **Forbidden Raw Shell Modules**: Checks and flags the use of `shell` or `command` modules, steering operators to use idempotent modules.
- **Explicit Privilege Escalation**: Asserts the explicit use of `become` directives for system configurations.
- **Log Exposure Protection**: Detects variables containing secrets (like password/token) and alerts if they lack the `no_log: true` safety flag to prevent credential leaks.
- **Metadata Tagging**: Configures default metadata tags under `common_tags:` for all playbooks.

