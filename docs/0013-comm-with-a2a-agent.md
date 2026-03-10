There are three main ways to communicate with an A2A-exposed agent, depending on whether you want to use the **official Python SDK**, **raw HTTP/JSON-RPC**, or a **streaming connection**. Here's a complete breakdown.

***

## Step 1: Discover the Agent Card

Before sending any task, fetch the agent's capabilities from its well-known endpoint: [a2aprotocol](https://a2aprotocol.ai/blog/a2a-sample-methods-and-json-responses)

```bash
GET http://localhost:8001/.well-known/agent.json
```

This returns metadata: name, skills, supported input/output modes, and auth requirements.

***

## Method 1: Official Python SDK (`a2a-python`)

Install the SDK: [github](https://github.com/a2aproject/a2a-python)

```bash
pip install a2a-sdk
```

Send a message using `A2AClient`: [codelabs.developers.google](https://codelabs.developers.google.com/intro-a2a-purchasing-concierge)

```python
import asyncio, uuid
from a2a.client import A2AClient
from a2a.types import SendMessageRequest, MessageSendParams

async def main():
    # Initialize client pointing to the remote agent
    client = await A2AClient.get_client_from_agent_card_url(
        httpx_client=httpx.AsyncClient(),
        base_url="http://localhost:8001"
    )

    message_id = str(uuid.uuid4())

    # Build the request payload
    request = SendMessageRequest(
        id=message_id,
        params=MessageSendParams.model_validate({
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": "Roll a 6-sided die"}],
                "messageId": message_id,
            }
        })
    )

    # Send and get response
    response = await client.send_message(message_request=request)
    print(response.model_dump_json(indent=2))

asyncio.run(main())
```

The response `result` will be either a **Task** (for long-running ops) or a **Message** (for quick responses). [towardsdatascience](https://towardsdatascience.com/multi-agent-communication-with-the-a2a-python-sdk/)

***

## Method 2: Raw HTTP / JSON-RPC (`message/send`)

No SDK needed — just a plain POST: [a2aprotocol](https://a2aprotocol.ai/blog/a2a-sample-methods-and-json-responses)

```python
import httpx, uuid

payload = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "message/send",
    "params": {
        "message": {
            "role": "user",
            "parts": [{"kind": "text", "text": "Is 17 a prime number?"}],
            "messageId": str(uuid.uuid4())
        },
        "metadata": {}
    }
}

response = httpx.post("http://localhost:8001", json=payload)
result = response.json()["result"]

# Extract the answer
if result["kind"] == "task":
    for artifact in result.get("artifacts", []):
        for part in artifact["parts"]:
            print(part["text"])
elif result["kind"] == "message":
    for part in result["parts"]:
        print(part["text"])
```

***

## Method 3: Streaming (`message/stream` via SSE)

Use this when the agent might take a while or streams partial output: [a2aprotocol](https://a2aprotocol.ai/blog/a2a-sample-methods-and-json-responses)

```python
import httpx, json, uuid

payload = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "message/stream",
    "params": {
        "message": {
            "role": "user",
            "parts": [{"kind": "text", "text": "Write a long report on AI trends"}],
            "messageId": str(uuid.uuid4())
        }
    }
}

with httpx.stream("POST", "http://localhost:8001", json=payload) as r:
    for line in r.iter_lines():
        if line.startswith("data: "):
            event = json.loads(line[6:])
            result = event.get("result", {})

            # Partial artifact chunks
            if result.get("kind") == "artifact-update":
                for part in result["artifact"]["parts"]:
                    print(part.get("text", ""), end="", flush=True)

            # Task completed
            if result.get("kind") == "status-update" and result.get("final"):
                print("\n[Done]")
                break
```

The server sends SSE events with `kind: artifact-update` for chunks and `kind: status-update` + `final: true` when done. [a2aprotocol](https://a2aprotocol.ai/blog/a2a-sample-methods-and-json-responses)

***

## Multi-Turn (Input-Required) Handling

If the agent returns `status.state: "input-required"`, continue the conversation using the **same `taskId` and `contextId`**: [a2aprotocol](https://a2aprotocol.ai/blog/a2a-sample-methods-and-json-responses)

```python
# Follow-up message on the same task
followup_payload = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "message/send",
    "params": {
        "message": {
            "role": "user",
            "parts": [{"kind": "text", "text": "JFK to LHR, Oct 10th"}],
            "contextId": "<contextId from first response>",
            "taskId": "<taskId from first response>",
            "messageId": str(uuid.uuid4())
        },
        "configuration": {"blocking": True}
    }
}
```

***

## Communication Modes at a Glance

| Method | Use Case | Transport |
|---|---|---|
| `message/send` | Short tasks, Q&A | HTTP POST, wait for full response |
| `message/stream` | Long tasks, streaming output | HTTP POST + SSE |
| `tasks/get` | Poll status of a running task | HTTP POST JSON-RPC |
| Webhook (`pushNotification`) | Fire-and-forget long jobs | Server POSTs back to your URL |

The `contextId` acts like a **session ID** — always pass it back to maintain conversation state across multiple turns. [a2aprotocol](https://a2aprotocol.ai/blog/a2a-sample-methods-and-json-responses)