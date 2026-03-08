"""
Code Logic Agent - Official A2A SDK compliant
Performs AST analysis, code complexity metrics, and code quality assessment
"""

import ast
import os
import re
from typing import Any, Dict, List

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
    DataPart,
    Part,
    TextPart,
)

# ─── Config ────────────────────────────────────────────────────────────────────

AGENT_ID = os.getenv("AGENT_ID", "code-logic-agent")
PORT     = int(os.getenv("PORT", "8001"))
HOST     = os.getenv("HOST", "localhost")

# ─── Agent Card ────────────────────────────────────────────────────────────────

agent_card = AgentCard(
    name="Code Logic Analysis Agent",
    description="Performs AST parsing, complexity analysis, code quality metrics, and structural analysis",
    url=f"http://{HOST}:{PORT}/",
    version="1.0.0",
    defaultInputModes=["text"],
    defaultOutputModes=["text", "data"],
    capabilities=AgentCapabilities(streaming=False),
    skills=[
        AgentSkill(
            id="code_analysis",
            name="Code Analysis",
            description="Full structural analysis of source code",
            tags=["analysis", "ast", "metrics"],
            examples=["Analyze this Python file for quality issues"],
        ),
        AgentSkill(
            id="ast_parsing",
            name="AST Parsing",
            description="Parse Python source into AST and extract structure",
            tags=["ast", "python"],
            examples=["Extract all function definitions from this code"],
        ),
        AgentSkill(
            id="complexity_metrics",
            name="Complexity Metrics",
            description="Cyclomatic complexity and structural complexity scoring",
            tags=["complexity", "metrics"],
            examples=["What is the complexity of this module?"],
        ),
        AgentSkill(
            id="code_quality",
            name="Code Quality",
            description="Quality score based on docstrings, size, and modularity",
            tags=["quality", "docstrings"],
            examples=["Rate the quality of this code"],
        ),
        AgentSkill(
            id="function_extraction",
            name="Function Extraction",
            description="List all functions with signatures and docstrings",
            tags=["functions", "signatures"],
            examples=["List all functions in this file"],
        ),
        AgentSkill(
            id="dependency_analysis",
            name="Dependency Analysis",
            description="Extract all imports and third-party dependencies",
            tags=["imports", "dependencies"],
            examples=["What dependencies does this code use?"],
        ),
    ],
)

# ─── CodeAnalyzer ──────────────────────────────────────────────────────────────

class CodeAnalyzer:
    """AST-based code analyzer with quality and complexity metrics"""

    def analyze_python_code(self, code: str) -> Dict[str, Any]:
        """Full Python analysis via AST"""
        try:
            tree = ast.parse(code)

            functions: List[Dict] = []
            classes: List[Dict] = []
            imports: List[str] = []

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append({
                        "name": node.name,
                        "line": node.lineno,
                        "args": len(node.args.args),
                        "docstring": ast.get_docstring(node) or "No docstring",
                    })
                elif isinstance(node, ast.ClassDef):
                    classes.append({
                        "name": node.name,
                        "line": node.lineno,
                        "methods": len([
                            n for n in node.body
                            if isinstance(n, ast.FunctionDef)
                        ]),
                    })
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.append(node.module)

            lines = code.split("\n")
            total_lines = len(lines)
            code_lines = len([
                l for l in lines
                if l.strip() and not l.strip().startswith("#")
            ])

            return {
                "language": "python",
                "metrics": {
                    "total_lines": total_lines,
                    "code_lines": code_lines,
                    "functions": len(functions),
                    "classes": len(classes),
                    "imports": len(set(imports)),
                },
                "functions": functions,
                "classes": classes,
                "imports": sorted(set(imports)),
                "complexity": self._calculate_complexity(len(functions), len(classes)),
                "quality_score": self._calculate_quality_score(functions, code_lines),
            }

        except SyntaxError as e:
            return {"error": f"Syntax error: {e}", "language": "python"}

    def analyze_generic_code(self, code: str, language: str) -> Dict[str, Any]:
        """Regex-based fallback for non-Python languages"""
        lines = code.split("\n")
        functions = len(re.findall(
            r"function\s+\w+|def\s+\w+|public\s+\w+\s+\w+\(", code
        ))
        classes = len(re.findall(r"class\s+\w+", code))
        return {
            "language": language,
            "metrics": {
                "total_lines": len(lines),
                "code_lines": len([l for l in lines if l.strip()]),
                "functions": functions,
                "classes": classes,
            },
            "complexity": "medium" if functions > 10 else "low",
            "note": "Generic analysis — install a language-specific parser for detailed results",
        }

    def _calculate_complexity(self, functions: int, classes: int) -> str:
        score = functions + (classes * 2)
        if score < 10:
            return "low"
        elif score < 30:
            return "medium"
        return "high"

    def _calculate_quality_score(self, functions: List[Dict], code_lines: int) -> float:
        score = 100.0
        if functions:
            missing_docs = sum(1 for f in functions if f["docstring"] == "No docstring")
            score -= (missing_docs / len(functions)) * 20
        if code_lines > 500:
            score -= 10
        if len(functions) > 20:
            score -= 15
        return max(0.0, round(score, 2))


# ─── Agent Executor ────────────────────────────────────────────────────────────

analyzer = CodeAnalyzer()


class CodeLogicAgentExecutor(AgentExecutor):
    """
    A2A executor — parses message parts, runs code analysis,
    emits text + data artifacts back to the caller.
    """

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        await updater.submit()
        await updater.start_work()

        try:
            # ── Parse incoming parts ──────────────────────────────────────────
            code_text = ""
            language  = "python"

            for part in context.message.parts:
                if isinstance(part.root, TextPart):
                    code_text += part.root.text
                elif isinstance(part.root, DataPart):
                    data: dict = part.root.data or {}
                    language  = data.get("language", "python")
                    code_text = data.get("code", code_text)

            # ── Run analysis ──────────────────────────────────────────────────
            analysis = (
                analyzer.analyze_python_code(code_text)
                if language == "python"
                else analyzer.analyze_generic_code(code_text, language)
            )

            # ── Format human-readable result ──────────────────────────────────
            if "error" in analysis:
                result_text = f"❌ Error: {analysis['error']}"
            else:
                metrics = analysis.get("metrics", {})
                result_text = (
                    f"🔍 Code Analysis Results\n\n"
                    f"Language: {analysis.get('language', 'unknown')}\n\n"
                    f"📊 Metrics:\n"
                    f"  • Total Lines  : {metrics.get('total_lines', 0)}\n"
                    f"  • Code Lines   : {metrics.get('code_lines', 0)}\n"
                    f"  • Functions    : {metrics.get('functions', 0)}\n"
                    f"  • Classes      : {metrics.get('classes', 0)}\n"
                    f"  • Imports      : {metrics.get('imports', 0)}\n"
                )

                if "complexity" in analysis:
                    result_text += f"\n⚡ Complexity   : {analysis['complexity']}\n"

                if "quality_score" in analysis:
                    result_text += f"✨ Quality Score: {analysis['quality_score']}/100\n"

                funcs = analysis.get("functions", [])
                if funcs:
                    result_text += "\n📦 Functions Found:\n"
                    for func in funcs[:5]:
                        result_text += (
                            f"  • {func['name']} "
                            f"(line {func['line']}, {func['args']} args)\n"
                        )

                if "note" in analysis:
                    result_text += f"\n📝 Note: {analysis['note']}\n"

            # ── Emit artifact ─────────────────────────────────────────────────
            await updater.add_artifact(
                parts=[
                    Part(root=TextPart(text=result_text)),
                    Part(root=DataPart(data=analysis)),
                ],
                name="code_analysis_results",
            )
            await updater.complete()

        except Exception as exc:
            await updater.failed(message=str(exc))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError("Cancel is not supported by this agent")


# ─── App Bootstrap ─────────────────────────────────────────────────────────────

def build_app():
    handler = DefaultRequestHandler(
        agent_executor=CodeLogicAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )
    return A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=handler,
    ).build()


app = build_app()

if __name__ == "__main__":
    print(f"🚀 Code Logic Agent  →  http://{HOST}:{PORT}/")
    print(f"📄 Agent Card        →  http://{HOST}:{PORT}/.well-known/agent.json")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
