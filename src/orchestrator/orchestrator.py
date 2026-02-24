"""
Simple A2A Orchestrator
Discovers and coordinates multiple A2A agents using MCP for documentation
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime
import os

# Import MCP client
from mcp_client import mcp_doc_client

app = FastAPI(title="A2A Orchestrator")

# Agent registry (in-memory, could be Redis)
AGENT_REGISTRY: Dict[str, Dict[str, Any]] = {}


class DiscoverRequest(BaseModel):
    url: str


class ExecuteRequest(BaseModel):
    request: str
    agent_id: Optional[str] = None
    metadata: Dict[str, Any] = {}


class SimpleOrchestrator:
    """
    Orchestrates tasks across multiple A2A agents
    Uses MCP Context7 for documentation lookup
    """

    def __init__(self):
        self.agents = AGENT_REGISTRY
        self.mcp = mcp_doc_client

    async def discover_agent(self, agent_url: str) -> Dict[str, Any]:
        """
        Discover agent by fetching its AgentCard

        Steps:
        1. GET {agent_url}/.well-known/agent-card
        2. Validate AgentCard structure
        3. Store in registry
        4. Return AgentCard
        """
        print(f"🔍 Discovering agent at: {agent_url}")

        try:
            # Get AgentCard
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{agent_url}/.well-known/agent-card",
                    timeout=5.0
                )
                response.raise_for_status()
                agent_card = response.json()

            # Validate required fields
            required = ["agentId", "name", "endpoints", "capabilities"]
            for field in required:
                if field not in agent_card:
                    raise ValueError(f"AgentCard missing required field: {field}")

            # Store in registry
            agent_id = agent_card["agentId"]
            AGENT_REGISTRY[agent_id] = {
                **agent_card,
                "discoveredAt": datetime.utcnow().isoformat(),
                "baseUrl": agent_url,
                "status": "active"
            }

            print(f"✅ Discovered: {agent_id} - {agent_card['name']}")
            return agent_card

        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to discover agent: {str(e)}"
            )

    async def find_agent_by_skill(self, skill: str) -> Optional[Dict[str, Any]]:
        """
        Find agent that has a specific skill
        """
        for agent in self.agents.values():
            skills = agent.get("capabilities", {}).get("skills", [])
            if skill in skills:
                return agent
        return None

    async def call_agent(
        self,
        agent_id: str,
        message_text: str,
        metadata: Dict[str, Any] = {}
    ) -> Dict[str, Any]:
        """
        Call an agent using A2A protocol

        Steps:
        1. Get docs via MCP if needed
        2. Build A2A createTask request
        3. Send to agent's RPC endpoint
        4. Return result
        """
        # Get agent card
        agent_card = self.agents.get(agent_id)
        if not agent_card:
            raise ValueError(f"Agent not found: {agent_id}")

        # Get A2A docs (using MCP Context7)
        print(f"📚 Getting A2A documentation via MCP...")
        docs = await self.mcp.get_a2a_docs("createTask")
        print(f"   ✓ Retrieved createTask documentation")

        # Build A2A request (JSON-RPC 2.0)
        rpc_url = agent_card["endpoints"]["rpc"]
        request = {
            "jsonrpc": "2.0",
            "id": f"orch-{datetime.utcnow().timestamp()}",
            "method": "a2a.createTask",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [
                        {"kind": "text", "text": message_text}
                    ]
                },
                "metadata": {
                    **metadata,
                    "orchestrator": "simple-orchestrator",
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        }

        print(f"📤 Calling agent: {agent_id}")
        print(f"   RPC URL: {rpc_url}")

        try:
            # Call agent
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    rpc_url,
                    json=request,
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()

            # Check for JSON-RPC error
            if "error" in result:
                error = result["error"]
                # Get error help via MCP
                help_text = await self.mcp.get_error_help(str(error))
                raise ValueError(f"Agent error: {error}\n\n{help_text}")

            print(f"✅ Task created: {result['result'].get('taskId', 'N/A')}")
            return result["result"]

        except httpx.HTTPError as e:
            # Get error help via MCP
            help_text = await self.mcp.get_error_help(str(e))
            raise HTTPException(
                status_code=500,
                detail=f"Failed to call agent: {str(e)}\n\n{help_text}"
            )

    async def execute_workflow(
        self,
        user_request: str,
        target_agent_id: Optional[str] = None,
        metadata: Dict[str, Any] = {}
    ) -> Dict[str, Any]:
        """
        Execute a simple workflow

        Steps:
        1. Select agent (by ID or auto-select)
        2. Call agent with user request
        3. Return result
        """
        print(f"\n🚀 Executing workflow: {user_request[:50]}...")

        # Check if we have any agents
        if not self.agents:
            return {
                "status": "error",
                "message": "No agents available. Use /discover to add agents."
            }

        # Select agent
        if target_agent_id:
            agent_id = target_agent_id
            if agent_id not in self.agents:
                return {
                    "status": "error",
                    "message": f"Agent not found: {agent_id}"
                }
        else:
            # Auto-select first available agent
            agent_id = list(self.agents.keys())[0]
            print(f"   Auto-selected agent: {agent_id}")

        # Call agent
        try:
            result = await self.call_agent(agent_id, user_request, metadata)

            return {
                "status": "completed",
                "agent_used": agent_id,
                "result": result
            }

        except Exception as e:
            return {
                "status": "error",
                "agent_used": agent_id,
                "error": str(e)
            }


# Global orchestrator instance
orchestrator = SimpleOrchestrator()


# ============================================
# FastAPI Endpoints
# ============================================

@app.get("/")
async def root():
    """Root endpoint with usage info"""
    return {
        "name": "A2A Orchestrator",
        "version": "0.1.0",
        "endpoints": {
            "discover": "POST /discover - Discover a new agent",
            "execute": "POST /execute - Execute a task",
            "agents": "GET /agents - List known agents",
            "health": "GET /health - Health check"
        },
        "docs": "/docs"
    }


@app.post("/discover")
async def discover(request: DiscoverRequest):
    """
    Discover a new A2A agent

    Body:
    {
      "url": "http://localhost:8001"
    }
    """
    agent_card = await orchestrator.discover_agent(request.url)
    return {
        "status": "discovered",
        "agent": agent_card
    }


@app.post("/execute")
async def execute(request: ExecuteRequest):
    """
    Execute a task on an agent

    Body:
    {
      "request": "Your task description",
      "agent_id": "optional-agent-id",
      "metadata": {}
    }
    """
    result = await orchestrator.execute_workflow(
        user_request=request.request,
        target_agent_id=request.agent_id,
        metadata=request.metadata
    )
    return result


@app.get("/agents")
async def list_agents():
    """
    List all discovered agents
    """
    return {
        "agents": list(AGENT_REGISTRY.values()),
        "total": len(AGENT_REGISTRY)
    }


@app.get("/health")
async def health():
    """
    Health check
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "agents_count": len(AGENT_REGISTRY),
        "mcp_available": True
    }


@app.get("/docs/a2a/{topic}")
async def get_docs(topic: str):
    """
    Get A2A documentation via MCP Context7

    Example: GET /docs/a2a/createTask
    """
    docs = await mcp_doc_client.get_a2a_docs(topic)
    return {
        "topic": topic,
        "documentation": docs
    }


if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("🚀 A2A Orchestrator Starting...")
    print("=" * 60)
    print("\n📍 Endpoints:")
    print("   - Main: http://localhost:8000")
    print("   - Docs: http://localhost:8000/docs")
    print("   - Health: http://localhost:8000/health")
    print("\n📚 Quick Start:")
    print("   1. Discover agent:")
    print('      curl -X POST http://localhost:8000/discover \\')
    print('        -H "Content-Type: application/json" \\')
    print('        -d \'{"url": "http://localhost:8001"}\'')
    print("\n   2. Execute task:")
    print('      curl -X POST http://localhost:8000/execute \\')
    print('        -H "Content-Type: application/json" \\')
    print('        -d \'{"request": "Hello World!"}\'')
    print("\n" + "=" * 60 + "\n")

    PORT = int(os.getenv("PORT", "8006"))
    uvicorn.run(app, host="0.0.0.0", port=PORT)
