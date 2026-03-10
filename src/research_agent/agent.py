"""
Research Agent - Strands Agents compliant
Real grep-based code search with AST parsing and file system support
"""

import ast
import os
import re
import subprocess
from typing import Any, Dict, List

from strands import Agent, tool
from strands.multiagent.a2a import A2AServer

# ─── Config ────────────────────────────────────────────────────────────────────

PORT = int(os.getenv("PORT", "8003"))

# ─── Research Tools ────────────────────────────────────────────────────────────


@tool
def grep_search(
    pattern: str,
    code: str = None,
    directory: str = None,
    context_lines: int = 2,
) -> List[Dict[str, Any]]:
    """Search for patterns in code using grep or ripgrep.

    Searches within provided code text or a directory on the filesystem.
    Uses ripgrep (rg) if available, falls back to standard grep.

    Args:
        pattern: Regex pattern to search for.
        code: Optional code text to search within.
        directory: Optional directory path to search in.
        context_lines: Number of context lines to include (default: 2).

    Returns:
        List of match dictionaries with file, line number, and content.
    """
    if code:
        return _search_in_text(pattern, code, context_lines)
    if directory and os.path.isdir(directory):
        return _search_in_directory(pattern, directory, context_lines)
    return [{"error": "No code or directory provided"}]


@tool
def find_all_functions(code: str, language: str = "python") -> List[Dict[str, Any]]:
    """Find all function definitions in source code.

    For Python: Uses AST parsing to extract detailed function metadata.
    For other languages: Uses regex patterns to detect functions.

    Args:
        code: Source code as a string.
        language: Programming language (default: python).

    Returns:
        List of function dictionaries with name, line, args, docstring, complexity.
    """
    if language != "python":
        return _find_functions_regex(code, language)

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
                    "complexity": _estimate_complexity(node),
                })

        return functions
    except SyntaxError as e:
        return [{"error": f"Syntax error: {e}"}]


@tool
def find_all_classes(code: str, language: str = "python") -> List[Dict[str, Any]]:
    """Find all class definitions in source code.

    Args:
        code: Source code as a string.
        language: Programming language (default: python).

    Returns:
        List of class dictionaries with name, line number, and definition.
    """
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
            results.append({
                "name": match.group(1),
                "line": i,
                "definition": line.strip()
            })

    return results


@tool
def extract_all_imports(code: str, language: str = "python") -> List[str]:
    """Extract all import statements from source code.

    For Python: Uses AST parsing for accurate extraction.
    For other languages: Uses regex patterns.

    Args:
        code: Source code as a string.
        language: Programming language (default: python).

    Returns:
        Sorted list of unique module/package names.
    """
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
        except SyntaxError:
            pass

    # Fallback to regex
    patterns = {
        "python": r"(?:from\s+([\w.]+)\s+)?import\s+([\w., ]+)",
        "javascript": r"import\s+.*from\s+['\"](.+)['\"]",
        "java": r"import\s+([\w.]+)",
        "go": r'import\s+["\'](.+)["\']',
    }
    pattern = patterns.get(language, patterns["python"])

    imports = set()
    for match in re.finditer(pattern, code):
        imports.update(g for g in match.groups() if g)

    return sorted(imports)


@tool
def comprehensive_code_research(code: str, language: str = "python") -> Dict[str, Any]:
    """Perform comprehensive research on source code.

    Combines function discovery, class extraction, and import analysis
    into a single comprehensive report.

    Args:
        code: Source code as a string.
        language: Programming language (default: python).

    Returns:
        Dictionary with functions, classes, imports, and summary statistics.
    """
    functions = find_all_functions(code, language)
    classes = find_all_classes(code, language)
    imports = extract_all_imports(code, language)

    return {
        "language": language,
        "summary": {
            "total_functions": len(functions),
            "total_classes": len(classes),
            "total_imports": len(imports),
        },
        "functions": functions,
        "classes": classes,
        "imports": imports,
    }


# ─── Helper Functions ──────────────────────────────────────────────────────────


def _search_in_text(pattern: str, text: str, context: int) -> List[Dict[str, Any]]:
    """Search for pattern within text with context lines."""
    results = []
    lines = text.split("\n")

    for i, line in enumerate(lines):
        if re.search(pattern, line, re.IGNORECASE):
            start = max(0, i - context)
            end = min(len(lines), i + context + 1)
            results.append({
                "line": i + 1,
                "content": line.strip(),
                "context_before": [l.strip() for l in lines[start:i]],
                "context_after": [l.strip() for l in lines[i + 1:end]],
                "match": pattern,
            })

    return results


def _search_in_directory(pattern: str, directory: str, context: int) -> List[Dict[str, Any]]:
    """Search for pattern in directory using ripgrep or grep."""
    # Try ripgrep first (faster)
    try:
        result = subprocess.run(
            ["rg", pattern, directory, "--context", str(context),
             "--line-number", "--no-heading", "--color", "never"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            return _parse_grep_output(result.stdout)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Fallback to grep
    try:
        result = subprocess.run(
            ["grep", "-r", "-n", "-C", str(context), pattern, directory],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode in [0, 1]:
            return _parse_grep_output(result.stdout)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return [{"error": f"No grep tool available or search failed"}]


def _parse_grep_output(output: str) -> List[Dict[str, Any]]:
    """Parse grep/ripgrep output into structured results."""
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


def _find_functions_regex(code: str, language: str) -> List[Dict[str, Any]]:
    """Find functions using regex patterns for non-Python languages."""
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
                results.append({
                    "name": func_name,
                    "line": i,
                    "signature": line.strip()
                })

    return results


def _estimate_complexity(node: ast.FunctionDef) -> int:
    """Estimate cyclomatic complexity of a function."""
    complexity = 1
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
            complexity += 1
        elif isinstance(child, ast.BoolOp):
            complexity += len(child.values) - 1
    return complexity


# ─── Agent Definition ──────────────────────────────────────────────────────────

root_agent = Agent(
    name='research_agent',
    description='Performs deep code research using grep/ripgrep for pattern matching and AST parsing for structural analysis. Discovers functions, classes, imports, and dependencies across multiple languages.',
    tools=[
        grep_search,
        find_all_functions,
        find_all_classes,
        extract_all_imports,
        comprehensive_code_research,
    ],
)

# Wrap as A2A server
a2a_server = A2AServer(root_agent, host="0.0.0.0", port=PORT)

# ─── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"🚀 Research Agent      →  http://localhost:{PORT}/")
    print(f"📄 Agent Card          →  http://localhost:{PORT}/.well-known/agent-card.json")
    a2a_server.serve()
