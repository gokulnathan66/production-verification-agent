"""
Code Logic Agent - A2A compliant
Performs AST analysis, code complexity metrics, and code quality assessment
"""
from fastapi import FastAPI, Request
from typing import Dict, Any, List
import uuid
from datetime import datetime
import os
import ast
import re

app = FastAPI(title="Code Logic Agent")

# In-memory task storage
TASKS = {}

# Agent configuration
AGENT_ID = os.getenv("AGENT_ID", "code-logic-agent")
PORT = int(os.getenv("PORT", "8001"))
HOST = os.getenv("HOST", "localhost")

# Agent Card
AGENT_CARD = {
    "agentId": AGENT_ID,
    "name": "Code Logic Analysis Agent",
    "description": "Performs AST parsing, complexity analysis, code quality metrics, and structural analysis",
    "version": "1.0.0",
    "endpoints": {
        "rpc": f"http://{HOST}:{PORT}/a2a",
        "health": f"http://{HOST}:{PORT}/health"
    },
    "capabilities": {
        "modalities": ["text", "file"],
        "skills": [
            "code_analysis",
            "ast_parsing",
            "complexity_metrics",
            "code_quality",
            "function_extraction",
            "dependency_analysis"
        ],
        "languages": ["python", "javascript", "java"],
        "fileTypes": [".py", ".js", ".java"]
    },
    "auth": {
        "scheme": "none",
        "required": False
    }
}


class CodeAnalyzer:
    """Simple code analysis using AST"""

    def analyze_python_code(self, code: str) -> Dict[str, Any]:
        """Analyze Python code using AST"""
        try:
            tree = ast.parse(code)

            functions = []
            classes = []
            imports = []

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append({
                        "name": node.name,
                        "line": node.lineno,
                        "args": len(node.args.args),
                        "docstring": ast.get_docstring(node) or "No docstring"
                    })
                elif isinstance(node, ast.ClassDef):
                    classes.append({
                        "name": node.name,
                        "line": node.lineno,
                        "methods": len([n for n in node.body if isinstance(n, ast.FunctionDef)])
                    })
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.append(alias.name)
                    else:
                        imports.append(node.module or "")

            # Calculate metrics
            lines = code.split('\n')
            total_lines = len(lines)
            code_lines = len([l for l in lines if l.strip() and not l.strip().startswith('#')])

            return {
                "language": "python",
                "metrics": {
                    "total_lines": total_lines,
                    "code_lines": code_lines,
                    "functions": len(functions),
                    "classes": len(classes),
                    "imports": len(set(imports))
                },
                "functions": functions,
                "classes": classes,
                "imports": list(set(imports)),
                "complexity": self._calculate_complexity(len(functions), len(classes)),
                "quality_score": self._calculate_quality_score(functions, code_lines)
            }
        except SyntaxError as e:
            return {
                "error": f"Syntax error: {str(e)}",
                "language": "python"
            }

    def analyze_generic_code(self, code: str, language: str) -> Dict[str, Any]:
        """Generic code analysis for non-Python languages"""
        lines = code.split('\n')

        # Simple pattern matching
        functions = len(re.findall(r'function\s+\w+|def\s+\w+|public\s+\w+\s+\w+\(', code))
        classes = len(re.findall(r'class\s+\w+', code))

        return {
            "language": language,
            "metrics": {
                "total_lines": len(lines),
                "code_lines": len([l for l in lines if l.strip()]),
                "functions": functions,
                "classes": classes
            },
            "complexity": "medium" if functions > 10 else "low",
            "note": "Generic analysis - install language-specific parser for detailed analysis"
        }

    def _calculate_complexity(self, functions: int, classes: int) -> str:
        """Calculate code complexity"""
        score = functions + (classes * 2)
        if score < 10:
            return "low"
        elif score < 30:
            return "medium"
        else:
            return "high"

    def _calculate_quality_score(self, functions: List[Dict], code_lines: int) -> float:
        """Calculate quality score 0-100"""
        score = 100.0

        # Deduct for missing docstrings
        functions_without_docs = sum(1 for f in functions if f["docstring"] == "No docstring")
        if functions:
            score -= (functions_without_docs / len(functions)) * 20

        # Deduct for long files
        if code_lines > 500:
            score -= 10

        # Deduct for too many functions (should be modular)
        if len(functions) > 20:
            score -= 15

        return max(0, round(score, 2))


analyzer = CodeAnalyzer()


@app.get("/.well-known/agent-card")
async def get_agent_card():
    """Expose AgentCard at standard A2A location"""
    return AGENT_CARD


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "agentId": AGENT_ID,
        "activeTasks": len([t for t in TASKS.values() if t["status"] == "in_progress"]),
        "capabilities": AGENT_CARD["capabilities"]["skills"]
    }


@app.post("/a2a")
async def a2a_endpoint(request: Request):
    """JSON-RPC 2.0 endpoint for A2A protocol"""
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
            "error": {"code": -32603, "message": f"Internal error: {str(e)}"}
        }


async def create_task(params: Dict[str, Any]) -> Dict[str, Any]:
    """Create code analysis task"""
    task_id = str(uuid.uuid4())
    message = params.get("message", {})
    metadata = params.get("metadata", {})

    # Extract code from message parts
    code_text = ""
    language = "python"  # default

    for part in message.get("parts", []):
        if part.get("kind") == "text":
            code_text += part.get("text", "")
        elif part.get("kind") == "data":
            data = part.get("data", {})
            language = data.get("language", "python")
            code_text = data.get("code", code_text)

    # Analyze code
    if language == "python":
        analysis = analyzer.analyze_python_code(code_text)
    else:
        analysis = analyzer.analyze_generic_code(code_text, language)

    # Format result
    result_text = f"""
🔍 Code Analysis Results

Language: {analysis.get('language', 'unknown')}

📊 Metrics:
"""

    if "metrics" in analysis:
        metrics = analysis["metrics"]
        result_text += f"  • Total Lines: {metrics.get('total_lines', 0)}\n"
        result_text += f"  • Code Lines: {metrics.get('code_lines', 0)}\n"
        result_text += f"  • Functions: {metrics.get('functions', 0)}\n"
        result_text += f"  • Classes: {metrics.get('classes', 0)}\n"

    if "complexity" in analysis:
        result_text += f"\n⚡ Complexity: {analysis['complexity']}\n"

    if "quality_score" in analysis:
        score = analysis['quality_score']
        result_text += f"✨ Quality Score: {score}/100\n"

    if "functions" in analysis and analysis["functions"]:
        result_text += f"\n📦 Functions Found:\n"
        for func in analysis["functions"][:5]:  # Show first 5
            result_text += f"  • {func['name']} (line {func['line']}, {func['args']} args)\n"

    if "error" in analysis:
        result_text = f"❌ Error: {analysis['error']}"

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
                    {"kind": "text", "text": result_text},
                    {"kind": "data", "data": analysis}
                ]
            }
        ],
        "artifacts": [],
        "metadata": {
            **metadata,
            "agentId": AGENT_ID,
            "analysisType": "code_logic"
        }
    }

    TASKS[task_id] = task
    return task


async def get_task(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get task by ID"""
    task_id = params.get("taskId")
    if not task_id or task_id not in TASKS:
        raise ValueError(f"Task not found: {task_id}")
    return TASKS[task_id]


async def list_tasks(params: Dict[str, Any]) -> Dict[str, Any]:
    """List all tasks"""
    status_filter = params.get("status")
    limit = params.get("limit", 100)

    tasks = list(TASKS.values())
    if status_filter:
        tasks = [t for t in tasks if t["status"] == status_filter]

    return {"tasks": tasks[:limit], "total": len(tasks)}


if __name__ == "__main__":
    import uvicorn
    print(f"🚀 Starting Code Logic Agent: {AGENT_ID}")
    print(f"📍 AgentCard: http://{HOST}:{PORT}/.well-known/agent-card")
    print(f"🔗 RPC: http://{HOST}:{PORT}/a2a")
    print(f"💚 Health: http://{HOST}:{PORT}/health")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
