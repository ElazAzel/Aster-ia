# Agents and Skills

Asterion agents and skills are runtime manifests, not Codex skills.

They are declarative JSON files loaded by `AgentRegistry`.

## File Locations

```text
agents/*.json
skills/*.json
```

## API

- `GET /api/agents/catalog`
- `GET /api/agents/catalog/agents`
- `GET /api/agents/catalog/skills`
- `GET /api/agents/catalog/agents/{agent_id}`

## Current Agents

| Agent | Purpose | Privacy |
| --- | --- | --- |
| `research-supervisor` | Deep research decomposition and aggregation | hybrid |
| `privacy-guardian` | Privacy Radar decisions and risk blocking | local |
| `rag-librarian` | Local document indexing and retrieval | local |
| `sandbox-runner` | AgentPlan and isolated code execution | local |
| `workflow-operator` | Workflow execution and approval gates | local |
| `image-studio` | Local ComfyUI image generation | local |

## Current Skills

| Skill | Purpose |
| --- | --- |
| `privacy-radar` | Risk classification |
| `model-routing` | Local/API model selection |
| `streaming-chat` | SSE chat streaming |
| `rag-indexing` | LanceDB hybrid RAG |
| `memory-ledger` | SQLCipher memory CRUD |
| `deep-research` | SearXNG plus DuckDB research |
| `contradiction-finder` | Similar but opposing claims |
| `task-simulation` | AgentPlan generation |
| `sandboxed-code` | Isolated Python subprocess execution |
| `comfyui-generation` | Local image generation |
| `workflow-automation` | Sequential workflows and approval gates |
| `plugin-management` | MCP plugin manifest loading |

## Agent Manifest Shape

```json
{
  "id": "rag-librarian",
  "name": "RAG Librarian",
  "role": "Indexes and retrieves local documents.",
  "description": "Uses LanceDB and local embeddings.",
  "privacy_level": "local",
  "default_model": "llama3.2",
  "skills": ["rag-indexing", "privacy-radar"],
  "permissions": {
    "allowed_folders": [],
    "network": false,
    "shell": false
  },
  "system_prompt": "Short runtime prompt.",
  "escalation_policy": "When to ask the user for approval."
}
```

## Skill Manifest Shape

```json
{
  "id": "privacy-radar",
  "name": "Privacy Radar",
  "category": "safety",
  "description": "Classifies risk.",
  "privacy_level": "local",
  "inputs": ["model_type"],
  "outputs": ["PrivacyReport"],
  "tools": ["PrivacyAnalyzer"],
  "guardrails": ["External API use is red risk."]
}
```

## Design Rules

- Keep manifests declarative.
- Do not place secrets or live credentials in manifests.
- Treat unknown plugin trust levels as `danger`.
- Use `privacy_level=local` unless the agent can intentionally touch web or external systems.
- Every agent that can write files, use network, or run shell must declare it in `permissions`.
- Every skill must name the backend service or tool it relies on.
