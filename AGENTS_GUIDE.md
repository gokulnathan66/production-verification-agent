# A2A Multi-Agent System - Complete Guide

## 🎯 System Overview

This is a complete A2A (Agent2Agent) multi-agent system with 5 specialized agents:

1. **Code Logic Agent** (Port 8001) - AST analysis, complexity metrics, code quality
2. **Research Agent** (Port 8003) - Grep-based search, pattern matching, RESEARCH.md generation
3. **Test Run Agent** (Port 8004) - Test generation and execution
4. **Validation Agent** (Port 8005) - Security checks, validation, compliance
5. **Orchestrator Agent** (Port 8000) - Coordinates all agents for complete workflows

---

## 🚀 Quick Start

### 1. Start All Agents

```bash
./run_all_agents.sh
```

Wait for all agents to start (about 10 seconds).

### 2. Test Everything

```bash
python test_all_agents.py
```

This will test all 5 agents and run a complete workflow.

### 3. Stop All Agents

```bash
./stop_all_agents.sh
```

---

## 📖 Using Individual Agents

### Code Logic Agent (Port 8001)

Analyzes code structure, complexity, and quality.

**Example:**
```bash
curl -X POST http://localhost:8001/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "a2a.createTask",
    "params": {
      "message": {
        "role": "user",
        "parts": [
          {"kind": "text", "text": "def hello(): return \"world\""},
          {"kind": "data", "data": {"code": "def hello(): return \"world\"", "language": "python"}}
        ]
      }
    }
  }'
```

**Features:**
- Function and class extraction
- Complexity analysis
- Quality scoring
- Docstring coverage
- Supports Python, JavaScript, Java

**Interactive Docs:** http://localhost:8001/docs

---

### Research Agent (Port 8003)

Performs grep-based code search and research.

**Example:**
```bash
curl -X POST http://localhost:8003/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "2",
    "method": "a2a.createTask",
    "params": {
      "message": {
        "role": "user",
        "parts": [
          {"kind": "data", "data": {
            "code": "def foo():\n    pass\n\ndef bar():\n    pass",
            "language": "python",
            "type": "functions"
          }}
        ]
      }
    }
  }'
```

**Features:**
- Find functions and classes
- Pattern matching
- Import analysis
- RESEARCH.md generation
- Dependency mapping

**Interactive Docs:** http://localhost:8003/docs

---

### Test Run Agent (Port 8004)

Generates and executes tests.

**Example:**
```bash
curl -X POST http://localhost:8004/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "3",
    "method": "a2a.createTask",
    "params": {
      "message": {
        "role": "user",
        "parts": [
          {"kind": "data", "data": {
            "code": "def add(a, b):\n    return a + b",
            "language": "python",
            "action": "generate"
          }}
        ]
      }
    }
  }'
```

**Features:**
- Generate pytest tests
- Generate Jest tests
- Execute tests in sandbox
- Coverage analysis
- Test validation

**Interactive Docs:** http://localhost:8004/docs

---

### Validation Agent (Port 8005)

Performs security and quality validation.

**Example:**
```bash
curl -X POST http://localhost:8005/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "4",
    "method": "a2a.createTask",
    "params": {
      "message": {
        "role": "user",
        "parts": [
          {"kind": "data", "data": {
            "code": "password = \"hardcoded123\"\nos.system(user_input)",
            "check_type": "all"
          }}
        ]
      }
    }
  }'
```

**Features:**
- Detect hardcoded secrets
- SQL injection patterns
- Command injection risks
- XSS vulnerabilities
- Code quality issues
- Insecure dependencies

**Interactive Docs:** http://localhost:8005/docs

---

### Orchestrator Agent (Port 8000)

Coordinates all agents for complete workflows.

**Example - Full Analysis:**
```bash
curl -X POST http://localhost:8000/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "5",
    "method": "a2a.createTask",
    "params": {
      "message": {
        "role": "user",
        "parts": [
          {"kind": "data", "data": {
            "code": "def calculate(x):\n    return x * 2",
            "language": "python",
            "workflow": "full_analysis"
          }}
        ]
      }
    }
  }'
```

**Workflows:**
- **full_analysis**: Runs all 4 agents sequentially
  1. Code Logic Analysis
  2. Research
  3. Validation
  4. Test Generation

**Interactive Docs:** http://localhost:8000/docs

---

## 🔄 Complete Workflow Example

The orchestrator runs a complete production verification workflow:

```python
import httpx
import asyncio

async def run_full_analysis():
    code = """
def process_payment(amount, card_number):
    # Process payment
    result = amount * 1.1
    return result

class PaymentProcessor:
    def __init__(self):
        self.transactions = []

    def process(self, amount):
        self.transactions.append(amount)
        return True
"""

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/a2a",
            json={
                "jsonrpc": "2.0",
                "id": "workflow-1",
                "method": "a2a.createTask",
                "params": {
                    "message": {
                        "role": "user",
                        "parts": [
                            {"kind": "data", "data": {
                                "code": code,
                                "language": "python",
                                "workflow": "full_analysis"
                            }}
                        ]
                    }
                }
            },
            timeout=120.0
        )

        result = response.json()
        print(result["result"]["messages"][-1]["parts"][0]["text"])

asyncio.run(run_full_analysis())
```

This will:
1. ✅ Analyze code structure and complexity
2. 🔍 Find all functions and classes
3. 🛡️ Check for security vulnerabilities
4. 🧪 Generate test cases

---

## 📊 Understanding Results

### Task Structure

All agents return A2A-compliant tasks:

```json
{
  "taskId": "uuid",
  "status": "completed",
  "messages": [
    {
      "role": "user",
      "parts": [...]
    },
    {
      "role": "assistant",
      "parts": [
        {"kind": "text", "text": "Human readable result"},
        {"kind": "data", "data": {...}}
      ]
    }
  ],
  "artifacts": []
}
```

### Result Parts

- **text**: Human-readable summary
- **data**: Structured data for programmatic use
- **artifacts**: Generated files (tests, reports, etc.)

---

## 🔧 Configuration

### Change Ports

Edit the agent scripts or use environment variables:

```bash
# Start agent on different port
PORT=9001 AGENT_ID=my-code-agent python src/code_logic_agent/agent.py
```

### Add New Agent

1. Copy an existing agent:
   ```bash
   cp -r src/simple_agent src/my_new_agent
   ```

2. Edit `agent.py`:
   - Change `AGENT_ID`
   - Update `AGENT_CARD`
   - Implement your logic in `create_task()`

3. Start it:
   ```bash
   PORT=8006 python src/my_new_agent/agent.py
   ```

4. Register with orchestrator:
   Edit `src/orchestorator_agent/agent.py`:
   ```python
   self.known_agents = {
       ...
       "my-new-agent": "http://localhost:8006"
   }
   ```

---

## 🐛 Troubleshooting

### Agent Won't Start

```bash
# Check port availability
lsof -i :8001

# Kill process on port
lsof -ti:8001 | xargs kill -9

# Check logs
tail -f logs/code-logic-agent.log
```

### Connection Refused

```bash
# Verify agent is running
curl http://localhost:8001/health

# Check AgentCard
curl http://localhost:8001/.well-known/agent-card
```

### Workflow Timeout

Increase timeout in orchestrator:

```python
response = await client.post(rpc_url, json=request, timeout=120.0)
```

---

## 📈 Monitoring

### Health Checks

All agents expose health endpoints:

```bash
curl http://localhost:8001/health
curl http://localhost:8003/health
curl http://localhost:8004/health
curl http://localhost:8005/health
curl http://localhost:8000/health
```

### View Logs

```bash
# List all logs
ls logs/

# Tail specific agent
tail -f logs/code-logic-agent.log

# View all logs
tail -f logs/*.log
```

### Check Running Agents

```bash
# List all agent processes
ps aux | grep agent.py

# Check ports
lsof -i :8000-8005
```

---

## 🎓 Advanced Usage

### Parallel Agent Calls

Call multiple agents simultaneously:

```python
async def parallel_analysis(code):
    async with httpx.AsyncClient() as client:
        # Create tasks for all agents
        tasks = [
            client.post("http://localhost:8001/a2a", json=request1),
            client.post("http://localhost:8003/a2a", json=request2),
            client.post("http://localhost:8005/a2a", json=request3),
        ]

        # Wait for all to complete
        results = await asyncio.gather(*tasks)
        return results
```

### Custom Workflows

Create your own workflows in the orchestrator:

```python
async def security_focused_workflow(code):
    # 1. Validation first
    validation = await call_agent("validation-agent", ...)

    # 2. Only proceed if secure
    if validation["passed"]:
        # 3. Generate tests
        tests = await call_agent("test-run-agent", ...)
        return {"validation": validation, "tests": tests}
    else:
        return {"error": "Security issues found"}
```

---

## 🌟 Best Practices

1. **Always check health** before sending requests
2. **Use timeouts** for long-running tasks
3. **Handle errors** gracefully
4. **Monitor logs** for issues
5. **Scale horizontally** by running multiple instances

---

## 📚 Resources

- **A2A Protocol**: https://a2a-protocol.org/latest/
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **Project Docs**: See `docs/` directory

---

## 🎉 Success!

You now have a complete A2A multi-agent system with:

✅ 5 specialized agents
✅ Complete workflows
✅ A2A protocol compliance
✅ Interactive API docs
✅ Comprehensive testing
✅ Production-ready architecture

**Start building amazing multi-agent applications!** 🚀
