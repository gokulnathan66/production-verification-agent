# A2A Multi-Agent System - Quick Start

## 🚀 Get Running in 5 Minutes!

This is a **minimal, working** implementation of Google's A2A (Agent2Agent) protocol with MCP integration.

---

## Prerequisites

- Python 3.9+
- pip

---

## Setup & Run

### Step 1: Install Dependencies

```bash
# Terminal 1: Setup Simple Agent
cd src/simple_agent
pip install -r requirements.txt

# Terminal 2: Setup Orchestrator
cd src/orchestrator
pip install -r requirements.txt
```

### Step 2: Start the Agent

```bash
# In Terminal 1
cd src/simple_agent
python agent.py
```

You should see:
```
🚀 Starting A2A Agent: simple-echo-agent
📍 AgentCard: http://localhost:8001/.well-known/agent-card
🔗 RPC Endpoint: http://localhost:8001/a2a
💚 Health: http://localhost:8001/health
```

### Step 3: Start the Orchestrator

```bash
# In Terminal 2
cd src/orchestrator
python orchestrator.py
```

You should see:
```
🚀 A2A Orchestrator Starting...
📍 Endpoints:
   - Main: http://localhost:8000
   - Docs: http://localhost:8000/docs
```

---

## Test It!

### Test 1: Check Agent Health

```bash
curl http://localhost:8001/health
```

Expected output:
```json
{
  "status": "healthy",
  "agentId": "simple-echo-agent",
  "activeTasks": 0,
  "completedTasks": 0
}
```

### Test 2: Get AgentCard

```bash
curl http://localhost:8001/.well-known/agent-card
```

Expected output:
```json
{
  "agentId": "simple-echo-agent",
  "name": "Simple Echo Agent",
  "endpoints": {
    "rpc": "http://localhost:8001/a2a"
  },
  "capabilities": {
    "skills": ["echo", "test", "ping"]
  }
}
```

### Test 3: Discover Agent via Orchestrator

```bash
curl -X POST http://localhost:8000/discover \
  -H "Content-Type: application/json" \
  -d '{"url": "http://localhost:8001"}'
```

Expected output:
```json
{
  "status": "discovered",
  "agent": {
    "agentId": "simple-echo-agent",
    "name": "Simple Echo Agent",
    ...
  }
}
```

### Test 4: Execute Task via Orchestrator

```bash
curl -X POST http://localhost:8000/execute \
  -H "Content-Type: application/json" \
  -d '{"request": "Hello from A2A!"}'
```

Expected output:
```json
{
  "status": "completed",
  "agent_used": "simple-echo-agent",
  "result": {
    "taskId": "...",
    "status": "completed",
    "messages": [
      {
        "role": "user",
        "parts": [{"kind": "text", "text": "Hello from A2A!"}]
      },
      {
        "role": "assistant",
        "parts": [{"kind": "text", "text": "🔄 Echo from simple-echo-agent: Hello from A2A!"}]
      }
    ]
  }
}
```

### Test 5: Direct A2A Protocol Call

```bash
curl -X POST http://localhost:8001/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-1",
    "method": "a2a.createTask",
    "params": {
      "message": {
        "role": "user",
        "parts": [
          {"kind": "text", "text": "Direct A2A call!"}
        ]
      }
    }
  }'
```

---

## Interactive API Documentation

Both services have interactive API docs (Swagger UI):

- **Agent**: http://localhost:8001/docs
- **Orchestrator**: http://localhost:8000/docs

---

## Architecture

```
User → Orchestrator (8000) → Agent (8001)
        ↓ Uses MCP           ↓ A2A Protocol
        Context7 Docs        JSON-RPC 2.0
```

### What's Happening:

1. **Agent** exposes:
   - AgentCard at `/.well-known/agent-card`
   - JSON-RPC endpoint at `/a2a`
   - Health check at `/health`

2. **Orchestrator**:
   - Discovers agents via AgentCard
   - Uses MCP Context7 for A2A documentation
   - Routes tasks to appropriate agents
   - Handles A2A protocol communication

3. **A2A Protocol** (JSON-RPC 2.0):
   - `a2a.createTask` - Create new task
   - `a2a.getTask` - Get task status
   - `a2a.listTasks` - List all tasks

---

## MCP Integration

The orchestrator uses **Model Context Protocol (MCP)** with **Context7 plugin** for:

1. **Documentation Lookup**: Get A2A protocol docs
2. **Library Resolution**: Find library documentation
3. **Error Help**: Get assistance with errors

### Get A2A Docs via MCP:

```bash
curl http://localhost:8000/docs/a2a/createTask
```

This will return A2A documentation fetched via MCP Context7.

---

## File Structure

```
src/
├── simple_agent/
│   ├── agent.py              # A2A agent (100 lines)
│   └── requirements.txt
└── orchestrator/
    ├── orchestrator.py       # Orchestrator (200 lines)
    ├── mcp_client.py         # MCP integration (100 lines)
    └── requirements.txt
```

**Total**: ~400 lines of working code!

---

## Next Steps

### Add More Agents

Run another agent on a different port:

```bash
# Terminal 3
PORT=8002 AGENT_ID=second-agent python src/simple_agent/agent.py
```

Then discover it:
```bash
curl -X POST http://localhost:8000/discover \
  -d '{"url": "http://localhost:8002"}'
```

### List All Agents

```bash
curl http://localhost:8000/agents
```

### Create a Code Analysis Agent

Replace the echo logic in `agent.py`:

```python
async def create_task(params: Dict[str, Any]) -> Dict[str, Any]:
    # ... existing code ...

    # Replace echo with actual code analysis
    result_text = analyze_code(input_text)  # Your logic here

    # ... rest of code ...
```

---

## Common Issues

### Port Already in Use

```bash
# Kill process on port 8001
lsof -ti:8001 | xargs kill -9

# Or use different port
PORT=8003 python agent.py
```

### Agent Not Discoverable

1. Check agent is running: `curl http://localhost:8001/health`
2. Check AgentCard: `curl http://localhost:8001/.well-known/agent-card`
3. Check orchestrator: `curl http://localhost:8000/health`

### Connection Refused

Make sure both agent and orchestrator are running in separate terminals.

---

## Understanding A2A Protocol

### 1. AgentCard (Discovery)

Every agent exposes its capabilities:

```json
{
  "agentId": "unique-id",
  "endpoints": {"rpc": "http://..."},
  "capabilities": {"skills": [...]}
}
```

### 2. JSON-RPC 2.0 (Communication)

All communication uses JSON-RPC:

```json
{
  "jsonrpc": "2.0",
  "method": "a2a.createTask",
  "params": {...}
}
```

### 3. Tasks (Long-running work)

Tasks track asynchronous work:

```json
{
  "taskId": "...",
  "status": "completed",
  "messages": [...],
  "artifacts": [...]
}
```

---

## Resources

- **A2A Protocol**: https://a2a-protocol.org/latest/
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **MCP Docs**: https://modelcontextprotocol.io/

---

## Success! 🎉

You now have a working A2A multi-agent system with:

✅ Standard A2A protocol (JSON-RPC 2.0)
✅ AgentCard discovery
✅ MCP integration for docs
✅ Simple orchestration
✅ Interactive API docs
✅ Easy to extend

**Start building your agents!** 🚀
