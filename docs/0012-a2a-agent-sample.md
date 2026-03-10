Here is a comprehensive A2A (Agent-to-Agent) protocol code sample using Google's official ADK (Agent Development Kit), along with a minimal `python-a2a` example.

***

## What is A2A?

The Agent2Agent (A2A) protocol is an open standard by Google that enables independent AI agents to discover each other, delegate tasks, and exchange results using **JSON-RPC 2.0 over HTTP(S)**. It centers around three concepts: **Agent Cards** (capability metadata), **Tasks** (stateful work units), and **Messages** (typed content). [dev](https://dev.to/czmilo/2025-complete-guide-agent2agent-a2a-protocol-the-new-standard-for-ai-agent-collaboration-1pph)

***

## Setup

Install the Google ADK with A2A support: [google.github](https://google.github.io/adk-docs/a2a/quickstart-exposing/)

```bash
pip install google-adk[a2a]
```

***

## Part 1: Remote Agent (Server Side)

This agent exposes tools via A2A — it rolls dice and checks prime numbers: [google.github](https://google.github.io/adk-docs/a2a/quickstart-exposing/)

```python
# remote_a2a/hello_world/agent.py
import random
from google.adk.agents import Agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a

def roll_die(sides: int) -> int:
    """Roll a die and return the result.
    Args:
        sides: Number of sides on the die.
    Returns:
        Integer result of rolling the die.
    """
    return random.randint(1, sides)

async def check_prime(nums: list[int]) -> str:
    """Check if numbers in a list are prime.
    Args:
        nums: List of integers to check.
    Returns:
        String indicating which numbers are prime.
    """
    def is_prime(n):
        if n < 2: return False
        for i in range(2, int(n**0.5)+1):
            if n % i == 0: return False
        return True

    results = {n: is_prime(n) for n in nums}
    return ", ".join(f"{n} is {'prime' if p else 'not prime'}" for n, p in results.items())

# Build the ADK agent
root_agent = Agent(
    model='gemini-2.0-flash',
    name='hello_world_agent',
    description='Rolls dice and checks prime numbers.',
    tools=[roll_die, check_prime],
)

# Wrap it as an A2A app (auto-generates Agent Card at /.well-known/agent-card.json)
a2a_app = to_a2a(root_agent, port=8001)
```

Start the remote agent server: [google.github](https://google.github.io/adk-docs/a2a/quickstart-exposing/)

```bash
uvicorn remote_a2a.hello_world.agent:a2a_app --host localhost --port 8001
```

***

## Part 2: Consumer Agent (Client Side)

This root agent discovers and delegates to the remote agent via A2A: [google.github](https://google.github.io/adk-docs/a2a/quickstart-exposing/)

```python
# agent.py (root/consuming agent)
from google.adk.agents import Agent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

# Point to the remote agent's well-known card URL
remote_hello_world = RemoteA2aAgent(
    agent_card_url="http://localhost:8001/.well-known/agent-card.json",
)

root_agent = Agent(
    model='gemini-2.0-flash',
    name='root_agent',
    description='Orchestrator that delegates to remote agents.',
    tools=[remote_hello_world],  # Remote A2A agent used as a tool
)
```

Run the dev UI to interact with both agents: [google.github](https://google.github.io/adk-docs/a2a/quickstart-exposing/)

```bash
adk web ./
```

***

## Part 3: Agent Card (Optional Manual Definition)

If you want explicit control over the agent card instead of auto-generation: [google.github](https://google.github.io/adk-docs/a2a/quickstart-exposing/)

```python
from a2a.types import AgentCard
from google.adk.a2a.utils.agent_to_a2a import to_a2a

my_agent_card = AgentCard(
    name="hello_world_agent",
    url="http://localhost:8001",
    description="Rolls dice and checks prime numbers.",
    version="1.0.0",
    capabilities={},
    skills=[],
    defaultInputModes=["text/plain"],
    defaultOutputModes=["text/plain"],
    supportsAuthenticatedExtendedCard=False,
)

a2a_app = to_a2a(root_agent, port=8001, agent_card=my_agent_card)
```

***

## Example Interaction Flow

Once both services are running: [google.github](https://google.github.io/adk-docs/a2a/quickstart-exposing/)

| User Input | Handled By | Response |
|---|---|---|
| `Roll a 6-sided die` | Local roll tool | `I rolled a 4 for you.` |
| `Is 7 a prime number?` | Remote A2A agent | `Yes, 7 is a prime number.` |
| `Roll a 10-sided die and check if it's prime` | Both agents | Roll result + prime check |

***

## Key Architecture Points

- **Agent Card** is auto-served at `/.well-known/agent-card.json` when you use `to_a2a()` [google.github](https://google.github.io/adk-docs/a2a/quickstart-exposing/)
- **`RemoteA2aAgent`** acts as a regular tool from the consuming agent's perspective — the A2A protocol is transparent [google.github](https://google.github.io/adk-docs/a2a/quickstart-exposing/)
- The protocol uses **JSON-RPC 2.0** under the hood, supporting streaming, push notifications, and multi-turn stateful tasks [dev](https://dev.to/czmilo/2025-complete-guide-agent2agent-a2a-protocol-the-new-standard-for-ai-agent-collaboration-1pph)
- For production, you can also deploy the remote agent on **Vertex AI Agent Engine** or Cloud Run instead of localhost [codelabs.developers.google](https://codelabs.developers.google.com/intro-a2a-purchasing-concierge)

For more samples, check the official repo: [github.com/a2aproject/a2a-samples](https://github.com/a2aproject/a2a-samples). [github](https://github.com/a2aproject/a2a-samples)