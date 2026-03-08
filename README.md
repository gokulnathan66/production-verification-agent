# A2A Multi-Agent System

A **simple, working** implementation of Google's A2A (Agent2Agent) protocol with MCP integration for production verification agents.

## 🚀 Quick Start

### Production Verification Workflow

```bash
# 1. Start all services
./run_all_agents.sh

# 2. Upload code & trigger verification
# Visit http://localhost:8006
# - Upload code zip
# - Click "Verify Production Code"
# - Monitor progress in real-time

# 3. Or test via script
python test_verification.py
```

### Complete System (All 5 Agents)

```bash
# 1. Start all agents at once
./run_all_agents.sh

# 2. Test everything
python test_all_agents.py

# 3. Stop all agents
./stop_all_agents.sh
```

### Simple Demo System (2 Agents)

```bash
# Terminal 1: Start Simple Agent
cd src/simple_agent
pip install -r requirements.txt
python agent.py

# Terminal 2: Start Simple Orchestrator
cd src/orchestrator
pip install -r requirements.txt
python orchestrator.py

# Terminal 3: Test
python test_system.py
```

## What This Is

A complete A2A multi-agent system with 5 specialized agents for production code verification:

### 🤖 The Agents

1. **Intract-Orchestrator** (Port 8006)
   - Web UI frontend gateway
   - S3 artifact management
   - Triggers verification workflows
   - Real-time monitoring dashboard

2. **Orchestrator Agent** (Port 8000)
   - Multi-agent workflow coordinator
   - Shared workspace management
   - S3 integration for results
   - Complete verification pipeline

3. **Code Logic Agent** (Port 8001)
   - AST parsing and structural analysis
   - Complexity metrics and quality scoring
   - Function/class extraction
   - Multi-language support (Python, JS, Java)

4. **Research Agent** (Port 8003)
   - Grep-based code search (Claude Code style)
   - Pattern matching and discovery
   - RESEARCH.md generation
   - Dependency mapping

3. **Test Run Agent** (Port 8004)
   - Automatic test generation (pytest, Jest)
   - Test execution in sandboxes
   - Coverage analysis
   - Test validation

4. **Validation Agent** (Port 8005)
   - Security vulnerability detection
   - Hardcoded secret detection
   - Code quality checks
   - Compliance verification

5. **Orchestrator Agent** (Port 8000)
   - Coordinates all agents
   - Multi-agent workflows
   - Complete production verification
   - Results aggregation

### ✨ Features

✅ **A2A Protocol** (JSON-RPC 2.0 over HTTP)
✅ **AgentCard Discovery** (standard `/.well-known/agent-card`)
✅ **MCP Integration** (Context7 for documentation)
✅ **Complete Workflows** (end-to-end verification)
✅ **Production Ready** (comprehensive testing)
✅ **Web Dashboard** (real-time monitoring UI with S3 uploads)

## 🎨 Web Dashboard

A modern, real-time web UI for monitoring and managing agents:

- **📁 Upload Artifacts**: Drag-and-drop file uploads to S3
- **📋 Task Dashboard**: View and filter agent tasks
- **📜 Logs Viewer**: Real-time log streaming with SSE
- **⚡ Progress Tracker**: Live agent status monitoring

**Access**: http://localhost:8006 (when orchestrator is running)

**Screenshot**: Command center aesthetic with dark mode, glowing accents, and real-time updates.

See [frontend/README.md](./frontend/README.md) for full documentation.

## Project Structure

```
├── docs/
│   ├── 008-plan-a2a.md                 # Full A2A implementation plan
│   ├── 009-simple-implementation-plan.md # Simple version plan
│   └── AGENTS_GUIDE.md                  # Complete agent usage guide
├── src/
│   ├── code_logic_agent/               # AST analysis, complexity metrics
│   │   ├── agent.py
│   │   └── requirements.txt
│   ├── research_agent/                 # Grep search, pattern matching
│   │   ├── agent.py
│   │   └── requirements.txt
│   ├── test_run_agents/                # Test generation & execution
│   │   ├── agent.py
│   │   └── requirements.txt
│   ├── validation_agent/               # Security & quality checks
│   │   ├── agent.py
│   │   └── requirements.txt
│   ├── orchestorator_agent/            # Multi-agent coordinator
│   │   ├── agent.py
│   │   └── requirements.txt
│   ├── simple_agent/                   # Basic echo agent (demo)
│   │   └── agent.py
│   └── orchestrator/                   # Simple orchestrator (demo)
│       ├── orchestrator.py
│       ├── mcp_client.py
│       ├── s3_client.py                # S3 artifact manager
│       └── storage.py                  # SQLite persistence
├── frontend/                            # Web dashboard UI
│   ├── index.html                      # Upload page
│   ├── tasks.html                      # Task dashboard
│   ├── logs.html                       # Logs viewer
│   ├── progress.html                   # Progress tracker
│   ├── static/
│   │   ├── css/                        # Design system
│   │   └── js/                         # Frontend logic
│   └── README.md                       # Frontend documentation
├── QUICKSTART.md                        # Step-by-step guide
├── AGENTS_GUIDE.md                      # Complete guide for all agents
├── run_all_agents.sh                    # Start all agents
├── stop_all_agents.sh                   # Stop all agents
├── test_all_agents.py                   # Test all agents
└── README.md                            # This file
```

## Documentation

- **[VERIFICATION_WORKFLOW.md](./VERIFICATION_WORKFLOW.md)** - Complete verification workflow guide
- **[QUICKSTART.md](./QUICKSTART.md)** - Get started in 5 minutes
- **[Simple Implementation Plan](./docs/009-simple-implementation-plan.md)** - Minimal working system
- **[Full Implementation Plan](./docs/008-plan-a2a.md)** - Complete A2A protocol details

## Key Features

### 1. Standard A2A Protocol

Every agent follows Google's A2A specification:
- AgentCard at `/.well-known/agent-card`
- JSON-RPC 2.0 endpoint at `/a2a`
- Task-based long-running operations

### 2. MCP Integration

Uses Model Context Protocol with Context7 plugin for:
- Real-time A2A documentation lookup
- Library documentation resolution
- Error message assistance

### 3. Simple but Extensible

- **Agent**: ~100 lines - easy to understand and extend
- **Orchestrator**: ~200 lines - clear workflow routing
- **MCP Client**: ~100 lines - simple doc integration

## Setup with Dashboard

### 1. Install Backend Dependencies

```bash
cd src/orchestrator
pip install -r requirements.txt
```

### 2. Configure S3 (Optional - for artifact uploads)

Create `.env` file in project root:

```bash
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_REGION=us-east-1
S3_BUCKET_NAME=a2a-multi-agent-artifacts
PORT=8006
```

### 3. Start Orchestrator

```bash
cd src/orchestrator
python orchestrator.py
```

Dashboard available at: **http://localhost:8006**

## Quick Test

```bash
# Discover agent
curl -X POST http://localhost:8006/discover \
  -H "Content-Type: application/json" \
  -d '{"url": "http://localhost:8001"}'

# Execute task
curl -X POST http://localhost:8006/execute \
  -H "Content-Type: application/json" \
  -d '{"request": "Hello A2A!"}'

# Or use the web dashboard at http://localhost:8006
```

## Next Steps

1. **Add More Agents**: Copy `simple_agent` and customize
2. **Add Real Logic**: Replace echo with actual processing
3. **Add MCP Tools**: Integrate file system, git, database tools
4. **Scale Up**: Add Redis, proper task queue, multiple agents

See [Full Implementation Plan](./docs/008-plan-a2a.md) for advanced features:
- Cloud deployment (S3 → Lambda → ECS)
- Dynamic test sandboxes
- Async task processing
- Code analysis agents

## Resources

- **A2A Protocol**: https://a2a-protocol.org/latest/
- **MCP Docs**: https://modelcontextprotocol.io/
- **FastAPI**: https://fastapi.tiangolo.com/

## License

MIT 