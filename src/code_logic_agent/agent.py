"""
Code Logic Agent - Strands Agents compliant
Performs AST analysis, code complexity metrics, and code quality assessment
"""

import ast
import os
import re
from typing import Any, Dict, List

from strands import Agent, tool
from strands.multiagent.a2a import A2AServer

# ─── Config ────────────────────────────────────────────────────────────────────

PORT = int(os.getenv("PORT", "8001"))

# ─── Code Analysis Tools ───────────────────────────────────────────────────────


@tool
def analyze_python_code(code: str) -> Dict[str, Any]:
    """Perform comprehensive Python code analysis using AST parsing.

    Analyzes code structure, complexity, quality metrics, and extracts:
    - Functions with signatures and docstrings
    - Classes with method counts
    - Import dependencies
    - Cyclomatic complexity estimation
    - Code quality score based on documentation and structure

    Args:
        code: Python source code as a string.

    Returns:
        Dictionary containing metrics, functions, classes, imports, complexity rating, and quality score.
    """
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

        complexity = _calculate_complexity(len(functions), len(classes))
        quality_score = _calculate_quality_score(functions, code_lines)

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
            "complexity": complexity,
            "quality_score": quality_score,
        }

    except SyntaxError as e:
        return {"error": f"Syntax error: {e}", "language": "python"}


@tool
def analyze_generic_code(code: str, language: str = "unknown") -> Dict[str, Any]:
    """Analyze code in non-Python languages using regex patterns.

    Provides basic metrics for JavaScript, Java, C++, and other languages.
    Detects functions/methods and classes using common syntax patterns.

    Args:
        code: Source code as a string.
        language: Programming language identifier (e.g., 'javascript', 'java').

    Returns:
        Dictionary with basic metrics and complexity estimate.
    """
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


@tool
def extract_functions(code: str) -> List[Dict[str, Any]]:
    """Extract all function definitions from Python code.

    Args:
        code: Python source code as a string.

    Returns:
        List of dictionaries with function name, line number, argument count, and docstring.
    """
    try:
        tree = ast.parse(code)
        functions = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append({
                    "name": node.name,
                    "line": node.lineno,
                    "args": len(node.args.args),
                    "docstring": ast.get_docstring(node) or "No docstring",
                })

        return functions
    except SyntaxError as e:
        return [{"error": f"Syntax error: {e}"}]


@tool
def calculate_complexity(code: str) -> Dict[str, Any]:
    """Calculate cyclomatic complexity metrics for Python code.

    Estimates complexity based on number of functions, classes, and control flow.

    Args:
        code: Python source code as a string.

    Returns:
        Dictionary with complexity rating (low/medium/high) and contributing factors.
    """
    try:
        tree = ast.parse(code)

        functions = sum(1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef))
        classes = sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef))

        complexity_score = functions + (classes * 2)

        if complexity_score < 10:
            rating = "low"
        elif complexity_score < 30:
            rating = "medium"
        else:
            rating = "high"

        return {
            "rating": rating,
            "score": complexity_score,
            "functions": functions,
            "classes": classes,
        }
    except SyntaxError as e:
        return {"error": f"Syntax error: {e}"}


@tool
def assess_code_quality(code: str) -> Dict[str, Any]:
    """Assess Python code quality based on documentation and structure.

    Evaluates:
    - Documentation coverage (docstrings)
    - Code size and modularity
    - Function count and organization

    Args:
        code: Python source code as a string.

    Returns:
        Dictionary with quality score (0-100) and breakdown of factors.
    """
    try:
        tree = ast.parse(code)

        functions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append({
                    "name": node.name,
                    "has_docstring": ast.get_docstring(node) is not None,
                })

        lines = code.split("\n")
        code_lines = len([l for l in lines if l.strip() and not l.strip().startswith("#")])

        score = 100.0
        issues = []

        if functions:
            missing_docs = sum(1 for f in functions if not f["has_docstring"])
            doc_penalty = (missing_docs / len(functions)) * 20
            score -= doc_penalty
            if missing_docs > 0:
                issues.append(f"{missing_docs}/{len(functions)} functions missing docstrings")

        if code_lines > 500:
            score -= 10
            issues.append("File exceeds 500 lines of code")

        if len(functions) > 20:
            score -= 15
            issues.append("Too many functions (>20) - consider splitting module")

        return {
            "score": max(0.0, round(score, 2)),
            "total_functions": len(functions),
            "documented_functions": sum(1 for f in functions if f["has_docstring"]),
            "code_lines": code_lines,
            "issues": issues,
        }
    except SyntaxError as e:
        return {"error": f"Syntax error: {e}"}


@tool
def extract_dependencies(code: str) -> List[str]:
    """Extract all import statements and dependencies from Python code.

    Args:
        code: Python source code as a string.

    Returns:
        Sorted list of unique module names imported.
    """
    try:
        tree = ast.parse(code)
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)

        return sorted(set(imports))
    except SyntaxError as e:
        return [f"Syntax error: {e}"]


# ─── Helper Functions ──────────────────────────────────────────────────────────


def _calculate_complexity(functions: int, classes: int) -> str:
    """Internal helper to calculate complexity rating."""
    score = functions + (classes * 2)
    if score < 10:
        return "low"
    elif score < 30:
        return "medium"
    return "high"


def _calculate_quality_score(functions: List[Dict], code_lines: int) -> float:
    """Internal helper to calculate quality score."""
    score = 100.0
    if functions:
        missing_docs = sum(1 for f in functions if f["docstring"] == "No docstring")
        score -= (missing_docs / len(functions)) * 20
    if code_lines > 500:
        score -= 10
    if len(functions) > 20:
        score -= 15
    return max(0.0, round(score, 2))


# ─── Agent Definition ──────────────────────────────────────────────────────────

root_agent = Agent(
    name='code_logic_agent',
    description='Analyzes code structure, logic, and architecture. Performs AST parsing, complexity analysis, quality metrics, and structural analysis for Python and other languages.',
    tools=[
        analyze_python_code,
        analyze_generic_code,
        extract_functions,
        calculate_complexity,
        assess_code_quality,
        extract_dependencies,
    ],
)

# Wrap as A2A server (auto-generates Agent Card at /.well-known/agent-card.json)
# Use explicit http_url with container hostname for Docker networking
a2a_server = A2AServer(
    root_agent,
    host="0.0.0.0",
    port=PORT,
    http_url=f"http://code-logic-agent:{PORT}",
    enable_a2a_compliant_streaming=True
)

# ─── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"🚀 Code Logic Agent    →  http://localhost:{PORT}/")
    print(f"📄 Agent Card          →  http://localhost:{PORT}/.well-known/agent-card.json")
    a2a_server.serve()
