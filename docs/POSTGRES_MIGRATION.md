# PostgreSQL Migration Summary

## Changes Made

### 1. Docker Compose (`src/docker-compose.yml`)
- ✅ Added PostgreSQL 15 service
- ✅ Configured health checks
- ✅ Added persistent volume `postgres-data`
- ✅ Updated app to depend on PostgreSQL

### 2. Storage Layer (`src/app/storage.py`)
- ✅ Changed from SQLite to PostgreSQL connection
- ✅ Updated schema: `SERIAL` instead of `AUTOINCREMENT`
- ✅ Updated schema: `TIMESTAMP` instead of `TEXT` for dates
- ✅ Updated schema: `JSONB` instead of `TEXT` for metadata
- ✅ Updated schema: `BIGINT` for file sizes

### 3. Requirements (`src/app/requirements.txt`)
- ✅ Replaced `aiosqlite` with `asyncpg`
- ✅ Changed `databases[aiosqlite]` to `databases[postgresql]`

## Database Credentials

```
Host: postgres (Docker network) / localhost (from host)
Port: 5432
Database: a2a_dashboard
User: a2a_user
Password: a2a_password
```

## Connection String

```
postgresql://a2a_user:a2a_password@postgres:5432/a2a_dashboard
```

## Start Services

```bash
cd src
docker-compose down
docker-compose up -d
```

## Verify

```bash
# Check PostgreSQL is healthy
docker-compose ps postgres

# Check logs
docker-compose logs -f app

# Test upload
curl http://localhost:8006/health
```

## Data Persistence

✅ Data now persists across container restarts
✅ Stored in Docker volume: `src_postgres-data`
✅ Backup: `docker-compose exec postgres pg_dump -U a2a_user a2a_dashboard > backup.sql`

## Rollback to SQLite (if needed)

1. Edit `docker-compose.yml` - remove postgres dependency
2. Edit `storage.py` - change back to `sqlite:///a2a_dashboard.db`
3. Edit `requirements.txt` - use `aiosqlite`
4. Rebuild: `docker-compose build app`
