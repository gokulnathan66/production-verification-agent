"""
Simple A2A Orchestrator
Discovers and coordinates multiple A2A agents using MCP for documentation
"""
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime
import os
import asyncio
import json
import pathlib

# Import MCP client
from mcp_client import mcp_doc_client

# Import S3 and Storage clients
from s3_client import S3ArtifactManager
from storage import PersistentStorage
import uuid

app = FastAPI(title="A2A Orchestrator")

# Agent registry (in-memory, could be Redis)
AGENT_REGISTRY: Dict[str, Dict[str, Any]] = {}

# In-memory task storage (supplemented by persistent storage)
TASKS: Dict[str, Dict[str, Any]] = {}

# Initialize S3 and Storage clients
try:
    s3_manager = S3ArtifactManager()
    print("✅ S3 client initialized")
except Exception as e:
    print(f"⚠️  S3 client initialization failed: {e}")
    s3_manager = None

storage = PersistentStorage()


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
# Lifecycle Events
# ============================================

@app.on_event("startup")
async def startup():
    """Initialize database and connections on startup"""
    await storage.database.connect()
    await storage.init_db()
    print("✅ Database initialized")


@app.on_event("shutdown")
async def shutdown():
    """Close database connection on shutdown"""
    await storage.database.disconnect()
    print("✅ Database disconnected")


# ============================================
# Static Files and Frontend
# ============================================

# Resolve frontend paths (orchestrator runs from src/orchestrator/)
FRONTEND_DIR = pathlib.Path(__file__).parent.parent.parent / "frontend"
STATIC_DIR = FRONTEND_DIR / "static"

# Mount static files (CSS, JS, assets)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def serve_frontend():
    """Serve frontend HTML"""
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/tasks.html")
async def serve_tasks():
    """Serve tasks page"""
    return FileResponse(str(FRONTEND_DIR / "tasks.html"))


@app.get("/logs.html")
async def serve_logs():
    """Serve logs page"""
    return FileResponse(str(FRONTEND_DIR / "logs.html"))


@app.get("/progress.html")
async def serve_progress():
    """Serve progress page"""
    return FileResponse(str(FRONTEND_DIR / "progress.html"))


# ============================================
# API Endpoints
# ============================================

@app.get("/api/info")
async def api_info():
    """API info endpoint"""
    return {
        "name": "A2A Orchestrator",
        "version": "0.1.0",
        "endpoints": {
            "discover": "POST /discover - Discover a new agent",
            "execute": "POST /execute - Execute a task",
            "agents": "GET /agents - List known agents",
            "health": "GET /health - Health check",
            "upload": "POST /api/artifacts/upload - Upload artifact to S3",
            "artifacts": "GET /api/artifacts - List artifacts",
            "tasks": "GET /api/tasks/history - Get task history",
            "logs": "GET /api/logs - Get agent logs"
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

    # Save task to database
    if result.get("status") == "completed" and result.get("result"):
        task_id = result["result"].get("taskId", f"task-{datetime.utcnow().timestamp()}")
        agent_id = result.get("agent_used", "unknown")
        agent_data = AGENT_REGISTRY.get(agent_id, {})

        await storage.save_task(
            task_id=task_id,
            agent_id=agent_id,
            agent_name=agent_data.get("name"),
            status="completed",
            request=request.request,
            result=json.dumps(result["result"]),
            metadata=request.metadata
        )

        # Log the execution
        await storage.save_log(
            agent_id=agent_id,
            agent_name=agent_data.get("name"),
            task_id=task_id,
            level="INFO",
            message=f"Task executed: {request.request[:100]}",
            metadata={"status": "completed"}
        )
    elif result.get("status") == "error":
        task_id = f"task-{datetime.utcnow().timestamp()}"
        agent_id = result.get("agent_used", "unknown")
        agent_data = AGENT_REGISTRY.get(agent_id, {})

        await storage.save_task(
            task_id=task_id,
            agent_id=agent_id,
            agent_name=agent_data.get("name"),
            status="error",
            request=request.request,
            error=result.get("error"),
            metadata=request.metadata
        )

        # Log the error
        await storage.save_log(
            agent_id=agent_id,
            agent_name=agent_data.get("name"),
            task_id=task_id,
            level="ERROR",
            message=f"Task failed: {result.get('error')}",
            metadata={"status": "error"}
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


# ============================================
# Artifact Management Endpoints
# ============================================

@app.post("/api/artifacts/upload")
async def upload_artifact(
    file: UploadFile = File(...),
    tags: Optional[str] = Form(None),
    description: Optional[str] = Form(None)
):
    """
    Upload artifact to S3 and save metadata

    Form fields:
    - file: File to upload
    - tags: Optional comma-separated tags
    - description: Optional description
    """
    if not s3_manager:
        raise HTTPException(
            status_code=503,
            detail="S3 service not available. Check AWS credentials."
        )

    try:
        # Read file content
        file_content = await file.read()

        # Upload to S3
        s3_result = await s3_manager.upload_artifact(
            file_content=file_content,
            filename=file.filename,
            content_type=file.content_type,
            metadata={
                "tags": tags,
                "description": description
            }
        )

        # Save metadata to database
        artifact_id = await storage.save_artifact(
            filename=file.filename,
            s3_key=s3_result["s3_key"],
            s3_url=s3_result["s3_url"],
            presigned_url=s3_result["presigned_url"],
            bucket=s3_result["bucket"],
            size=s3_result["size"],
            content_type=s3_result["content_type"],
            tags=tags,
            description=description
        )

        # Log the upload
        await storage.save_log(
            agent_id="orchestrator",
            agent_name="Orchestrator",
            level="INFO",
            message=f"Artifact uploaded: {file.filename}",
            metadata={"artifact_id": artifact_id, "size": s3_result["size"]}
        )

        return {
            "status": "success",
            "artifact_id": artifact_id,
            "filename": file.filename,
            "s3_url": s3_result["s3_url"],
            "presigned_url": s3_result["presigned_url"],
            "size": s3_result["size"]
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )


@app.get("/api/artifacts")
async def list_artifacts(limit: int = 100, offset: int = 0):
    """
    List all uploaded artifacts

    Query params:
    - limit: Max number of artifacts to return (default 100)
    - offset: Number of artifacts to skip (default 0)
    """
    try:
        artifacts = await storage.get_artifacts(limit=limit, offset=offset)
        return {
            "artifacts": artifacts,
            "total": len(artifacts),
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list artifacts: {str(e)}"
        )


# ============================================
# Task Management Endpoints
# ============================================

@app.get("/api/tasks/history")
async def get_task_history(
    agent_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    Get task history with optional filters

    Query params:
    - agent_id: Filter by agent ID
    - status: Filter by status (pending, in_progress, completed, error)
    - limit: Max number of tasks to return (default 100)
    - offset: Number of tasks to skip (default 0)
    """
    try:
        tasks = await storage.get_tasks(
            agent_id=agent_id,
            status=status,
            limit=limit,
            offset=offset
        )

        return {
            "tasks": tasks,
            "total": len(tasks),
            "limit": limit,
            "offset": offset,
            "filters": {
                "agent_id": agent_id,
                "status": status
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get task history: {str(e)}"
        )


@app.get("/api/tasks/{task_id}/details")
async def get_task_details(task_id: str):
    """
    Get full details for a specific task

    Path params:
    - task_id: Task ID
    """
    try:
        task = await storage.get_task_by_id(task_id)

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        return {
            "task": task
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get task details: {str(e)}"
        )


# ============================================
# Logs Endpoints
# ============================================

@app.get("/api/logs")
async def get_logs(
    agent_id: Optional[str] = None,
    task_id: Optional[str] = None,
    level: Optional[str] = None,
    limit: int = 500,
    offset: int = 0
):
    """
    Get agent logs with optional filters

    Query params:
    - agent_id: Filter by agent ID
    - task_id: Filter by task ID
    - level: Filter by log level (INFO, WARNING, ERROR)
    - limit: Max number of logs to return (default 500)
    - offset: Number of logs to skip (default 0)
    """
    try:
        logs = await storage.get_logs(
            agent_id=agent_id,
            task_id=task_id,
            level=level,
            limit=limit,
            offset=offset
        )

        return {
            "logs": logs,
            "total": len(logs),
            "limit": limit,
            "offset": offset,
            "filters": {
                "agent_id": agent_id,
                "task_id": task_id,
                "level": level
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get logs: {str(e)}"
        )


@app.get("/api/logs/stream")
async def stream_logs():
    """
    Stream logs in real-time using Server-Sent Events (SSE)

    Returns:
    - SSE stream of log entries as they're created
    """
    async def event_generator():
        """Generate SSE events for new logs"""
        last_id = 0

        while True:
            try:
                # Query for new logs since last_id
                logs = await storage.get_logs(limit=100)

                # Filter logs with id > last_id
                new_logs = [log for log in logs if log.get('id', 0) > last_id]

                if new_logs:
                    # Update last_id
                    last_id = max(log.get('id', 0) for log in new_logs)

                    # Send new logs as SSE
                    for log in reversed(new_logs):  # Reverse to get chronological order
                        yield f"data: {json.dumps(log)}\n\n"

                # Wait before checking again
                await asyncio.sleep(1)

            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                await asyncio.sleep(5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


# ============================================
# Progress Tracking Endpoints
# ============================================

@app.get("/api/progress/stream")
async def stream_progress():
    """
    Stream agent status and progress in real-time using SSE

    Returns:
    - SSE stream of agent status updates
    """
    async def event_generator():
        """Generate SSE events for agent status"""
        while True:
            try:
                # Collect agent statuses
                agent_statuses = []

                for agent_id, agent_data in AGENT_REGISTRY.items():
                    # Get agent health
                    try:
                        async with httpx.AsyncClient() as client:
                            response = await client.get(
                                f"{agent_data['baseUrl']}/health",
                                timeout=2.0
                            )
                            health = response.json()
                            health_status = health.get("status", "unknown")
                    except:
                        health_status = "offline"

                    # Count tasks for this agent
                    tasks = await storage.get_tasks(agent_id=agent_id, limit=1000)
                    active_tasks = [t for t in tasks if t['status'] == 'in_progress']
                    completed_tasks = [t for t in tasks if t['status'] == 'completed']

                    agent_statuses.append({
                        "agent_id": agent_id,
                        "name": agent_data.get("name"),
                        "health": health_status,
                        "active_tasks": len(active_tasks),
                        "completed_tasks": len(completed_tasks),
                        "total_tasks": len(tasks)
                    })

                # Get global stats
                all_tasks = await storage.get_tasks(limit=1000)
                global_stats = {
                    "total_tasks": len(all_tasks),
                    "active_tasks": len([t for t in all_tasks if t['status'] == 'in_progress']),
                    "completed_tasks": len([t for t in all_tasks if t['status'] == 'completed']),
                    "error_tasks": len([t for t in all_tasks if t['status'] == 'error'])
                }

                # Send update
                update = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "agents": agent_statuses,
                    "global": global_stats
                }

                yield f"data: {json.dumps(update)}\n\n"

                # Wait before next update
                await asyncio.sleep(2)

            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                await asyncio.sleep(5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


# ============================================
# Production Verification Trigger
# ============================================

@app.post("/api/verify/trigger")
async def trigger_verification(
    s3_key: str = Form(...),
    project_name: str = Form(...),
    metadata: Optional[str] = Form(None)
):
    """
    Trigger production verification workflow
    
    Steps:
    1. Validate S3 artifact exists
    2. Call orchestrator_agent via A2A protocol
    3. Return task_id for tracking
    """
    if not s3_manager:
        raise HTTPException(
            status_code=503,
            detail="S3 service not available"
        )
    
    # Parse metadata
    meta_dict = {}
    if metadata:
        try:
            meta_dict = json.loads(metadata)
        except:
            pass
    
    # Call orchestrator_agent
    orchestrator_url = "http://localhost:8000"
    request_id = str(uuid.uuid4())
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{orchestrator_url}/a2a",
                json={
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "method": "a2a.createTask",
                    "params": {
                        "message": {
                            "role": "user",
                            "parts": [
                                {
                                    "kind": "text",
                                    "text": f"Verify production code: {project_name}"
                                },
                                {
                                    "kind": "data",
                                    "data": {
                                        "s3_key": s3_key,
                                        "s3_bucket": s3_manager.bucket_name,
                                        "project_name": project_name,
                                        "metadata": meta_dict
                                    }
                                }
                            ]
                        }
                    }
                },
                timeout=300.0
            )
            response.raise_for_status()
            result = response.json()
        
        # Extract task_id
        task_id = result.get("result", {}).get("taskId", f"task-{request_id}")
        
        # Save task to database
        await storage.save_task(
            task_id=task_id,
            agent_id="orchestrator-agent",
            agent_name="Orchestrator Agent",
            status="in_progress",
            request=f"Verify production code: {project_name}",
            metadata={
                "s3_key": s3_key,
                "project_name": project_name,
                **meta_dict
            }
        )
        
        # Log the trigger
        await storage.save_log(
            agent_id="intract-orchestrator",
            agent_name="Intract Orchestrator",
            task_id=task_id,
            level="INFO",
            message=f"Triggered verification for {project_name}",
            metadata={"s3_key": s3_key}
        )
        
        return {
            "status": "triggered",
            "task_id": task_id,
            "project_name": project_name,
            "s3_key": s3_key
        }
    
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger orchestrator: {str(e)}"
        )


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
