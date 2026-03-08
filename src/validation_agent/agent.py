"""
Validation Agent - Official A2A SDK compliant
Performs security checks, code validation, and compliance verification
"""

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

AGENT_ID = os.getenv("AGENT_ID", "validation-agent")
PORT     = int(os.getenv("PORT", "8005"))
HOST     = os.getenv("HOST", "localhost")

# ─── Agent Card ────────────────────────────────────────────────────────────────

agent_card = AgentCard(
    name="Validation Agent",
    description=(
        "Performs security validation, code quality checks, "
        "and compliance verification"
    ),
    url=f"http://{HOST}:{PORT}/",
    version="1.0.0",
    defaultInputModes=["text"],
    defaultOutputModes=["text", "data"],
    capabilities=AgentCapabilities(streaming=False),
    skills=[
        AgentSkill(
            id="security_validation",
            name="Security Validation",
            description="Detect hardcoded secrets, injections, and insecure patterns",
            tags=["security", "secrets", "injection"],
            examples=["Scan this code for security vulnerabilities"],
        ),
        AgentSkill(
            id="secret_detection",
            name="Secret Detection",
            description="Find hardcoded passwords, API keys, and tokens",
            tags=["secrets", "credentials", "api-keys"],
            examples=["Check for hardcoded credentials in this file"],
        ),
        AgentSkill(
            id="code_quality_check",
            name="Code Quality Check",
            description="Identify poor naming, magic numbers, and missing error handling",
            tags=["quality", "naming", "best-practices"],
            examples=["Check code quality and style issues"],
        ),
        AgentSkill(
            id="vulnerability_scan",
            name="Vulnerability Scan",
            description="Scan for SQL injection, XSS, command injection patterns",
            tags=["vulnerability", "sql-injection", "xss"],
            examples=["Scan for common vulnerabilities in this code"],
        ),
        AgentSkill(
            id="compliance_check",
            name="Compliance Check",
            description="Verify code against security compliance best practices",
            tags=["compliance", "standards"],
            examples=["Run compliance checks on this module"],
        ),
        AgentSkill(
            id="best_practices",
            name="Best Practices",
            description="Check use of risky builtins like eval, exec, pickle",
            tags=["best-practices", "risky-builtins"],
            examples=["Are there any dangerous builtins used here?"],
        ),
    ],
)

# ─── Validator ─────────────────────────────────────────────────────────────────

class Validator:
    """Security and code quality validation"""

    SECURITY_PATTERNS: Dict[str, List[tuple]] = {
        "hardcoded_secrets": [
            (r'password\s*=\s*["\']([^"\']+)["\']',  "Hardcoded password"),
            (r'api[_-]?key\s*=\s*["\']([^"\']+)["\']', "Hardcoded API key"),
            (r'secret\s*=\s*["\']([^"\']+)["\']',    "Hardcoded secret"),
            (r'token\s*=\s*["\']([^"\']+)["\']',     "Hardcoded token"),
        ],
        "sql_injection": [
            (r'execute\(["\''].*%s.*["\']\s*%',       "Potential SQL injection"),
            (r'\.format\(.*\).*execute',               "SQL query with string format"),
        ],
        "command_injection": [
            (r'os\.system\(',                          "os.system() — command injection risk"),
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

    # ── Core validation ────────────────────────────────────────────────────────

    def validate_code(self, code: str) -> Dict[str, Any]:
        """Run all security and quality checks, return scored report."""
        issues: Dict[str, List] = {"security": [], "quality": [], "warnings": []}
        lines = code.split("\n")

        for category, patterns in self.SECURITY_PATTERNS.items():
            for pattern, description in patterns:
                for i, line in enumerate(lines, 1):
                    if re.search(pattern, line, re.IGNORECASE):
                        issues["security"].append({
                            "line"       : i,
                            "category"   : category,
                            "severity"   : "high",
                            "description": description,
                            "code"       : line.strip(),
                        })

        for category, patterns in self.QUALITY_PATTERNS.items():
            for pattern, description in patterns:
                for i, line in enumerate(lines, 1):
                    if re.search(pattern, line):
                        issues["quality"].append({
                            "line"       : i,
                            "category"   : category,
                            "severity"   : "medium",
                            "description": description,
                            "code"       : line.strip(),
                        })

        if len(lines) > 1000:
            issues["warnings"].append({
                "type"       : "file_size",
                "description": f"Large file ({len(lines)} lines) — consider splitting",
            })

        security_score = max(0, 100 - len(issues["security"]) * 20)
        quality_score  = max(0, 100 - len(issues["quality"])  * 5)

        return {
            "issues": issues,
            "scores": {
                "security": security_score,
                "quality" : quality_score,
                "overall" : (security_score + quality_score) / 2,
            },
            "summary": {
                "total_issues": len(issues["security"]) + len(issues["quality"]),
                "critical"    : len([i for i in issues["security"] if i["severity"] == "high"]),
                "warnings"    : len(issues["warnings"]),
            },
        }

    def check_dependencies(self, code: str) -> List[Dict[str, Any]]:
        """Flag known risky builtins / modules."""
        return [
            {"module": mod, "risk": "high", "recommendation": msg}
            for mod, msg in self.RISKY_BUILTINS.items()
            if re.search(rf"\b{mod}\b", code)
        ]

    # ── Result formatter ───────────────────────────────────────────────────────

    @staticmethod
    def format_result(
        validation: Dict[str, Any],
        dependency_issues: List[Dict[str, Any]],
    ) -> str:
        scores  = validation["scores"]
        summary = validation["summary"]
        issues  = validation["issues"]

        lines = [
            "🛡️  Validation Results\n",
            "📊 Scores:",
            f"  • Security : {scores['security']}/100",
            f"  • Quality  : {scores['quality']}/100",
            f"  • Overall  : {scores['overall']:.1f}/100\n",
            "📈 Summary:",
            f"  • Total Issues : {summary['total_issues']}",
            f"  • Critical     : {summary['critical']}",
            f"  • Warnings     : {summary['warnings']}",
        ]

        if issues["security"]:
            lines.append("\n🚨 Security Issues:")
            for issue in issues["security"][:5]:
                lines.append(f"  Line {issue['line']}: {issue['description']}")
                lines.append(f"    `{issue['code'][:60]}`")

        if issues["quality"]:
            lines.append("\n⚠️  Quality Issues:")
            for issue in issues["quality"][:5]:
                lines.append(f"  Line {issue['line']}: {issue['description']}")

        if dependency_issues:
            lines.append("\n📦 Dependency / Builtin Issues:")
            for dep in dependency_issues:
                lines.append(f"  • {dep['module']}: {dep['recommendation']}")

        if summary["critical"] > 0:
            lines.append("\n⛔ Action Required: Fix critical security issues before deployment!")
        elif scores["overall"] >= 80:
            lines.append("\n✅ Code looks good! Minor improvements suggested.")
        else:
            lines.append("\n📝 Consider addressing quality issues for better maintainability.")

        return "\n".join(lines)


# ─── Agent Executor ────────────────────────────────────────────────────────────

validator = Validator()


class ValidationAgentExecutor(AgentExecutor):
    """
    A2A executor — parses incoming message parts, runs security +
    quality validation, and emits a text summary + structured data artifact.
    """

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        await updater.submit()
        await updater.start_work()

        try:
            # ── Parse incoming parts ──────────────────────────────────────────
            code_text  = ""
            check_type = "all"   # "security" | "quality" | "all"

            for part in context.message.parts:
                if isinstance(part.root, TextPart):
                    code_text += part.root.text
                elif isinstance(part.root, DataPart):
                    data: dict = part.root.data or {}
                    code_text  = data.get("code", code_text)
                    check_type = data.get("check_type", "all")

            # ── Run validation ────────────────────────────────────────────────
            validation_result  = validator.validate_code(code_text)
            dependency_issues  = validator.check_dependencies(code_text)

            result_text = Validator.format_result(validation_result, dependency_issues)

            data_result: Dict[str, Any] = {
                "validation"  : validation_result,
                "dependencies": dependency_issues,
                "check_type"  : check_type,
                "passed"      : validation_result["summary"]["critical"] == 0,
            }

            # ── Emit artifact ─────────────────────────────────────────────────
            await updater.add_artifact(
                parts=[
                    Part(root=TextPart(text=result_text)),
                    Part(root=DataPart(data=data_result)),
                ],
                name="validation_results",
            )
            await updater.complete()

        except Exception as exc:
            await updater.failed(message=str(exc))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError("Cancel is not supported by this agent")


# ─── App Bootstrap ─────────────────────────────────────────────────────────────

def build_app():
    handler = DefaultRequestHandler(
        agent_executor=ValidationAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )
    return A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=handler,
    ).build()


app = build_app()

if __name__ == "__main__":
    print(f"🚀 Validation Agent  →  http://{HOST}:{PORT}/")
    print(f"📄 Agent Card        →  http://{HOST}:{PORT}/.well-known/agent.json")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
