"""
Main Orchestrator Agent - Official A2A SDK compliant
Coordinates all specialized agents for complete production verification workflow
"""

import asyncio
import os
import sys
import uuid
import json
import zipfile
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import boto3
import httpx
import uvicorn
from a2a.client import A2AClient
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps import A2AStarletteApplication
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    DataPart,
    Message,
    MessageSendParams,
    Part,
    Role,
    TextPart,
)

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared.s3_client import SharedS3Client

# ─── Config ────────────────────────────────────────────────────────────────────

AGENT_ID = os.getenv("AGENT_ID", "orchestrator-agent")
PORT     = int(os.getenv("PORT", "8000"))
HOST     = os.getenv("HOST", "localhost")

# ─── Agent Card ────────────────────────────────────────────────────────────────

agent_card = AgentCard(
    name="Main Orchestrator Agent",
    description="Orchestrates multi-agent workflows for production verification and code analysis",
    url=f"http://{HOST}:{PORT}/",
    version="1.0.0",
    defaultInputModes=["text"],
    defaultOutputModes=["text", "data"],
    capabilities=AgentCapabilities(streaming=False),
    skills=[
        AgentSkill(
            id="workflow_orchestration",
            name="Workflow Orchestration",
            description="Coordinate multiple agents in a sequential verification pipeline",
            tags=["orchestration", "workflow", "pipeline"],
            examples=["Run full analysis on this Python file"],
        ),
        AgentSkill(
            id="agent_coordination",
            name="Agent Coordination",
            description="Discover and delegate tasks to specialized downstream agents",
            tags=["coordination", "delegation", "discovery"],
            examples=["Coordinate code-logic and research agents"],
        ),
        AgentSkill(
            id="production_verification",
            name="Production Verification",
            description="End-to-end verification: analysis, research, validation, tests",
            tags=["verification", "production", "complete"],
            examples=["Verify this code is production-ready"],
        ),
    ],
)

# ─── Agent Registry ────────────────────────────────────────────────────────────

# { agent_id: { "baseUrl": str, "client": A2AClient | None, "status": str } }
AGENT_REGISTRY: Dict[str, Dict[str, Any]] = {}

KNOWN_AGENTS = {
    "code-logic-agent" : "http://localhost:8001",
    "research-agent"   : "http://localhost:8003",
    "test-run-agent"   : "http://localhost:8004",
    "validation-agent" : "http://localhost:8005",
}

AGENT_DESCRIPTIONS = {
    "code-logic-agent": "Analyzes code structure, logic, and architecture using AST parsing",
    "research-agent": "Searches codebase for patterns, functions, and dependencies using grep",
    "test-run-agent": "Generates and executes tests with coverage analysis",
    "validation-agent": "Runs security scans, finds secrets and vulnerabilities",
}

# ─── Orchestrator ──────────────────────────────────────────────────────────────

class MultiAgentOrchestrator:
    """
    Discovers downstream A2A agents and coordinates them into workflows.
    Uses the official A2AClient for all outbound calls.
    """
    
    def __init__(self):
        try:
            self.s3_client = SharedS3Client()
            print("✅ S3 client initialized")
        except Exception as e:
            print(f"⚠️  S3 client initialization failed: {e}")
            self.s3_client = None

        # Initialize Bedrock client
        try:
            self.bedrock = boto3.client("bedrock-runtime", region_name=os.getenv("AWS_REGION", "us-east-1"))
            print("✅ Bedrock client initialized")
        except Exception as e:
            print(f"⚠️  Bedrock client initialization failed: {e}")
            self.bedrock = None

        # Get model ID from environment variable
        self.model_id = os.getenv("MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")
        print(f"✅ Using Bedrock model: {self.model_id}")

        # Load system prompt
        prompt_path = Path(__file__).parent / "prompt.txt"
        try:
            self.system_prompt = prompt_path.read_text()
            print("✅ System prompt loaded")
        except Exception as e:
            print(f"⚠️  Failed to load prompt.txt: {e}")
            self.system_prompt = "You are an orchestrator agent."

    async def discover_agents(self, http_client: httpx.AsyncClient) -> Dict[str, Any]:
        """
        Ping each known agent's /.well-known/agent.json and build A2AClient instances.
        Returns a snapshot of discovery results for logging.
        """
        results: Dict[str, Any] = {}

        for agent_id, base_url in KNOWN_AGENTS.items():
            try:
                client = await A2AClient.get_client_from_agent_card_url(
                    http_client, base_url
                )
                AGENT_REGISTRY[agent_id] = {
                    "baseUrl": base_url,
                    "client": client,
                    "status": "online",
                }
                results[agent_id] = {"status": "online", "baseUrl": base_url}
            except Exception as exc:
                AGENT_REGISTRY[agent_id] = {
                    "baseUrl": base_url,
                    "client": None,
                    "status": "offline",
                }
                results[agent_id] = {
                    "status": "offline",
                    "baseUrl": base_url,
                    "error": str(exc),
                }

        return results

    async def call_agent(
        self,
        agent_id: str,
        parts: List[Part],
        http_client: httpx.AsyncClient,
    ) -> Dict[str, Any]:
        """
        Send a message to a downstream agent using A2AClient.send_message().
        Falls back to re-discovery if the client is missing.
        """
        entry = AGENT_REGISTRY.get(agent_id, {})

        # Re-discover if not yet known or offline
        if not entry.get("client"):
            await self.discover_agents(http_client)
            entry = AGENT_REGISTRY.get(agent_id, {})

        if entry.get("status") != "online" or not entry.get("client"):
            raise ValueError(f"Agent '{agent_id}' is not available")

        client: A2AClient = entry["client"]

        message = Message(
            messageId=str(uuid.uuid4()),
            role=Role.user,
            parts=parts,
        )
        params = MessageSendParams(message=message)
        response = await client.send_message(params)
        return response.model_dump()
    
    def _build_system_prompt(self) -> str:
        """Build system prompt with agent registry."""
        agents_info = "\n".join([
            f"- {agent_id}: {AGENT_DESCRIPTIONS[agent_id]}"
            for agent_id in KNOWN_AGENTS
        ])
        
        return f"""{self.system_prompt}

## Available Agents

{agents_info}

## Response Format

You must respond with valid JSON in one of these formats:

1. To call an agent:
{{"action": "call_agent", "agent_id": "<agent_id>", "instruction": "<what to do>"}}

2. To provide final answer:
{{"action": "final_answer", "summary": "<comprehensive summary of all results>"}}

Rules:
- Analyze the task and decide which agents are needed and in what order
- Call agents sequentially, using results from previous agents to inform next steps
- Only call agents that are relevant to the task
- After all necessary agents complete, provide a final_answer with comprehensive summary
"""

    async def llm_run(
        self,
        user_task: str,
        context: dict,
        http_client: httpx.AsyncClient,
    ) -> Dict[str, Any]:
        """LLM-driven agentic loop using AWS Bedrock."""
        if not self.bedrock:
            raise Exception("Bedrock client not initialized")
        
        messages = [{"role": "user", "content": user_task}]
        agent_results = {}
        
        print(f"\n🤖 LLM Orchestration Started")
        print(f"   Task: {user_task[:100]}...")
        
        for turn in range(10):  # max 10 LLM turns
            print(f"\n🔄 Turn {turn + 1}/10")
            
            try:
                # Call Bedrock
                response = self.bedrock.invoke_model(
                    modelId=self.model_id,
                    body=json.dumps({
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 2048,
                        "system": self._build_system_prompt(),
                        "messages": messages,
                    })
                )
                
                result = json.loads(response["body"].read())
                llm_text = result["content"][0]["text"]
                messages.append({"role": "assistant", "content": llm_text})
                
                print(f"   LLM Response: {llm_text[:200]}...")
                
                # Parse decision
                try:
                    decision = json.loads(llm_text)
                except json.JSONDecodeError:
                    print(f"   ⚠️  LLM returned non-JSON, treating as final answer")
                    return {
                        "summary": llm_text,
                        "details": agent_results,
                        "turns": turn + 1
                    }
                
                # Handle actions
                if decision.get("action") == "final_answer":
                    print(f"   ✅ Final answer received")
                    return {
                        "summary": decision.get("summary", ""),
                        "details": agent_results,
                        "turns": turn + 1
                    }
                
                elif decision.get("action") == "call_agent":
                    agent_id = decision.get("agent_id")
                    instruction = decision.get("instruction", "")
                    
                    print(f"   📞 Calling agent: {agent_id}")
                    print(f"      Instruction: {instruction[:100]}...")
                    
                    # Call the agent
                    try:
                        result = await self.call_agent(
                            agent_id,
                            [
                                Part(root=TextPart(text=instruction)),
                                Part(root=DataPart(data=context))
                            ],
                            http_client
                        )
                        agent_results[agent_id] = result
                        
                        # Feed result back to LLM
                        result_summary = json.dumps(result)[:2000]
                        messages.append({
                            "role": "user",
                            "content": f"Agent '{agent_id}' completed. Result: {result_summary}"
                        })
                        print(f"   ✅ Agent {agent_id} completed")
                        
                    except Exception as e:
                        error_msg = f"Agent '{agent_id}' failed: {str(e)}"
                        agent_results[agent_id] = {"error": str(e)}
                        messages.append({
                            "role": "user",
                            "content": error_msg
                        })
                        print(f"   ❌ {error_msg}")
                
                else:
                    print(f"   ⚠️  Unknown action: {decision.get('action')}")
                    break
                    
            except Exception as e:
                print(f"   ❌ LLM call failed: {e}")
                return {
                    "summary": f"Orchestration failed: {str(e)}",
                    "details": agent_results,
                    "error": str(e),
                    "turns": turn + 1
                }
        
        print(f"\n⚠️  Max turns reached")
        return {
            "summary": "Orchestration reached maximum turns",
            "details": agent_results,
            "turns": 10
        }

    # ── Workflows ──────────────────────────────────────────────────────────────

    async def run_full_analysis(
        self,
        code: str,
        language: str,
        http_client: httpx.AsyncClient,
    ) -> Dict[str, Any]:
        """
        Sequential pipeline:
          1. Code Logic Analysis
          2. Research (functions / classes / imports)
          3. Security Validation
          4. Test Generation
        """
        parts: List[Part] = [
            Part(root=TextPart(text=code)),
            Part(root=DataPart(data={"code": code, "language": language})),
        ]

        steps = [
            ("code_analysis", "code-logic-agent"),
            ("research",      "research-agent"),
            ("validation",    "validation-agent"),
            ("tests",         "test-run-agent"),
        ]

        results: Dict[str, Any] = {}
        for key, agent_id in steps:
            try:
                results[key] = await self.call_agent(agent_id, parts, http_client)
            except Exception as exc:
                results[key] = {"error": str(exc)}

        return results
    
    async def handle_verification_workflow(
        self,
        s3_key: str,
        s3_bucket: str,
        project_name: str,
        http_client: httpx.AsyncClient,
        metadata: Dict[str, Any] = {}
    ) -> Dict[str, Any]:
        """
        Complete production verification workflow with shared workspace:
        1. Download code from S3
        2. Extract to /tmp/workspace/{task_id}/
        3. Run agents sequentially (pass workspace path)
        4. Upload results to S3
        5. Cleanup workspace
        6. Return summary
        """
        if not self.s3_client:
            raise Exception("S3 client not available")
        
        task_id = str(uuid.uuid4())
        workspace = f"/tmp/workspace/{task_id}"
        os.makedirs(workspace, exist_ok=True)
        
        print(f"\n🚀 Starting verification workflow: {project_name}")
        print(f"   Task ID: {task_id}")
        print(f"   Workspace: {workspace}")
        
        try:
            # 1. Download from S3
            print(f"📥 Downloading from S3: {s3_key}")
            zip_path = f"{workspace}/code.zip"
            self.s3_client.download_file(s3_key, zip_path)
            
            # 2. Extract
            print(f"📦 Extracting archive...")
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(workspace)
            os.remove(zip_path)
            
            # 3. Run agents sequentially
            results = {}
            
            print(f"🔍 Running Code Logic Agent...")
            try:
                results["code_logic"] = await self.call_agent(
                    "code-logic-agent",
                    [
                        TextPart(text=f"Analyze code in workspace"),
                        DataPart(data={
                            "workspace": workspace,
                            "project_name": project_name,
                            "task_id": task_id
                        })
                    ],
                    http_client
                )
            except Exception as e:
                results["code_logic"] = {"error": str(e), "status": "failed"}
            
            print(f"📚 Running Research Agent...")
            try:
                results["research"] = await self.call_agent(
                    "research-agent",
                    [
                        TextPart(text=f"Research patterns in workspace"),
                        DataPart(data={
                            "workspace": workspace,
                            "project_name": project_name,
                            "task_id": task_id
                        })
                    ],
                    http_client
                )
            except Exception as e:
                results["research"] = {"error": str(e), "status": "failed"}
            
            print(f"🧪 Running Test Run Agent...")
            try:
                results["tests"] = await self.call_agent(
                    "test-run-agent",
                    [
                        TextPart(text=f"Generate and run tests"),
                        DataPart(data={
                            "workspace": workspace,
                            "project_name": project_name,
                            "task_id": task_id
                        })
                    ],
                    http_client
                )
            except Exception as e:
                results["tests"] = {"error": str(e), "status": "failed"}
            
            print(f"🛡️  Running Validation Agent...")
            try:
                results["validation"] = await self.call_agent(
                    "validation-agent",
                    [
                        TextPart(text=f"Validate code security and quality"),
                        DataPart(data={
                            "workspace": workspace,
                            "project_name": project_name,
                            "task_id": task_id
                        })
                    ],
                    http_client
                )
            except Exception as e:
                results["validation"] = {"error": str(e), "status": "failed"}
            
            # 4. Upload results to S3
            print(f"📤 Uploading results to S3...")
            results_file = f"{workspace}/verification_results.json"
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            result_s3_key = f"results/{task_id}/verification_results.json"
            results_url = self.s3_client.upload_file(results_file, result_s3_key)
            
            summary = {
                "code_logic": results["code_logic"].get("status", "completed"),
                "research": results["research"].get("status", "completed"),
                "tests": results["tests"].get("status", "completed"),
                "validation": results["validation"].get("status", "completed")
            }
            
            print(f"✅ Verification complete!")
            
            return {
                "task_id": task_id,
                "status": "completed",
                "project_name": project_name,
                "workspace": workspace,
                "results_s3_key": result_s3_key,
                "results_url": results_url,
                "summary": summary,
                "results": results
            }
        
        except Exception as e:
            print(f"❌ Verification failed: {e}")
            return {
                "task_id": task_id,
                "status": "error",
                "error": str(e),
                "workspace": workspace
            }
        
        finally:
            print(f"🧹 Cleaning up workspace...")
            try:
                shutil.rmtree(workspace, ignore_errors=True)
            except:
                pass

    # ── Summary Builder ────────────────────────────────────────────────────────

    @staticmethod
    def _extract_text(task_result: Dict[str, Any], max_chars: int = 500) -> str:
        """Pull the first text part out of a task result safely."""
        try:
            for part in (
                task_result
                .get("result", {})
                .get("artifacts", [{}])[0]
                .get("parts", [])
            ):
                root = part.get("root", {})
                if root.get("kind") == "text":
                    return root["text"][:max_chars]
        except (KeyError, IndexError, TypeError):
            pass
        return "(no output)"

    def generate_summary(self, results: Dict[str, Any]) -> str:
        sep = "═" * 55
        lines = [
            "🎯 Production Verification Complete",
            sep,
        ]

        section_map = {
            "code_analysis": ("📊", "CODE ANALYSIS"),
            "research":      ("🔍", "RESEARCH"),
            "validation":    ("🛡️ ", "VALIDATION"),
            "tests":         ("🧪", "TEST GENERATION"),
        }

        for key, (icon, title) in section_map.items():
            if key not in results:
                continue
            res = results[key]
            if "error" in res:
                lines.append(f"\n{icon} {title}\n  ✗ {res['error']}")
            else:
                lines.append(f"\n{icon} {title}")
                lines.append(self._extract_text(res))

        lines += [sep, "✅ All checks complete!"]
        return "\n".join(lines)


# ─── Agent Executor ────────────────────────────────────────────────────────────

orchestrator = MultiAgentOrchestrator()


class OrchestratorAgentExecutor(AgentExecutor):
    """
    A2A executor for the orchestrator.
    Parses the incoming message, discovers agents, runs the requested
    workflow, and emits a summary + raw results as artifacts.
    """

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        await updater.submit()
        await updater.start_work()

        try:
            # ── Parse incoming parts ──────────────────────────────────────────
            code_text = ""
            language  = "python"
            workflow  = "full_analysis"
            
            # New: verification workflow params
            s3_key = None
            s3_bucket = None
            project_name = None
            metadata = {}

            for part in context.message.parts:
                if isinstance(part.root, TextPart):
                    text = part.root.text
                    code_text += text
                    # Check if this is a verification request
                    if "verify production code" in text.lower():
                        workflow = "verification"
                elif isinstance(part.root, DataPart):
                    data: dict = part.root.data or {}
                    code_text = data.get("code", code_text)
                    language  = data.get("language", "python")
                    workflow  = data.get("workflow", workflow)
                    
                    # Extract verification params
                    s3_key = data.get("s3_key")
                    s3_bucket = data.get("s3_bucket")
                    project_name = data.get("project_name")
                    metadata = data.get("metadata", {})

            # ── Discover + run workflow ───────────────────────────────────────
            async with httpx.AsyncClient(timeout=300.0) as http_client:
                await orchestrator.discover_agents(http_client)

                if workflow == "verification" and s3_key:
                    # Prepare workspace for verification
                    task_id = str(uuid.uuid4())
                    workspace = f"/tmp/workspace/{task_id}"
                    os.makedirs(workspace, exist_ok=True)
                    
                    # Download and extract code
                    if orchestrator.s3_client:
                        zip_path = f"{workspace}/code.zip"
                        orchestrator.s3_client.download_file(s3_key, zip_path)
                        with zipfile.ZipFile(zip_path, 'r') as zf:
                            zf.extractall(workspace)
                        os.remove(zip_path)
                    
                    # LLM-driven orchestration
                    workflow_results = await orchestrator.llm_run(
                        user_task=f"Verify production code for project '{project_name}'. The code is in workspace: {workspace}",
                        context={
                            "workspace": workspace,
                            "project_name": project_name,
                            "task_id": task_id,
                            "s3_key": s3_key
                        },
                        http_client=http_client
                    )
                    
                    # Upload results
                    if orchestrator.s3_client:
                        results_file = f"{workspace}/verification_results.json"
                        with open(results_file, 'w') as f:
                            json.dump(workflow_results, f, indent=2)
                        result_s3_key = f"results/{task_id}/verification_results.json"
                        results_url = orchestrator.s3_client.upload_file(results_file, result_s3_key)
                        workflow_results["results_url"] = results_url
                    
                    # Cleanup
                    shutil.rmtree(workspace, ignore_errors=True)
                    
                elif workflow == "full_analysis":
                    # LLM-driven orchestration for code analysis
                    workflow_results = await orchestrator.llm_run(
                        user_task=f"Analyze this {language} code:\n\n{code_text[:1000]}",
                        context={"code": code_text, "language": language},
                        http_client=http_client
                    )
                else:
                    workflow_results = {"error": f"Unknown workflow: '{workflow}'"}

            # ── Build summary ─────────────────────────────────────────────────
            summary_text = workflow_results.get("summary", "No summary available")
            
            if workflow == "verification":
                summary_text = f"""
🎯 Production Verification Complete (LLM-Driven)

Project: {project_name or 'N/A'}
Workflow: {workflow}
LLM Turns: {workflow_results.get('turns', 'N/A')}

{summary_text}

Results URL: {workflow_results.get('results_url', 'N/A')}
"""

            # ── Emit artifacts ────────────────────────────────────────────────
            await updater.add_artifact(
                parts=[
                    Part(root=TextPart(text=summary_text)),
                    Part(root=DataPart(data={
                        "workflow": workflow,
                        "agents_used": list(workflow_results.keys()) if isinstance(workflow_results, dict) else [],
                        "results": workflow_results,
                    })),
                ],
                name="orchestration_results",
            )
            await updater.complete()

        except Exception as exc:
            await updater.failed(message=str(exc))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError("Cancel is not supported by this agent")


# ─── App ───────────────────────────────────────────────────────────────────────

# Initialize S3 client
try:
    s3_client = SharedS3Client()
    print("✅ S3 client initialized")
except Exception as e:
    print(f"⚠️  S3 client initialization failed: {e}")
    s3_client = None

# Create components
executor = OrchestratorAgentExecutor()
task_store = InMemoryTaskStore()
handler = DefaultRequestHandler(
    agent_executor=executor,
    task_store=task_store
)

# Create app
app = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=handler,
).build()

# ─── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"🚀 Orchestrator Agent  →  http://{HOST}:{PORT}/")
    print(f"📄 Agent Card          →  http://{HOST}:{PORT}/.well-known/agent.json")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        log_level="info",
    )
