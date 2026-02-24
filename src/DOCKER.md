# Docker Setup for A2A Multi-Agent System

## Quick Start

```bash
# Build and start all agents
docker-compose up --build

# Run in background
docker-compose up -d

# Stop all agents
docker-compose down

# View logs
docker-compose logs -f

# View specific agent logs
docker-compose logs -f orchestrator-agent
```

## Services

- **orchestrator-agent**: Port 8000 (main coordinator)
- **code-logic-agent**: Port 8001 (AST analysis)
- **research-agent**: Port 8003 (grep search)
- **test-run-agent**: Port 8004 (test generation)
- **validation-agent**: Port 8005 (security checks)

## Test

```bash
# Health check
curl http://localhost:8000/.well-known/agent-card

# Execute task
curl -X POST http://localhost:8000/a2a \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "execute", "params": {"request": "Hello"}, "id": 1}'
```

## Network

All agents run on `a2a-network` bridge network and can communicate using service names:
- `http://code-logic-agent:8001`
- `http://research-agent:8003`
- `http://test-run-agent:8004`
- `http://validation-agent:8005`
