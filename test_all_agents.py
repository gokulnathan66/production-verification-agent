#!/usr/bin/env python3
"""
Comprehensive test script for all A2A agents
"""
import httpx
import asyncio
import json
from typing import Dict, Any


SAMPLE_CODE = """
def calculate_sum(a, b):
    return a + b

def multiply(x, y):
    result = x * y
    return result

class Calculator:
    def __init__(self):
        self.history = []

    def add(self, a, b):
        result = a + b
        self.history.append(result)
        return result
"""


async def test_agent_health(name: str, port: int) -> bool:
    """Test agent health endpoint"""
    print(f"\n{'='*60}")
    print(f"Testing {name}")
    print('='*60)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://localhost:{port}/health", timeout=5.0)
            result = response.json()
            print(f"✅ Health Check: {result['status']}")
            print(f"   Agent ID: {result.get('agentId', 'N/A')}")
            return True
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


async def test_agent_card(name: str, port: int) -> bool:
    """Test AgentCard endpoint"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://localhost:{port}/.well-known/agent-card",
                timeout=5.0
            )
            card = response.json()
            print(f"✅ AgentCard: {card['name']}")
            print(f"   Skills: {', '.join(card['capabilities']['skills'][:3])}...")
            return True
    except Exception as e:
        print(f"❌ AgentCard failed: {e}")
        return False


async def test_agent_a2a(name: str, port: int, test_data: Dict[str, Any]) -> bool:
    """Test A2A protocol"""
    try:
        async with httpx.AsyncClient() as client:
            request = {
                "jsonrpc": "2.0",
                "id": f"test-{name}",
                "method": "a2a.createTask",
                "params": {
                    "message": {
                        "role": "user",
                        "parts": test_data["parts"]
                    }
                }
            }

            response = await client.post(
                f"http://localhost:{port}/a2a",
                json=request,
                timeout=30.0
            )
            result = response.json()

            if "error" in result:
                print(f"❌ A2A call failed: {result['error']}")
                return False

            task = result["result"]
            print(f"✅ Task created: {task['taskId'][:8]}...")
            print(f"   Status: {task['status']}")

            # Show result snippet
            for msg in task['messages']:
                if msg['role'] == 'assistant':
                    for part in msg['parts']:
                        if part['kind'] == 'text':
                            text = part['text'][:150]
                            print(f"   Result: {text}...")
                            break
                    break

            return True
    except Exception as e:
        print(f"❌ A2A call failed: {e}")
        return False


async def test_code_logic_agent():
    """Test Code Logic Agent"""
    return await test_agent_a2a(
        "code-logic-agent",
        8001,
        {
            "parts": [
                {"kind": "text", "text": SAMPLE_CODE},
                {"kind": "data", "data": {"code": SAMPLE_CODE, "language": "python"}}
            ]
        }
    )


async def test_research_agent():
    """Test Research Agent"""
    return await test_agent_a2a(
        "research-agent",
        8003,
        {
            "parts": [
                {"kind": "text", "text": SAMPLE_CODE},
                {"kind": "data", "data": {"code": SAMPLE_CODE, "language": "python", "type": "functions"}}
            ]
        }
    )


async def test_test_run_agent():
    """Test Test Run Agent"""
    return await test_agent_a2a(
        "test-run-agent",
        8004,
        {
            "parts": [
                {"kind": "text", "text": SAMPLE_CODE},
                {"kind": "data", "data": {"code": SAMPLE_CODE, "language": "python", "action": "generate"}}
            ]
        }
    )


async def test_validation_agent():
    """Test Validation Agent"""
    bad_code = """
password = "hardcoded123"
api_key = "sk-1234567890"
os.system(user_input)
"""
    return await test_agent_a2a(
        "validation-agent",
        8005,
        {
            "parts": [
                {"kind": "text", "text": bad_code},
                {"kind": "data", "data": {"code": bad_code, "check_type": "all"}}
            ]
        }
    )


async def test_orchestrator_workflow():
    """Test Main Orchestrator with full workflow"""
    print(f"\n{'='*60}")
    print("Testing Orchestrator - Full Workflow")
    print('='*60)

    try:
        async with httpx.AsyncClient() as client:
            request = {
                "jsonrpc": "2.0",
                "id": "test-orchestrator",
                "method": "a2a.createTask",
                "params": {
                    "message": {
                        "role": "user",
                        "parts": [
                            {"kind": "text", "text": SAMPLE_CODE},
                            {"kind": "data", "data": {
                                "code": SAMPLE_CODE,
                                "language": "python",
                                "workflow": "full_analysis"
                            }}
                        ]
                    }
                }
            }

            print("🚀 Running full analysis workflow...")
            response = await client.post(
                "http://localhost:8000/a2a",
                json=request,
                timeout=120.0  # Longer timeout for workflow
            )
            result = response.json()

            if "error" in result:
                print(f"❌ Workflow failed: {result['error']}")
                return False

            task = result["result"]
            print(f"✅ Workflow completed!")
            print(f"   Task ID: {task['taskId'][:8]}...")

            # Show summary
            for msg in task['messages']:
                if msg['role'] == 'assistant':
                    for part in msg['parts']:
                        if part['kind'] == 'text':
                            text = part['text'][:500]
                            print(f"\n📊 Summary:\n{text}...")
                            break
                    break

            return True
    except Exception as e:
        print(f"❌ Workflow failed: {e}")
        return False


async def run_all_tests():
    """Run all tests"""
    print("\n" + "🧪 "*30)
    print("A2A Multi-Agent System - Comprehensive Test Suite")
    print("🧪 "*30 + "\n")

    agents = [
        ("Code Logic Agent", 8001),
        ("Research Agent", 8003),
        ("Test Run Agent", 8004),
        ("Validation Agent", 8005),
        ("Orchestrator Agent", 8000),
    ]

    results = []

    # Test each agent
    for name, port in agents:
        health_ok = await test_agent_health(name, port)
        if not health_ok:
            results.append((name, "Health Check", False))
            continue

        card_ok = await test_agent_card(name, port)
        results.append((name, "AgentCard", card_ok))

    # Test individual agent functionality
    print(f"\n{'='*60}")
    print("Testing Individual Agent Functionality")
    print('='*60)

    tests = [
        ("Code Logic", test_code_logic_agent),
        ("Research", test_research_agent),
        ("Test Run", test_test_run_agent),
        ("Validation", test_validation_agent),
    ]

    for name, test_func in tests:
        print(f"\n→ Testing {name}...")
        result = await test_func()
        results.append((name, "A2A Protocol", result))

    # Test orchestrator workflow
    orch_result = await test_orchestrator_workflow()
    results.append(("Orchestrator", "Full Workflow", orch_result))

    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)

    passed = 0
    failed = 0

    for agent, test_type, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {agent}: {test_type}")
        if result:
            passed += 1
        else:
            failed += 1

    total = passed + failed
    print("\n" + "="*60)
    print(f"Results: {passed}/{total} tests passed")
    print("="*60)

    if passed == total:
        print("\n🎉 All tests passed! System is fully operational!")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Check logs for details.")
        print("\nTroubleshooting:")
        print("  1. Ensure all agents are running: ./run_all_agents.sh")
        print("  2. Check logs: ls logs/")
        print("  3. Verify ports: lsof -i :8000-8005")


if __name__ == "__main__":
    print("\n⏳ Starting tests...")
    print("   (Make sure all agents are running!)\n")
    asyncio.run(run_all_tests())
