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


# ─── Agent Definition ──────────────────────────────────────────────────────────

root_agent = Agent(
    name='validation_agent',
    description='Performs comprehensive security validation, code quality checks, and compliance verification. Detects vulnerabilities, hardcoded secrets, injection risks, and code quality issues.',
    tools=[
        scan_security_vulnerabilities,
        check_code_quality,
        detect_risky_dependencies,
        comprehensive_validation,
        validate_production_readiness,
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
