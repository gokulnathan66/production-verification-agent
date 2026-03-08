# Redis Storage Implementation Plan for A2A Agents

## Overview
Migrate from in-memory storage (`TASKS = {}`) to Redis-backed persistent storage for all 5 agents.

## Current State
- All agents use `TASKS = {}` (volatile, in-memory)
- Orchestrator uses `AGENT_REGISTRY = {}` (volatile)
- No persistence, no shared state
- Data lost on restart

## Target State
- Redis for task storage (persistent, shared)
- PostgreSQL for historical data (optional Phase 2)
- Shared state across agent instances
- Task history and audit trail

---

## Phase 1: Redis Integration (Immediate)

### 1.1 Redis Schema Design

```
# Task Storage
task:{agent_id}:{task_id}          → JSON (task data)
task:{agent_id}:list               → LIST (task IDs, newest first)
task:{agent_id}:count              → STRING (total tasks)

# Agent Registry (Orchestrator)
agent:registry:{agent_id}          → JSON (agent card + status)
agent:registry:list                → SET (all agent IDs)
agent:heartbeat:{agent_id}         → STRING (timestamp, TTL 30s)

# Session State
session:{session_id}:agents        → HASH (agent_id → status JSON)
session:{session_id}:findings      → LIST (findings JSON)
session:{session_id}:metadata      → JSON (session info)

# Task Indexes
task:status:{status}               → SET (task IDs by status)
task:recent                        → ZSET (task_id → timestamp)
```

### 1.2 TTL Strategy

| Key Pattern | TTL | Reason |
|-------------|-----|--------|
| `task:{agent}:{id}` | 24 hours | Keep recent tasks |
| `agent:heartbeat:{id}` | 30 seconds | Detect offline agents |
| `session:{id}:*` | 1 hour | Active sessions only |
| `agent:registry:{id}` | None | Persistent registry |

### 1.3 Shared Redis Client

```python
# src/shared/redis_client.py
import redis.asyncio as redis
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import os

class RedisTaskStore:
    """Shared Redis client for all agents"""
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.client: Optional[redis.Redis] = None
    
    async def connect(self):
        """Initialize Redis connection"""
        self.client = await redis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
    
    async def close(self):
        """Close Redis connection"""
        if self.client:
            await self.client.close()
    
    # Task Operations
    async def save_task(self, agent_id: str, task: Dict[str, Any], ttl: int = 86400):
        """Save task to Redis"""
        task_id = task["taskId"]
        key = f"task:{agent_id}:{task_id}"
        
        # Save task data
        await self.client.setex(key, ttl, json.dumps(task))
        
        # Add to agent's task list
        await self.client.lpush(f"task:{agent_id}:list", task_id)
        await self.client.ltrim(f"task:{agent_id}:list", 0, 999)  # Keep last 1000
        
        # Add to status index
        status = task.get("status", "unknown")
        await self.client.sadd(f"task:status:{status}", f"{agent_id}:{task_id}")
        
        # Add to recent tasks (sorted by timestamp)
        timestamp = datetime.utcnow().timestamp()
        await self.client.zadd("task:recent", {f"{agent_id}:{task_id}": timestamp})
        
        # Increment counter
        await self.client.incr(f"task:{agent_id}:count")
    
    async def get_task(self, agent_id: str, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve task from Redis"""
        key = f"task:{agent_id}:{task_id}"
        data = await self.client.get(key)
        return json.loads(data) if data else None
    
    async def list_tasks(self, agent_id: str, status: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """List tasks for an agent"""
        if status:
            # Get by status
            task_keys = await self.client.smembers(f"task:status:{status}")
            task_keys = [k for k in task_keys if k.startswith(f"{agent_id}:")]
        else:
            # Get recent tasks
            task_ids = await self.client.lrange(f"task:{agent_id}:list", 0, limit - 1)
            task_keys = [f"{agent_id}:{tid}" for tid in task_ids]
        
        tasks = []
        for key in task_keys[:limit]:
            parts = key.split(":", 1)
            if len(parts) == 2:
                task = await self.get_task(parts[0], parts[1])
                if task:
                    tasks.append(task)
        
        return tasks
    
    async def update_task_status(self, agent_id: str, task_id: str, status: str):
        """Update task status"""
        task = await self.get_task(agent_id, task_id)
        if task:
            old_status = task.get("status")
            task["status"] = status
            task["updatedAt"] = datetime.utcnow().isoformat()
            
            # Update task
            await self.save_task(agent_id, task)
            
            # Update status indexes
            if old_status:
                await self.client.srem(f"task:status:{old_status}", f"{agent_id}:{task_id}")
            await self.client.sadd(f"task:status:{status}", f"{agent_id}:{task_id}")
    
    # Agent Registry Operations (Orchestrator)
    async def register_agent(self, agent_id: str, agent_card: Dict[str, Any]):
        """Register agent in registry"""
        await self.client.set(f"agent:registry:{agent_id}", json.dumps(agent_card))
        await self.client.sadd("agent:registry:list", agent_id)
        await self.update_agent_heartbeat(agent_id)
    
    async def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent from registry"""
        data = await self.client.get(f"agent:registry:{agent_id}")
        return json.loads(data) if data else None
    
    async def list_agents(self) -> List[Dict[str, Any]]:
        """List all registered agents"""
        agent_ids = await self.client.smembers("agent:registry:list")
        agents = []
        for agent_id in agent_ids:
            agent = await self.get_agent(agent_id)
            if agent:
                # Check if online
                heartbeat = await self.client.get(f"agent:heartbeat:{agent_id}")
                agent["online"] = heartbeat is not None
                agents.append(agent)
        return agents
    
    async def update_agent_heartbeat(self, agent_id: str):
        """Update agent heartbeat (30s TTL)"""
        await self.client.setex(
            f"agent:heartbeat:{agent_id}",
            30,
            datetime.utcnow().isoformat()
        )
    
    async def is_agent_online(self, agent_id: str) -> bool:
        """Check if agent is online"""
        return await self.client.exists(f"agent:heartbeat:{agent_id}") > 0
    
    # Session Operations (Orchestrator workflows)
    async def create_session(self, session_id: str, metadata: Dict[str, Any]):
        """Create analysis session"""
        await self.client.setex(
            f"session:{session_id}:metadata",
            3600,
            json.dumps(metadata)
        )
    
    async def update_session_agent_status(self, session_id: str, agent_id: str, status: Dict[str, Any]):
        """Update agent status in session"""
        await self.client.hset(
            f"session:{session_id}:agents",
            agent_id,
            json.dumps(status)
        )
    
    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get all agent statuses in session"""
        agents = await self.client.hgetall(f"session:{session_id}:agents")
        return {k: json.loads(v) for k, v in agents.items()}
    
    async def add_session_finding(self, session_id: str, finding: Dict[str, Any]):
        """Add finding to session"""
        await self.client.lpush(
            f"session:{session_id}:findings",
            json.dumps(finding)
        )
    
    async def get_session_findings(self, session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get session findings"""
        findings = await self.client.lrange(f"session:{session_id}:findings", 0, limit - 1)
        return [json.loads(f) for f in findings]
    
    # Cleanup Operations
    async def cleanup_old_tasks(self, max_age_hours: int = 24):
        """Remove tasks older than max_age_hours"""
        cutoff = datetime.utcnow().timestamp() - (max_age_hours * 3600)
        old_tasks = await self.client.zrangebyscore("task:recent", 0, cutoff)
        
        for task_key in old_tasks:
            parts = task_key.split(":", 1)
            if len(parts) == 2:
                agent_id, task_id = parts
                await self.client.delete(f"task:{agent_id}:{task_id}")
                await self.client.zrem("task:recent", task_key)
```

---

## Phase 1 Implementation Steps

### Step 1: Update docker-compose.yml

```yaml
# src/docker-compose.yml
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    container_name: a2a-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  code-logic-agent:
    build: ./code_logic_agent
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis

  research-agent:
    build: ./research_agent
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis

  test-run-agent:
    build: ./test_run_agents
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis

  validation-agent:
    build: ./validation_agent
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis

  orchestrator-agent:
    build: ./orchestorator_agent
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis

volumes:
  redis_data:
```

### Step 2: Update Agent Code Pattern

```python
# Example: src/code_logic_agent/agent.py
from shared.redis_client import RedisTaskStore

# Replace: TASKS = {}
redis_store = RedisTaskStore()

@app.on_event("startup")
async def startup():
    await redis_store.connect()

@app.on_event("shutdown")
async def shutdown():
    await redis_store.close()

async def create_task(params: Dict[str, Any]) -> Dict[str, Any]:
    task_id = str(uuid.uuid4())
    # ... build task ...
    
    # Replace: TASKS[task_id] = task
    await redis_store.save_task(AGENT_ID, task)
    
    return task

async def get_task(params: Dict[str, Any]) -> Dict[str, Any]:
    task_id = params.get("taskId")
    
    # Replace: if task_id not in TASKS
    task = await redis_store.get_task(AGENT_ID, task_id)
    if not task:
        raise ValueError(f"Task not found: {task_id}")
    
    return task

async def list_tasks(params: Dict[str, Any]) -> Dict[str, Any]:
    status_filter = params.get("status")
    limit = params.get("limit", 100)
    
    # Replace: tasks = list(TASKS.values())
    tasks = await redis_store.list_tasks(AGENT_ID, status_filter, limit)
    
    return {"tasks": tasks, "total": len(tasks)}
```

### Step 3: Update Orchestrator

```python
# src/orchestorator_agent/agent.py
from shared.redis_client import RedisTaskStore

# Replace: AGENT_REGISTRY = {}
redis_store = RedisTaskStore()

async def discover_agents(self) -> Dict[str, Any]:
    """Discover agents from Redis registry"""
    discovered = {}
    
    for agent_id, base_url in self.known_agents.items():
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{base_url}/.well-known/agent-card", timeout=5.0)
                if response.status_code == 200:
                    card = response.json()
                    discovered[agent_id] = {
                        "card": card,
                        "baseUrl": base_url,
                        "status": "online"
                    }
                    # Save to Redis
                    await redis_store.register_agent(agent_id, discovered[agent_id])
        except:
            discovered[agent_id] = {"status": "offline", "baseUrl": base_url}
    
    return discovered

async def run_full_analysis_workflow(self, code: str, language: str = "python") -> Dict[str, Any]:
    """Run workflow with session tracking"""
    session_id = str(uuid.uuid4())
    
    # Create session
    await redis_store.create_session(session_id, {
        "language": language,
        "started_at": datetime.utcnow().isoformat()
    })
    
    results = {}
    
    # Run agents and track status
    for agent_id in ["code-logic-agent", "research-agent", "validation-agent", "test-run-agent"]:
        await redis_store.update_session_agent_status(session_id, agent_id, {
            "status": "running",
            "started_at": datetime.utcnow().isoformat()
        })
        
        try:
            result = await self.call_agent(agent_id, message_parts, {"session_id": session_id})
            results[agent_id] = result
            
            await redis_store.update_session_agent_status(session_id, agent_id, {
                "status": "completed",
                "completed_at": datetime.utcnow().isoformat()
            })
        except Exception as e:
            await redis_store.update_session_agent_status(session_id, agent_id, {
                "status": "failed",
                "error": str(e)
            })
    
    return results
```

---

## Phase 2: PostgreSQL Integration (Optional)

### 2.1 Add PostgreSQL for Historical Data

```yaml
# docker-compose.yml
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: a2a_history
      POSTGRES_USER: a2a
      POSTGRES_PASSWORD: a2a_local
    ports:
      - "5432:5432"
    volumes:
      - pg_data:/var/lib/postgresql/data
      - ./schema:/docker-entrypoint-initdb.d

volumes:
  redis_data:
  pg_data:
```

### 2.2 Schema (Minimal)

```sql
-- schema/init.sql
CREATE TABLE task_history (
    id SERIAL PRIMARY KEY,
    agent_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    status TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    task_data JSONB,
    INDEX idx_agent_task (agent_id, task_id)
);

CREATE TABLE agent_metrics (
    agent_id TEXT PRIMARY KEY,
    total_tasks INTEGER DEFAULT 0,
    successful_tasks INTEGER DEFAULT 0,
    failed_tasks INTEGER DEFAULT 0,
    avg_duration_ms INTEGER,
    last_active TIMESTAMP
);
```

---

## Migration Strategy

### Backward Compatibility

```python
# Support both in-memory and Redis
class TaskStore:
    def __init__(self, use_redis: bool = True):
        self.use_redis = use_redis
        if use_redis:
            self.redis = RedisTaskStore()
        else:
            self.memory = {}
    
    async def save_task(self, agent_id: str, task: Dict):
        if self.use_redis:
            await self.redis.save_task(agent_id, task)
        else:
            self.memory[task["taskId"]] = task
```

### Rollout Plan

1. **Week 1**: Deploy Redis, test with one agent
2. **Week 2**: Migrate all agents to Redis
3. **Week 3**: Add PostgreSQL for history
4. **Week 4**: Remove in-memory fallback

---

## Testing

```python
# tests/test_redis_store.py
import pytest
from shared.redis_client import RedisTaskStore

@pytest.mark.asyncio
async def test_save_and_get_task():
    store = RedisTaskStore("redis://localhost:6379")
    await store.connect()
    
    task = {
        "taskId": "test-123",
        "status": "completed",
        "data": {"result": "success"}
    }
    
    await store.save_task("test-agent", task)
    retrieved = await store.get_task("test-agent", "test-123")
    
    assert retrieved["taskId"] == "test-123"
    assert retrieved["status"] == "completed"
    
    await store.close()
```

---

## Benefits

✅ **Persistence** - Tasks survive restarts
✅ **Shared State** - Multiple agent instances can share data
✅ **Scalability** - Horizontal scaling with shared Redis
✅ **Monitoring** - Real-time agent status tracking
✅ **History** - Task audit trail (with PostgreSQL)
✅ **Performance** - Fast in-memory operations

## Effort Estimate

- **Redis Integration**: 4-6 hours
- **Agent Migration**: 2 hours per agent (10 hours total)
- **Testing**: 4 hours
- **PostgreSQL (optional)**: 6 hours

**Total**: ~20-26 hours
