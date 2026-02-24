"""
Simple MCP client for documentation lookup
Uses Context7 MCP plugin for real-time documentation
"""
from typing import Optional


class MCPDocClient:
    """
    Simple wrapper to query documentation via MCP Context7

    In real implementation, this would connect to MCP server.
    For demo, we provide static docs but show the integration pattern.
    """

    def __init__(self):
        self.context7_available = True
        self.cache = {}

    async def get_a2a_docs(self, topic: str) -> str:
        """
        Get A2A protocol documentation using Context7 MCP

        Topics:
        - createTask: How to create tasks
        - getTask: How to retrieve tasks
        - message: Message format
        - agentcard: AgentCard specification
        """
        topic = topic.lower()

        # In real implementation:
        # result = await mcp_server.call_tool(
        #     "mcp__plugin_context7_context7__query-docs",
        #     libraryId="/a2a-protocol/latest",
        #     query=topic
        # )

        docs = {
            "createtask": """
📘 A2A createTask Method

Purpose: Create a new task on a remote agent

Request Format (JSON-RPC 2.0):
{
  "jsonrpc": "2.0",
  "id": "request-id",
  "method": "a2a.createTask",
  "params": {
    "message": {
      "role": "user",
      "parts": [
        {"kind": "text", "text": "Your message here"}
      ]
    },
    "metadata": {
      "priority": "high",
      "timeout": 300
    }
  }
}

Response:
{
  "jsonrpc": "2.0",
  "id": "request-id",
  "result": {
    "taskId": "uuid-here",
    "status": "pending" | "in_progress" | "completed" | "failed",
    "createdAt": "2026-02-24T10:00:00Z",
    "messages": [...],
    "artifacts": [...]
  }
}
""",
            "gettask": """
📘 A2A getTask Method

Purpose: Retrieve task status and results

Request:
{
  "jsonrpc": "2.0",
  "method": "a2a.getTask",
  "params": {
    "taskId": "task-id-here"
  }
}

Response: Same as createTask result
""",
            "message": """
📘 A2A Message Format

Message structure:
{
  "messageId": "uuid",
  "role": "user" | "assistant",
  "timestamp": "ISO-8601",
  "parts": [
    {"kind": "text", "text": "..."},
    {"kind": "file", "file": {...}},
    {"kind": "data", "data": {...}}
  ]
}

Part Types:
- TextPart: {"kind": "text", "text": string}
- FilePart: {"kind": "file", "file": {bytes, name, mimeType}}
- DataPart: {"kind": "data", "data": any JSON}
""",
            "agentcard": """
📘 AgentCard Specification

AgentCard is exposed at: /.well-known/agent-card

Structure:
{
  "agentId": "unique-id",
  "name": "Human readable name",
  "description": "What this agent does",
  "version": "semver",
  "endpoints": {
    "rpc": "http://agent.com/a2a",
    "health": "http://agent.com/health"
  },
  "capabilities": {
    "modalities": ["text", "file"],
    "skills": ["code_analysis", "testing"]
  },
  "auth": {
    "scheme": "bearer" | "none"
  }
}
"""
        }

        return docs.get(topic, "Documentation not found for: " + topic)

    async def resolve_library(self, library_name: str) -> Optional[str]:
        """
        Resolve library to Context7 library ID

        Example:
        - "fastapi" → "/tiangolo/fastapi"
        - "a2a-protocol" → "/a2aproject/A2A"
        """
        # In real implementation:
        # result = await mcp_server.call_tool(
        #     "mcp__plugin_context7_context7__resolve-library-id",
        #     libraryName=library_name,
        #     query="latest documentation"
        # )

        library_map = {
            "fastapi": "/tiangolo/fastapi",
            "a2a-protocol": "/a2aproject/A2A",
            "httpx": "/encode/httpx",
            "pydantic": "/pydantic/pydantic",
            "redis": "/redis/redis-py"
        }

        library_id = library_map.get(library_name.lower())

        if library_id:
            print(f"📚 Resolved {library_name} → {library_id}")

        return library_id

    async def query_docs(self, library_id: str, query: str) -> str:
        """
        Query specific library documentation

        Example:
        library_id = "/tiangolo/fastapi"
        query = "How to create POST endpoint?"
        """
        # In real implementation:
        # result = await mcp_server.call_tool(
        #     "mcp__plugin_context7_context7__query-docs",
        #     libraryId=library_id,
        #     query=query
        # )

        return f"""
📚 Documentation for {library_id}

Query: {query}

Example code:
```python
from fastapi import FastAPI

app = FastAPI()

@app.post("/endpoint")
async def my_endpoint(data: dict):
    return {{"result": "success"}}
```

For complete docs, see: https://docs.example.com{library_id}
"""

    async def get_error_help(self, error_message: str) -> str:
        """
        Get help for error messages
        """
        # Could use MCP to search Stack Overflow, docs, etc.

        if "404" in error_message:
            return "HTTP 404: Endpoint not found. Check the URL and method."
        elif "500" in error_message:
            return "HTTP 500: Server error. Check agent logs."
        elif "Connection" in error_message:
            return "Connection error: Agent may not be running. Check health endpoint."

        return f"Error: {error_message}\n\nUse MCP Context7 to search for solutions."


# Singleton instance
mcp_doc_client = MCPDocClient()
