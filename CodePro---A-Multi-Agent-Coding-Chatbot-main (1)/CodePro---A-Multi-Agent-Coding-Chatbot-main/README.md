# Multi-Agent Coding Assistant (FastAPI + LangGraph)

A small FastAPI service that routes a user’s message through a **LangGraph** state machine.
It uses an LLM (AWS Bedrock via `langchain_aws.ChatBedrock`) to classify intent and then executes one or more specialized agents:

- **Coding Agent**: generates/updates code.
- **Review Agent**: reviews code and returns pass/fail + detected issues.
- **Research Agent**: uses external tools (MCP) to gather supporting context.

## High-level architecture

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                                   Client / UI                                │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │  POST /api/chat
                                       v
┌──────────────────────────────────────────────────────────────────────────────┐
│ FastAPI Router: `src/routers/router.py`                                      │
│   - endpoint: `/api/chat`                                                    │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       v
┌──────────────────────────────────────────────────────────────────────────────┐
│ Service: `src/services/coding_service.py`                                    │
│   - validates user + thread (Postgres via SQLAlchemy async)                  │
│   - invokes LangGraph via `GraphService.invoke_graph(...)`                   │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       v
┌──────────────────────────────────────────────────────────────────────────────┐
│ Orchestrator: `src/services/graph_service.py`                                │
│   LangGraph StateGraph(CommonState)                                          │
│   nodes: decision_node, coding_node, review_node, research_node              │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       v
┌─────────────────────────────────────────────────────────────────────────────────┐
│ Agents                                                                          │
│   - `src/agents/coding_agent.py`                                                │
│   - `src/agents/review_agent.py` (uses `src/tools/tool.py:detailed_code_review`)│
│   - `src/agents/research_agent.py` (loads MCP tools, e.g., DuckDuckGo)          │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 🧭 Terminal-style flow diagram (decision routing)

Intent classification happens in `GraphService.decision_node()` using `DECISION_PROMPT`
from `src/prompts/decision_node_prompt.py`.

Intents:
- `coding`
- `review`
- `research`
- `research_and_code`
- `off_context`

Below is the technical routing you asked for (terminal-level flow).

```text
user
  |
  |  (POST /api/chat)
  v
decision_node  [LLM intent classifier]
  |
  +--> intent=coding -------------------------------> coding_agent
  |                                                   |
  |                                                   v
  |                                                review_agent
  |                                                   |
  |      +-- if review_status == FAILED --------------+----> coding_agent (iterate fixing)
  |      |
  |      +-- else (PASSED/anything else) ------------------> END -> respond to user
  |
  +--> intent=review -------------------------------> review_agent
  |                                                   |
  |      +-- if review_status == FAILED -------------------> coding_agent
  |      |                                                  |
  |      |                                                  v
  |      |                                               review_agent
  |      |                                                  |
  |      |                               (then END; graph stops after review node)
  |      |
  |      +-- else -----------------------------------------> END -> respond to user
  |
  +--> intent=research -----------------------------------> research_agent
  |                                                   |
  |                                                   +--> END -> respond to user
  |
  +--> intent=research_and_code -----------------------> research_agent
  |                                                   |
  |                                                   v
  |                                                coding_agent
  |                                                   |
  |                                                   v
  |                                                review_agent
  |                                                   |
  |                                                   +--> END -> respond to user
  |
  +--> intent=off_context -----------------------------> END
                                                      |
                                                      v
                                              respond to user (polite message)
```

### Notes on the “review failed → research” vs code behavior

Your requested flow says:
> “if review is the intent review agent with review failed, go to research agent”.

Current code in `GraphService.decision_router()` routes **review failure → `coding_node`**, not
`research_node`:

- If the graph is at `review_node` and `review_status == "FAILED"` → next is `coding_node`.

If you want **FAILED review to go to research first**, we can implement that change safely
(by adding a `review_failed -> research_node` transition, and then from research back to coding).

## Key modules

- API
  - `src/routers/router.py`: `/api/chat` endpoint
- Orchestration
  - `src/services/graph_service.py`: LangGraph compilation + routing logic
  - `src/models/coding_model.py`: `CommonState` + request/response models
- Agents
  - `src/agents/coding_agent.py`: produces `{"code": ...}` JSON (string)
  - `src/agents/review_agent.py`: uses `detailed_code_review` tool; returns status + issues
  - `src/agents/research_agent.py`: loads MCP tools (DuckDuckGo) for research context
- Prompts
  - `src/prompts/decision_node_prompt.py`: intent classifier schema
  - `src/prompts/*_agent_prompt.py`: system prompts for agents
- Persistence
  - `src/repositories/database.py`: async SQLAlchemy engine/session
  - `src/repositories/coding_repository.py`: user + thread checks
  - `src/repositories/schemas/coding_schema.py`: DB models

## Response shape

The endpoint returns `APIResponse` (`src/models/coding_model.py`):

- `data`: either generated `code` (string/dict depending on agent output) or `research_context`
- `message`: currently hardcoded to `"Code generated Successfully"`
- `status_code`: `200` on success

## Local development

This repo snippet doesn’t include the app entrypoint (e.g., `main.py`) or dependency files
(`pyproject.toml` / `requirements.txt`) in the workspace tree you shared.

If you point me to the entrypoint, I can extend this README with:
- exact run command (uvicorn module path)
- required env vars for Bedrock + Postgres
- how `app.state.graph` is initialized

## Troubleshooting

- Intent classifier must return valid JSON exactly as specified in `DECISION_PROMPT`.
- `ResearchAgent` depends on MCP server availability (DuckDuckGo MCP).
- Database connection uses `settings.config` values in `src/repositories/database.py`.
