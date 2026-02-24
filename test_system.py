#!/usr/bin/env python3
"""
Simple test script for A2A multi-agent system
Run this after starting both agent and orchestrator
"""
import httpx
import asyncio
import json
from typing import Dict, Any


async def test_agent_health():
    """Test 1: Check agent health"""
    print("\n" + "="*60)
    print("Test 1: Agent Health Check")
    print("="*60)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8001/health")
            result = response.json()
            print(f"✅ Agent is healthy!")
            print(f"   Agent ID: {result['agentId']}")
            print(f"   Active Tasks: {result['activeTasks']}")
            print(f"   Completed Tasks: {result['completedTasks']}")
            return True
    except Exception as e:
        print(f"❌ Agent health check failed: {e}")
        print("   Make sure agent is running on port 8001")
        return False


async def test_agent_card():
    """Test 2: Get AgentCard"""
    print("\n" + "="*60)
    print("Test 2: Get AgentCard")
    print("="*60)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8001/.well-known/agent-card")
            agent_card = response.json()
            print(f"✅ AgentCard retrieved!")
            print(f"   Agent: {agent_card['name']}")
            print(f"   Skills: {', '.join(agent_card['capabilities']['skills'])}")
            print(f"   RPC: {agent_card['endpoints']['rpc']}")
            return True
    except Exception as e:
        print(f"❌ AgentCard retrieval failed: {e}")
        return False


async def test_direct_a2a_call():
    """Test 3: Direct A2A protocol call"""
    print("\n" + "="*60)
    print("Test 3: Direct A2A Protocol Call")
    print("="*60)

    try:
        async with httpx.AsyncClient() as client:
            request = {
                "jsonrpc": "2.0",
                "id": "test-direct",
                "method": "a2a.createTask",
                "params": {
                    "message": {
                        "role": "user",
                        "parts": [
                            {"kind": "text", "text": "Test direct A2A call"}
                        ]
                    }
                }
            }

            response = await client.post(
                "http://localhost:8001/a2a",
                json=request
            )
            result = response.json()

            if "error" in result:
                print(f"❌ A2A call failed: {result['error']}")
                return False

            task = result["result"]
            print(f"✅ Task created via A2A protocol!")
            print(f"   Task ID: {task['taskId']}")
            print(f"   Status: {task['status']}")
            print(f"   Messages: {len(task['messages'])}")

            # Show response
            for msg in task['messages']:
                if msg['role'] == 'assistant':
                    text = msg['parts'][0]['text']
                    print(f"   Response: {text}")

            return True
    except Exception as e:
        print(f"❌ Direct A2A call failed: {e}")
        return False


async def test_orchestrator_health():
    """Test 4: Check orchestrator health"""
    print("\n" + "="*60)
    print("Test 4: Orchestrator Health Check")
    print("="*60)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/health")
            result = response.json()
            print(f"✅ Orchestrator is healthy!")
            print(f"   Status: {result['status']}")
            print(f"   Agents Known: {result['agents_count']}")
            print(f"   MCP Available: {result['mcp_available']}")
            return True
    except Exception as e:
        print(f"❌ Orchestrator health check failed: {e}")
        print("   Make sure orchestrator is running on port 8000")
        return False


async def test_discover_agent():
    """Test 5: Discover agent via orchestrator"""
    print("\n" + "="*60)
    print("Test 5: Discover Agent via Orchestrator")
    print("="*60)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/discover",
                json={"url": "http://localhost:8001"}
            )
            result = response.json()

            if result["status"] == "discovered":
                agent = result["agent"]
                print(f"✅ Agent discovered!")
                print(f"   Agent: {agent['name']}")
                print(f"   ID: {agent['agentId']}")
                return True
            else:
                print(f"❌ Discovery failed: {result}")
                return False
    except Exception as e:
        print(f"❌ Discovery failed: {e}")
        return False


async def test_execute_via_orchestrator():
    """Test 6: Execute task via orchestrator"""
    print("\n" + "="*60)
    print("Test 6: Execute Task via Orchestrator")
    print("="*60)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/execute",
                json={
                    "request": "Hello from test script!",
                    "metadata": {"test": True}
                }
            )
            result = response.json()

            if result["status"] == "completed":
                print(f"✅ Task executed successfully!")
                print(f"   Agent Used: {result['agent_used']}")
                print(f"   Task ID: {result['result']['taskId']}")

                # Show response
                for msg in result['result']['messages']:
                    if msg['role'] == 'assistant':
                        text = msg['parts'][0]['text']
                        print(f"   Response: {text}")

                return True
            else:
                print(f"❌ Execution failed: {result}")
                return False
    except Exception as e:
        print(f"❌ Execution failed: {e}")
        return False


async def test_mcp_docs():
    """Test 7: Get docs via MCP"""
    print("\n" + "="*60)
    print("Test 7: Get A2A Docs via MCP")
    print("="*60)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/docs/a2a/createTask")
            result = response.json()
            print(f"✅ MCP documentation retrieved!")
            print(f"   Topic: {result['topic']}")
            print(f"   Docs preview: {result['documentation'][:100]}...")
            return True
    except Exception as e:
        print(f"❌ MCP docs retrieval failed: {e}")
        return False


async def run_all_tests():
    """Run all tests"""
    print("\n" + "🧪 "*20)
    print("A2A Multi-Agent System - Test Suite")
    print("🧪 "*20)

    tests = [
        ("Agent Health", test_agent_health),
        ("AgentCard", test_agent_card),
        ("Direct A2A Call", test_direct_a2a_call),
        ("Orchestrator Health", test_orchestrator_health),
        ("Discover Agent", test_discover_agent),
        ("Execute via Orchestrator", test_execute_via_orchestrator),
        ("MCP Docs", test_mcp_docs),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Test '{name}' crashed: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")

    print("\n" + "="*60)
    print(f"Results: {passed}/{total} tests passed")
    print("="*60)

    if passed == total:
        print("\n🎉 All tests passed! System is working correctly!")
    else:
        print("\n⚠️  Some tests failed. Check the output above.")
        print("\nMake sure both services are running:")
        print("  1. Agent: python src/simple_agent/agent.py")
        print("  2. Orchestrator: python src/orchestrator/orchestrator.py")


if __name__ == "__main__":
    print("\n⏳ Starting tests in 2 seconds...")
    print("   (Make sure agent and orchestrator are running!)")
    asyncio.sleep(2)

    asyncio.run(run_all_tests())
