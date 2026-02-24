"""
Validation Agent - A2A compliant
Performs security checks, code validation, and compliance verification
"""
from fastapi import FastAPI, Request
from typing import Dict, Any, List
import uuid
from datetime import datetime
import os
import re

app = FastAPI(title="Validation Agent")

TASKS = {}

AGENT_ID = os.getenv("AGENT_ID", "validation-agent")
PORT = int(os.getenv("PORT", "8005"))
HOST = os.getenv("HOST", "localhost")

AGENT_CARD = {
    "agentId": AGENT_ID,
    "name": "Validation Agent",
    "description": "Performs security validation, code quality checks, and compliance verification",
    "version": "1.0.0",
    "endpoints": {
        "rpc": f"http://{HOST}:{PORT}/a2a",
        "health": f"http://{HOST}:{PORT}/health"
    },
    "capabilities": {
        "modalities": ["text", "file"],
        "skills": [
            "security_validation",
            "secret_detection",
            "code_quality_check",
            "compliance_check",
            "vulnerability_scan",
            "best_practices"
        ],
        "languages": ["python", "javascript", "java", "all"],
        "checks": ["security", "quality", "compliance"]
    },
    "auth": {"scheme": "none", "required": False}
}


class Validator:
    """Security and validation checks"""

    # Security patterns to detect
    SECURITY_PATTERNS = {
        "hardcoded_secrets": [
            (r'password\s*=\s*["\']([^"\']+)["\']', "Hardcoded password"),
            (r'api[_-]?key\s*=\s*["\']([^"\']+)["\']', "Hardcoded API key"),
            (r'secret\s*=\s*["\']([^"\']+)["\']', "Hardcoded secret"),
            (r'token\s*=\s*["\']([^"\']+)["\']', "Hardcoded token"),
        ],
        "sql_injection": [
            (r'execute\(["\'].*%s.*["\']\s*%', "Potential SQL injection"),
            (r'\.format\(.*\).*execute', "SQL query with string format"),
        ],
        "command_injection": [
            (r'os\.system\(', "Use of os.system (command injection risk)"),
            (r'subprocess\.(run|call|Popen).*shell=True', "Shell=True in subprocess"),
        ],
        "xss": [
            (r'\.innerHTML\s*=', "Direct innerHTML assignment (XSS risk)"),
            (r'document\.write\(', "document.write() usage (XSS risk)"),
        ],
        "insecure_random": [
            (r'random\.random\(\)', "Insecure random (use secrets module)"),
        ]
    }

    QUALITY_CHECKS = {
        "missing_error_handling": [
            (r'open\([^)]+\)[^:]*$', "File open without try-except"),
        ],
        "poor_naming": [
            (r'\bdef\s+[a-z]\s*\(', "Single letter function name"),
            (r'\bclass\s+[a-z]', "Single letter class name"),
        ],
        "magic_numbers": [
            (r'=\s*\d{3,}', "Magic number (use constant)"),
        ]
    }

    def validate_code(self, code: str) -> Dict[str, Any]:
        """Run all validation checks"""

        issues = {
            "security": [],
            "quality": [],
            "warnings": []
        }

        lines = code.split('\n')

        # Security checks
        for category, patterns in self.SECURITY_PATTERNS.items():
            for pattern, description in patterns:
                for i, line in enumerate(lines, 1):
                    if re.search(pattern, line, re.IGNORECASE):
                        issues["security"].append({
                            "line": i,
                            "category": category,
                            "severity": "high",
                            "description": description,
                            "code": line.strip()
                        })

        # Quality checks
        for category, patterns in self.QUALITY_CHECKS.items():
            for pattern, description in patterns:
                for i, line in enumerate(lines, 1):
                    if re.search(pattern, line):
                        issues["quality"].append({
                            "line": i,
                            "category": category,
                            "severity": "medium",
                            "description": description,
                            "code": line.strip()
                        })

        # Additional checks
        if len(lines) > 1000:
            issues["warnings"].append({
                "type": "file_size",
                "description": f"Large file ({len(lines)} lines) - consider splitting"
            })

        # Calculate scores
        total_issues = len(issues["security"]) + len(issues["quality"])
        security_score = max(0, 100 - (len(issues["security"]) * 20))
        quality_score = max(0, 100 - (len(issues["quality"]) * 5))

        return {
            "issues": issues,
            "scores": {
                "security": security_score,
                "quality": quality_score,
                "overall": (security_score + quality_score) / 2
            },
            "summary": {
                "total_issues": total_issues,
                "critical": len([i for i in issues["security"] if i["severity"] == "high"]),
                "warnings": len(issues["warnings"])
            }
        }

    def check_dependencies(self, code: str) -> List[Dict[str, Any]]:
        """Check for known vulnerable dependencies"""

        # Simple check for known risky imports
        risky_imports = {
            "pickle": "Pickle is insecure - use json instead",
            "eval": "eval() is dangerous - avoid if possible",
            "exec": "exec() is dangerous - avoid if possible",
        }

        issues = []
        for module, warning in risky_imports.items():
            if re.search(rf'\b{module}\b', code):
                issues.append({
                    "module": module,
                    "risk": "high",
                    "recommendation": warning
                })

        return issues


validator = Validator()


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
    """Create validation task"""
    task_id = str(uuid.uuid4())
    message = params.get("message", {})
    metadata = params.get("metadata", {})

    # Extract code
    code_text = ""
    check_type = "all"  # security, quality, or all

    for part in message.get("parts", []):
        if part.get("kind") == "text":
            code_text += part.get("text", "")
        elif part.get("kind") == "data":
            data = part.get("data", {})
            code_text = data.get("code", code_text)
            check_type = data.get("check_type", "all")

    # Run validation
    validation_result = validator.validate_code(code_text)
    dependency_issues = validator.check_dependencies(code_text)

    # Format result
    scores = validation_result["scores"]
    summary = validation_result["summary"]
    issues = validation_result["issues"]

    result_text = f"""
🛡️ Validation Results

📊 Scores:
  • Security: {scores['security']}/100
  • Quality: {scores['quality']}/100
  • Overall: {scores['overall']:.1f}/100

📈 Summary:
  • Total Issues: {summary['total_issues']}
  • Critical: {summary['critical']}
  • Warnings: {summary['warnings']}

"""

    # Show critical security issues
    if issues["security"]:
        result_text += "🚨 Security Issues:\n"
        for issue in issues["security"][:5]:
            result_text += f"  Line {issue['line']}: {issue['description']}\n"
            result_text += f"    `{issue['code'][:60]}...`\n"

    # Show quality issues
    if issues["quality"]:
        result_text += "\n⚠️ Quality Issues:\n"
        for issue in issues["quality"][:5]:
            result_text += f"  Line {issue['line']}: {issue['description']}\n"

    # Show dependency issues
    if dependency_issues:
        result_text += "\n📦 Dependency Issues:\n"
        for dep in dependency_issues:
            result_text += f"  • {dep['module']}: {dep['recommendation']}\n"

    # Recommendations
    if summary['critical'] > 0:
        result_text += "\n⚠️ Action Required: Fix critical security issues before deployment!\n"
    elif scores['overall'] >= 80:
        result_text += "\n✅ Code looks good! Minor improvements suggested.\n"
    else:
        result_text += "\n📝 Consider addressing quality issues for better maintainability.\n"

    data_result = {
        "validation": validation_result,
        "dependencies": dependency_issues,
        "passed": summary['critical'] == 0
    }

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
        "metadata": {**metadata, "agentId": AGENT_ID, "checkType": check_type}
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
    print(f"🚀 Starting Validation Agent: {AGENT_ID}")
    print(f"📍 AgentCard: http://{HOST}:{PORT}/.well-known/agent-card")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
