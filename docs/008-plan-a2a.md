# A2A Multi-Agent System - Enhanced Implementation Plan

## Overview
 
This document outlines the enhanced A2A (Agent-to-Agent) implementation plan for the multi-agent production verification system, focusing on advanced agent discovery, cloud deployment, and autonomous testing capabilities using **Google's A2A Protocol** (JSON-RPC 2.0 over HTTP/HTTPS).

---

## Google's A2A Protocol - Core Implementation

### Protocol Foundation

**A2A (Agent2Agent)** is an open JSON-RPC 2.0 based standard that enables different AI agents to communicate over HTTP(S) in a consistent, vendor-neutral way.

#### Key Characteristics
- **Transport**: HTTP(S) with JSON-RPC 2.0
- **Format**: Structured JSON messages
- **Roles**:
  - **Client Agent**: Initiates tasks and requests
  - **Remote Agent (A2A Server)**: Exposes capabilities and executes tasks
- **Interoperability**: Vendor-neutral, works across different agent frameworks

### Core A2A Objects           

#### 1. AgentCard
**Purpose**: Self-description document for agent discovery and capability negotiation

```json
{
  "agentId": "code-logic-agent",
  "name": "Code Logic Analysis Agent",
  "description": "Performs static code analysis, AST parsing, and complexity metrics",
  "version": "1.0.0",
  "endpoints": {
    "rpc": "https://agents.example.com/code-logic-agent/a2a"
  },
  "capabilities": {
    "modalities": ["text", "file"],
    "skills": [
      "code_analysis",
      "static_analysis",
      "complexity_metrics",
      "ast_parsing"
    ]
  },
  "auth": {
    "scheme": "bearer"
  },
  "resources": {
    "memory": "2GB",
    "timeout": 300
  }
}
```

#### 2. Task
**Purpose**: Represents a long-running job with lifecycle management

```json
{
  "taskId": "task-001",
  "status": "in_progress",
  "createdAt": "2026-02-24T10:00:00Z",
  "updatedAt": "2026-02-24T10:05:00Z",
  "messages": [
    {
      "messageId": "msg-001",
      "role": "user",
      "parts": [...]
    }
  ],
  "artifacts": [
    {
      "artifactId": "artifact-001",
      "name": "analysis-report.json",
      "mimeType": "application/json",
      "uri": "s3://results/analysis-report.json"
    }
  ],
  "metadata": {
    "priority": "high",
    "project": "code-verification"
  }
}
```

#### 3. Message
**Purpose**: Chat-like turn in a conversation with structured parts

```json
{
  "messageId": "msg-001",
  "role": "user",
  "timestamp": "2026-02-24T10:00:00Z",
  "parts": [
    {
      "kind": "text",
      "text": "Analyze this Python codebase for security vulnerabilities"
    },
    {
      "kind": "file",
      "file": {
        "name": "codebase.zip",
        "mimeType": "application/zip",
        "uri": "s3://uploads/codebase-abc123.zip"
      }
    }
  ]
}
```

#### 4. Part (Union Type)
**Purpose**: Individual content unit within a message

```typescript
// TextPart
{
  "kind": "text",
  "text": "Analyze this code",
  "metadata": {
    "language": "en"
  }
}

// FilePart (with bytes - base64 encoded)
{
  "kind": "file",
  "file": {
    "bytes": "SGVsbG8gV29ybGQ=",
    "name": "test.py",
    "mimeType": "text/x-python"
  }
}

// FilePart (with URI)
{
  "kind": "file",
  "file": {
    "uri": "s3://bucket/project/file.py",
    "name": "file.py",
    "mimeType": "text/x-python"
  }
}

// DataPart
{
  "kind": "data",
  "data": {
    "analysisType": "security",
    "depth": "comprehensive"
  },
  "metadata": {
    "schema": "analysis-config-v1"
  }
}
```

### JSON-RPC 2.0 Methods

All A2A communication uses standard JSON-RPC 2.0 format:

```json
{
  "jsonrpc": "2.0",
  "id": "req-123",
  "method": "a2a.createTask",
  "params": {
    "message": {...}
  }
}
```

#### Core A2A Methods

1. **a2a.createTask** - Create a new task
   ```json
   {
     "method": "a2a.createTask",
     "params": {
       "message": {
         "role": "user",
         "parts": [...]
       },
       "metadata": {}
     }
   }
   ```

2. **a2a.sendMessage** - Send message to existing task
   ```json
   {
     "method": "a2a.sendMessage",
     "params": {
       "taskId": "task-001",
       "message": {...}
     }
   }
   ```

3. **a2a.getTask** - Retrieve task status and results
   ```json
   {
     "method": "a2a.getTask",
     "params": {
       "taskId": "task-001"
     }
   }
   ```

4. **a2a.listTasks** - List all tasks
   ```json
   {
     "method": "a2a.listTasks",
     "params": {
       "status": "in_progress",
       "limit": 50
     }
   }
   ```

5. **a2a.cancelTask** - Cancel running task
   ```json
   {
     "method": "a2a.cancelTask",
     "params": {
       "taskId": "task-001"
     }
   }
   ```

### A2A Agent Project Structure

#### Server (Remote Agent) Structure
```
a2a-agent/
├── src/
│   ├── server/
│   │   ├── index.py              # Main entry, bootstraps A2A server
│   │   ├── routes.py             # Maps JSON-RPC methods to handlers
│   │   └── middleware.py         # Auth, logging, error handling
│   ├── agent/
│   │   ├── agent_card.py         # AgentCard definition
│   │   ├── capabilities.py       # Skills, modalities, auth
│   │   └── handlers/
│   │       ├── create_task.py    # a2a.createTask handler
│   │       ├── get_task.py       # a2a.getTask handler
│   │       ├── list_tasks.py     # a2a.listTasks handler
│   │       ├── send_message.py   # a2a.sendMessage handler
│   │       └── cancel_task.py    # a2a.cancelTask handler
│   ├── domain/
│   │   ├── task_manager.py       # Task lifecycle management
│   │   ├── message_processor.py  # Process incoming messages
│   │   ├── tools.py              # Agent-specific tools
│   │   └── llm_client.py         # LLM integration
│   ├── types/
│   │   ├── a2a_types.py          # TypeScript/JSON schemas
│   │   └── models.py             # Data models
│   └── storage/
│       ├── task_store.py         # Persist tasks
│       └── artifact_store.py     # Store artifacts
├── config/
│   └── a2a.config.yaml           # Server config
├── requirements.txt
└── README.md
```

#### Client (Initiating Agent) Structure
```
a2a-client/
├── src/
│   ├── config/
│   │   ├── agents.py             # Known remote AgentCard registry
│   │   └── settings.py           # Client configuration
│   ├── client/
│   │   ├── a2a_client.py         # JSON-RPC client wrapper
│   │   ├── agent_discovery.py    # Discover agents via AgentCard
│   │   └── workflows.py          # Multi-agent workflows
│   └── utils/
│       ├── auth.py               # Authentication helpers
│       └── retry.py              # Retry logic
└── requirements.txt
```

### Implementation Example (Python)

#### Agent Server Handler
```python
# src/agent/handlers/create_task.py
from typing import Dict, Any
from ..domain.task_manager import TaskManager
from ..types.a2a_types import Task, Message

class CreateTaskHandler:
    def __init__(self, task_manager: TaskManager):
        self.task_manager = task_manager

    async def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle a2a.createTask JSON-RPC method

        Params:
            message: Message object with parts
            metadata: Optional task metadata

        Returns:
            Task object
        """
        message = Message(**params['message'])
        metadata = params.get('metadata', {})

        # Create task
        task = await self.task_manager.create_task(
            initial_message=message,
            metadata=metadata
        )

        # Start processing asynchronously
        await self.task_manager.process_task_async(task.taskId)

        return task.dict()
```

#### JSON-RPC Router
```python
# src/server/routes.py
from fastapi import FastAPI, Request
from typing import Dict, Any

app = FastAPI()

# Handler registry
handlers = {
    'a2a.createTask': create_task_handler,
    'a2a.getTask': get_task_handler,
    'a2a.sendMessage': send_message_handler,
    'a2a.listTasks': list_tasks_handler,
    'a2a.cancelTask': cancel_task_handler
}

@app.post('/a2a')
async def a2a_endpoint(request: Request):
    """
    JSON-RPC 2.0 endpoint for A2A protocol
    """
    body = await request.json()

    # Validate JSON-RPC 2.0 format
    if body.get('jsonrpc') != '2.0':
        return {
            'jsonrpc': '2.0',
            'id': body.get('id'),
            'error': {
                'code': -32600,
                'message': 'Invalid Request'
            }
        }

    method = body.get('method')
    params = body.get('params', {})
    request_id = body.get('id')

    # Route to handler
    handler = handlers.get(method)
    if not handler:
        return {
            'jsonrpc': '2.0',
            'id': request_id,
            'error': {
                'code': -32601,
                'message': f'Method not found: {method}'
            }
        }

    try:
        result = await handler.handle(params)
        return {
            'jsonrpc': '2.0',
            'id': request_id,
            'result': result
        }
    except Exception as e:
        return {
            'jsonrpc': '2.0',
            'id': request_id,
            'error': {
                'code': -32603,
                'message': f'Internal error: {str(e)}'
            }
        }
```

#### A2A Client
```python
# src/client/a2a_client.py
import httpx
from typing import Dict, Any, Optional

class A2AClient:
    def __init__(self, agent_card_url: str, auth_token: Optional[str] = None):
        """
        Initialize A2A client for a remote agent

        Args:
            agent_card_url: URL to fetch AgentCard
            auth_token: Bearer token for authentication
        """
        self.agent_card = self._fetch_agent_card(agent_card_url)
        self.rpc_endpoint = self.agent_card['endpoints']['rpc']
        self.auth_token = auth_token
        self.request_counter = 0

    async def create_task(self, message: Dict[str, Any], metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Create a new task on remote agent"""
        return await self._call_method('a2a.createTask', {
            'message': message,
            'metadata': metadata or {}
        })

    async def get_task(self, task_id: str) -> Dict[str, Any]:
        """Get task status and results"""
        return await self._call_method('a2a.getTask', {
            'taskId': task_id
        })

    async def send_message(self, task_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """Send message to existing task"""
        return await self._call_method('a2a.sendMessage', {
            'taskId': task_id,
            'message': message
        })

    async def _call_method(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make JSON-RPC 2.0 call"""
        self.request_counter += 1

        payload = {
            'jsonrpc': '2.0',
            'id': f'req-{self.request_counter}',
            'method': method,
            'params': params
        }

        headers = {'Content-Type': 'application/json'}
        if self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.rpc_endpoint,
                json=payload,
                headers=headers
            )

            result = response.json()

            if 'error' in result:
                raise Exception(f"A2A Error: {result['error']}")

            return result['result']
```

### Task Lifecycle Flow

```
1. Client discovers agent via AgentCard
   ↓
2. Client calls a2a.createTask with initial message
   ↓
3. Remote agent creates Task, returns task ID
   ↓
4. Remote agent processes task asynchronously
   ↓
5. Client polls a2a.getTask for status updates
   ↓
6. Client can send additional messages via a2a.sendMessage
   ↓
7. Task completes with status="completed"
   ↓
8. Client retrieves artifacts from task
```

---

## Core Enhancement Features

### 1. Agent Discovery via Agent Cards (A2A Standard)

**Objective**: Implement self-discovery mechanism using **Google's A2A AgentCard** specification for dynamic agent discovery and capability negotiation.

#### A2A-Compliant Agent Card Structure

Each agent exposes a standardized AgentCard (JSON format) that describes its capabilities:

```json
{
  "agentId": "code-logic-agent",
  "name": "Code Logic Analysis Agent",
  "description": "Performs static code analysis, AST parsing, complexity metrics, and code quality assessment",
  "version": "1.0.0",
  "homepage": "https://agents.example.com/code-logic-agent",
  "endpoints": {
    "rpc": "https://agents.example.com/code-logic-agent/a2a",
    "health": "https://agents.example.com/code-logic-agent/health"
  },
  "capabilities": {
    "modalities": ["text", "file"],
    "skills": [
      "code_analysis",
      "static_analysis",
      "complexity_metrics",
      "ast_parsing",
      "code_quality"
    ],
    "languages": ["python", "javascript", "java", "go"],
    "fileTypes": [".py", ".js", ".java", ".go"]
  },
  "auth": {
    "scheme": "bearer",
    "required": true
  },
  "resources": {
    "memory": "2GB",
    "timeout": 300,
    "concurrentTasks": 5
  },
  "dependencies": {
    "tools": ["pylint", "eslint", "radon"],
    "agents": ["research-agent"]
  },
  "status": "active",
  "metadata": {
    "owner": "platform-team",
    "tier": "production",
    "region": "us-east-1"
  }
}
```

#### Implementation Plan

##### Week 1-2: AgentCard Service & Registry
**Goal**: Central registry for AgentCard management and discovery

```python
# src/discovery/agent_registry.py
from typing import Dict, List, Optional
from datetime import datetime

class AgentRegistry:
    """
    Central registry for A2A AgentCards
    Supports registration, discovery, and health monitoring
    """

    def __init__(self, storage_backend: str = 'redis'):
        self.storage = self._init_storage(storage_backend)

    async def register_agent(self, agent_card: Dict) -> bool:
        """
        Register or update an agent's AgentCard

        Args:
            agent_card: A2A-compliant AgentCard JSON

        Returns:
            Success status
        """
        # Validate against A2A schema
        self._validate_agent_card(agent_card)

        agent_id = agent_card['agentId']
        version = agent_card['version']

        # Store AgentCard with versioning
        key = f'agent:{agent_id}:v{version}'
        await self.storage.set(key, agent_card)

        # Update latest pointer
        await self.storage.set(f'agent:{agent_id}:latest', agent_card)

        # Add to searchable index
        await self._index_capabilities(agent_card)

        return True

    async def discover_agents(
        self,
        skill: Optional[str] = None,
        modality: Optional[str] = None,
        status: str = 'active'
    ) -> List[Dict]:
        """
        Discover agents by capability, skill, or modality

        Args:
            skill: Required skill (e.g., 'code_analysis')
            modality: Required modality (e.g., 'file')
            status: Agent status filter

        Returns:
            List of matching AgentCards
        """
        # Query index by skill/modality
        if skill:
            agent_ids = await self.storage.smembers(f'skill:{skill}')
        elif modality:
            agent_ids = await self.storage.smembers(f'modality:{modality}')
        else:
            agent_ids = await self.storage.smembers('agents:all')

        # Fetch AgentCards
        agents = []
        for agent_id in agent_ids:
            card = await self.storage.get(f'agent:{agent_id}:latest')
            if card and card.get('status') == status:
                agents.append(card)

        return agents

    async def get_agent_card(self, agent_id: str, version: str = 'latest') -> Optional[Dict]:
        """Retrieve specific AgentCard"""
        key = f'agent:{agent_id}:{version}'
        return await self.storage.get(key)

    async def health_check(self, agent_id: str) -> Dict:
        """
        Check agent health via health endpoint

        Returns:
            Health status and metrics
        """
        card = await self.get_agent_card(agent_id)
        if not card:
            return {'status': 'not_found'}

        health_url = card['endpoints'].get('health')
        if not health_url:
            return {'status': 'no_health_endpoint'}

        # Ping health endpoint
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(health_url, timeout=5.0)
                return {
                    'status': 'healthy' if response.status_code == 200 else 'unhealthy',
                    'latency_ms': response.elapsed.total_seconds() * 1000,
                    'details': response.json()
                }
        except Exception as e:
            return {'status': 'unreachable', 'error': str(e)}
```

##### Week 2-3: Capability Matching & Discovery
**Goal**: Smart routing based on agent capabilities

```python
# src/discovery/capability_matcher.py
from typing import Dict, List, Optional

class CapabilityMatcher:
    """
    Match task requirements to agent capabilities
    """

    def __init__(self, registry: AgentRegistry):
        self.registry = registry

    async def find_best_agent(
        self,
        required_skills: List[str],
        required_modalities: List[str] = None,
        file_type: Optional[str] = None,
        preferences: Dict = None
    ) -> Optional[Dict]:
        """
        Find best matching agent for task requirements

        Args:
            required_skills: List of required skills
            required_modalities: Required modalities (text/file/etc)
            file_type: File extension if file processing needed
            preferences: Scoring preferences (latency, cost, etc.)

        Returns:
            Best matching AgentCard or None
        """
        # Discover candidates
        candidates = []
        for skill in required_skills:
            agents = await self.registry.discover_agents(skill=skill)
            candidates.extend(agents)

        # Remove duplicates
        candidates = list({a['agentId']: a for a in candidates}.values())

        # Filter by modality
        if required_modalities:
            candidates = [
                a for a in candidates
                if all(m in a['capabilities']['modalities'] for m in required_modalities)
            ]

        # Filter by file type
        if file_type:
            candidates = [
                a for a in candidates
                if file_type in a['capabilities'].get('fileTypes', [])
            ]

        # Score and rank
        scored = await self._score_agents(candidates, required_skills, preferences)

        return scored[0] if scored else None

    async def _score_agents(
        self,
        candidates: List[Dict],
        required_skills: List[str],
        preferences: Dict
    ) -> List[Dict]:
        """
        Score agents based on capability match and preferences
        """
        scores = []

        for agent in candidates:
            score = 0

            # Skill match score
            agent_skills = set(agent['capabilities']['skills'])
            required = set(required_skills)
            skill_match = len(required & agent_skills) / len(required)
            score += skill_match * 100

            # Health check (bonus for healthy agents)
            health = await self.registry.health_check(agent['agentId'])
            if health['status'] == 'healthy':
                score += 20
                # Latency bonus (lower is better)
                if health.get('latency_ms', 1000) < 100:
                    score += 10

            # Resource availability
            if agent['status'] == 'active':
                score += 10

            scores.append({'agent': agent, 'score': score})

        # Sort by score (descending)
        scores.sort(key=lambda x: x['score'], reverse=True)

        return [s['agent'] for s in scores]
```

##### Week 3-4: A2A Client Wrapper
**Goal**: Easy-to-use client for agent-to-agent communication

```python
# src/discovery/a2a_orchestrator.py
from typing import Dict, Any, List
from .agent_registry import AgentRegistry
from .capability_matcher import CapabilityMatcher
from ..client.a2a_client import A2AClient

class A2AOrchestrator:
    """
    High-level orchestrator for multi-agent workflows
    Handles discovery, routing, and task coordination
    """

    def __init__(self, registry: AgentRegistry):
        self.registry = registry
        self.matcher = CapabilityMatcher(registry)
        self.clients = {}  # Cache of A2A clients

    async def execute_task(
        self,
        task_description: str,
        required_skills: List[str],
        input_data: Dict[str, Any],
        modalities: List[str] = ['text']
    ) -> Dict[str, Any]:
        """
        Execute task by automatically discovering and routing to best agent

        Workflow:
        1. Find best matching agent
        2. Create A2A client
        3. Create task on remote agent
        4. Poll for completion
        5. Return results
        """
        # Discover best agent
        agent_card = await self.matcher.find_best_agent(
            required_skills=required_skills,
            required_modalities=modalities
        )

        if not agent_card:
            raise Exception(f"No agent found with skills: {required_skills}")

        # Get or create A2A client
        client = await self._get_client(agent_card)

        # Create task with message
        message = {
            'role': 'user',
            'parts': [
                {'kind': 'text', 'text': task_description},
                {'kind': 'data', 'data': input_data}
            ]
        }

        task = await client.create_task(message)

        # Poll for completion
        result = await self._wait_for_completion(client, task['taskId'])

        return result

    async def _get_client(self, agent_card: Dict) -> A2AClient:
        """Get cached or create new A2A client for agent"""
        agent_id = agent_card['agentId']

        if agent_id not in self.clients:
            self.clients[agent_id] = A2AClient(
                rpc_endpoint=agent_card['endpoints']['rpc'],
                auth_token=self._get_auth_token(agent_id)
            )

        return self.clients[agent_id]

    async def _wait_for_completion(
        self,
        client: A2AClient,
        task_id: str,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """Poll task until completion"""
        import asyncio

        start_time = asyncio.get_event_loop().time()

        while True:
            task = await client.get_task(task_id)

            if task['status'] == 'completed':
                return task
            elif task['status'] == 'failed':
                raise Exception(f"Task failed: {task.get('error')}")

            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                await client.cancel_task(task_id)
                raise TimeoutError(f"Task timeout after {timeout}s")

            # Wait before polling again
            await asyncio.sleep(2)
```

#### AgentCard Hosting

Each agent exposes its AgentCard at a well-known endpoint:

```python
# src/agent/endpoints.py
from fastapi import FastAPI

app = FastAPI()

@app.get('/.well-known/agent-card')
async def get_agent_card():
    """
    Expose AgentCard at standard location
    """
    return {
        "agentId": "code-logic-agent",
        "name": "Code Logic Analysis Agent",
        "version": "1.0.0",
        # ... full AgentCard
    }

@app.get('/health')
async def health_check():
    """
    Health check endpoint
    """
    return {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'metrics': {
            'activeTasks': 3,
            'queuedTasks': 5,
            'avgResponseTime': 1.2
        }
    }
```

#### Key Components

```
discovery/
├── agent_registry.py          # Central AgentCard registry
├── capability_matcher.py      # Match tasks to agents
├── a2a_orchestrator.py        # High-level orchestration
├── health_monitor.py          # Monitor agent health
└── schemas/
    └── agent_card_schema.json # A2A AgentCard JSON schema

agents/
├── code_logic_agent/
│   ├── agent_card.json        # Static AgentCard
│   ├── server.py              # A2A JSON-RPC server
│   └── handlers/              # A2A method handlers
├── research_agent/
│   ├── agent_card.json
│   └── ...
└── test_run_agent/
    ├── agent_card.json
    └── ...
```

---

### 2. Cloud Deployment with Code Upload

**Objective**: Enable agents to upload their code as zip files to cloud storage and deploy dynamically.

#### Architecture
```
User/Agent → Upload ZIP → S3 Bucket → Lambda Trigger → ECS Deployment
                ↓
          Agent Registry Update
                ↓
          New Agent Available
```

#### Implementation Details

##### Phase 1: Code Upload Service
```python
# deployment/code_uploader.py
class CodeUploadService:
    """Handles code upload and validation"""

    def upload_agent_code(
        self,
        agent_name: str,
        code_zip: BinaryIO,
        metadata: dict
    ) -> str:
        """
        Upload agent code to S3 and return deployment URL

        Returns:
            S3 URL: s3://bucket/agents/{agent_name}/{version}/code.zip
        """
        # Validate zip structure
        # Scan for security issues
        # Upload to S3
        # Update agent registry with new version
        pass
```

##### Phase 2: Deployment Pipeline
- **Automated Deployment Steps**:
  1. Code uploaded to S3 bucket
  2. S3 event triggers Lambda function
  3. Lambda validates agent structure:
     - Check for agent.yaml
     - Validate dependencies
     - Security scan (no secrets, malicious code)
  4. Build Docker image from code
  5. Push to ECR (Elastic Container Registry)
  6. Update ECS task definition
  7. Deploy to ECS/Fargate
  8. Register agent in discovery service

##### Phase 3: Storage & Versioning
```yaml
# S3 bucket structure
agents-codebase/
├── code_logic_agent/
│   ├── v1.0.0/
│   │   ├── code.zip
│   │   ├── agent.yaml
│   │   └── metadata.json
│   └── v1.1.0/
│       ├── code.zip
│       ├── agent.yaml
│       └── metadata.json
└── test_run_agents/
    └── v1.0.0/
        ├── code.zip
        ├── agent.yaml
        └── metadata.json
```

#### Security Considerations
- **Code Scanning**:
  - Scan for hardcoded secrets
  - Check for malicious imports
  - Validate dependencies against known vulnerabilities
  - Enforce code signing for production deployments

- **Isolation**:
  - Each agent runs in isolated container
  - Network policies restrict inter-agent communication
  - Resource limits (CPU, memory, timeout)

#### Key Components
```
deployment/
├── upload_service/
│   ├── code_validator.py      # Validate uploaded code
│   ├── security_scanner.py    # Security checks
│   └── s3_uploader.py         # S3 upload handler
├── build_pipeline/
│   ├── docker_builder.py      # Build Docker images
│   ├── image_scanner.py       # Scan Docker images
│   └── registry_pusher.py     # Push to ECR
└── deployment/
    ├── ecs_deployer.py        # Deploy to ECS
    ├── version_manager.py     # Manage versions
    └── rollback_handler.py    # Handle rollbacks
```

---

### 3. Dynamic Test Execution Sandbox

**Objective**: Enable agents to create and execute tests on-the-go in isolated sandbox environments.

#### Architecture
```
Test Agent → Test Generator → Sandbox Creation → Test Execution → Result Collection
                                      ↓
                              Isolated Container
                                (E2E/Unit Tests)
```

#### Implementation Plan

##### Phase 1: Test Generation by Agents
```python
# testing/agentic_test_generator.py
class AgenticTestGenerator:
    """AI-powered test generation"""

    def generate_tests(
        self,
        code_context: str,
        test_type: str  # unit, integration, e2e
    ) -> List[TestCase]:
        """
        Use LLM to generate relevant tests based on code

        Returns:
            List of generated test cases
        """
        # Analyze code structure
        # Identify test scenarios
        # Generate test code using LLM
        # Validate test syntax
        pass
```

##### Phase 2: Sandbox Environment
```python
# testing/sandbox_manager.py
class SandboxManager:
    """Manages isolated test execution environments"""

    def create_sandbox(
        self,
        test_suite: TestSuite,
        dependencies: List[str]
    ) -> Sandbox:
        """
        Create isolated container for test execution

        Features:
        - Network isolation
        - Resource limits
        - Temporary file system
        - Auto-cleanup after execution
        """
        pass

    def execute_tests(
        self,
        sandbox: Sandbox,
        timeout: int = 300
    ) -> TestResults:
        """Execute tests with timeout and collect results"""
        pass
```

##### Phase 3: Test Orchestration
- **On-the-Go Test Creation**:
  - Code Analysis Agent identifies untested code paths
  - Requests Test Agent to generate tests
  - Test Agent creates tests dynamically
  - Tests executed in isolated sandbox
  - Results fed back to validation workflow

#### Sandbox Implementation Options

**Option A: Docker-based Sandboxes**
```yaml
# Docker container per test suite
test-sandbox:
  image: test-runner:latest
  environment:
    - TEST_TYPE=unit
    - TIMEOUT=300
  resources:
    limits:
      memory: 1GB
      cpus: 0.5
  network_mode: none  # Isolated
  volumes:
    - test-code:/app
  security_opt:
    - no-new-privileges:true
```

**Option B: Kubernetes Jobs**
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: test-execution-${TEST_ID}
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: test-runner
        image: test-runner:latest
        resources:
          limits:
            memory: "1Gi"
            cpu: "500m"
      ttlSecondsAfterFinished: 3600  # Auto-cleanup
```

#### Test Lifecycle
```
1. Test Request → Agent receives test requirement
2. Test Generation → LLM generates test code
3. Sandbox Creation → Isolated environment created
4. Dependency Setup → Install required packages
5. Test Execution → Run tests with timeout
6. Result Collection → Capture logs, coverage, results
7. Cleanup → Destroy sandbox
8. Report → Send results back to orchestrator
```

#### Key Components
```
testing/
├── generation/
│   ├── test_generator.py       # Generate tests using LLM
│   ├── test_validator.py       # Validate generated tests
│   └── test_templates/         # Test templates
├── sandbox/
│   ├── sandbox_manager.py      # Manage sandboxes
│   ├── docker_sandbox.py       # Docker-based sandbox
│   ├── k8s_sandbox.py          # Kubernetes-based sandbox
│   └── cleanup_service.py      # Auto-cleanup
└── execution/
    ├── test_runner.py          # Execute tests
    ├── result_collector.py     # Collect results
    └── coverage_analyzer.py    # Analyze coverage
```

---

### 4. Async & Long-Running Task Support

**Objective**: Handle long-running analysis tasks asynchronously with proper status tracking and resumption.

#### Architecture
```
Request → Task Queue → Worker Pool → Progress Updates → Result Store
             ↓                             ↓
        Task Status DB              Real-time Updates
```

#### Implementation Details

##### Phase 1: Task Queue System
```python
# async_tasks/task_queue.py
class AsyncTaskQueue:
    """Manages async task execution"""

    def submit_task(
        self,
        task_type: str,
        payload: dict,
        priority: int = 0
    ) -> str:
        """
        Submit task for async execution

        Returns:
            task_id for status tracking
        """
        task_id = generate_task_id()

        # Store task metadata
        task_metadata = {
            'task_id': task_id,
            'type': task_type,
            'status': 'queued',
            'created_at': timestamp(),
            'priority': priority
        }

        # Add to queue (Redis/SQS)
        self.queue.push(task_metadata, priority)

        return task_id

    def get_task_status(self, task_id: str) -> TaskStatus:
        """Get real-time task status"""
        pass
```

##### Phase 2: Worker Pool
```python
# async_tasks/worker_pool.py
class TaskWorker:
    """Worker that processes tasks from queue"""

    async def process_tasks(self):
        """Main worker loop"""
        while True:
            task = await self.queue.pop()

            try:
                # Update status
                await self.update_status(
                    task.id,
                    'in_progress',
                    progress=0
                )

                # Execute task
                result = await self.execute_task(task)

                # Store result
                await self.store_result(task.id, result)

                # Update status
                await self.update_status(
                    task.id,
                    'completed',
                    progress=100
                )

            except Exception as e:
                await self.handle_error(task, e)
```

##### Phase 3: Status Tracking & Progress Updates
```python
# async_tasks/status_tracker.py
class StatusTracker:
    """Track and broadcast task status"""

    def update_progress(
        self,
        task_id: str,
        progress: int,
        message: str,
        metadata: dict = None
    ):
        """
        Update task progress

        Broadcasts to:
        - WebSocket connections (real-time UI)
        - Database (persistent storage)
        - Webhooks (external notifications)
        """
        status_update = {
            'task_id': task_id,
            'progress': progress,
            'message': message,
            'timestamp': timestamp(),
            'metadata': metadata
        }

        # Update database
        self.db.update_task_status(task_id, status_update)

        # Broadcast via WebSocket
        self.websocket.broadcast(
            channel=f'task:{task_id}',
            data=status_update
        )

        # Trigger webhooks if configured
        self.webhook_manager.notify(task_id, status_update)
```

##### Phase 4: Result Storage & Retrieval
```python
# async_tasks/result_store.py
class ResultStore:
    """Store and retrieve task results"""

    def store_result(
        self,
        task_id: str,
        result: dict,
        ttl: int = 86400  # 24 hours
    ):
        """
        Store task result with TTL

        Large results stored in S3
        Metadata in database
        """
        if self._is_large_result(result):
            # Store in S3
            s3_url = self.s3.upload(
                f'results/{task_id}.json',
                result
            )

            # Store reference in DB
            self.db.store_task_result(task_id, {
                'type': 's3',
                'url': s3_url,
                'size': len(json.dumps(result)),
                'expires_at': timestamp() + ttl
            })
        else:
            # Store directly in database
            self.db.store_task_result(task_id, result)
```

#### Use Cases
- **Large Codebase Analysis**: 100K+ lines of code
- **Comprehensive Security Scans**: Multiple tool execution
- **Full Test Suite Runs**: Hundreds of tests
- **Multi-Repository Analysis**: Organization-wide scans

#### Task Types & Priority
```python
TASK_PRIORITIES = {
    'critical_security_scan': 0,      # Highest
    'production_validation': 1,
    'full_code_analysis': 2,
    'test_suite_execution': 3,
    'background_research': 4          # Lowest
}
```

#### Key Components
```
async_tasks/
├── queue/
│   ├── task_queue.py          # Task queue management
│   ├── priority_queue.py      # Priority-based queuing
│   └── dead_letter_queue.py   # Failed task handling
├── workers/
│   ├── worker_pool.py         # Worker pool management
│   ├── task_executor.py       # Execute individual tasks
│   └── worker_scaling.py      # Auto-scale workers
├── status/
│   ├── status_tracker.py      # Track task status
│   ├── progress_updater.py    # Update progress
│   └── notification_service.py # Notify on completion
└── storage/
    ├── result_store.py        # Store results
    ├── s3_storage.py          # S3 integration
    └── cache_manager.py       # Result caching
```

#### Integration with A2A Tasks

Our internal async task system maps directly to **A2A Task objects**, providing seamless interoperability:

##### Mapping Internal Tasks to A2A Tasks

```python
# async_tasks/a2a_adapter.py
class A2ATaskAdapter:
    """
    Adapter between internal task system and A2A Task format
    """

    def to_a2a_task(self, internal_task: InternalTask) -> Dict:
        """
        Convert internal task to A2A Task format

        Internal Task → A2A Task
        """
        return {
            "taskId": internal_task.task_id,
            "status": self._map_status(internal_task.status),
            "createdAt": internal_task.created_at.isoformat(),
            "updatedAt": internal_task.updated_at.isoformat(),
            "messages": [
                self._to_a2a_message(msg)
                for msg in internal_task.messages
            ],
            "artifacts": [
                {
                    "artifactId": a.id,
                    "name": a.name,
                    "mimeType": a.mime_type,
                    "uri": a.s3_url if a.size > 1_000_000 else None,
                    "bytes": a.content_base64 if a.size <= 1_000_000 else None
                }
                for a in internal_task.artifacts
            ],
            "metadata": internal_task.metadata
        }

    def _map_status(self, internal_status: str) -> str:
        """Map internal status to A2A status"""
        status_map = {
            'queued': 'pending',
            'in_progress': 'in_progress',
            'completed': 'completed',
            'failed': 'failed',
            'cancelled': 'cancelled'
        }
        return status_map.get(internal_status, 'pending')

    def _to_a2a_message(self, internal_message: InternalMessage) -> Dict:
        """Convert internal message to A2A Message"""
        return {
            "messageId": internal_message.id,
            "role": internal_message.role,
            "timestamp": internal_message.timestamp.isoformat(),
            "parts": self._to_a2a_parts(internal_message.content)
        }

    def _to_a2a_parts(self, content: Dict) -> List[Dict]:
        """Convert internal content to A2A Parts"""
        parts = []

        if 'text' in content:
            parts.append({
                "kind": "text",
                "text": content['text']
            })

        if 'files' in content:
            for file in content['files']:
                parts.append({
                    "kind": "file",
                    "file": {
                        "uri": file['uri'],
                        "name": file['name'],
                        "mimeType": file.get('mime_type', 'application/octet-stream')
                    }
                })

        if 'data' in content:
            parts.append({
                "kind": "data",
                "data": content['data']
            })

        return parts
```

##### A2A Handler Implementation

```python
# agent/handlers/create_task.py
class CreateTaskHandler:
    """
    A2A createTask handler that uses internal async task system
    """

    def __init__(
        self,
        task_queue: AsyncTaskQueue,
        task_adapter: A2ATaskAdapter
    ):
        self.task_queue = task_queue
        self.adapter = task_adapter

    async def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle a2a.createTask JSON-RPC method

        Flow:
        1. Validate A2A message format
        2. Submit to internal async task queue
        3. Return A2A Task object immediately
        4. Process task asynchronously in background
        """
        # Extract A2A message
        a2a_message = params['message']
        metadata = params.get('metadata', {})

        # Submit to internal task queue
        internal_task_id = await self.task_queue.submit_task(
            task_type='agent_task',
            payload={
                'message': a2a_message,
                'metadata': metadata
            },
            priority=metadata.get('priority', 5)
        )

        # Get initial task state
        internal_task = await self.task_queue.get_task(internal_task_id)

        # Convert to A2A format
        a2a_task = self.adapter.to_a2a_task(internal_task)

        return a2a_task
```

##### Benefits of Integration

1. **Native Async Support**: A2A Tasks naturally support long-running operations
2. **Progress Tracking**: Internal status updates automatically reflected in A2A Task status
3. **Artifact Management**: Large results stored in S3, exposed via A2A artifacts
4. **Interoperability**: External agents can create tasks via A2A, internal queue processes them
5. **Unified Interface**: Single task model for both internal and external communication

##### Task Lifecycle Comparison

```
A2A Task Lifecycle          Internal Task Lifecycle
───────────────────────────────────────────────────
pending                  →  queued
in_progress             →  in_progress
completed               →  completed
failed                  →  failed
cancelled               →  cancelled

Additional Internal States (mapped to in_progress):
- processing
- validating
- executing_tests
```

---

### 5. Code Understanding via Logic & Grep (Claude Code Style)

**Objective**: Implement code understanding using grep, AST parsing, and control flow analysis instead of semantic search embeddings.

#### Research Agent Enhancement

##### Phase 1: Grep-Based Code Search
```python
# research/code_search.py
class CodeSearchEngine:
    """Search code using grep patterns and regex"""

    def search_function_definitions(
        self,
        project_path: str,
        function_name: str
    ) -> List[CodeLocation]:
        """Find function definitions using grep"""
        patterns = [
            f"def {function_name}",           # Python
            f"function {function_name}",      # JavaScript
            f"func {function_name}",          # Go
            f"public.*{function_name}",       # Java
        ]

        results = []
        for pattern in patterns:
            matches = self.grep_search(project_path, pattern)
            results.extend(matches)

        return results

    def find_function_calls(
        self,
        project_path: str,
        function_name: str
    ) -> List[CodeLocation]:
        """Find where a function is called"""
        return self.grep_search(
            project_path,
            f"{function_name}\\("
        )
```

##### Phase 2: AST-Based Analysis
```python
# research/ast_analyzer.py
class ASTAnalyzer:
    """Analyze code structure using AST"""

    def extract_function_info(
        self,
        file_path: str,
        function_name: str
    ) -> FunctionInfo:
        """Extract function metadata using AST"""
        tree = ast.parse(open(file_path).read())

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name == function_name:
                    return FunctionInfo(
                        name=node.name,
                        args=self._extract_args(node),
                        returns=self._extract_return_type(node),
                        docstring=ast.get_docstring(node),
                        calls=self._extract_function_calls(node),
                        variables=self._extract_variables(node)
                    )

    def build_call_graph(
        self,
        project_path: str
    ) -> CallGraph:
        """Build function call graph"""
        # Parse all files
        # Extract function definitions
        # Find function calls
        # Build directed graph
        pass
```

##### Phase 3: Control Flow Analysis
```python
# research/control_flow_analyzer.py
class ControlFlowAnalyzer:
    """Analyze control flow and dependencies"""

    def trace_variable_flow(
        self,
        file_path: str,
        variable_name: str
    ) -> VariableFlowGraph:
        """Trace how a variable flows through code"""
        # Find variable definition
        # Track assignments
        # Find usages
        # Identify transformations
        pass

    def find_dependencies(
        self,
        file_path: str
    ) -> List[Dependency]:
        """Find all dependencies of a file"""
        # Extract import statements
        # Identify external dependencies
        # Find internal module dependencies
        # Detect circular dependencies
        pass
```

##### Phase 4: RESEARCH.md Generation
```python
# research/research_generator.py
class ResearchDocGenerator:
    """Generate RESEARCH.md documentation"""

    def generate_research_doc(
        self,
        project_path: str,
        research_query: str
    ) -> str:
        """
        Generate comprehensive research document

        Steps:
        1. Grep-based initial discovery
        2. AST-based detailed analysis
        3. Control flow tracing
        4. Dependency mapping
        5. Generate structured markdown
        """
        findings = {
            'overview': self._analyze_project_structure(project_path),
            'key_files': self._identify_key_files(project_path),
            'functions': self._analyze_functions(project_path, research_query),
            'dependencies': self._map_dependencies(project_path),
            'call_graphs': self._build_call_graphs(project_path),
            'patterns': self._identify_patterns(project_path)
        }

        return self._format_as_markdown(findings)

    def _format_as_markdown(self, findings: dict) -> str:
        """Format findings as structured markdown"""
        template = """
# Code Research Report

## Project Overview
{overview}

## Key Files Identified
{key_files}

## Function Analysis
{functions}

## Dependency Map
{dependencies}

## Call Graphs
{call_graphs}

## Patterns & Observations
{patterns}

## Recommendations
{recommendations}
"""
        return template.format(**findings)
```

#### Research Workflow
```
User Query → Research Agent
              ↓
    1. Grep-based file discovery
    2. AST parsing for structure
    3. Control flow analysis
    4. Dependency mapping
    5. Call graph generation
              ↓
    Generate RESEARCH.md
              ↓
    Store in project context
```

#### Example RESEARCH.md Structure
```markdown
# RESEARCH.md - Authentication System

## Overview
- Located in: `src/auth/`
- Primary entry point: `src/auth/login.py:authenticate()`
- Dependencies: `jwt`, `bcrypt`, `redis`

## Key Files
1. **src/auth/login.py**
   - `authenticate(username, password)` - Main authentication function
   - `validate_token(token)` - JWT validation
   - Called by: 15 endpoints

2. **src/auth/middleware.py**
   - `auth_required` decorator
   - Used across 23 routes

## Function Call Graph
```
authenticate()
├── validate_credentials()
│   ├── hash_password()
│   └── compare_hash()
├── generate_token()
│   └── jwt.encode()
└── store_session()
    └── redis.setex()
```

## Dependencies
- External: jwt, bcrypt, redis
- Internal: src.models.user, src.utils.crypto
- Circular dependencies: None

## Security Observations
- Password hashing: bcrypt (rounds=12)
- Token expiry: 1 hour
- Session storage: Redis with TTL
- Potential issue: No rate limiting on line 45
```

#### Key Components
```
research/
├── search/
│   ├── code_search.py         # Grep-based search
│   ├── pattern_matcher.py     # Pattern matching
│   └── file_indexer.py        # Index project files
├── analysis/
│   ├── ast_analyzer.py        # AST parsing
│   ├── control_flow.py        # Control flow analysis
│   ├── dependency_mapper.py   # Map dependencies
│   └── call_graph_builder.py  # Build call graphs
├── generation/
│   ├── research_generator.py  # Generate RESEARCH.md
│   ├── markdown_formatter.py  # Format as markdown
│   └── templates/             # Report templates
└── cache/
    ├── analysis_cache.py      # Cache analysis results
    └── index_cache.py         # Cache file indexes
```

---

## Implementation Timeline

### Phase 1: Foundation (Weeks 1-4)
- [ ] Agent Card specification and parser
- [ ] Agent registry and discovery service
- [ ] Basic A2A protocol implementation
- [ ] Code upload service to S3

### Phase 2: Core Features (Weeks 5-8)
- [ ] Cloud deployment pipeline (S3 → Lambda → ECS)
- [ ] Async task queue and worker pool
- [ ] Test sandbox environment
- [ ] Grep-based code search engine

### Phase 3: Advanced Features (Weeks 9-12)
- [ ] Dynamic test generation by agents
- [ ] AST-based code analysis
- [ ] RESEARCH.md generation skill
- [ ] Full A2A protocol with auth

### Phase 4: Integration & Testing (Weeks 13-16)
- [ ] End-to-end workflow testing
- [ ] Performance optimization
- [ ] Security hardening
- [ ] Documentation and examples

---

## Architecture Diagram (A2A Protocol)

```
┌─────────────────────────────────────────────────────────────────┐
│                  A2A Agent Registry & Discovery                  │
│           (AgentCard Storage + Capability Matching)              │
│                                                                  │
│  - Agent registration via AgentCard                              │
│  - Skill-based discovery                                         │
│  - Health monitoring                                             │
│  - Version management                                            │
└─────────────────────────────────────────────────────────────────┘
                              ↑
                              │ GET /.well-known/agent-card
                              │ Register/Discover
                              │
┌──────────────┬──────────────┴────────────────┬─────────────────┐
│              │                                │                 │
▼              ▼                                ▼                 ▼
┌──────────────────┐   ┌──────────────────┐   ┌────────────────┐   ┌─────────────────┐
│  Orchestrator    │   │  Code Logic      │   │  Research      │   │  Test Run       │
│  Agent           │   │  Agent           │   │  Agent         │   │  Agent          │
│  (Client)        │   │  (A2A Server)    │   │  (A2A Server)  │   │  (A2A Server)   │
│                  │   │                  │   │                │   │                 │
│ - Discovers      │   │ Exposes:         │   │ Exposes:       │   │ Exposes:        │
│   agents         │   │ /.well-known/    │   │ /.well-known/  │   │ /.well-known/   │
│ - Routes tasks   │   │   agent-card     │   │   agent-card   │   │   agent-card    │
│ - Coordinates    │   │ /a2a (JSON-RPC)  │   │ /a2a (JSON-RPC)│   │ /a2a (JSON-RPC) │
│   workflow       │   │                  │   │                │   │                 │
└──────────────────┘   │ Methods:         │   │ Methods:       │   │ Methods:        │
         │             │ - createTask     │   │ - createTask   │   │ - createTask    │
         │             │ - getTask        │   │ - getTask      │   │ - getTask       │
         │             │ - sendMessage    │   │ - sendMessage  │   │ - sendMessage   │
         │             │ - listTasks      │   │ - listTasks    │   │ - listTasks     │
         │             │ - cancelTask     │   │ - cancelTask   │   │ - cancelTask    │
         │             └──────────────────┘   └────────────────┘   └─────────────────┘
         │                      │                      │                     │
         └──────────────────────┴──────────────────────┴─────────────────────┘
                                │
                    JSON-RPC 2.0 over HTTPS
                      (A2A Protocol)
                                │
         ┌──────────────────────┴─────────────────────────┐
         │                                                 │
         ▼                                                 ▼
┌────────────────────┐                         ┌────────────────────┐
│   A2A Task Store   │                         │   Artifact Store   │
│   (PostgreSQL)     │                         │   (S3 + CDN)       │
│                    │                         │                    │
│ - Task metadata    │                         │ - Files (code zips)│
│ - Messages         │                         │ - Reports (JSON)   │
│ - Status tracking  │                         │ - Test results     │
│ - Lifecycle mgmt   │                         │ - Logs/artifacts   │
└────────────────────┘                         └────────────────────┘
         │                                                 │
         └─────────────────┬───────────────────────────────┘
                           │
                           ▼
         ┌─────────────────────────────────────────┐
         │     Background Task Workers              │
         │                                          │
         │  ┌──────────────┐  ┌──────────────┐     │
         │  │  Task        │  │  Sandbox     │     │
         │  │  Executor    │  │  Manager     │     │
         │  │  (Redis MQ)  │  │  (Docker/K8s)│     │
         │  └──────────────┘  └──────────────┘     │
         └─────────────────────────────────────────┘


Communication Flow Example:
──────────────────────────

1. Orchestrator discovers "code-logic-agent" via registry
   GET https://registry.example.com/agents/code-logic-agent/card

2. Orchestrator creates task on code-logic-agent
   POST https://code-logic-agent.example.com/a2a
   {
     "jsonrpc": "2.0",
     "method": "a2a.createTask",
     "params": {
       "message": {
         "role": "user",
         "parts": [{"kind": "text", "text": "Analyze security"}]
       }
     }
   }

3. Code-logic-agent returns Task ID
   {
     "jsonrpc": "2.0",
     "result": {
       "taskId": "task-abc123",
       "status": "pending"
     }
   }

4. Orchestrator polls for status
   POST https://code-logic-agent.example.com/a2a
   {
     "jsonrpc": "2.0",
     "method": "a2a.getTask",
     "params": {"taskId": "task-abc123"}
   }

5. Task completes with artifacts
   {
     "taskId": "task-abc123",
     "status": "completed",
     "artifacts": [
       {"uri": "s3://results/report.json"}
     ]
   }
```

---

## Success Metrics

### Phase 1 (Foundation)
- [ ] 3+ agents discoverable via Agent Cards
- [ ] Agent code deployable via S3 upload
- [ ] Basic A2A message exchange working

### Phase 2 (Core Features)
- [ ] Async tasks processing <5min latency
- [ ] Test sandboxes create/destroy <30sec
- [ ] Code search finds 95%+ relevant results

### Phase 3 (Advanced)
- [ ] Agents generate valid tests 80%+ success
- [ ] RESEARCH.md generated in <2min
- [ ] Full A2A protocol compliant

### Phase 4 (Production Ready)
- [ ] End-to-end analysis <15min for 50K LOC
- [ ] 99% uptime for core services
- [ ] Security scan coverage 95%+

---

## Risk Mitigation

### Technical Risks
1. **Agent Discovery Complexity**
   - Mitigation: Start with centralized registry, move to distributed later
   - Fallback: Hard-coded agent endpoints for critical agents

2. **Sandbox Security**
   - Mitigation: Use proven container isolation (gVisor, Kata Containers)
   - Fallback: VM-based sandboxes for higher security needs

3. **Async Task Reliability**
   - Mitigation: Implement dead-letter queues and retry logic
   - Fallback: Synchronous processing for critical tasks

### Operational Risks
1. **Cloud Cost Overruns**
   - Mitigation: Set AWS budget alerts and resource limits
   - Monitoring: Track costs per agent and per analysis

2. **Performance Bottlenecks**
   - Mitigation: Load testing at each phase
   - Optimization: Caching, parallel processing, resource tuning

---

## Next Steps

1. **Immediate (This Week)**
   - Define Agent Card schema (JSON Schema)
   - Setup S3 bucket and IAM roles
   - Create basic agent registry service

2. **Short Term (Next 2 Weeks)**
   - Implement code upload and validation
   - Build task queue with Redis/SQS
   - Create test sandbox prototype

3. **Medium Term (Next Month)**
   - Full deployment pipeline
   - AST-based code analysis
   - Dynamic test generation

4. **Long Term (Next Quarter)**
   - Production deployment
   - Advanced A2A features
   - Full observability and monitoring

---

## References

### A2A Protocol & Standards
- [A2A Protocol Official Specification (v0.2.0)](https://a2a-protocol.org/v0.2.0/specification/)
- [A2A Protocol Latest](https://a2a-protocol.org/latest/)
- [Google A2A Blog Post - A New Era of Agent Interoperability](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/)
- [A2A GitHub Repository](https://github.com/a2aproject/A2A)
- [A2A Protocol Explained - HuggingFace](https://huggingface.co/blog/1bo/a2a-protocol-explained)
- [A2A Protocol Specification - Python Implementation](https://dev.to/czmilo/a2a-protocol-specification-python-3i2f)
- [DeepLearning.AI - A2A Agent2Agent Protocol Course](https://www.deeplearning.ai/short-courses/a2a-the-agent2agent-protocol/)

### Google Agent Development
- [Google Agent Development Kit (ADK) Documentation](https://google.github.io/adk-docs/)
- [Building Multi-Agents with Google AI Services - TietoEvry](https://www.tietoevry.com/en/blog/2025/07/building-multi-agents-google-ai-services/)
- [Agent Development Kit - InfoQ News](https://www.infoq.com/news/2025/04/agent-development-kit/)
- [Building AI Agents with Gemini 3 and Open Source Frameworks](https://developers.googleblog.com/building-ai-agents-with-google-gemini-3-and-open-source-frameworks/)
- [Intro to A2A - Purchasing Concierge Codelab](https://codelabs.developers.google.com/intro-a2a-purchasing-concierge)

### Model Context Protocol (MCP)
- [Model Context Protocol Official Site](https://modelcontextprotocol.io/)
- [Google's A2A and Anthropic's MCP - Gravitee Blog](https://www.gravitee.io/blog/googles-agent-to-agent-a2a-and-anthropics-model-context-protocol-mcp)

### Infrastructure & Deployment
- [AWS ECS Best Practices Guide](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/)
- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [Vertex AI Multi-System Agents](https://cloud.google.com/blog/products/ai-machine-learning/build-and-manage-multi-system-agents-with-vertex-ai)
- [Agent2Agent Protocol Upgrade - Google Cloud](https://cloud.google.com/blog/products/ai-machine-learning/agent2agent-protocol-is-getting-an-upgrade)

### JSON-RPC Specification
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)

### Related Technologies
- [OpenTelemetry - Distributed Tracing](https://opentelemetry.io/)
- [Redis Message Queue](https://redis.io/docs/manual/patterns/pub-sub/)
- [PostgreSQL JSON Support](https://www.postgresql.org/docs/current/datatype-json.html)
