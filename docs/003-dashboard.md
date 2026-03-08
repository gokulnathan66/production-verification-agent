# Dashboard - Live Monitoring Frontend

## Overview
Simple web dashboard to monitor agents, knowledge base, and Redis Streams in real-time.

## Tech Stack
- **Backend**: FastAPI + WebSockets
- **Frontend**: HTML + Vanilla JS + SSE/WebSocket
- **Styling**: Tailwind CSS (CDN)

## Architecture
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Browser    │◀───▶│  FastAPI    │◀───▶│   Redis     │
│  Dashboard  │ WS  │  Backend    │     │   Streams   │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  PostgreSQL │
                    │  (KB)       │
                    └─────────────┘
```

---

## Backend Implementation

### FastAPI Server
```python
# dashboard/server.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import redis.asyncio as redis
import asyncpg
import asyncio
import json

app = FastAPI(title="PVA Dashboard")

# Connections
redis_client: redis.Redis = None
pg_pool: asyncpg.Pool = None

@app.on_event("startup")
async def startup():
    global redis_client, pg_pool
    redis_client = await redis.from_url("redis://localhost:6379", decode_responses=True)
    pg_pool = await asyncpg.create_pool("postgresql://pva:pva_local@localhost:5432/pva_kb")

@app.on_event("shutdown")
async def shutdown():
    await redis_client.close()
    await pg_pool.close()

# Serve frontend
@app.get("/", response_class=HTMLResponse)
async def index():
    with open("dashboard/static/index.html") as f:
        return f.read()

# REST APIs
@app.get("/api/agents")
async def get_agents():
    """Get all agent statuses from Redis"""
    keys = await redis_client.keys("session:*:agents")
    agents = {}
    for key in keys:
        session_id = key.split(":")[1]
        status = await redis_client.hgetall(key)
        agents[session_id] = {k: json.loads(v) for k, v in status.items()}
    return agents

@app.get("/api/sessions")
async def get_sessions():
    """Get recent analysis sessions from KB"""
    async with pg_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, project_id, status, started_at, completed_at, overall_score
            FROM analysis_sessions ORDER BY started_at DESC LIMIT 20
        """)
        return [dict(r) for r in rows]

@app.get("/api/findings/{session_id}")
async def get_findings(session_id: str):
    """Get findings for a session"""
    async with pg_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT * FROM current_findings 
            WHERE session_id = $1 ORDER BY created_at DESC
        """, session_id)
        return [dict(r) for r in rows]

@app.get("/api/streams/info")
async def get_streams_info():
    """Get Redis streams metadata"""
    streams = ["pva:tasks", "pva:findings", "pva:status", "pva:coordination"]
    info = {}
    for stream in streams:
        try:
            data = await redis_client.xinfo_stream(stream)
            info[stream] = {
                "length": data["length"],
                "last_entry_id": data.get("last-generated-id")
            }
        except:
            info[stream] = {"length": 0, "status": "empty"}
    return info

# WebSocket for live stream
@app.websocket("/ws/streams")
async def websocket_streams(websocket: WebSocket):
    await websocket.accept()
    streams = ["pva:tasks", "pva:findings", "pva:status", "pva:coordination"]
    last_ids = {s: "$" for s in streams}
    
    try:
        while True:
            # Read from all streams
            result = await redis_client.xread(
                {s: last_ids[s] for s in streams},
                block=1000, count=10
            )
            if result:
                for stream, messages in result:
                    for msg_id, data in messages:
                        await websocket.send_json({
                            "stream": stream,
                            "id": msg_id,
                            "data": data,
                            "timestamp": msg_id.split("-")[0]
                        })
                        last_ids[stream] = msg_id
    except WebSocketDisconnect:
        pass

@app.websocket("/ws/agents")
async def websocket_agents(websocket: WebSocket):
    """Live agent status updates"""
    await websocket.accept()
    pubsub = redis_client.pubsub()
    await pubsub.psubscribe("__keyspace@0__:session:*:agents")
    
    try:
        async for msg in pubsub.listen():
            if msg["type"] == "pmessage":
                # Fetch updated status
                key = msg["channel"].split(":", 1)[1]
                status = await redis_client.hgetall(key)
                await websocket.send_json({
                    "type": "agent_update",
                    "key": key,
                    "data": {k: json.loads(v) for k, v in status.items()}
                })
    except WebSocketDisconnect:
        await pubsub.unsubscribe()
```

### Run Server
```bash
uvicorn dashboard.server:app --reload --port 8000
```

---

## Frontend Implementation

### HTML Dashboard
```html
<!-- dashboard/static/index.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PVA Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .stream-msg { animation: fadeIn 0.3s ease-in; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; } }
        .severity-CRITICAL { background: #fee2e2; border-left: 4px solid #dc2626; }
        .severity-HIGH { background: #ffedd5; border-left: 4px solid #ea580c; }
        .severity-MEDIUM { background: #fef9c3; border-left: 4px solid #ca8a04; }
        .severity-LOW { background: #dcfce7; border-left: 4px solid #16a34a; }
        .severity-INFO { background: #e0f2fe; border-left: 4px solid #0284c7; }
    </style>
</head>
<body class="bg-gray-900 text-white min-h-screen">
    <div class="container mx-auto p-4">
        <!-- Header -->
        <header class="mb-6">
            <h1 class="text-2xl font-bold">🔍 Production Verification Agent</h1>
            <p class="text-gray-400">Live Dashboard</p>
        </header>

        <!-- Stats Row -->
        <div class="grid grid-cols-4 gap-4 mb-6" id="stats">
            <div class="bg-gray-800 p-4 rounded-lg">
                <div class="text-gray-400 text-sm">Active Sessions</div>
                <div class="text-2xl font-bold" id="stat-sessions">0</div>
            </div>
            <div class="bg-gray-800 p-4 rounded-lg">
                <div class="text-gray-400 text-sm">Agents Running</div>
                <div class="text-2xl font-bold" id="stat-agents">0</div>
            </div>
            <div class="bg-gray-800 p-4 rounded-lg">
                <div class="text-gray-400 text-sm">Findings</div>
                <div class="text-2xl font-bold" id="stat-findings">0</div>
            </div>
            <div class="bg-gray-800 p-4 rounded-lg">
                <div class="text-gray-400 text-sm">Stream Messages</div>
                <div class="text-2xl font-bold" id="stat-messages">0</div>
            </div>
        </div>

        <!-- Main Grid -->
        <div class="grid grid-cols-3 gap-4">
            <!-- Agents Panel -->
            <div class="bg-gray-800 rounded-lg p-4">
                <h2 class="text-lg font-semibold mb-3 flex items-center">
                    <span class="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse"></span>
                    Agents
                </h2>
                <div id="agents-list" class="space-y-2">
                    <!-- Agent cards rendered here -->
                </div>
            </div>

            <!-- Streams Panel -->
            <div class="bg-gray-800 rounded-lg p-4">
                <h2 class="text-lg font-semibold mb-3 flex items-center">
                    <span class="w-2 h-2 bg-blue-500 rounded-full mr-2 animate-pulse"></span>
                    Live Streams
                </h2>
                <div class="flex gap-2 mb-3">
                    <button onclick="filterStream('all')" class="px-2 py-1 bg-gray-700 rounded text-sm">All</button>
                    <button onclick="filterStream('pva:tasks')" class="px-2 py-1 bg-gray-700 rounded text-sm">Tasks</button>
                    <button onclick="filterStream('pva:findings')" class="px-2 py-1 bg-gray-700 rounded text-sm">Findings</button>
                    <button onclick="filterStream('pva:status')" class="px-2 py-1 bg-gray-700 rounded text-sm">Status</button>
                </div>
                <div id="streams-list" class="space-y-2 max-h-96 overflow-y-auto">
                    <!-- Stream messages rendered here -->
                </div>
            </div>

            <!-- KB Panel -->
            <div class="bg-gray-800 rounded-lg p-4">
                <h2 class="text-lg font-semibold mb-3 flex items-center">
                    <span class="w-2 h-2 bg-purple-500 rounded-full mr-2"></span>
                    Knowledge Base
                </h2>
                <div id="kb-panel">
                    <h3 class="text-sm text-gray-400 mb-2">Recent Sessions</h3>
                    <div id="sessions-list" class="space-y-2 mb-4">
                        <!-- Sessions rendered here -->
                    </div>
                    <h3 class="text-sm text-gray-400 mb-2">Latest Findings</h3>
                    <div id="findings-list" class="space-y-2 max-h-48 overflow-y-auto">
                        <!-- Findings rendered here -->
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let streamFilter = 'all';
        let messageCount = 0;
        const maxMessages = 50;

        // WebSocket connections
        const streamsWs = new WebSocket(`ws://${location.host}/ws/streams`);
        const agentsWs = new WebSocket(`ws://${location.host}/ws/agents`);

        // Stream messages handler
        streamsWs.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            messageCount++;
            document.getElementById('stat-messages').textContent = messageCount;
            
            if (streamFilter === 'all' || streamFilter === msg.stream) {
                addStreamMessage(msg);
            }
            
            // Update findings count if it's a finding
            if (msg.stream === 'pva:findings') {
                const count = parseInt(document.getElementById('stat-findings').textContent);
                document.getElementById('stat-findings').textContent = count + 1;
            }
        };

        // Agent updates handler
        agentsWs.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            updateAgentsList(msg.data);
        };

        function addStreamMessage(msg) {
            const list = document.getElementById('streams-list');
            const severity = msg.data.severity || 'INFO';
            const streamName = msg.stream.replace('pva:', '');
            
            const el = document.createElement('div');
            el.className = `stream-msg p-2 rounded text-sm severity-${severity}`;
            el.innerHTML = `
                <div class="flex justify-between text-xs text-gray-600 mb-1">
                    <span class="font-mono">${streamName}</span>
                    <span>${new Date(parseInt(msg.timestamp)).toLocaleTimeString()}</span>
                </div>
                <div class="text-gray-800">
                    <span class="font-semibold">${msg.data.agent_id || 'system'}</span>: 
                    ${msg.data.type || 'message'}
                </div>
                ${msg.data.details ? `<pre class="text-xs mt-1 overflow-hidden">${JSON.stringify(JSON.parse(msg.data.details || '{}'), null, 2).slice(0, 100)}...</pre>` : ''}
            `;
            
            list.insertBefore(el, list.firstChild);
            
            // Keep only last N messages
            while (list.children.length > maxMessages) {
                list.removeChild(list.lastChild);
            }
        }

        function updateAgentsList(agents) {
            const list = document.getElementById('agents-list');
            list.innerHTML = '';
            let runningCount = 0;
            
            for (const [agentId, status] of Object.entries(agents)) {
                if (status.status === 'running') runningCount++;
                
                const statusColor = {
                    'running': 'bg-green-500',
                    'completed': 'bg-blue-500',
                    'failed': 'bg-red-500',
                    'idle': 'bg-gray-500'
                }[status.status] || 'bg-gray-500';
                
                const el = document.createElement('div');
                el.className = 'bg-gray-700 p-3 rounded';
                el.innerHTML = `
                    <div class="flex justify-between items-center">
                        <span class="font-medium">${agentId}</span>
                        <span class="w-2 h-2 ${statusColor} rounded-full"></span>
                    </div>
                    <div class="text-sm text-gray-400">${status.status}</div>
                    ${status.progress !== undefined ? `
                        <div class="mt-2 bg-gray-600 rounded-full h-2">
                            <div class="bg-blue-500 h-2 rounded-full" style="width: ${status.progress}%"></div>
                        </div>
                    ` : ''}
                `;
                list.appendChild(el);
            }
            
            document.getElementById('stat-agents').textContent = runningCount;
        }

        function filterStream(stream) {
            streamFilter = stream;
            document.getElementById('streams-list').innerHTML = '';
        }

        // Initial data load
        async function loadInitialData() {
            // Load agents
            const agents = await fetch('/api/agents').then(r => r.json());
            for (const [sessionId, agentData] of Object.entries(agents)) {
                updateAgentsList(agentData);
            }
            
            // Load sessions
            const sessions = await fetch('/api/sessions').then(r => r.json());
            const sessionsList = document.getElementById('sessions-list');
            document.getElementById('stat-sessions').textContent = sessions.length;
            
            sessions.slice(0, 5).forEach(s => {
                const el = document.createElement('div');
                el.className = 'bg-gray-700 p-2 rounded text-sm cursor-pointer hover:bg-gray-600';
                el.innerHTML = `
                    <div class="font-medium">${s.id.slice(0, 8)}...</div>
                    <div class="text-gray-400 text-xs">${s.status} - Score: ${s.overall_score || 'N/A'}</div>
                `;
                el.onclick = () => loadFindings(s.id);
                sessionsList.appendChild(el);
            });
            
            // Load stream info
            const streamInfo = await fetch('/api/streams/info').then(r => r.json());
            let totalMsgs = 0;
            for (const info of Object.values(streamInfo)) {
                totalMsgs += info.length || 0;
            }
            document.getElementById('stat-messages').textContent = totalMsgs;
        }

        async function loadFindings(sessionId) {
            const findings = await fetch(`/api/findings/${sessionId}`).then(r => r.json());
            const list = document.getElementById('findings-list');
            list.innerHTML = '';
            
            findings.forEach(f => {
                const el = document.createElement('div');
                el.className = `p-2 rounded text-sm severity-${f.severity}`;
                el.innerHTML = `
                    <div class="font-medium text-gray-800">${f.finding_type}</div>
                    <div class="text-xs text-gray-600">${f.agent_id}</div>
                `;
                list.appendChild(el);
            });
        }

        loadInitialData();
    </script>
</body>
</html>
```

---

## Project Structure
```
dashboard/
├── server.py          # FastAPI backend
├── static/
│   └── index.html     # Frontend
└── requirements.txt
```

### Requirements
```txt
# dashboard/requirements.txt
fastapi==0.109.0
uvicorn==0.27.0
redis==5.0.1
asyncpg==0.29.0
websockets==12.0
```

---

## Running the Dashboard

### 1. Start Infrastructure
```bash
docker-compose up -d  # PostgreSQL + Redis
```

### 2. Start Dashboard
```bash
cd dashboard
pip install -r requirements.txt
uvicorn server:app --reload --port 8000
```

### 3. Open Browser
```
http://localhost:8000
```

---

## Features

| Panel | Data Source | Update Method |
|-------|-------------|---------------|
| Agents | Redis Hash | WebSocket (keyspace notifications) |
| Streams | Redis Streams | WebSocket (XREAD) |
| Sessions | PostgreSQL | REST API |
| Findings | PostgreSQL | REST API (on click) |

## Screenshots Layout
```
┌─────────────────────────────────────────────────────────────┐
│  🔍 Production Verification Agent - Live Dashboard          │
├─────────────────────────────────────────────────────────────┤
│  [Sessions: 5]  [Agents: 3]  [Findings: 42]  [Messages: 156]│
├───────────────┬───────────────────┬─────────────────────────┤
│   AGENTS      │   LIVE STREAMS    │   KNOWLEDGE BASE        │
│               │                   │                         │
│ ┌───────────┐ │ [All][Tasks][Find]│   Recent Sessions       │
│ │ code-     │ │                   │   ┌─────────────────┐   │
│ │ analysis  │ │ ┌───────────────┐ │   │ session-abc     │   │
│ │ ████░░ 60%│ │ │ finding       │ │   │ completed - 85  │   │
│ └───────────┘ │ │ security-agent│ │   └─────────────────┘   │
│               │ │ CRITICAL vuln │ │                         │
│ ┌───────────┐ │ └───────────────┘ │   Latest Findings       │
│ │ security- │ │                   │   ┌─────────────────┐   │
│ │ analysis  │ │ ┌───────────────┐ │   │ vulnerability   │   │
│ │ ████████ ✓│ │ │ status        │ │   │ HIGH            │   │
│ └───────────┘ │ │ code-analysis │ │   └─────────────────┘   │
│               │ │ progress: 60% │ │                         │
└───────────────┴─└───────────────┘─┴─────────────────────────┘
```
