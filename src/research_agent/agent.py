"""
Research Agent - Official A2A SDK compliant
Real grep-based code search with AST parsing and file system support
"""

import ast
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

import uvicorn
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps import A2AStarletteApplication
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    Part,
    Task,
    TaskState,
    TextPart,
    DataPart,
)

# ─── Config ────────────────────────────────────────────────────────────────────

AGENT_ID = os.getenv("AGENT_ID", "research-agent")
PORT = int(os.getenv("PORT", "8003"))
HOST = os.getenv("HOST", "localhost")

# ─── Agent Card ────────────────────────────────────────────────────────────────

agent_card = AgentCard(
    name="Research Agent",
    description="Real grep-based code search with AST parsing and file system support",
    url=f"http://{HOST}:{PORT}/",
    version="2.0.0",
    defaultInputModes=["text"],
    defaultOutputModes=["text", "data"],
    capabilities=AgentCapabilities(streaming=False),
    skills=[
        AgentSkill(
            id="grep_search",
            name="Grep Search",
            description="Search for patterns in code using ripgrep/grep",
            tags=["search", "grep", "pattern"],
            examples=["search for: def authenticate"],
        ),
        AgentSkill(
            id="ast_function_discovery",
            name="AST Function Discovery",
            description="Find all functions, classes, imports using AST parsing",
            tags=["ast", "python", "functions", "classes"],
            examples=["analyze functions in this Python file"],
        ),
        AgentSkill(
            id="dependency_mapping",
            name="Dependency Mapping",
            description="Extract all imports and dependencies from source code",
            tags=["imports", "dependencies"],
            examples=["what are the imports in this code?"],
        ),
    ],
)

# ─── CodeResearcher ────────────────────────────────────────────────────────────

class CodeResearcher:
    """Real grep-based research with AST support"""

    def grep_search(
        self,
        pattern: str,
        text: str = None,
        directory: str = None,
        context_lines: int = 2,
    ) -> List[Dict[str, Any]]:
        if text:
            return self._search_in_text(pattern, text, context_lines)
        if directory and os.path.isdir(directory):
            return self._search_in_directory(pattern, directory, context_lines)
        return []

    def _search_in_text(self, pattern: str, text: str, context: int) -> List[Dict[str, Any]]:
        results = []
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if re.search(pattern, line, re.IGNORECASE):
                start = max(0, i - context)
                end = min(len(lines), i + context + 1)
                results.append({
                    "line": i + 1,
                    "content": line.strip(),
                    "context_before": lines[start:i],
                    "context_after": lines[i + 1 : end],
                    "match": pattern,
                })
        return results

    def _search_in_directory(self, pattern: str, directory: str, context: int) -> List[Dict[str, Any]]:
        try:
            result = subprocess.run(
                ["rg", pattern, directory, "--context", str(context),
                 "--line-number", "--no-heading", "--color", "never"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                return self._parse_grep_output(result.stdout)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        try:
            result = subprocess.run(
                ["grep", "-r", "-n", "-C", str(context), pattern, directory],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode in [0, 1]:
                return self._parse_grep_output(result.stdout)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return []

    def _parse_grep_output(self, output: str) -> List[Dict[str, Any]]:
        results = []
        for line in output.split("\n"):
            if not line.strip() or line.startswith("--"):
                continue
            parts = line.split(":", 2)
            if len(parts) >= 3:
                results.append({
                    "file": parts[0],
                    "line": parts[1],
                    "content": parts[2].strip(),
                })
        return results

    def find_functions(self, code: str, language: str = "python") -> List[Dict[str, Any]]:
        if language != "python":
            return self._find_functions_regex(code, language)
        try:
            tree = ast.parse(code)
            functions = []
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append({
                        "name": node.name,
                        "line": node.lineno,
                        "end_line": node.end_lineno,
                        "args": [arg.arg for arg in node.args.args],
                        "decorators": [ast.unparse(d) for d in node.decorator_list],
                        "docstring": ast.get_docstring(node),
                        "complexity": self._estimate_complexity(node),
                    })
            return functions
        except SyntaxError:
            return self._find_functions_regex(code, language)

    def _find_functions_regex(self, code: str, language: str) -> List[Dict[str, Any]]:
        patterns = {
            "javascript": r"(?:async\s+)?(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>)",
            "java": r"(?:public|private|protected)\s+(?:static\s+)?[\w<>]+\s+(\w+)\s*\(",
            "go": r"func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(",
            "rust": r"(?:pub\s+)?(?:async\s+)?fn\s+(\w+)\s*[<(]",
        }
        pattern = patterns.get(language, r"def\s+(\w+)\s*\(")
        results = []
        for i, line in enumerate(code.split("\n"), 1):
            match = re.search(pattern, line)
            if match:
                func_name = next((g for g in match.groups() if g), None)
                if func_name:
                    results.append({"name": func_name, "line": i, "signature": line.strip()})
        return results

    def _estimate_complexity(self, node: ast.FunctionDef) -> int:
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity

    def find_classes(self, code: str, language: str = "python") -> List[Dict[str, Any]]:
        patterns = {
            "python": r"class\s+(\w+)",
            "javascript": r"class\s+(\w+)",
            "java": r"class\s+(\w+)",
            "go": r"type\s+(\w+)\s+struct",
            "rust": r"struct\s+(\w+)",
        }
        pattern = patterns.get(language, patterns["python"])
        results = []
        for i, line in enumerate(code.split("\n"), 1):
            match = re.search(pattern, line)
            if match:
                results.append({"name": match.group(1), "line": i, "definition": line.strip()})
        return results

    def find_imports(self, code: str, language: str = "python") -> List[str]:
        if language == "python":
            try:
                tree = ast.parse(code)
                imports = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.add(alias.name)
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        imports.add(node.module)
                return sorted(imports)
            except Exception:
                pass

        patterns = {
            "python": r"(?:from\s+([\w.]+)\s+)?import\s+([\w., ]+)",
            "javascript": r"import\s+.*from\s+['\"](.+)['\"]",
            "java": r"import\s+([\w.]+)",
            "go": r'import\s+["\'](.+)["\']',
        }
        pattern = patterns.get(language, patterns["python"])
        imports: set = set()
        for match in re.finditer(pattern, code):
            imports.update(g for g in match.groups() if g)
        return sorted(imports)


# ─── Agent Executor ────────────────────────────────────────────────────────────

researcher = CodeResearcher()


class ResearchAgentExecutor(AgentExecutor):
    """
    Core A2A executor — handles all incoming tasks routed by DefaultRequestHandler.
    Extracts text/data parts from the A2A message and runs the appropriate research.
    """

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        await updater.submit()
        await updater.start_work()

        try:
            # ── Parse incoming message parts ──────────────────────────────────
            code_text = ""
            query = ""
            language = "python"
            research_type = "functions"
            directory = None

            for part in context.message.parts:
                if isinstance(part.root, TextPart):
                    text = part.root.text
                    code_text = code_text or text
                    query = text
                elif isinstance(part.root, DataPart):
                    data: dict = part.root.data or {}
                    language = data.get("language", "python")
                    code_text = data.get("code", code_text)
                    research_type = data.get("type", "functions")
                    directory = data.get("directory")

            # ── Run research ──────────────────────────────────────────────────
            if research_type in ("grep", "pattern"):
                pattern = (
                    query.split("search for:")[-1].strip()
                    if "search for:" in query
                    else query
                )
                matches = researcher.grep_search(pattern, code_text, directory)

                result_text = (
                    f"🔍 Grep Search: '{pattern}'\n"
                    f"Matches: {len(matches)}\n\n"
                )
                for m in matches[:20]:
                    result_text += f"Line {m.get('line', '?')}: {m.get('content', '')}\n"

                data_result = {"pattern": pattern, "matches": matches}

            elif research_type == "functions":
                functions = researcher.find_functions(code_text, language)
                classes = researcher.find_classes(code_text, language)
                imports = researcher.find_imports(code_text, language)

                result_text = (
                    f"🔍 Research Results\n\n"
                    f"📦 Functions : {len(functions)}\n"
                    f"🏛️  Classes   : {len(classes)}\n"
                    f"📚 Imports   : {len(imports)}\n\n"
                    f"Functions Found:\n"
                )
                for func in functions[:10]:
                    result_text += f"  • {func['name']} (line {func['line']}"
                    if "complexity" in func:
                        result_text += f", complexity: {func['complexity']}"
                    result_text += ")\n"
                    if func.get("docstring"):
                        result_text += f"    {func['docstring'][:60]}...\n"

                data_result = {
                    "functions": functions,
                    "classes": classes,
                    "imports": imports,
                    "language": language,
                }

            else:
                result_text = f"❌ Unknown research type: {research_type}"
                data_result = {"error": "Unknown type"}

            # ── Emit result parts back to the client ──────────────────────────
            await updater.add_artifact(
                parts=[
                    Part(root=TextPart(text=result_text)),
                    Part(root=DataPart(data=data_result)),
                ],
                name="research_results",
            )
            await updater.complete()

        except Exception as exc:
            await updater.failed(message=str(exc))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError("Cancel is not supported by this agent")


# ─── App Bootstrap ─────────────────────────────────────────────────────────────

def build_app():
    executor = ResearchAgentExecutor()
    handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
    )
    return A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=handler,
    ).build()


app = build_app()

if __name__ == "__main__":
    print(f"🚀 Research Agent  →  http://{HOST}:{PORT}/")
    print(f"📄 Agent Card      →  http://{HOST}:{PORT}/.well-known/agent.json")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
