# Production Verification Workflow

Complete implementation of the production code verification system using shared workspace architecture.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  intract-orchestrator (Port 8006)                           │
│  • Web UI (upload, dashboard, logs)                         │
│  • S3 client (upload/download artifacts)                    │
│  • Triggers orchestrator_agent via A2A                      │
└──────────────────────┬──────────────────────────────────────┘
                       │ POST /a2a (A2A protocol)
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  orchestrator_agent (Port 8000)                             │
│  • Downloads code from S3                                   │
│  • Extracts to /tmp/workspace/{task_id}/                    │
│  • Coordinates 4 agents with workspace path                 │
│  • Uploads results to S3                                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────┼─────────────┬─────────────┐
         ▼             ▼             ▼             ▼
    Code Logic    Research      Test Run     Validation
    (8001)        (8003)        (8004)       (8005)
    • Read from shared workspace
    • Write results to workspace
```

## Components

### 1. Shared S3 Client (`src/shared/s3_client.py`)

Unified S3 client used by all agents:
- Download files from S3
- Upload files to S3
- Generate presigned URLs
- Check file existence

### 2. Intract-Orchestrator (`src/intract-orchestrator/`)

Frontend gateway with new endpoint:

**POST `/api/verify/trigger`**
- Accepts: `s3_key`, `project_name`, `metadata`
- Calls orchestrator_agent via A2A protocol
- Returns: `task_id` for tracking

### 3. Orchestrator Agent (`src/orchestorator_agent/`)

Multi-agent coordinator with new workflow:

**`handle_verification_workflow()`**
1. Downloads code zip from S3
2. Extracts to `/tmp/workspace/{task_id}/`
3. Calls agents sequentially:
   - Code Logic Agent (AST analysis)
   - Research Agent (pattern matching)
   - Test Run Agent (test generation)
   - Validation Agent (security checks)
4. Uploads results to S3
5. Cleans up workspace
6. Returns summary + results URL

### 4. Frontend UI (`frontend/index.html`)

New verification section:
- Dropdown to select uploaded artifacts
- Project name input
- "Verify Production Code" button
- Status display with link to progress page

## Usage

### 1. Start All Services

```bash
# Terminal 1: Start intract-orchestrator
cd src/intract-orchestrator
python app.py

# Terminal 2: Start orchestrator agent
cd src/orchestorator_agent
python agent.py

# Terminal 3-6: Start specialized agents
cd src/code_logic_agent && python agent.py
cd src/research_agent && python agent.py
cd src/test_run_agents && python agent.py
cd src/validation_agent && python agent.py
```

Or use the convenience script:
```bash
./run_all_agents.sh
```

### 2. Upload Code Artifact

1. Visit http://localhost:8006
2. Upload a code zip file
3. Note the S3 key from "Recent Uploads"

### 3. Trigger Verification

**Option A: Web UI**
1. Scroll to "Production Code Verification" section
2. Select artifact from dropdown
3. Enter project name
4. Click "Verify Production Code"
5. View progress at the redirected page

**Option B: API**
```bash
curl -X POST http://localhost:8006/api/verify/trigger \
  -F "s3_key=artifacts/2026/03/08/mycode.zip" \
  -F "project_name=my-project"
```

**Option C: Test Script**
```bash
python test_verification.py
```

### 4. Monitor Progress

- **Tasks Dashboard**: http://localhost:8006/tasks.html
- **Progress Tracker**: http://localhost:8006/progress.html?task_id={task_id}
- **Logs Viewer**: http://localhost:8006/logs.html

## Workflow Details

### Shared Workspace Pattern

Each verification creates an isolated workspace:

```
/tmp/workspace/{task_id}/
├── code.zip (downloaded from S3)
├── [extracted files]
├── verification_results.json (uploaded to S3)
└── [agent outputs]
```

**Benefits:**
- Simple file I/O for agents
- No S3 credentials needed by specialized agents
- Easy cleanup after completion
- Isolated per task

### Agent Communication

Each agent receives:
```json
{
  "parts": [
    {
      "kind": "text",
      "text": "Analyze code in workspace"
    },
    {
      "kind": "data",
      "data": {
        "workspace": "/tmp/workspace/{task_id}",
        "project_name": "my-project",
        "task_id": "{task_id}"
      }
    }
  ]
}
```

Agents read from `workspace` path and write results there.

### Results Storage

Results are uploaded to S3:
```
s3://bucket/results/{task_id}/verification_results.json
```

Contains:
```json
{
  "code_logic": { ... },
  "research": { ... },
  "tests": { ... },
  "validation": { ... }
}
```

## Configuration

### Environment Variables

Create `.env` in project root:

```bash
# AWS Configuration
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-east-1
S3_BUCKET_NAME=a2a-multi-agent-artifacts

# Ports
PORT=8006  # intract-orchestrator
```

### Agent Ports

- intract-orchestrator: 8006
- orchestrator_agent: 8000
- code-logic-agent: 8001
- research-agent: 8003
- test-run-agent: 8004
- validation-agent: 8005

## Testing

Run the test script:
```bash
python test_verification.py
```

This will:
1. Check service health
2. List available artifacts
3. Trigger verification on first artifact
4. Monitor task status
5. Display results

## Troubleshooting

### S3 Connection Issues
```bash
# Check AWS credentials
aws s3 ls s3://your-bucket-name

# Verify .env file exists
cat .env
```

### Agent Not Responding
```bash
# Check agent health
curl http://localhost:8001/health  # code-logic
curl http://localhost:8003/health  # research
curl http://localhost:8004/health  # test-run
curl http://localhost:8005/health  # validation
```

### Workspace Cleanup
```bash
# Manual cleanup if needed
rm -rf /tmp/workspace/*
```

### View Logs
```bash
# Check orchestrator logs
tail -f src/orchestorator_agent/agent.log

# Or use web UI
open http://localhost:8006/logs.html
```

## Next Steps

1. **Add Agent Logic**: Implement actual analysis in specialized agents
2. **Enhance Results**: Add more detailed reporting
3. **Add Notifications**: Email/Slack alerts on completion
4. **Scale Up**: Deploy to cloud with ECS/Lambda
5. **Add Caching**: Cache analysis results for faster re-runs

## Files Modified

- `src/shared/s3_client.py` - New shared S3 client
- `src/intract-orchestrator/app.py` - Added `/api/verify/trigger` endpoint
- `src/orchestorator_agent/agent.py` - Added `handle_verification_workflow()`
- `frontend/index.html` - Added verification UI section
- `frontend/static/js/upload.js` - Added verification trigger logic
- `test_verification.py` - New test script

## API Reference

### POST /api/verify/trigger

Trigger production verification workflow.

**Request:**
```
Content-Type: multipart/form-data

s3_key: artifacts/2026/03/08/code.zip
project_name: my-project
metadata: {"key": "value"}  (optional JSON string)
```

**Response:**
```json
{
  "status": "triggered",
  "task_id": "uuid",
  "project_name": "my-project",
  "s3_key": "artifacts/2026/03/08/code.zip"
}
```

### GET /api/tasks/{task_id}/details

Get task details and results.

**Response:**
```json
{
  "task": {
    "task_id": "uuid",
    "status": "completed",
    "result": { ... },
    "created_at": "2026-03-08T10:00:00Z",
    "updated_at": "2026-03-08T10:05:00Z"
  }
}
```
