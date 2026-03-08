# Communication Bus Architecture

## Overview
The Communication Bus enables agent-to-agent messaging, orchestrator coordination, and event-driven processing across the Production Verification Agent system.

## Recommended Technology by Stage

### Phase 1 (Local): Redis Streams
**Why Redis Streams:**
- Already in stack (shared with KB)
- Persistent message log
- Consumer groups for parallel processing
- Message acknowledgment
- Replay capability
- Easy to monitor with RedisInsight

### Phase 2 (Cloud): AWS SQS + SNS
**Why SQS:**
- Managed message queue service
- Guaranteed delivery
- Dead letter queue support
- Scales automatically

### Phase 3 (Production): SQS + SNS + EventBridge
**Add EventBridge:**
- Complex event routing
- Cross-service integration
- Event replay capability

---

## Message Format (Shared Across All Stages)

### Standard Message Schema
```json
{
    "message_id": "msg-uuid-12345",
    "agent_id": "security-agent-01",
    "timestamp": "2024-01-15T10:30:00Z",
    "type": "finding",
    "severity": "CRITICAL",
    "finding_type": "vulnerability",
    "details": {
        "file": "src/auth/login.py",
        "line": 45,
        "rule": "B105",
        "description": "Hardcoded password detected",
        "cwe": "CWE-259"
    },
    "requires_coordination": ["iac-agent", "remediation-agent"],
    "blocking": true,
    "correlation_id": "session-abc-123",
    "reply_to": "orchestrator"
}
```

### Message Types
| Type | Description | Producers | Consumers |
|------|-------------|-----------|-----------|
| `task` | Work assignment | Orchestrator | Agents |
| `finding` | Analysis result | Agents | Orchestrator, KB |
| `status` | Progress update | Agents | Orchestrator, Dashboard |
| `coordination` | Cross-agent request | Agents | Other Agents |
| `completion` | Task finished | Agents | Orchestrator |
| `error` | Failure notification | Agents | Orchestrator |

---

## Phase 1: Redis Streams Implementation

### Stream Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                      Redis Streams                           │
├─────────────────────────────────────────────────────────────┤
│  Streams:                    Consumer Groups:                │
│  ┌─────────────────┐        ┌─────────────────────────┐    │
│  │ pva:tasks       │───────▶│ agents-group            │    │
│  │ pva:findings    │───────▶│ orchestrator-group      │    │
│  │ pva:status      │───────▶│ dashboard-group         │    │
│  │ pva:coordination│───────▶│ coordination-group      │    │
│  └─────────────────┘        └─────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Stream Definitions
```python
# comm/streams.py
class Streams:
    TASKS = "pva:tasks"              # Orchestrator → Agents
    FINDINGS = "pva:findings"        # Agents → Orchestrator/KB
    STATUS = "pva:status"            # Agents → Dashboard
    COORDINATION = "pva:coordination" # Agent ↔ Agent
    ERRORS = "pva:errors"            # Agents → Orchestrator
```

### Implementation
```python
# comm/message_bus.py
import redis.asyncio as redis
from dataclasses import dataclass, field, asdict
from typing import AsyncIterator
from datetime import datetime
import uuid
import json

@dataclass
class Message:
    agent_id: str
    type: str
    details: dict
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    severity: str = "INFO"
    finding_type: str = None
    requires_coordination: list = field(default_factory=list)
    blocking: bool = False
    correlation_id: str = None
    reply_to: str = None
    
    def to_redis(self) -> dict:
        data = asdict(self)
        data['details'] = json.dumps(data['details'])
        data['requires_coordination'] = json.dumps(data['requires_coordination'])
        data['blocking'] = str(data['blocking'])
        return {k: v for k, v in data.items() if v is not None}
    
    @classmethod
    def from_redis(cls, data: dict) -> 'Message':
        data['details'] = json.loads(data.get('details', '{}'))
        data['requires_coordination'] = json.loads(data.get('requires_coordination', '[]'))
        data['blocking'] = data.get('blocking', 'False') == 'True'
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class RedisStreamBus:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis: redis.Redis = None
        self._running = False
    
    async def connect(self):
        self.redis = await redis.from_url(self.redis_url, decode_responses=True)
        self._running = True
        await self._init_streams()
    
    async def close(self):
        self._running = False
        await self.redis.close()
    
    async def _init_streams(self):
        """Initialize streams and consumer groups"""
        streams_config = [
            (Streams.TASKS, "agents-group"),
            (Streams.FINDINGS, "orchestrator-group"),
            (Streams.STATUS, "dashboard-group"),
            (Streams.COORDINATION, "coordination-group"),
        ]
        for stream, group in streams_config:
            try:
                await self.redis.xgroup_create(stream, group, id='0', mkstream=True)
            except redis.ResponseError:
                pass  # Group already exists
    
    async def publish(self, stream: str, message: Message) -> str:
        """Publish message to stream, returns message ID"""
        msg_id = await self.redis.xadd(stream, message.to_redis())
        return msg_id
    
    async def subscribe(self, stream: str, group: str, consumer: str) -> AsyncIterator[tuple[str, Message]]:
        """Subscribe to stream as consumer in group"""
        while self._running:
            try:
                results = await self.redis.xreadgroup(
                    group, consumer,
                    {stream: '>'},
                    count=1,
                    block=5000
                )
                if results:
                    for _, messages in results:
                        for msg_id, data in messages:
                            yield msg_id, Message.from_redis(data)
            except redis.ResponseError as e:
                if "NOGROUP" in str(e):
                    await self._init_streams()
    
    async def ack(self, stream: str, group: str, msg_id: str):
        """Acknowledge message processing"""
        await self.redis.xack(stream, group, msg_id)
    
    async def send_to_agent(self, agent_id: str, message: Message) -> str:
        """Direct message to specific agent via tasks stream"""
        message.reply_to = agent_id
        return await self.publish(Streams.TASKS, message)
    
    async def get_pending(self, stream: str, group: str) -> list:
        """Get pending messages for a group"""
        return await self.redis.xpending(stream, group)
    
    async def get_stream_info(self, stream: str) -> dict:
        """Get stream metadata"""
        return await self.redis.xinfo_stream(stream)
```

### Agent Integration
```python
# agents/base_agent.py
from comm.message_bus import RedisStreamBus, Message, Streams

class BaseAgent:
    def __init__(self, agent_id: str, bus: RedisStreamBus):
        self.agent_id = agent_id
        self.bus = bus
        self.group = "agents-group"
    
    async def start(self):
        """Start listening for tasks"""
        async for msg_id, message in self.bus.subscribe(Streams.TASKS, self.group, self.agent_id):
            if message.reply_to == self.agent_id or message.details.get('target') == self.agent_id:
                try:
                    await self.process_task(message)
                    await self.bus.ack(Streams.TASKS, self.group, msg_id)
                except Exception as e:
                    await self.publish_error(str(e), message)
    
    async def publish_finding(self, finding: dict, severity: str = "INFO", blocking: bool = False):
        message = Message(
            agent_id=self.agent_id,
            type="finding",
            severity=severity,
            details=finding,
            blocking=blocking
        )
        await self.bus.publish(Streams.FINDINGS, message)
    
    async def update_status(self, status: str, progress: int):
        message = Message(
            agent_id=self.agent_id,
            type="status",
            details={"status": status, "progress": progress}
        )
        await self.bus.publish(Streams.STATUS, message)
    
    async def request_coordination(self, agents: list, request: dict):
        message = Message(
            agent_id=self.agent_id,
            type="coordination",
            details=request,
            requires_coordination=agents,
            reply_to=self.agent_id
        )
        await self.bus.publish(Streams.COORDINATION, message)
    
    async def publish_error(self, error: str, original: Message = None):
        message = Message(
            agent_id=self.agent_id,
            type="error",
            severity="ERROR",
            details={"error": error, "original_message_id": original.message_id if original else None}
        )
        await self.bus.publish(Streams.ERRORS, message)
```

### Orchestrator Integration
```python
# agents/orchestrator.py
class Orchestrator:
    def __init__(self, bus: RedisStreamBus):
        self.bus = bus
        self.group = "orchestrator-group"
    
    async def dispatch_task(self, agent_id: str, task: dict):
        message = Message(
            agent_id="orchestrator",
            type="task",
            details={"target": agent_id, **task}
        )
        await self.bus.publish(Streams.TASKS, message)
    
    async def listen_findings(self):
        async for msg_id, message in self.bus.subscribe(Streams.FINDINGS, self.group, "orchestrator"):
            await self.handle_finding(message)
            await self.bus.ack(Streams.FINDINGS, self.group, msg_id)
```

### Monitoring Script
```python
# scripts/monitor_streams.py
import asyncio
import redis.asyncio as redis
from comm.streams import Streams

async def monitor():
    r = await redis.from_url("redis://localhost:6379", decode_responses=True)
    streams = [Streams.TASKS, Streams.FINDINGS, Streams.STATUS, Streams.COORDINATION]
    last_ids = {s: '0' for s in streams}
    
    print("Monitoring streams... (Ctrl+C to stop)\n")
    while True:
        for stream in streams:
            msgs = await r.xread({stream: last_ids[stream]}, block=1000, count=10)
            for s, entries in msgs or []:
                for msg_id, data in entries:
                    print(f"[{stream}] {msg_id}")
                    for k, v in data.items():
                        print(f"  {k}: {v}")
                    print()
                    last_ids[stream] = msg_id

if __name__ == "__main__":
    asyncio.run(monitor())
```

---

## Orchestrator Communication Flow

```
┌──────────────┐                    ┌──────────────┐
│ Orchestrator │                    │    Agent     │
└──────┬───────┘                    └──────┬───────┘
       │                                   │
       │  1. Task Assignment               │
       │──────────────────────────────────▶│
       │     {type: "task", target: "CA"}  │
       │                                   │
       │  2. Status Update                 │
       │◀──────────────────────────────────│
       │     {type: "status", progress: 50}│
       │                                   │
       │  3. Finding Report                │
       │◀──────────────────────────────────│
       │     {type: "finding", ...}        │
       │                                   │
       │  4. Completion                    │
       │◀──────────────────────────────────│
       │     {type: "completion"}          │
       │                                   │
```

## Agent-to-Agent Coordination

```
┌──────────────┐                    ┌──────────────┐
│ Security     │                    │ Remediation  │
│ Agent        │                    │ Agent        │
└──────┬───────┘                    └──────┬───────┘
       │                                   │
       │  1. Coordination Request          │
       │──────────────────────────────────▶│
       │     {requires_coordination:       │
       │      ["remediation-agent"]}       │
       │                                   │
       │  2. Coordination Response         │
       │◀──────────────────────────────────│
       │     {type: "coordination_ack"}    │
       │                                   │
```

---

## Phase 2: Cloud Migration

### AWS Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                        AWS Cloud                             │
│  ┌─────────┐     ┌─────────┐     ┌─────────────────────┐   │
│  │   SNS   │────▶│   SQS   │────▶│   Agent (ECS)       │   │
│  │ Topics  │     │ Queues  │     │   - code-analysis   │   │
│  │         │     │         │     │   - security        │   │
│  │ - tasks │     │ - CA-q  │     │   - testing         │   │
│  │ - events│     │ - SA-q  │     └─────────────────────┘   │
│  └─────────┘     │ - TV-q  │                               │
│                  │ - DLQ   │     ┌─────────────────────┐   │
│                  └─────────┘     │   Orchestrator      │   │
│                                  │   (Lambda/ECS)      │   │
│                                  └─────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### SQS Queue Configuration
```python
# comm/sqs_bus.py
import boto3
import json

class SQSMessageBus:
    def __init__(self, region: str = "us-east-1"):
        self.sqs = boto3.client('sqs', region_name=region)
        self.sns = boto3.client('sns', region_name=region)
        self.queues = {}
    
    async def publish(self, topic_arn: str, message: Message):
        self.sns.publish(
            TopicArn=topic_arn,
            Message=json.dumps(message.__dict__),
            MessageAttributes={
                'agent_id': {'DataType': 'String', 'StringValue': message.agent_id},
                'type': {'DataType': 'String', 'StringValue': message.type},
                'severity': {'DataType': 'String', 'StringValue': message.severity}
            }
        )
    
    async def receive(self, queue_url: str, timeout: int = 20) -> Message:
        response = self.sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=timeout,
            MessageAttributeNames=['All']
        )
        if 'Messages' in response:
            msg = response['Messages'][0]
            self.sqs.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=msg['ReceiptHandle']
            )
            return Message(**json.loads(msg['Body']))
        return None
```

---

## Configuration

### Phase 1 Config
```yaml
# config/comm_config.yaml
message_bus:
  type: "redis-streams"
  redis_url: "redis://localhost:6379"
  
streams:
  tasks: "pva:tasks"
  findings: "pva:findings"
  status: "pva:status"
  coordination: "pva:coordination"
  errors: "pva:errors"

consumer_groups:
  agents: "agents-group"
  orchestrator: "orchestrator-group"
  dashboard: "dashboard-group"

settings:
  block_timeout_ms: 5000
  max_retries: 3
  retention_hours: 24
```

### Phase 2 Config
```yaml
# config/comm_config.yaml
message_bus:
  type: "aws"
  region: "us-east-1"
  
sns_topics:
  tasks: "arn:aws:sns:us-east-1:123456789:pva-tasks"
  findings: "arn:aws:sns:us-east-1:123456789:pva-findings"
  
sqs_queues:
  code-analysis: "https://sqs.us-east-1.amazonaws.com/123456789/pva-ca-queue"
  security-analysis: "https://sqs.us-east-1.amazonaws.com/123456789/pva-sa-queue"
  dlq: "https://sqs.us-east-1.amazonaws.com/123456789/pva-dlq"
```

---

## Viewing Streams Live

### RedisInsight (Recommended GUI)
```bash
docker run -d --name redisinsight -p 5540:5540 redis/redisinsight:latest
# Open http://localhost:5540
```

### Redis CLI Commands
```bash
# List all streams
redis-cli KEYS "pva:*"

# Read all messages from stream
redis-cli XRANGE pva:tasks - +

# Read last 10 messages
redis-cli XREVRANGE pva:findings + - COUNT 10

# Stream info
redis-cli XINFO STREAM pva:tasks

# Consumer group info
redis-cli XINFO GROUPS pva:tasks

# Pending messages
redis-cli XPENDING pva:tasks agents-group

# Monitor live
redis-cli XREAD BLOCK 0 STREAMS pva:tasks pva:findings $
```

---

## Error Handling

### Retry with Pending Messages
```python
# comm/retry.py
class StreamRetryHandler:
    def __init__(self, bus: RedisStreamBus):
        self.bus = bus
    
    async def process_pending(self, stream: str, group: str, consumer: str):
        """Reprocess pending (unacknowledged) messages"""
        pending = await self.bus.redis.xpending_range(
            stream, group, '-', '+', count=100
        )
        for msg in pending:
            msg_id = msg['message_id']
            # Claim and reprocess
            claimed = await self.bus.redis.xclaim(
                stream, group, consumer, min_idle_time=60000, message_ids=[msg_id]
            )
            for _, data in claimed:
                yield msg_id, Message.from_redis(data)
```

### Dead Letter Handling
```python
# comm/dlq.py
class DeadLetterHandler:
    def __init__(self, bus: RedisStreamBus):
        self.bus = bus
        self.dlq_stream = "pva:dlq"
    
    async def move_to_dlq(self, stream: str, group: str, msg_id: str, error: str):
        # Get original message
        msgs = await self.bus.redis.xrange(stream, msg_id, msg_id)
        if msgs:
            _, data = msgs[0]
            data['_original_stream'] = stream
            data['_error'] = error
            data['_failed_at'] = datetime.utcnow().isoformat()
            await self.bus.redis.xadd(self.dlq_stream, data)
            await self.bus.redis.xack(stream, group, msg_id)
```

---

## Stream Maintenance

### Trim Old Messages
```python
# Keep only last 1000 messages per stream
async def trim_streams(bus: RedisStreamBus):
    for stream in [Streams.TASKS, Streams.FINDINGS, Streams.STATUS]:
        await bus.redis.xtrim(stream, maxlen=1000, approximate=True)
```

### Health Check
```python
class StreamHealthCheck:
    async def check(self, bus: RedisStreamBus) -> dict:
        info = {}
        for stream in [Streams.TASKS, Streams.FINDINGS, Streams.STATUS]:
            try:
                stream_info = await bus.redis.xinfo_stream(stream)
                info[stream] = {
                    'length': stream_info['length'],
                    'first_entry': stream_info.get('first-entry'),
                    'last_entry': stream_info.get('last-entry')
                }
            except:
                info[stream] = {'status': 'not_found'}
        return info
```

---

## Monitoring

### Message Metrics
```python
# comm/metrics.py
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class BusMetrics:
    messages_sent: int = 0
    messages_received: int = 0
    messages_failed: int = 0
    avg_latency_ms: float = 0.0
    by_channel: dict = field(default_factory=lambda: defaultdict(int))
    by_agent: dict = field(default_factory=lambda: defaultdict(int))
```

### Health Check
```python
# comm/health.py
class BusHealthCheck:
    async def check(self, bus: MessageBus) -> dict:
        return {
            'status': 'healthy' if bus._running else 'stopped',
            'queues': len(bus._queues),
            'subscribers': sum(len(s) for s in bus._subscribers.values())
        }
```
