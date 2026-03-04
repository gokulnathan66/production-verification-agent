"""
Improved Research Agent - A2A compliant
Real grep-based search, AST-aware function discovery, file system support
"""
from fastapi import FastAPI, Request
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime
import os
import re
import subprocess
import ast
from pathlib import Path

app = FastAPI(title="Research Agent")

TASKS = {}

AGENT_ID = os.getenv("AGENT_ID", "research-agent")
PORT = int(os.getenv("PORT", "8003"))
HOST = os.getenv("HOST", "localhost")

AGENT_CARD = {
    "agentId": AGENT_ID,
    "name": "Research Agent",
    "description": "Real grep-based code search with AST parsing and file system support",
    "version": "2.0.0",
    "endpoints": {
        "rpc": f"http://{HOST}:{PORT}/a2a",
        "health": f"http://{HOST}:{PORT}/health"
    },
    "capabilities": {
        "modalities": ["text", "file"],
        "skills": [
            "grep_search",
            "ast_function_discovery",
            "pattern_matching",
            "file_search",
            "context_extraction",
            "dependency_mapping"
        ],
        "languages": ["python", "javascript", "java", "go", "rust"],
        "fileTypes": ["*"]
    },
    "auth": {"scheme": "none", "required": False}
}


class ImprovedResearcher:
    """Real grep-based research with AST support"""

    def grep_search(
        self,
        pattern: str,
        text: str = None,
        directory: str = None,
        file_pattern: str = "*.py",
        context_lines: int = 2
    ) -> List[Dict[str, Any]]:
        """Real grep search using ripgrep or grep"""
        
        # If text provided, search in text
        if text:
            return self._search_in_text(pattern, text, context_lines)
        
        # If directory provided, use actual grep
        if directory and os.path.isdir(directory):
            return self._search_in_directory(pattern, directory, file_pattern, context_lines)
        
        return []

    def _search_in_text(self, pattern: str, text: str, context: int) -> List[Dict[str, Any]]:
        """Search pattern in text with context"""
        results = []
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            if re.search(pattern, line, re.IGNORECASE):
                # Get context
                start = max(0, i - context)
                end = min(len(lines), i + context + 1)
                
                results.append({
                    "line": i + 1,
                    "content": line.strip(),
                    "context_before": lines[start:i],
                    "context_after": lines[i+1:end],
                    "match": pattern
                })
        
        return results

    def _search_in_directory(
        self,
        pattern: str,
        directory: str,
        file_pattern: str,
        context: int
    ) -> List[Dict[str, Any]]:
        """Use ripgrep or grep for directory search"""
        results = []
        
        # Try ripgrep first (faster)
        try:
            cmd = [
                'rg',
                pattern,
                directory,
                '--glob', file_pattern,
                '--context', str(context),
                '--line-number',
                '--no-heading',
                '--color', 'never'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return self._parse_grep_output(result.stdout)
                
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        # Fallback to grep
        try:
            cmd = [
                'grep',
                '-r',
                '-n',
                '-C', str(context),
                pattern,
                directory,
                '--include', file_pattern
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode in [0, 1]:  # 0=found, 1=not found
                return self._parse_grep_output(result.stdout)
                
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        return results

    def _parse_grep_output(self, output: str) -> List[Dict[str, Any]]:
        """Parse grep/ripgrep output"""
        results = []
        lines = output.split('\n')
        
        for line in lines:
            if not line.strip() or line.startswith('--'):
                continue
            
            # Parse format: file:line:content
            parts = line.split(':', 2)
            if len(parts) >= 3:
                results.append({
                    "file": parts[0],
                    "line": parts[1],
                    "content": parts[2].strip()
                })
        
        return results

    def find_functions_ast(self, code: str, language: str = "python") -> List[Dict[str, Any]]:
        """Use AST for accurate function discovery (Python only)"""
        
        if language != "python":
            return self._find_functions_regex(code, language)
        
        try:
            tree = ast.parse(code)
            functions = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Extract full signature
                    args = []
                    for arg in node.args.args:
                        args.append(arg.arg)
                    
                    # Get decorators
                    decorators = [ast.unparse(d) for d in node.decorator_list]
                    
                    # Check if async
                    is_async = isinstance(node, ast.AsyncFunctionDef)
                    
                    # Get return type hint
                    return_type = ast.unparse(node.returns) if node.returns else None
                    
                    functions.append({
                        "name": node.name,
                        "line": node.lineno,
                        "end_line": node.end_lineno,
                        "args": args,
                        "decorators": decorators,
                        "is_async": is_async,
                        "return_type": return_type,
                        "docstring": ast.get_docstring(node),
                        "complexity": self._estimate_complexity(node)
                    })
            
            return functions
            
        except SyntaxError:
            # Fallback to regex
            return self._find_functions_regex(code, language)

    def _find_functions_regex(self, code: str, language: str) -> List[Dict[str, Any]]:
        """Regex-based function finding for non-Python"""
        patterns = {
            "javascript": r'(?:async\s+)?(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>)',
            "java": r'(?:public|private|protected)\s+(?:static\s+)?[\w<>]+\s+(\w+)\s*\(',
            "go": r'func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(',
            "rust": r'(?:pub\s+)?(?:async\s+)?fn\s+(\w+)\s*[<(]'
        }
        
        pattern = patterns.get(language, r'def\s+(\w+)\s*\(')
        results = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            match = re.search(pattern, line)
            if match:
                func_name = next((g for g in match.groups() if g), None)
                if func_name:
                    results.append({
                        "name": func_name,
                        "line": i,
                        "signature": line.strip()
                    })
        
        return results

    def _estimate_complexity(self, node: ast.FunctionDef) -> int:
        """Estimate cyclomatic complexity"""
        complexity = 1
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        
        return complexity

    def find_call_sites(self, code: str, function_name: str, language: str = "python") -> List[Dict[str, Any]]:
        """Find where a function is called"""
        
        if language == "python":
            try:
                tree = ast.parse(code)
                calls = []
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Name) and node.func.id == function_name:
                            calls.append({
                                "line": node.lineno,
                                "type": "direct_call"
                            })
                        elif isinstance(node.func, ast.Attribute) and node.func.attr == function_name:
                            calls.append({
                                "line": node.lineno,
                                "type": "method_call"
                            })
                
                return calls
            except:
                pass
        
        # Fallback: regex search
        pattern = rf'\b{function_name}\s*\('
        return self._search_in_text(pattern, code, 0)

    def extract_imports(self, code: str, language: str = "python") -> Dict[str, List[str]]:
        """Extract imports with categorization"""
        
        if language == "python":
            try:
                tree = ast.parse(code)
                imports = {
                    "stdlib": [],
                    "third_party": [],
                    "local": []
                }
                
                stdlib_modules = {'os', 'sys', 're', 'json', 'datetime', 'pathlib', 'typing', 'collections'}
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            module = alias.name.split('.')[0]
                            if module in stdlib_modules:
                                imports["stdlib"].append(alias.name)
                            else:
                                imports["third_party"].append(alias.name)
                    
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            module = node.module.split('.')[0]
                            if module in stdlib_modules:
                                imports["stdlib"].append(node.module)
                            elif node.level > 0:  # relative import
                                imports["local"].append(node.module or ".")
                            else:
                                imports["third_party"].append(node.module)
                
                return imports
            except:
                pass
        
        # Fallback
        return {"all": self._extract_imports_regex(code, language)}

    def _extract_imports_regex(self, code: str, language: str) -> List[str]:
        """Regex-based import extraction"""
        patterns = {
            "python": r'(?:from\s+([\w.]+)\s+)?import\s+([\w., ]+)',
            "javascript": r'import\s+.*from\s+[\'"](.+)[\'"]',
            "java": r'import\s+([\w.]+)',
            "go": r'import\s+[\'"](.+)[\'"]'
        }
        
        pattern = patterns.get(language, patterns["python"])
        imports = set()
        
        for match in re.finditer(pattern, code):
            imports.update(g for g in match.groups() if g)
        
        return sorted(list(imports))


researcher = ImprovedResearcher()


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

    code_text = ""
    query = ""
    language = "python"
    research_type = "functions"
    directory = None

    for part in message.get("parts", []):
        if part.get("kind") == "text":
            text = part.get("text", "")
            code_text = code_text or text
            query = text
        elif part.get("kind") == "data":
            data = part.get("data", {})
            language = data.get("language", "python")
            code_text = data.get("code", code_text)
            research_type = data.get("type", "functions")
            directory = data.get("directory")

    # Perform research based on type
    if research_type == "grep":
        pattern = query.split("search for:")[-1].strip() if "search for:" in query else query
        matches = researcher.grep_search(pattern, code_text, directory)
        
        result_text = f"🔍 Grep Search: '{pattern}'\nMatches: {len(matches)}\n\n"
        for match in matches[:20]:
            result_text += f"Line {match.get('line', '?')}: {match.get('content', '')}\n"
        
        data_result = {"pattern": pattern, "matches": matches}

    elif research_type == "functions":
        functions = researcher.find_functions_ast(code_text, language)
        
        result_text = f"📦 Functions Found: {len(functions)}\n\n"
        for func in functions[:15]:
            result_text += f"• {func['name']} (line {func['line']}"
            if 'complexity' in func:
                result_text += f", complexity: {func['complexity']}"
            result_text += ")\n"
            if func.get('docstring'):
                result_text += f"  {func['docstring'][:60]}...\n"
        
        data_result = {"functions": functions, "language": language}

    elif research_type == "calls":
        func_name = query.split("calls to")[-1].strip() if "calls to" in query else query
        calls = researcher.find_call_sites(code_text, func_name, language)
        
        result_text = f"📞 Calls to '{func_name}': {len(calls)}\n\n"
        for call in calls:
            result_text += f"Line {call['line']}: {call.get('type', 'call')}\n"
        
        data_result = {"function": func_name, "calls": calls}

    elif research_type == "imports":
        imports = researcher.extract_imports(code_text, language)
        
        result_text = "📚 Imports:\n\n"
        for category, modules in imports.items():
            if modules:
                result_text += f"{category.title()}: {len(modules)}\n"
                for mod in modules[:10]:
                    result_text += f"  • {mod}\n"
        
        data_result = {"imports": imports, "language": language}

    else:
        result_text = f"❌ Unknown research type: {research_type}"
        data_result = {"error": "Unknown type"}

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
    print(f"🚀 Starting Improved Research Agent: {AGENT_ID}")
    print(f"📍 AgentCard: http://{HOST}:{PORT}/.well-known/agent-card")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
