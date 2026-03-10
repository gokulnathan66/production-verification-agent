# PostgreSQL Setup for A2A Multi-Agent System

## What Changed

The system now uses **PostgreSQL** instead of SQLite for persistent storage.

### Benefits
- ✅ **Data persists** across container restarts
- ✅ **Better concurrency** - handles multiple uploads simultaneously
- ✅ **Production-ready** - scales with your needs
- ✅ **JSONB support** - efficient metadata storage

## Quick Start

### 1. Start All Services

```bash
cd src
docker-compose up -d
```

PostgreSQL will automatically:
- Create database `a2a_dashboard`
- Create user `a2a_user` with password `a2a_password`
- Initialize tables on first run
- Store data in Docker volume `postgres-data`

### 2. Verify PostgreSQL is Running

```bash
docker-compose ps postgres
```

Should show `healthy` status.

### 3. Access PostgreSQL (Optional)

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U a2a_user -d a2a_dashboard

# List tables
\dt

# View artifacts
SELECT filename, uploaded_at FROM artifacts ORDER BY uploaded_at DESC LIMIT 10;

# Exit
\q
```

## Configuration

### Environment Variables

Set in `docker-compose.yml`:

```yaml
DATABASE_URL=postgresql://a2a_user:a2a_password@postgres:5432/a2a_dashboard
```

### Change Password (Production)

Edit `docker-compose.yml`:

```yaml
postgres:
  environment:
    - POSTGRES_PASSWORD=your_secure_password

app:
  environment:
    - DATABASE_URL=postgresql://a2a_user:your_secure_password@postgres:5432/a2a_dashboard
```

## Data Persistence

Data is stored in Docker volume `postgres-data`:

```bash
# View volumes
docker volume ls | grep postgres

# Backup database
docker-compose exec postgres pg_dump -U a2a_user a2a_dashboard > backup.sql

# Restore database
docker-compose exec -T postgres psql -U a2a_user a2a_dashboard < backup.sql
```

## Troubleshooting

### Connection Refused

Wait for PostgreSQL to be healthy:
```bash
docker-compose logs postgres
```

Look for: `database system is ready to accept connections`

### Reset Database

```bash
# Stop services
docker-compose down

# Remove volume
docker volume rm src_postgres-data

# Restart
docker-compose up -d
```

### View Logs

```bash
# PostgreSQL logs
docker-compose logs -f postgres

# Application logs
docker-compose logs -f app
```

## Schema

### Tables

1. **artifacts** - Uploaded files metadata
   - `id`, `filename`, `s3_key`, `s3_url`, `size`, `uploaded_at`

2. **tasks** - Verification task history
   - `id`, `agent_id`, `status`, `request`, `result`, `created_at`

3. **agent_logs** - Agent execution logs
   - `id`, `agent_id`, `task_id`, `level`, `message`, `timestamp`

### Indexes

- `idx_tasks_agent_id` - Fast task lookup by agent
- `idx_tasks_status` - Fast filtering by status
- `idx_logs_agent_id` - Fast log lookup by agent
- `idx_logs_task_id` - Fast log lookup by task

## Migration from SQLite

If you have existing SQLite data:

1. Export from SQLite:
```bash
sqlite3 a2a_dashboard.db .dump > data.sql
```

2. Convert to PostgreSQL format (manual adjustments needed)

3. Import to PostgreSQL:
```bash
docker-compose exec -T postgres psql -U a2a_user a2a_dashboard < data_postgres.sql
```

## Performance

PostgreSQL handles:
- **1000+ concurrent connections**
- **Millions of rows** efficiently
- **Complex queries** with joins
- **Full-text search** on logs

Perfect for production deployments!
