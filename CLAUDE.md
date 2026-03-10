# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## System Overview

This is an **A2A (Agent2Agent) multi-agent system** for production code verification. It implements Google's A2A protocol specification with LLM-driven orchestration using AWS Bedrock (Claude 3.5 Sonnet).

### Core Architecture Pattern

```
┌─────────────────────────────────────────────────────────┐
│  App (Port 8006) - Web UI + S3 Gateway                 │
│  Uploads artifacts → Triggers orchestrator via A2A      │
└────────────────────┬────────────────────────────────────┘
                     │ A2A Protocol (JSON-RPC 2.0)
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Orchestrator Agent (Port 8000) - LLM Brain             │
│  • Bedrock Claude decides which agents to call          │
│  • Downloads code from S3 → /tmp/workspace/{task_id}/   │
│  • Coordinates specialists via A2A protocol             │
│  • Uploads results back to S3                           │
└──────┬──────────┬──────────┬──────────┬─────────────────┘
       │          │          │          │
       ▼          ▼          ▼          ▼
  Code Logic  Research  Test Run  Validation
  (8001)      (8003)    (8004)    (8005)
  All agents read/write from shared workspace
```

## Key Architectural Concepts

### 1. A2A Protocol Implementation

Every agent is a **A2A-compliant server** (using official `a2a` SDK):
- **AgentCard**: Exposed at `/.well-known/agent.json` - describes capabilities, skills
- **Task-based execution**: Async operations with status tracking (`submitted`, `running`, `completed`, `error`)
- **Message format**: `Message` with `parts` (can be `TextPart` or `DataPart`)
- **A2AClient**: Orchestrator uses this to call downstream agents

### 2. LLM-Driven Orchestration

The orchestrator is **NOT rule-based** - it uses an LLM agentic loop:

**Implementation in `src/orchestorator_agent/agent.py:llm_run()`:**
1. LLM receives task + agent registry (in system prompt from `prompt.txt`)
2. LLM responds with JSON decisions: `{"action": "call_agent", "agent_id": "...", "instruction": "..."}`
3. Orchestrator calls that agent via A2A protocol
4. Agent result fed BACK into LLM messages
5. LLM decides next step (call another agent or return `final_answer`)
6. Max 10 turns to prevent infinite loops

**Why this matters**: To modify agent selection logic, edit `src/orchestorator_agent/prompt.txt`, NOT the code.

### 3. Shared Workspace Pattern

Each verification task creates an isolated workspace:
```
/tmp/workspace/{task_id}/
├── code.zip (downloaded from S3 by orchestrator)
├── [extracted source files]
└── verification_results.json (aggregated results)
```

**Benefits**:
- Agents use simple file I/O (no S3 credentials needed)
- Orchestrator handles S3 download/upload/cleanup
- Isolated per task (parallel executions don't conflict)

**Agent communication**: Each agent receives `DataPart` with `{"workspace": "/tmp/workspace/{id}", "project_name": "...", "task_id": "..."}`

### 4. Docker Compose Architecture

All services run via `src/docker-compose.yml`:
- Single shared `Dockerfile.agent` with build arg `AGENT_DIR`
- Shared `src/shared/` module copied into all containers
- PostgreSQL for app's task storage (orchestrator uses in-memory A2A task store)
- Internal network `a2a-network` for inter-agent communication

## Development Commands

### Start All Services
```bash
cd src
docker-compose up --build
# Or for detached mode:
docker-compose up -d --build

# View logs:
docker-compose logs -f orchestrator-agent
docker-compose logs -f app
```

### Stop All Services
```bash
cd src
docker-compose down
# With volume cleanup:
docker-compose down -v
```

### Start Individual Agent (for development)
```bash
cd src/orchestorator_agent
pip install -r requirements.txt
python agent.py  # Runs on port 8000

# In another terminal:
cd src/code_logic_agent
pip install -r requirements.txt
PORT=8001 python agent.py
```

### Test Complete Workflow
```bash
python test_verification.py
# Prerequisites: All services running + at least one artifact uploaded
```

### Check Agent Health
```bash
curl http://localhost:8000/.well-known/agent.json  # Orchestrator card
curl http://localhost:8001/.well-known/agent.json  # Code logic agent card
# Health check (if implemented):
curl http://localhost:8000/health
```

### Access Web UI
- **Main app**: http://localhost:8006
- **Upload & trigger**: http://localhost:8006 (index.html)
- **Task dashboard**: http://localhost:8006/tasks.html
- **Progress tracker**: http://localhost:8006/progress.html?task_id={id}

## Environment Variables

Required in `.env` (or docker-compose environment):

```bash
# AWS (required for S3 + Bedrock)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_SESSION_TOKEN=...  # if using SSO/temp credentials
S3_BUCKET_NAME=a2a-multi-agent-artifacts

# PostgreSQL (for app only)
DATABASE_URL=postgresql://a2a_user:a2a_password@postgres:5432/a2a_dashboard

# Ports (optional overrides)
PORT=8000  # orchestrator
```

**Note**: Orchestrator needs Bedrock access for Claude model. Ensure IAM role/credentials have `bedrock:InvokeModel` permission.

## Code Structure Critical Paths

### Adding a New Specialized Agent

1. Create `src/new_agent/agent.py` with:
   ```python
   from a2a.server.agent_execution import AgentExecutor, RequestContext
   from a2a.server.apps import A2AStarletteApplication

   class NewAgentExecutor(AgentExecutor):
       async def execute(self, context: RequestContext, event_queue: EventQueue):
           # Parse context.message.parts
           # Do work
           # Emit results via TaskUpdater.add_artifact()
   ```

2. Add to `src/orchestorator_agent/agent.py`:
   ```python
   KNOWN_AGENTS = {
       "new-agent": "http://localhost:8007",
       ...
   }
   AGENT_DESCRIPTIONS = {
       "new-agent": "What this agent does",
       ...
   }
   ```

3. Add service to `src/docker-compose.yml`:
   ```yaml
   new-agent:
     build:
       context: ..
       dockerfile: src/Dockerfile.agent
       args:
         AGENT_DIR: new_agent
     ports:
       - "8007:8007"
     environment:
       - PORT=8007
   ```

4. **The LLM will automatically discover and use it** based on the description in the system prompt.

### Modifying Orchestration Logic

**DO NOT** edit the `llm_run()` method in `agent.py`. Instead:

1. Edit `src/orchestorator_agent/prompt.txt`
2. Update agent descriptions in `AGENT_DESCRIPTIONS` dict
3. The LLM will adapt its behavior based on the prompt

Example: To make orchestrator always call validation first, add to prompt:
```
## Required Order
- ALWAYS call validation-agent first for security checks
- Then proceed with other agents based on validation results
```

### Shared S3 Client Usage

All agents import from `src/shared/s3_client.py`:
```python
from shared.s3_client import SharedS3Client

s3 = SharedS3Client()  # Reads from env vars
s3.download_file(s3_key, local_path)
s3.upload_file(local_path, s3_key)
s3.get_presigned_url(s3_key)  # 7-day expiry
```

### A2A Message Parsing Pattern

Standard pattern in all agent executors:
```python
async def execute(self, context: RequestContext, event_queue: EventQueue):
    code_text = ""
    workspace = None

    for part in context.message.parts:
        if isinstance(part.root, TextPart):
            code_text += part.root.text
        elif isinstance(part.root, DataPart):
            data = dict(part.root.data) or {}
            workspace = data.get("workspace")
            # Extract other data...

    # Do work with code_text or workspace
    # Emit results with TaskUpdater
```

## Important Implementation Details

### Orchestrator's Two Workflows

1. **`llm_run()`** - LLM-driven agentic loop (NEW - default)
   - Used for verification workflow
   - LLM decides which agents to call and when
   - Handles complex decision-making

2. **`run_full_analysis()`** - Legacy hardcoded pipeline (DEPRECATED)
   - Sequential: code-logic → research → validation → tests
   - No LLM decisions
   - Keep for backwards compatibility only

### Docker Build Context

The Dockerfile is at `src/Dockerfile.agent` but context is `..` (parent dir):
```dockerfile
# Copies from project root:
COPY src/shared /app/shared
COPY src/${AGENT_DIR}/agent.py .
```

This allows shared module access without git submodules.

### PostgreSQL vs In-Memory Task Store

- **App (`src/app/`)**: Uses PostgreSQL for persistent task history (web UI)
- **Agents**: Use `InMemoryTaskStore` from A2A SDK (stateless, restart clears tasks)

This is intentional - agents are stateless workers, app provides persistence.

### Agent Ports Convention

- **8000**: Orchestrator (entry point)
- **8001-8005**: Specialist agents
- **8006**: App/web UI (user-facing)
- **5432**: PostgreSQL

When adding agents, use 8007+.

## Debugging Tips

### Orchestrator Returns "Internal Server Error"

1. Check Bedrock access: `aws bedrock list-foundation-models --region us-east-1`
2. Check `prompt.txt` exists: `ls -la src/orchestorator_agent/prompt.txt`
3. View orchestrator logs: `docker-compose logs orchestrator-agent`
4. Common issue: Missing AWS credentials or wrong region

### Agent Not Discovered

1. Check agent is running: `curl http://localhost:8001/.well-known/agent.json`
2. Verify agent is in `KNOWN_AGENTS` dict in orchestrator
3. Check Docker network: `docker network inspect src_a2a-network`

### Workspace Files Not Found

1. Check S3 download succeeded (orchestrator logs)
2. Verify zip extraction: `ls -la /tmp/workspace/{task_id}/`
3. Ensure agents receive correct `workspace` path in DataPart

### LLM Not Calling Expected Agents

1. Review system prompt in `src/orchestorator_agent/prompt.txt`
2. Check agent descriptions are clear and specific
3. Increase `max_tokens` in `llm_run()` if JSON gets truncated
4. Add explicit examples to prompt for desired behavior

## Testing Patterns

### Unit Test Individual Agent
```python
# Test agent's execute() method directly
from src.code_logic_agent.agent import CodeLogicAgentExecutor
from a2a.types import Message, Part, TextPart

executor = CodeLogicAgentExecutor()
# Mock RequestContext and EventQueue
# Call executor.execute(context, queue)
# Assert on emitted artifacts
```

### Integration Test Full Workflow
Use `test_verification.py` as template - it:
1. Uploads artifact
2. Triggers orchestrator
3. Polls task status
4. Validates results

### Manual A2A Protocol Test
```bash
# Direct A2A call to orchestrator
curl -X POST http://localhost:8000/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-123",
    "method": "a2a.createTask",
    "params": {
      "message": {
        "role": "user",
        "parts": [
          {"kind": "text", "text": "Analyze this code"},
          {"kind": "data", "data": {"code": "print(123)", "language": "python"}}
        ]
      }
    }
  }'
```

## Common Gotchas

1. **Agent ports must match Docker Compose and KNOWN_AGENTS dict** - mismatch causes discovery failures
2. **Workspace cleanup happens in finally block** - if orchestrator crashes, `/tmp/workspace/` may fill up
3. **S3_BUCKET_NAME must exist and be accessible** - orchestrator won't create it
4. **LLM responses must be valid JSON** - malformed JSON breaks the loop (handled gracefully now)
5. **A2A SDK uses Pydantic models** - be careful with dict vs model conversions
6. **Docker Compose env vars override code defaults** - check docker-compose.yml first when debugging config

## Migration Notes

### From Old `intract-orchestrator/` to New `app/`

The old directory was removed. Key changes:
- S3 client moved to `src/shared/s3_client.py` (shared by all)
- Orchestrator now uses Bedrock LLM instead of hardcoded rules
- App is now a simple trigger/UI, orchestrator does heavy lifting
- PostgreSQL added for web UI task history

### Adding LLM to Existing Orchestrator

If you're maintaining this:
1. The `llm_run()` method is the entry point
2. Prompt is externalized to `prompt.txt` for easy tuning
3. Agent descriptions in code feed into system prompt
4. Don't modify the agentic loop - tune the prompt instead
