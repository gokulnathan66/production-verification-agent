"""
Validation Agent - Strands Agents compliant
Performs security checks, code validation, and compliance verification
"""

import os
import re
from typing import Any, Dict, List

from strands import Agent, tool
from strands.multiagent.a2a import A2AServer

# ─── Config ────────────────────────────────────────────────────────────────────

PORT = int(os.getenv("PORT", "8005"))

# ─── Security Patterns ─────────────────────────────────────────────────────────

SECURITY_PATTERNS: Dict[str, List[tuple]] = {
    "hardcoded_secrets": [
        (r'password\s*=\s*["\']([^"\']+)["\']',  "Hardcoded password"),
        (r'api[_-]?key\s*=\s*["\']([^"\']+)["\']', "Hardcoded API key"),
        (r'secret\s*=\s*["\']([^"\']+)["\']',    "Hardcoded secret"),
        (r'token\s*=\s*["\']([^"\']+)["\']',     "Hardcoded token"),
    ],
    "sql_injection": [
        (r'execute\(["\'].*%s.*["\']\s*%',       "Potential SQL injection"),
        (r'\.format\(.*\).*execute',             "SQL query with string format"),
    ],
    "command_injection": [
        (r'os\.system\(',                        "os.system() — command injection risk"),
        (r'subprocess\.(run|call|Popen).*shell=True', "shell=True in subprocess"),
    ],
    "xss": [
        (r'\.innerHTML\s*=',   "Direct innerHTML assignment — XSS risk"),
        (r'document\.write\(', "document.write() — XSS risk"),
    ],
    "insecure_random": [
        (r'random\.random\(\)', "Insecure random — use secrets module"),
    ],
}

QUALITY_PATTERNS: Dict[str, List[tuple]] = {
    "missing_error_handling": [
        (r'open\([^)]+\)[^:]*$', "File open without try-except"),
    ],
    "poor_naming": [
        (r'\bdef\s+[a-z]\s*\(',  "Single-letter function name"),
        (r'\bclass\s+[a-z]',     "Single-letter class name"),
    ],
    "magic_numbers": [
        (r'=\s*\d{3,}', "Magic number — use a named constant"),
    ],
}

RISKY_BUILTINS: Dict[str, str] = {
    "pickle": "pickle is insecure — use json instead",
    "eval":   "eval() is dangerous — avoid if possible",
    "exec":   "exec() is dangerous — avoid if possible",
}

# ─── Validation Tools ──────────────────────────────────────────────────────────


@tool
def scan_security_vulnerabilities(code: str) -> Dict[str, Any]:
    """Scan code for security vulnerabilities.

    Detects:
    - Hardcoded secrets (passwords, API keys, tokens)
    - SQL injection patterns
    - Command injection risks
    - XSS vulnerabilities
    - Insecure random number generation

    Args:
        code: Source code as a string.

    Returns:
        Dictionary with security issues, score, and recommendations.
    """
    issues = []
    lines = code.split("\n")

    for category, patterns in SECURITY_PATTERNS.items():
        for pattern, description in patterns:
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append({
                        "line": i,
                        "category": category,
                        "severity": "high",
                        "description": description,
                        "code": line.strip(),
                    })

    security_score = max(0, 100 - len(issues) * 20)

    return {
        "security_issues": issues,
        "security_score": security_score,
        "critical_count": len(issues),
        "passed": len(issues) == 0,
    }


@tool
def check_code_quality(code: str) -> Dict[str, Any]:
    """Check code quality and best practices.

    Analyzes:
    - Missing error handling
    - Poor naming conventions
    - Magic numbers
    - File size issues

    Args:
        code: Source code as a string.

    Returns:
        Dictionary with quality issues, score, and improvement suggestions.
    """
    issues = []
    warnings = []
    lines = code.split("\n")

    for category, patterns in QUALITY_PATTERNS.items():
        for pattern, description in patterns:
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line):
                    issues.append({
                        "line": i,
                        "category": category,
                        "severity": "medium",
                        "description": description,
                        "code": line.strip(),
                    })

    if len(lines) > 1000:
        warnings.append({
            "type": "file_size",
            "description": f"Large file ({len(lines)} lines) — consider splitting",
        })

    quality_score = max(0, 100 - len(issues) * 5)

    return {
        "quality_issues": issues,
        "warnings": warnings,
        "quality_score": quality_score,
        "total_issues": len(issues),
    }


@tool
def detect_risky_dependencies(code: str) -> List[Dict[str, Any]]:
    """Detect usage of risky builtins and modules.

    Flags dangerous functions like eval(), exec(), and insecure modules like pickle.

    Args:
        code: Source code as a string.

    Returns:
        List of risky dependencies with risk level and recommendations.
    """
    return [
        {"module": mod, "risk": "high", "recommendation": msg}
        for mod, msg in RISKY_BUILTINS.items()
        if re.search(rf"\b{mod}\b", code)
    ]


@tool
def comprehensive_validation(code: str) -> Dict[str, Any]:
    """Run comprehensive security and quality validation.

    Combines all validation checks into a single comprehensive report with
    scores, issues, and actionable recommendations.

    Args:
        code: Source code as a string.

    Returns:
        Complete validation report with security, quality, and dependency analysis.
    """
    security_result = scan_security_vulnerabilities(code)
    quality_result = check_code_quality(code)
    dependency_issues = detect_risky_dependencies(code)

    overall_score = (security_result["security_score"] + quality_result["quality_score"]) / 2

    return {
        "scores": {
            "security": security_result["security_score"],
            "quality": quality_result["quality_score"],
            "overall": overall_score,
        },
        "security": security_result,
        "quality": quality_result,
        "risky_dependencies": dependency_issues,
        "summary": {
            "total_issues": security_result["critical_count"] + quality_result["total_issues"],
            "critical": security_result["critical_count"],
            "warnings": len(quality_result["warnings"]),
            "passed": security_result["passed"] and quality_result["total_issues"] < 5,
        },
        "recommendation": _get_recommendation(security_result, quality_result, overall_score),
    }


@tool
def validate_production_readiness(code: str) -> Dict[str, bool]:
    """Quick check if code meets production readiness criteria.

    Args:
        code: Source code as a string.

    Returns:
        Dictionary with boolean flags for production readiness checks.
    """
    security_result = scan_security_vulnerabilities(code)
    quality_result = check_code_quality(code)

    return {
        "no_security_issues": security_result["passed"],
        "acceptable_quality": quality_result["quality_score"] >= 70,
        "no_risky_builtins": len(detect_risky_dependencies(code)) == 0,
        "production_ready": (
            security_result["passed"] and
            quality_result["quality_score"] >= 70 and
            len(detect_risky_dependencies(code)) == 0
        ),
    }


# ─── Helper Functions ──────────────────────────────────────────────────────────


def _get_recommendation(security_result: Dict, quality_result: Dict, overall_score: float) -> str:
    """Generate actionable recommendation based on validation results."""
    if security_result["critical_count"] > 0:
        return "⛔ Action Required: Fix critical security issues before deployment!"
    elif overall_score >= 80:
        return "✅ Code looks good! Minor improvements suggested."
    elif quality_result["total_issues"] > 10:
        return "📝 Consider refactoring to address quality issues for better maintainability."
    else:
        return "⚠️  Review and address the identified issues before production deployment."


@tool
def validate_workspace(workspace_path: str, max_files: int = 10) -> Dict[str, Any]:
    """Validate all Python files in a workspace for security and quality issues.

    Scans entire workspace for security vulnerabilities and quality issues across
    all Python files, providing aggregate statistics and critical findings.

    Args:
        workspace_path: Path to workspace directory (e.g., /tmp/workspace/task-id).
        max_files: Maximum number of files to validate (default: 10).

    Returns:
        Dictionary with concise workspace-wide validation summary (NOT all issues).
    """
    if not os.path.isdir(workspace_path):
        return {"error": f"Workspace not found: {workspace_path}"}

    python_files = []
    for root, dirs, files in os.walk(workspace_path):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))

    if not python_files:
        return {"error": "No Python files found in workspace"}

    # Aggregate validation results
    all_security_issues = []
    all_quality_issues = []
    total_security_score = 0
    total_quality_score = 0
    files_validated = 0

    for filepath in python_files[:max_files]:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                code = f.read()

            validation = comprehensive_validation(code)

            files_validated += 1
            total_security_score += validation['scores']['security']
            total_quality_score += validation['scores']['quality']

            # Collect critical security issues
            for issue in validation['security']['security_issues']:
                issue['file'] = os.path.relpath(filepath, workspace_path)
                all_security_issues.append(issue)

            # Collect quality issues
            for issue in validation['quality']['quality_issues']:
                issue['file'] = os.path.relpath(filepath, workspace_path)
                all_quality_issues.append(issue)

        except Exception as e:
            continue

    avg_security_score = total_security_score / files_validated if files_validated > 0 else 0
    avg_quality_score = total_quality_score / files_validated if files_validated > 0 else 0

    # Get only high severity security issues (limit to 5)
    high_severity = [i for i in all_security_issues if i.get('severity') == 'high'][:5]

    # Categorize security issues
    security_categories = {}
    for issue in all_security_issues:
        category = issue.get('category', 'unknown')
        security_categories[category] = security_categories.get(category, 0) + 1

    return {
        "workspace": workspace_path.split('/')[-1],  # Just task ID
        "total_python_files": len(python_files),
        "validated_files": files_validated,
        "scores": {
            "security": round(avg_security_score, 2),
            "quality": round(avg_quality_score, 2),
            "overall": round((avg_security_score + avg_quality_score) / 2, 2)
        },
        "issues_summary": {
            "total_security_issues": len(all_security_issues),
            "total_quality_issues": len(all_quality_issues),
            "security_by_category": security_categories,
            "critical_security_samples": [f"{i.get('category')}: {i.get('description')}" for i in high_severity]
        },
        "production_ready": len(all_security_issues) == 0 and avg_quality_score >= 70,
        "summary": f"Validated {files_validated} files. Security: {avg_security_score:.1f}/100 ({len(all_security_issues)} issues). Quality: {avg_quality_score:.1f}/100. {'✅ Production ready' if len(all_security_issues) == 0 and avg_quality_score >= 70 else '⚠️ Needs work'}"
    }


# ─── Agent Definition ──────────────────────────────────────────────────────────

root_agent = Agent(
    name='validation_agent',
    description='Performs comprehensive security validation, code quality checks, and compliance verification. Detects vulnerabilities, hardcoded secrets, injection risks, and code quality issues. Can validate individual files or entire workspace directories.',
    tools=[
        scan_security_vulnerabilities,
        check_code_quality,
        detect_risky_dependencies,
        comprehensive_validation,
        validate_production_readiness,
        validate_workspace,
    ],
)

# Wrap as A2A server with compliant streaming
# Use explicit http_url with container hostname for Docker networking
a2a_server = A2AServer(
    root_agent,
    host="0.0.0.0",
    port=PORT,
    http_url=f"http://validation-agent:{PORT}",
    enable_a2a_compliant_streaming=True
)

# ─── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"🚀 Validation Agent    →  http://localhost:{PORT}/")
    print(f"📄 Agent Card          →  http://localhost:{PORT}/.well-known/agent-card.json")
    a2a_server.serve()
