"""
App - Trigger Tool for Orchestrator Agent
Simple frontend gateway that uploads artifacts and triggers the orchestrator agent
"""
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
import httpx
from typing import Optional
from datetime import datetime
import os
import json
import pathlib
import uuid

# Import S3 client
from s3_client import S3ArtifactManager

app = FastAPI(title="A2A Trigger App")

# Add validation error handler for debugging
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    print(f"❌ Validation Error:")
    print(f"   Path: {request.url.path}")
    print(f"   Method: {request.method}")
    print(f"   Errors: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()}
    )

# Initialize S3 client
try:
    s3_manager = S3ArtifactManager()
    print("✅ S3 client initialized")
except Exception as e:
    print(f"⚠️  S3 client initialization failed: {e}")
    s3_manager = None

# Orchestrator agent endpoint
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://localhost:8000")


# ============================================
# Static Files and Frontend
# ============================================

# Resolve frontend paths
FRONTEND_DIR = pathlib.Path(__file__).parent.parent.parent / "frontend"
STATIC_DIR = FRONTEND_DIR / "static"

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def serve_frontend():
    """Serve frontend HTML"""
    return FileResponse(str(FRONTEND_DIR / "index.html"))


# ============================================
# API Endpoints
# ============================================

@app.get("/api/info")
async def api_info():
    """API info endpoint"""
    return {
        "name": "A2A Trigger App",
        "version": "0.1.0",
        "role": "Frontend gateway - triggers orchestrator agent",
        "orchestrator": ORCHESTRATOR_URL
    }


@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================
# Artifact Upload
# ============================================

@app.post("/api/artifacts/upload")
async def upload_artifact(
    file: UploadFile = File(...),
    project_name: str = Form(...),
    description: Optional[str] = Form(None)
):
    """Upload artifact to S3"""
    print(f"📥 Upload request received:")
    print(f"   File: {file.filename if file else 'None'}")
    print(f"   Project: {project_name}")
    print(f"   Description: {description}")

    if not s3_manager:
        raise HTTPException(
            status_code=503,
            detail="S3 service not available"
        )

    try:
        file_content = await file.read()
        
        s3_result = await s3_manager.upload_artifact(
            file_content=file_content,
            filename=file.filename,
            content_type=file.content_type,
            metadata={
                "project_name": project_name,
                "description": description
            }
        )

        return {
            "status": "success",
            "filename": file.filename,
            "s3_key": s3_result["s3_key"],
            "s3_url": s3_result["s3_url"],
            "size": s3_result["size"]
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )


@app.get("/api/artifacts")
async def list_artifacts(limit: int = 10):
    """List recent artifacts from S3"""
    if not s3_manager:
        raise HTTPException(
            status_code=503,
            detail="S3 service not available"
        )
    
    try:
        artifacts = await s3_manager.list_artifacts(prefix="artifacts/")
        
        # Sort by last modified (newest first) and limit
        artifacts = sorted(
            artifacts, 
            key=lambda x: x.get('last_modified', ''), 
            reverse=True
        )[:limit]
        
        # Add friendly fields
        for artifact in artifacts:
            # Extract filename from key
            artifact['filename'] = artifact['key'].split('/')[-1]
            # Add uploaded_at field
            artifact['uploaded_at'] = artifact.get('last_modified', datetime.utcnow().isoformat())
        
        return {
            "status": "success",
            "artifacts": artifacts,
            "count": len(artifacts)
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list artifacts: {str(e)}"
        )


# ============================================
# Trigger Orchestrator Agent
# ============================================

@app.post("/api/verify/trigger")
async def trigger_verification(
    s3_key: str = Form(...),
    project_name: str = Form(...)
):
    """
    Trigger orchestrator agent with project artifact and name
    The orchestrator handles everything else
    """
    request_id = str(uuid.uuid4())

    print(f"🔥 Trigger verification request:")
    print(f"   S3 Key: {s3_key}")
    print(f"   Project: {project_name}")
    print(f"   Orchestrator URL: {ORCHESTRATOR_URL}")

    try:
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "message/send",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [
                        {
                            "kind": "text",
                            "text": f"Run full verification workflow for project '{project_name}' with S3 key '{s3_key}'"
                        },
                        {
                            "kind": "data",
                            "data": {
                                "workflow": "verification",
                                "s3_key": s3_key,
                                "project_name": project_name,
                                "s3_bucket": os.getenv("S3_BUCKET_NAME")
                            }
                        }
                    ],
                    "messageId": request_id
                },
                "metadata": {}
            }
        }

        print(f"📤 Sending to orchestrator: {json.dumps(payload, indent=2)}")

        # Strands A2A agents use root endpoint
        endpoints = [
            f"{ORCHESTRATOR_URL}/",
        ]

        last_error = None

        async with httpx.AsyncClient(timeout=300.0) as client:
            for endpoint in endpoints:
                try:
                    print(f"📍 Trying endpoint: {endpoint}")

                    response = await client.post(
                        endpoint,
                        json=payload,
                        headers={"Content-Type": "application/json"}
                    )

                    print(f"📥 Response status: {response.status_code}")

                    if response.status_code == 404:
                        print(f"   ⚠️  404 - trying next endpoint...")
                        continue

                    print(f"📥 Response body: {response.text[:500]}")
                    response.raise_for_status()

                    response_data = response.json()

                    # Check for JSON-RPC error
                    if "error" in response_data:
                        error = response_data["error"]
                        raise HTTPException(
                            status_code=500,
                            detail=f"A2A error: {error.get('message', 'Unknown error')}"
                        )

                    result = response_data.get("result", {})

                    # Extract task_id based on result kind
                    if result.get("kind") == "task":
                        task_id = result.get("taskId", f"task-{request_id}")
                    elif result.get("kind") == "message":
                        # For immediate message responses, use request_id as task_id
                        task_id = f"message-{request_id}"
                    else:
                        task_id = f"task-{request_id}"

                    print(f"✅ Task created: {task_id} (kind: {result.get('kind', 'unknown')})")

                    return {
                        "status": "triggered",
                        "task_id": task_id,
                        "project_name": project_name,
                        "orchestrator": ORCHESTRATOR_URL,
                        "endpoint_used": endpoint,
                        "result_kind": result.get("kind", "unknown")
                    }

                except httpx.ConnectError as e:
                    print(f"❌ Connection Error to {endpoint}: {str(e)}")
                    last_error = e
                    continue
                except httpx.HTTPError as e:
                    print(f"❌ HTTP Error for {endpoint}: {str(e)}")
                    if hasattr(e, 'response') and e.response:
                        print(f"   Response: {e.response.text[:200]}")
                    last_error = e
                    continue

        # If we got here, all endpoints failed
        error_msg = f"All orchestrator endpoints failed. Last error: {str(last_error)}"
        print(f"❌ {error_msg}")
        raise HTTPException(
            status_code=503,
            detail=error_msg
        )
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("🚀 A2A Trigger App Starting...")
    print("=" * 60)
    print("\n📍 Role: Frontend gateway - triggers orchestrator agent")
    print(f"   App: http://localhost:8006")
    print(f"   Orchestrator: {ORCHESTRATOR_URL}")
    print("\n📚 Workflow:")
    print("   1. Upload code artifact (zip)")
    print("   2. Trigger orchestrator with project_artifact + project_name")
    print("   3. Orchestrator handles everything else")
    print("\n" + "=" * 60 + "\n")

    PORT = int(os.getenv("PORT", "8006"))
    uvicorn.run(app, host="0.0.0.0", port=PORT)
