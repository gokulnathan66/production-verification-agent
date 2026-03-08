# A2A Multi-Agent Dashboard - Frontend

A modern, real-time web dashboard for monitoring and managing the A2A multi-agent system.

## Features

- **📁 Upload Artifacts**: Drag-and-drop file uploads to S3 with metadata
- **📋 Task Dashboard**: View and filter agent tasks with auto-refresh
- **📜 Logs Viewer**: Real-time log streaming with SSE, filtering, and download
- **⚡ Progress Tracker**: Live agent status monitoring with health indicators

## Tech Stack

- **Frontend**: Vanilla HTML/CSS/JavaScript (no build tools required)
- **Styling**: Custom CSS design system with command center aesthetic
- **Real-time**: Server-Sent Events (SSE) for live updates
- **Backend**: FastAPI with SQLite persistence and S3 integration

## Design System

### Color Palette
- **Primary**: Electric Cyan (#00d9ff)
- **Secondary**: Deep Purple (#7c3aed)
- **Background**: Dark navy (#0a0e14)
- **Success**: Emerald green (#10b981)
- **Error**: Red (#ef4444)

### Typography
- **UI Font**: Outfit (sans-serif)
- **Mono Font**: JetBrains Mono (for code/data)

### Aesthetic
Command center / spacecraft control interface with:
- Dark-mode first design
- Frosted glass effects (backdrop-filter)
- Glowing borders on hover
- Animated status indicators
- Terminal-inspired log styling

## Project Structure

```
frontend/
├── index.html              # Upload artifact page
├── tasks.html              # Task dashboard
├── logs.html               # Logs viewer
├── progress.html           # Progress tracker
├── components/             # Shared components (future)
└── static/
    ├── css/
    │   ├── main.css       # Design system & base styles
    │   ├── components.css # Reusable UI components
    │   └── pages.css      # Page-specific styles
    ├── js/
    │   ├── api.js         # API client wrapper
    │   ├── utils.js       # Common utilities
    │   ├── upload.js      # Upload page logic
    │   ├── tasks.js       # Tasks page logic
    │   ├── logs.js        # Logs page logic (SSE)
    │   └── progress.js    # Progress page logic (SSE)
    └── assets/
        └── (logos, icons)
```

## Setup

### 1. Install Backend Dependencies

```bash
cd src/orchestrator
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file in project root:

```bash
# AWS S3 Configuration
AWS_REGION=us-east-1
S3_BUCKET_NAME=a2a-multi-agent-artifacts

# Orchestrator Configuration
PORT=8006
```

### 3. Start the Orchestrator

```bash
cd src/orchestrator
python orchestrator.py
```

The dashboard will be available at: http://localhost:8006

## Usage

### Upload Artifacts

1. Navigate to http://localhost:8006
2. Drag and drop a code file (.py, .js, .java, .go, .rs, etc.)
3. Add optional tags and description
4. Click "Upload to S3"
5. View recent uploads in the right panel

### Monitor Tasks

1. Navigate to http://localhost:8006/tasks.html
2. Use filters to find specific tasks (by agent or status)
3. Click any task row to view full details
4. Auto-refresh enabled by default (5s interval)

### View Logs

1. Navigate to http://localhost:8006/logs.html
2. Real-time logs stream automatically via SSE
3. Filter by agent, level, or search keywords
4. Toggle auto-scroll for continuous monitoring
5. Download logs as text file

### Track Progress

1. Navigate to http://localhost:8006/progress.html
2. View global task statistics (total, active, completed, errors)
3. Monitor individual agent health and task counts
4. Real-time updates via SSE (2s interval)

## API Endpoints

### Artifact Management
- `POST /api/artifacts/upload` - Upload artifact to S3
- `GET /api/artifacts` - List all artifacts

### Task Management
- `GET /api/tasks/history` - Get task history (with filters)
- `GET /api/tasks/{task_id}/details` - Get task details

### Logs
- `GET /api/logs` - Get logs (with filters)
- `GET /api/logs/stream` - SSE stream for real-time logs

### Progress
- `GET /api/progress/stream` - SSE stream for agent status

### System
- `GET /health` - Health check
- `GET /agents` - List discovered agents
- `POST /discover` - Discover new agent
- `POST /execute` - Execute task on agent

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

**Note**: Server-Sent Events (SSE) and `backdrop-filter` are required.

## Performance

- **Max logs in memory**: 500 entries
- **Log stream interval**: 1 second
- **Progress stream interval**: 2 seconds
- **Task auto-refresh**: 5 seconds (optional)
- **File upload limit**: 50MB

## Customization

### Colors

Edit CSS variables in `static/css/main.css`:

```css
:root {
  --color-accent-primary: #00d9ff; /* Change primary color */
  --color-bg-primary: #0a0e14;     /* Change background */
  /* ... */
}
```

### Fonts

Replace font imports in `static/css/main.css`:

```css
@import url('https://fonts.googleapis.com/css2?family=YourFont:wght@300;400;500&display=swap');

:root {
  --font-display: 'YourFont', sans-serif;
}
```

## Security Notes

⚠️ **Important**: This dashboard has NO authentication. Recommendations for production:

1. Add FastAPI OAuth2 middleware
2. Restrict `/api/*` endpoints with JWT tokens
3. Use HTTPS (not HTTP)
4. Configure CORS properly
5. Validate S3 bucket permissions
6. Rate limit API endpoints

## Troubleshooting

### Frontend not loading
- Check that orchestrator is running: `python src/orchestrator/orchestrator.py`
- Verify frontend path resolution in orchestrator.py
- Check browser console for errors

### S3 upload fails
- Verify AWS credentials in `.env`
- Check S3 bucket permissions (PutObject, GetObject)
- Ensure bucket name is correct
- Check CORS configuration on S3 bucket

### SSE streams not working
- Check browser console for connection errors
- Verify orchestrator is running
- Check firewall/proxy settings (SSE uses long-lived connections)
- Try different browser

### No logs/tasks appearing
- Execute a task first: `curl -X POST http://localhost:8006/execute -H "Content-Type: application/json" -d '{"request": "Hello!"}'`
- Check database: `sqlite3 a2a_dashboard.db "SELECT * FROM tasks;"`
- Verify agents are discovered: `curl http://localhost:8006/agents`

## Development

### Adding New Pages

1. Create HTML file in `frontend/`
2. Create JS file in `frontend/static/js/`
3. Add route in `orchestrator.py`:

```python
@app.get("/your-page.html")
async def serve_your_page():
    return FileResponse(str(FRONTEND_DIR / "your-page.html"))
```

### Adding New Components

Add reusable component styles to `static/css/components.css`:

```css
.your-component {
  /* styles */
}
```

## Future Enhancements

- [ ] Chart.js integration for visualizations
- [ ] Task execution form in UI
- [ ] Agent discovery UI
- [ ] Dark/light mode toggle
- [ ] Mobile-responsive improvements
- [ ] WebSocket alternative to SSE
- [ ] Export tasks as JSON/CSV
- [ ] Advanced filtering (date ranges, regex)
- [ ] User authentication & authorization
- [ ] Multi-language support

## License

Part of the A2A Multi-Agent System project.
