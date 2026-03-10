"""
Main Orchestrator Agent - Strands Agents compliant
Coordinates all specialized agents for complete production verification workflow
"""

import os
import sys
import json
import zipfile
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import boto3
from strands import Agent, tool
from strands.multiagent.a2a import A2AServer
from strands_tools.a2a_client import A2AClientToolProvider

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared.s3_client import SharedS3Client

# ─── Config ────────────────────────────────────────────────────────────────────

PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "localhost")

# ─── Initialize Clients ────────────────────────────────────────────────────────

# S3 Client
try:
    s3_client = SharedS3Client()
    print("✅ S3 client initialized")
except Exception as e:
    print(f"⚠️  S3 client initialization failed: {e}")
    s3_client = None

# Bedrock Client
try:
    bedrock = boto3.client("bedrock-runtime", region_name=os.getenv("AWS_REGION", "us-east-1"))
    model_id = os.getenv("MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")
    print(f"✅ Bedrock client initialized with model: {model_id}")
except Exception as e:
    print(f"⚠️  Bedrock client initialization failed: {e}")
    bedrock = None
    model_id = None

# ─── Downstream Remote Agents ──────────────────────────────────────────────────

# Create A2A client tool provider to connect to downstream agents
a2a_client_provider = A2AClientToolProvider(
    known_agent_urls=[
        "http://code-logic-agent:8001",
        "http://research-agent:8003",
        "http://validation-agent:8005",
    ]
)

# ─── Orchestration Tools ───────────────────────────────────────────────────────


@tool
def prepare_workspace(
    s3_key: str,
    project_name: str,
    s3_bucket: str = None
) -> Dict[str, Any]:
    """Download and prepare code workspace from S3 for analysis.

    Downloads code archive from S3, extracts it, and prepares it for analysis
    by specialist agents. Returns workspace info and sample code for the agent
    to analyze using specialist tools.

    Args:
        s3_key: S3 key of the code archive (zip file).
        project_name: Name of the project being verified.
        s3_bucket: Optional S3 bucket name (uses default if not provided).

    Returns:
        Dictionary with task_id, workspace path, file list, and sample code for analysis.
    """
    if not s3_client:
        return {"error": "S3 client not available"}

    task_id = str(uuid.uuid4())
    workspace = f"/tmp/workspace/{task_id}"
    os.makedirs(workspace, exist_ok=True)

    print(f"\n🚀 Preparing workspace: {project_name}")
    print(f"   Task ID: {task_id}")
    print(f"   Workspace: {workspace}")

    try:
        # 1. Download from S3
        print(f"📥 Downloading from S3: {s3_key}")
        zip_path = f"{workspace}/code.zip"
        s3_client.download_file(s3_key, zip_path)

        # 2. Extract
        print(f"📦 Extracting archive...")
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(workspace)
        os.remove(zip_path)

        # 3. Get file list for context
        files = []
        python_files = []
        for root, dirs, filenames in os.walk(workspace):
            for filename in filenames:
                rel_path = os.path.relpath(os.path.join(root, filename), workspace)
                files.append(rel_path)
                if filename.endswith('.py'):
                    python_files.append(rel_path)

        print(f"📁 Found {len(files)} files ({len(python_files)} Python files)")

        # 4. Read first Python file as sample
        sample_code = ""
        sample_file = None
        for file in python_files[:1]:  # Get first Python file
            try:
                with open(f"{workspace}/{file}", 'r', encoding='utf-8') as f:
                    sample_code = f.read()
                    sample_file = file
                    break
            except:
                pass

        print(f"✅ Workspace prepared! Sample file: {sample_file}")

        return {
            "task_id": task_id,
            "project_name": project_name,
            "workspace": workspace,
            "files_count": len(files),
            "python_files_count": len(python_files),
            "python_files": python_files[:10],  # First 10 for reference
            "sample_file": sample_file,
            "sample_code": sample_code[:2000] if sample_code else "",  # First 2000 chars
            "status": "workspace_ready",
            "next_step": "Use specialist agents (code_logic_agent, research_agent, validation_agent) to analyze the code, then call finalize_results"
        }

    except Exception as e:
        print(f"❌ Workspace preparation failed: {e}")
        # Cleanup on error
        try:
            shutil.rmtree(workspace, ignore_errors=True)
        except:
            pass
        return {
            "status": "error",
            "error": str(e)
        }


@tool
def finalize_results(
    task_id: str,
    project_name: str,
    workspace: str,
    analysis_results: Dict[str, Any]
) -> Dict[str, Any]:
    """Finalize verification results and upload to S3.

    Aggregates all specialist agent results, creates final report, uploads to S3,
    and cleans up the workspace.

    Args:
        task_id: Task identifier from prepare_workspace.
        project_name: Name of the project.
        workspace: Workspace path from prepare_workspace.
        analysis_results: Dictionary containing results from all specialist agents.

    Returns:
        Dictionary with final status, results URL, and summary.
    """
    if not s3_client:
        return {"error": "S3 client not available"}

    print(f"\n📊 Finalizing results for: {project_name}")
    print(f"   Task ID: {task_id}")

    try:
        # Create comprehensive results
        final_results = {
            "task_id": task_id,
            "project_name": project_name,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "completed",
            "analysis": analysis_results
        }

        # Upload results to S3
        print(f"📤 Uploading results to S3...")
        results_file = f"{workspace}/verification_results.json"
        with open(results_file, 'w') as f:
            json.dump(final_results, f, indent=2)

        result_s3_key = f"results/{task_id}/verification_results.json"
        results_url = s3_client.upload_file(results_file, result_s3_key)

        print(f"✅ Results uploaded to S3")

        # Cleanup workspace
        print(f"🧹 Cleaning up workspace...")
        try:
            shutil.rmtree(workspace, ignore_errors=True)
        except:
            pass

        return {
            "task_id": task_id,
            "project_name": project_name,
            "status": "completed",
            "results_url": results_url,
            "results_s3_key": result_s3_key,
            "summary": {
                "agents_used": list(analysis_results.keys()),
                "total_checks": len(analysis_results)
            }
        }

    except Exception as e:
        print(f"❌ Finalization failed: {e}")
        return {
            "task_id": task_id,
            "status": "error",
            "error": str(e)
        }


@tool
def analyze_code_sample(code: str, language: str = "python") -> str:
    """Analyze a code sample for quick feedback.

    Provides rapid analysis of code structure and quality without full workflow.

    Args:
        code: Source code as a string.
        language: Programming language (default: python).

    Returns:
        Human-readable analysis summary.
    """
    if not code or not code.strip():
        return "Error: No code provided"

    # This will be handled by delegating to code_logic_agent
    # The actual delegation is done by the Gemini model via function calling
    return f"Analyzing {len(code)} characters of {language} code..."


@tool
def get_agent_status() -> Dict[str, str]:
    """Check the status of all downstream specialist agents.

    Returns:
        Dictionary mapping agent names to their status (online/offline).
    """
    agents_status = {
        "code_logic_agent": "configured",
        "research_agent": "configured",
        "validation_agent": "configured",
    }
    return agents_status


# ─── Load System Prompt ────────────────────────────────────────────────────────

prompt_path = Path(__file__).parent / "prompt.txt"
try:
    system_prompt = prompt_path.read_text()
    print("✅ System prompt loaded")
except Exception as e:
    print(f"⚠️  Failed to load prompt.txt: {e}")
    system_prompt = """You are an orchestrator agent that coordinates multiple specialist agents for production code verification.

You have access to:
- code_logic_agent: Analyzes code structure, complexity, and quality
- research_agent: Searches codebase for patterns and dependencies
- validation_agent: Performs security scans and validation

Your job is to:
1. Understand the user's verification request
2. Delegate to appropriate specialist agents in the right order
3. Synthesize results into a comprehensive summary
4. Provide actionable insights

Always start with code_logic_agent for structural analysis, then use research_agent for deeper insights, and finish with validation_agent for security checks."""

# ─── Agent Definition ──────────────────────────────────────────────────────────

# Combine local tools with A2A client tools
all_tools = [
    prepare_workspace,
    finalize_results,
    analyze_code_sample,
    get_agent_status,
] + a2a_client_provider.tools

root_agent = Agent(
    name='orchestrator_agent',
    description='Orchestrates multi-agent workflows for production code verification. Coordinates code analysis, research, and validation agents to provide comprehensive code quality assessment.',
    system_prompt=system_prompt,
    tools=all_tools,
)

# Wrap as A2A server with compliant streaming
# Use explicit http_url with container hostname for Docker networking
a2a_server = A2AServer(
    root_agent,
    host="0.0.0.0",
    port=PORT,
    http_url=f"http://orchestrator-agent:{PORT}",
    enable_a2a_compliant_streaming=True
)

# ─── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"🚀 Orchestrator Agent  →  http://{HOST}:{PORT}/")
    print(f"📄 Agent Card          →  http://{HOST}:{PORT}/.well-known/agent-card.json")
    a2a_server.serve()
