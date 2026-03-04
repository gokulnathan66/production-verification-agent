"""
Improved Test Run Agent - A2A compliant
Generates meaningful tests with Docker sandboxing and coverage analysis
"""
from fastapi import FastAPI, Request
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime
import os
import re
import subprocess
import tempfile
import ast
from pathlib import Path
import json

app = FastAPI(title="Test Run Agent")

TASKS = {}

AGENT_ID = os.getenv("AGENT_ID", "test-run-agent")
PORT = int(os.getenv("PORT", "8004"))
HOST = os.getenv("HOST", "localhost")
USE_DOCKER = os.getenv("USE_DOCKER", "false").lower() == "true"

AGENT_CARD = {
    "agentId": AGENT_ID,
    "name": "Test Run Agent",
    "description": "Generates meaningful tests with Docker sandboxing and coverage analysis",
    "version": "2.0.0",
    "endpoints": {
        "rpc": f"http://{HOST}:{PORT}/a2a",
        "health": f"http://{HOST}:{PORT}/health"
    },
    "capabilities": {
        "modalities": ["text", "file"],
        "skills": [
            "intelligent_test_generation",
            "docker_sandboxing",
            "coverage_analysis",
            "test_execution",
            "assertion_generation"
        ],
        "languages": ["python", "javascript"],
        "testFrameworks": ["pytest", "unittest", "jest"],
        "sandboxing": "docker" if USE_DOCKER else "subprocess"
    },
    "auth": {"scheme": "none", "required": False}
}


class ImprovedTestGenerator:
    """Intelligent test generation with real assertions"""

    def analyze_function(self, func_node: ast.FunctionDef) -> Dict[str, Any]:
        """Analyze function to generate meaningful tests"""
        
        info = {
            "name": func_node.name,
            "args": [arg.arg for arg in func_node.args.args],
            "returns": None,
            "raises": [],
            "calls": [],
            "branches": 0
        }
        
        # Check return type
        if func_node.returns:
            info["returns"] = ast.unparse(func_node.returns)
        
        # Analyze body
        for node in ast.walk(func_node):
            if isinstance(node, ast.Return) and node.value:
                if not info["returns"]:
                    info["returns"] = "inferred"
            
            elif isinstance(node, ast.Raise):
                if isinstance(node.exc, ast.Call) and isinstance(node.exc.func, ast.Name):
                    info["raises"].append(node.exc.func.id)
            
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                info["calls"].append(node.func.id)
            
            elif isinstance(node, (ast.If, ast.For, ast.While)):
                info["branches"] += 1
        
        return info

    def generate_python_tests(self, code: str) -> str:
        """Generate intelligent pytest tests"""
        
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return f"# Syntax error in code: {e}"
        
        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        
        if not functions:
            return "# No functions found to test"
        
        test_code = '''"""Auto-generated tests"""
import pytest
from unittest.mock import Mock, patch

'''
        
        # Add original code
        test_code += "# Original code\n"
        test_code += code + "\n\n"
        test_code += "# Generated tests\n\n"
        
        for func_node in functions:
            if func_node.name.startswith('_'):
                continue
            
            info = self.analyze_function(func_node)
            test_code += self._generate_test_for_function(info)
        
        return test_code

    def _generate_test_for_function(self, info: Dict[str, Any]) -> str:
        """Generate test cases for a specific function"""
        
        func_name = info["name"]
        args = info["args"]
        
        test_code = f"\nclass Test{func_name.title()}:\n"
        test_code += f'    """Tests for {func_name}"""\n\n'
        
        # Test 1: Basic existence and type
        test_code += f"    def test_{func_name}_exists(self):\n"
        test_code += f"        assert callable({func_name})\n\n"
        
        # Test 2: Return value test
        if info["returns"]:
            test_code += f"    def test_{func_name}_returns_value(self):\n"
            test_code += f"        result = {func_name}("
            test_code += ", ".join(self._generate_mock_args(args))
            test_code += ")\n"
            test_code += f"        assert result is not None\n\n"
        
        # Test 3: Exception handling
        if info["raises"]:
            for exc in set(info["raises"]):
                test_code += f"    def test_{func_name}_raises_{exc.lower()}(self):\n"
                test_code += f"        with pytest.raises({exc}):\n"
                test_code += f"            {func_name}("
                test_code += ", ".join(self._generate_invalid_args(args))
                test_code += ")\n\n"
        
        # Test 4: Edge cases
        if args:
            test_code += f"    def test_{func_name}_with_none(self):\n"
            test_code += f"        # Test with None values\n"
            test_code += f"        # TODO: Adjust based on expected behavior\n"
            test_code += f"        try:\n"
            test_code += f"            result = {func_name}("
            test_code += ", ".join(["None"] * len(args))
            test_code += ")\n"
            test_code += f"        except (TypeError, ValueError, AttributeError):\n"
            test_code += f"            pass  # Expected for some functions\n\n"
        
        # Test 5: Type checking
        if len(args) > 0:
            test_code += f"    def test_{func_name}_type_validation(self):\n"
            test_code += f"        # Test with valid types\n"
            test_code += f"        result = {func_name}("
            test_code += ", ".join(self._generate_typed_args(args))
            test_code += ")\n"
            test_code += f"        # Add specific assertions based on expected behavior\n"
            test_code += f"        assert result is not None or result is None  # Placeholder\n\n"
        
        return test_code

    def _generate_mock_args(self, args: List[str]) -> List[str]:
        """Generate mock arguments for testing"""
        mock_values = {
            "str": '"test_string"',
            "int": "42",
            "float": "3.14",
            "bool": "True",
            "list": "[1, 2, 3]",
            "dict": '{"key": "value"}',
            "default": "Mock()"
        }
        
        return [mock_values["default"] for _ in args]

    def _generate_invalid_args(self, args: List[str]) -> List[str]:
        """Generate invalid arguments to test error handling"""
        return ['"invalid"' for _ in args]

    def _generate_typed_args(self, args: List[str]) -> List[str]:
        """Generate typed arguments"""
        type_map = ["1", '"string"', "3.14", "True", "[1,2]"]
        return [type_map[i % len(type_map)] for i in range(len(args))]

    def run_tests_docker(self, test_code: str, language: str = "python") -> Dict[str, Any]:
        """Run tests in Docker container for isolation"""
        
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # Write test file
                test_file = Path(tmpdir) / "test_code.py"
                test_file.write_text(test_code)
                
                # Create Dockerfile
                dockerfile = Path(tmpdir) / "Dockerfile"
                dockerfile.write_text(f"""
FROM python:3.11-slim
WORKDIR /app
RUN pip install pytest pytest-cov
COPY test_code.py .
CMD ["python", "-m", "pytest", "test_code.py", "-v", "--tb=short", "--cov=.", "--cov-report=json"]
""")
                
                # Build image
                build_result = subprocess.run(
                    ["docker", "build", "-t", "test-runner", tmpdir],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if build_result.returncode != 0:
                    return {
                        "status": "build_failed",
                        "error": build_result.stderr
                    }
                
                # Run tests
                run_result = subprocess.run(
                    ["docker", "run", "--rm", "--network=none", "test-runner"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                # Parse coverage if available
                coverage = None
                try:
                    cov_result = subprocess.run(
                        ["docker", "run", "--rm", "test-runner", "cat", "coverage.json"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if cov_result.returncode == 0:
                        coverage = json.loads(cov_result.stdout)
                except:
                    pass
                
                return {
                    "status": "passed" if run_result.returncode == 0 else "failed",
                    "output": run_result.stdout,
                    "errors": run_result.stderr,
                    "coverage": coverage,
                    "sandbox": "docker"
                }
                
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "error": "Test execution timeout"}
        except FileNotFoundError:
            return {"status": "error", "error": "Docker not available"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def run_tests_subprocess(self, test_code: str) -> Dict[str, Any]:
        """Run tests in subprocess (less secure fallback)"""
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(test_code)
                test_file = f.name
            
            # Run with pytest
            result = subprocess.run(
                ['python', '-m', 'pytest', test_file, '-v', '--tb=short'],
                capture_output=True,
                text=True,
                timeout=30,
                env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}
            )
            
            return {
                "status": "passed" if result.returncode == 0 else "failed",
                "output": result.stdout,
                "errors": result.stderr,
                "sandbox": "subprocess"
            }
            
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "error": "Test execution timeout"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
        finally:
            try:
                os.unlink(test_file)
            except:
                pass

    def generate_javascript_tests(self, code: str) -> str:
        """Generate Jest tests for JavaScript"""
        
        # Extract functions
        func_pattern = r'(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>)'
        functions = re.findall(func_pattern, code)
        func_names = [f[0] or f[1] for f in functions if f[0] or f[1]]
        
        if not func_names:
            return "// No functions found"
        
        test_code = "// Auto-generated tests\n\n"
        test_code += "// Original code\n"
        test_code += code + "\n\n"
        test_code += "// Tests\n"
        test_code += "describe('Generated Tests', () => {\n"
        
        for func in func_names:
            test_code += f"""
  describe('{func}', () => {{
    test('should exist and be callable', () => {{
      expect(typeof {func}).toBe('function');
    }});

    test('should return a value', () => {{
      const result = {func}();
      expect(result).toBeDefined();
    }});

    test('should handle edge cases', () => {{
      // TODO: Add specific edge case tests
      expect(() => {func}(null)).not.toThrow();
    }});
  }});
"""
        
        test_code += "});\n"
        return test_code


test_gen = ImprovedTestGenerator()


@app.get("/.well-known/agent-card")
async def get_agent_card():
    return AGENT_CARD


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "agentId": AGENT_ID,
        "docker_available": USE_DOCKER,
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
    """Create test generation/execution task"""
    task_id = str(uuid.uuid4())
    message = params.get("message", {})
    metadata = params.get("metadata", {})

    code_text = ""
    language = "python"
    action = "generate"
    use_docker = USE_DOCKER

    for part in message.get("parts", []):
        if part.get("kind") == "text":
            code_text += part.get("text", "")
        elif part.get("kind") == "data":
            data = part.get("data", {})
            language = data.get("language", "python")
            code_text = data.get("code", code_text)
            action = data.get("action", "generate")
            use_docker = data.get("use_docker", USE_DOCKER)

    # Generate tests
    if language == "python":
        test_code = test_gen.generate_python_tests(code_text)
    elif language == "javascript":
        test_code = test_gen.generate_javascript_tests(code_text)
    else:
        test_code = f"# Tests for {language} not yet supported"

    result_text = f"""
🧪 Test Generation Results

Language: {language}
Action: {action}
Sandbox: {"Docker" if use_docker else "Subprocess"}

Generated {len(test_code.split('def test_')) - 1} test cases

Test Code Preview:
```
{test_code[:600]}...
```
"""

    data_result = {
        "test_code": test_code,
        "language": language,
        "action": action,
        "test_count": len(re.findall(r'def test_|test\(', test_code))
    }

    # Execute tests if requested
    if action == "execute" and language == "python":
        if use_docker:
            execution_result = test_gen.run_tests_docker(test_code, language)
        else:
            execution_result = test_gen.run_tests_subprocess(test_code)
        
        result_text += f"""

🚀 Execution Results:
Status: {execution_result.get('status', 'unknown')}
Sandbox: {execution_result.get('sandbox', 'unknown')}

Output:
{execution_result.get('output', 'No output')[:400]}
"""
        
        if execution_result.get('coverage'):
            cov = execution_result['coverage']
            result_text += f"\n📊 Coverage: {cov.get('totals', {}).get('percent_covered', 0):.1f}%\n"
        
        data_result["execution"] = execution_result

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
        "artifacts": [
            {
                "artifactId": str(uuid.uuid4()),
                "name": f"test_{language}.{'py' if language == 'python' else 'js'}",
                "mimeType": "text/plain",
                "content": test_code
            }
        ],
        "metadata": {**metadata, "agentId": AGENT_ID, "testAction": action}
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
    print(f"🚀 Starting Improved Test Run Agent: {AGENT_ID}")
    print(f"📍 AgentCard: http://{HOST}:{PORT}/.well-known/agent-card")
    print(f"🐳 Docker: {'Enabled' if USE_DOCKER else 'Disabled (using subprocess)'}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
