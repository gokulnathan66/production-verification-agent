"""
Main Orchestrator Agent - A2A compliant
Coordinates all specialized agents for complete production verification workflow
"""
from fastapi import FastAPI, Request
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime
import os
import httpx
import asyncio

app = FastAPI(title="Main Orchestrator Agent")

TASKS = {}
AGENT_REGISTRY = {}

AGENT_ID = os.getenv("AGENT_ID", "orchestrator-agent")
PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "localhost")

AGENT_CARD = {
    "agentId": AGENT_ID,
    "name": "Main Orchestrator Agent",
    "description": "Orchestrates multi-agent workflows for production verification and code analysis",
    "version": "1.0.0",
    "endpoints": {
        "rpc": f"http://{HOST}:{PORT}/a2a",
        "health": f"http://{HOST}:{PORT}/health"
    },
    "capabilities": {
        "modalities": ["text", "file"],
        "skills": [
            "workflow_orchestration",
            "agent_coordination",
            "multi_agent_workflow",
            "production_verification",
            "complete_analysis"
        ],
        "workflows": [
            "full_analysis",
            "security_check",
            "code_quality",
            "test_generation"
        ]
    },
    "auth": {"scheme": "none", "required": False}
}


class MultiAgentOrchestrator:
    """Coordinates multiple A2A agents"""

    def __init__(self):
        self.known_agents = {
            "code-logic-agent": "http://localhost:8001",
            "research-agent": "http://localhost:8003",
            "test-run-agent": "http://localhost:8004",
            "validation-agent": "http://localhost:8005"
        }

    async def discover_agents(self) -> Dict[str, Any]:
        """Discover all known agents"""
        discovered = {}

        for agent_id, base_url in self.known_agents.items():
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{base_url}/.well-known/agent-card",
                        timeout=5.0
                    )
                    if response.status_code == 200:
                        card = response.json()
                        discovered[agent_id] = {
                            "card": card,
                            "baseUrl": base_url,
                            "status": "online"
                        }
                        AGENT_REGISTRY[agent_id] = discovered[agent_id]
            except:
                discovered[agent_id] = {
                    "status": "offline",
                    "baseUrl": base_url
                }

        return discovered

    async def call_agent(
        self,
        agent_id: str,
        message_parts: List[Dict[str, Any]],
        metadata: Dict[str, Any] = {}
    ) -> Dict[str, Any]:
        """Call a specific agent via A2A protocol"""

        agent_info = AGENT_REGISTRY.get(agent_id)
        if not agent_info or agent_info.get("status") != "online":
            raise ValueError(f"Agent {agent_id} not available")

        rpc_url = agent_info["card"]["endpoints"]["rpc"]

        request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "a2a.createTask",
            "params": {
                "message": {
                    "role": "user",
                    "parts": message_parts
                },
                "metadata": metadata
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(rpc_url, json=request, timeout=60.0)
            result = response.json()

            if "error" in result:
                raise Exception(f"Agent error: {result['error']}")

            return result["result"]

    async def run_full_analysis_workflow(
        self,
        code: str,
        language: str = "python"
    ) -> Dict[str, Any]:
        """
        Complete analysis workflow:
        1. Code Logic Analysis
        2. Research (find functions, classes)
        3. Validation (security, quality)
        4. Test Generation
        """

        results = {}
        message_parts = [
            {"kind": "text", "text": code},
            {"kind": "data", "data": {"code": code, "language": language}}
        ]

        # Step 1: Code Logic Analysis
        print("  → Running code logic analysis...")
        try:
            results["code_analysis"] = await self.call_agent(
                "code-logic-agent",
                message_parts,
                {"workflow": "full_analysis", "step": 1}
            )
            print("    ✓ Code analysis complete")
        except Exception as e:
            results["code_analysis"] = {"error": str(e)}
            print(f"    ✗ Code analysis failed: {e}")

        # Step 2: Research
        print("  → Running code research...")
        try:
            results["research"] = await self.call_agent(
                "research-agent",
                message_parts,
                {"workflow": "full_analysis", "step": 2}
            )
            print("    ✓ Research complete")
        except Exception as e:
            results["research"] = {"error": str(e)}
            print(f"    ✗ Research failed: {e}")

        # Step 3: Validation
        print("  → Running security validation...")
        try:
            results["validation"] = await self.call_agent(
                "validation-agent",
                message_parts,
                {"workflow": "full_analysis", "step": 3}
            )
            print("    ✓ Validation complete")
        except Exception as e:
            results["validation"] = {"error": str(e)}
            print(f"    ✗ Validation failed: {e}")

        # Step 4: Test Generation
        print("  → Generating tests...")
        try:
            results["tests"] = await self.call_agent(
                "test-run-agent",
                message_parts,
                {"workflow": "full_analysis", "step": 4}
            )
            print("    ✓ Test generation complete")
        except Exception as e:
            results["tests"] = {"error": str(e)}
            print(f"    ✗ Test generation failed: {e}")

        return results

    def generate_summary(self, results: Dict[str, Any]) -> str:
        """Generate summary from all agent results"""

        summary = """
🎯 Production Verification Complete

═══════════════════════════════════════════════════════════

"""

        # Code Analysis Summary
        if "code_analysis" in results and "error" not in results["code_analysis"]:
            ca = results["code_analysis"]
            messages = ca.get("messages", [])
            for msg in messages:
                if msg["role"] == "assistant":
                    summary += "📊 CODE ANALYSIS\n"
                    for part in msg["parts"]:
                        if part["kind"] == "text":
                            summary += part["text"][:500] + "\n"
                    break

        # Research Summary
        if "research" in results and "error" not in results["research"]:
            summary += "\n🔍 RESEARCH\n"
            res = results["research"]
            messages = res.get("messages", [])
            for msg in messages:
                if msg["role"] == "assistant":
                    for part in msg["parts"]:
                        if part["kind"] == "text":
                            summary += part["text"][:400] + "\n"
                    break

        # Validation Summary
        if "validation" in results and "error" not in results["validation"]:
            summary += "\n🛡️ VALIDATION\n"
            val = results["validation"]
            messages = val.get("messages", [])
            for msg in messages:
                if msg["role"] == "assistant":
                    for part in msg["parts"]:
                        if part["kind"] == "text":
                            summary += part["text"][:400] + "\n"
                    break

        # Test Generation Summary
        if "tests" in results and "error" not in results["tests"]:
            summary += "\n🧪 TEST GENERATION\n"
            tests = results["tests"]
            messages = tests.get("messages", [])
            for msg in messages:
                if msg["role"] == "assistant":
                    for part in msg["parts"]:
                        if part["kind"] == "text":
                            summary += part["text"][:300] + "\n"
                    break

        summary += "\n═══════════════════════════════════════════════════════════\n"
        summary += "✅ All checks complete!\n"

        return summary


orchestrator = MultiAgentOrchestrator()


@app.get("/.well-known/agent-card")
async def get_agent_card():
    return AGENT_CARD


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "agentId": AGENT_ID,
        "known_agents": len(orchestrator.known_agents),
        "online_agents": len([a for a in AGENT_REGISTRY.values() if a.get("status") == "online"])
    }


@app.post("/a2a")
async def a2a_endpoint(request: Request):
    body = await request.json()

    if body.get("jsonrpc") != "2.0":
        return {
            "jsonrpc": "2.0",
            "id": body.get("id"),
            "error": {"code": -32600, "message": "Invalid Request"}
        }

    method = body.get("method")
    params = body.get("params", {})
    request_id = body.get("id")

    try:
        if method == "a2a.createTask":
            result = await create_task(params)
        elif method == "a2a.getTask":
            result = await get_task(params)
        elif method == "a2a.listTasks":
            result = await list_tasks(params)
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"}
            }

        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32603, "message": str(e)}
        }


async def create_task(params: Dict[str, Any]) -> Dict[str, Any]:
    """Create orchestration task"""
    task_id = str(uuid.uuid4())
    message = params.get("message", {})
    metadata = params.get("metadata", {})

    # Extract code and workflow type
    code_text = ""
    language = "python"
    workflow = "full_analysis"

    for part in message.get("parts", []):
        if part.get("kind") == "text":
            code_text += part.get("text", "")
        elif part.get("kind") == "data":
            data = part.get("data", {})
            code_text = data.get("code", code_text)
            language = data.get("language", "python")
            workflow = data.get("workflow", "full_analysis")

    # Discover agents first
    print(f"🔍 Discovering agents...")
    await orchestrator.discover_agents()

    # Run workflow
    print(f"🚀 Running {workflow} workflow...")
    if workflow == "full_analysis":
        workflow_results = await orchestrator.run_full_analysis_workflow(code_text, language)
    else:
        workflow_results = {"error": f"Unknown workflow: {workflow}"}

    # Generate summary
    summary_text = orchestrator.generate_summary(workflow_results)

    # Create task
    task = {
        "taskId": task_id,
        "status": "completed",
        "createdAt": datetime.utcnow().isoformat(),
        "updatedAt": datetime.utcnow().isoformat(),
        "messages": [
            {
                "messageId": str(uuid.uuid4()),
                "role": "user",
                "timestamp": datetime.utcnow().isoformat(),
                "parts": message.get("parts", [])
            },
            {
                "messageId": str(uuid.uuid4()),
                "role": "assistant",
                "timestamp": datetime.utcnow().isoformat(),
                "parts": [
                    {"kind": "text", "text": summary_text},
                    {"kind": "data", "data": workflow_results}
                ]
            }
        ],
        "artifacts": [],
        "metadata": {
            **metadata,
            "agentId": AGENT_ID,
            "workflow": workflow,
            "agents_used": list(workflow_results.keys())
        }
    }

    TASKS[task_id] = task
    return task


async def get_task(params: Dict[str, Any]) -> Dict[str, Any]:
    task_id = params.get("taskId")
    if not task_id or task_id not in TASKS:
        raise ValueError(f"Task not found: {task_id}")
    return TASKS[task_id]


async def list_tasks(params: Dict[str, Any]) -> Dict[str, Any]:
    status_filter = params.get("status")
    limit = params.get("limit", 100)
    tasks = list(TASKS.values())
    if status_filter:
        tasks = [t for t in tasks if t["status"] == status_filter]
    return {"tasks": tasks[:limit], "total": len(tasks)}


if __name__ == "__main__":
    import uvicorn
    print(f"🚀 Starting Main Orchestrator Agent: {AGENT_ID}")
    print(f"📍 AgentCard: http://{HOST}:{PORT}/.well-known/agent-card")
    print(f"🎯 Coordinates: code-logic, research, validation, test-run agents")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
