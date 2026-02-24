"""
Research Agent - A2A compliant
Performs grep-based code search, pattern matching, and research documentation generation
"""
from fastapi import FastAPI, Request
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime
import os
import re
import subprocess
from pathlib import Path

app = FastAPI(title="Research Agent")

TASKS = {}

AGENT_ID = os.getenv("AGENT_ID", "research-agent")
PORT = int(os.getenv("PORT", "8003"))
HOST = os.getenv("HOST", "localhost")

AGENT_CARD = {
    "agentId": AGENT_ID,
    "name": "Research Agent",
    "description": "Performs grep-based code search, pattern matching, and generates RESEARCH.md documentation",
    "version": "1.0.0",
    "endpoints": {
        "rpc": f"http://{HOST}:{PORT}/a2a",
        "health": f"http://{HOST}:{PORT}/health"
    },
    "capabilities": {
        "modalities": ["text", "file"],
        "skills": [
            "code_search",
            "pattern_matching",
            "grep_search",
            "function_discovery",
            "research_generation",
            "dependency_mapping"
        ],
        "languages": ["python", "javascript", "java", "go", "rust"],
        "fileTypes": ["*"]
    },
    "auth": {"scheme": "none", "required": False}
}


class CodeResearcher:
    """Grep-based code research"""

    def search_pattern(self, pattern: str, text: str) -> List[Dict[str, Any]]:
        """Search for pattern in text"""
        results = []
        lines = text.split('\n')

        for i, line in enumerate(lines, 1):
            if re.search(pattern, line, re.IGNORECASE):
                results.append({
                    "line": i,
                    "content": line.strip(),
                    "match": pattern
                })

        return results

    def find_functions(self, code: str, language: str = "python") -> List[Dict[str, Any]]:
        """Find function definitions"""
        patterns = {
            "python": r'def\s+(\w+)\s*\(',
            "javascript": r'function\s+(\w+)\s*\(|const\s+(\w+)\s*=\s*\(',
            "java": r'(public|private|protected)\s+\w+\s+(\w+)\s*\(',
            "go": r'func\s+(\w+)\s*\(',
            "rust": r'fn\s+(\w+)\s*\('
        }

        pattern = patterns.get(language, patterns["python"])
        results = []
        lines = code.split('\n')

        for i, line in enumerate(lines, 1):
            match = re.search(pattern, line)
            if match:
                func_name = match.group(1) or match.group(2) if match.lastindex >= 2 else match.group(1)
                results.append({
                    "name": func_name,
                    "line": i,
                    "signature": line.strip()
                })

        return results

    def find_classes(self, code: str, language: str = "python") -> List[Dict[str, Any]]:
        """Find class definitions"""
        patterns = {
            "python": r'class\s+(\w+)',
            "javascript": r'class\s+(\w+)',
            "java": r'class\s+(\w+)',
            "go": r'type\s+(\w+)\s+struct',
            "rust": r'struct\s+(\w+)'
        }

        pattern = patterns.get(language, patterns["python"])
        results = []
        lines = code.split('\n')

        for i, line in enumerate(lines, 1):
            match = re.search(pattern, line)
            if match:
                results.append({
                    "name": match.group(1),
                    "line": i,
                    "definition": line.strip()
                })

        return results

    def find_imports(self, code: str, language: str = "python") -> List[str]:
        """Find import statements"""
        patterns = {
            "python": r'(?:from\s+[\w.]+\s+)?import\s+([\w., ]+)',
            "javascript": r'import\s+.*from\s+[\'"](.+)[\'"]',
            "java": r'import\s+([\w.]+)',
            "go": r'import\s+[\'"](.+)[\'"]',
            "rust": r'use\s+([\w:]+)'
        }

        pattern = patterns.get(language, patterns["python"])
        imports = set()

        for match in re.finditer(pattern, code):
            imports.add(match.group(1))

        return sorted(list(imports))

    def generate_research_doc(
        self,
        code: str,
        language: str,
        query: str
    ) -> str:
        """Generate RESEARCH.md style documentation"""

        functions = self.find_functions(code, language)
        classes = self.find_classes(code, language)
        imports = self.find_imports(code, language)

        doc = f"""# Code Research Report

## Query
{query}

## Overview
- Language: {language}
- Functions: {len(functions)}
- Classes: {len(classes)}
- Imports: {len(imports)}

## Functions Discovered

"""
        for func in functions[:10]:  # First 10
            doc += f"### {func['name']}\n"
            doc += f"- **Line**: {func['line']}\n"
            doc += f"- **Signature**: `{func['signature']}`\n\n"

        if classes:
            doc += "\n## Classes Discovered\n\n"
            for cls in classes:
                doc += f"### {cls['name']}\n"
                doc += f"- **Line**: {cls['line']}\n"
                doc += f"- **Definition**: `{cls['definition']}`\n\n"

        if imports:
            doc += "\n## Dependencies\n\n"
            for imp in imports:
                doc += f"- {imp}\n"

        doc += "\n## Recommendations\n\n"
        if len(functions) > 20:
            doc += "- ⚠️ High function count - consider splitting into modules\n"
        if len(classes) > 10:
            doc += "- ⚠️ Many classes - ensure good organization\n"
        if not imports:
            doc += "- ℹ️ No external dependencies found\n"

        return doc


researcher = CodeResearcher()


@app.get("/.well-known/agent-card")
async def get_agent_card():
    return AGENT_CARD


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "agentId": AGENT_ID,
        "capabilities": AGENT_CARD["capabilities"]["skills"]
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
    """Create research task"""
    task_id = str(uuid.uuid4())
    message = params.get("message", {})
    metadata = params.get("metadata", {})

    # Extract code and query
    code_text = ""
    query = ""
    language = "python"
    research_type = "functions"  # or "pattern", "full"

    for part in message.get("parts", []):
        if part.get("kind") == "text":
            text = part.get("text", "")
            if not code_text:
                code_text = text
            query = text
        elif part.get("kind") == "data":
            data = part.get("data", {})
            language = data.get("language", "python")
            code_text = data.get("code", code_text)
            research_type = data.get("type", "functions")

    # Perform research
    if research_type == "functions":
        functions = researcher.find_functions(code_text, language)
        classes = researcher.find_classes(code_text, language)
        imports = researcher.find_imports(code_text, language)

        result_text = f"""
🔍 Research Results

📦 Functions: {len(functions)}
🏛️ Classes: {len(classes)}
📚 Imports: {len(imports)}

Functions Found:
"""
        for func in functions[:10]:
            result_text += f"  • {func['name']} (line {func['line']})\n"

        data_result = {
            "functions": functions,
            "classes": classes,
            "imports": imports,
            "language": language
        }

    elif research_type == "pattern":
        pattern = query.split("search for:")[-1].strip() if "search for:" in query else query
        matches = researcher.search_pattern(pattern, code_text)

        result_text = f"""
🔍 Pattern Search Results

Pattern: {pattern}
Matches: {len(matches)}

Results:
"""
        for match in matches[:20]:
            result_text += f"  Line {match['line']}: {match['content']}\n"

        data_result = {"pattern": pattern, "matches": matches}

    else:  # full research
        research_doc = researcher.generate_research_doc(code_text, language, query)
        result_text = f"📄 RESEARCH.md generated\n\n{research_doc}"
        data_result = {"research_document": research_doc, "language": language}

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
                    {"kind": "data", "data": data_result}
                ]
            }
        ],
        "artifacts": [],
        "metadata": {**metadata, "agentId": AGENT_ID, "researchType": research_type}
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
    print(f"🚀 Starting Research Agent: {AGENT_ID}")
    print(f"📍 AgentCard: http://{HOST}:{PORT}/.well-known/agent-card")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
