"""
Persistent Storage Layer for A2A Multi-Agent System
Uses SQLite for task history, logs, and artifact metadata
"""
import databases
import aiosqlite
from datetime import datetime
from typing import Dict, List, Optional, Any
import json


class PersistentStorage:
    """
    Handles persistent storage of tasks, logs, and artifacts
    Uses SQLite with async support
    """

    def __init__(self, db_path: str = "a2a_dashboard.db"):
        """
        Initialize database connection
        """
        self.database = databases.Database(f"sqlite:///{db_path}")
        self.db_path = db_path

    async def init_db(self):
        """
        Initialize database schema
        Creates tables if they don't exist
        """
        await self.database.execute("""
            CREATE TABLE IF NOT EXISTS artifacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                s3_key TEXT NOT NULL,
                s3_url TEXT NOT NULL,
                presigned_url TEXT NOT NULL,
                bucket TEXT NOT NULL,
                size INTEGER NOT NULL,
                content_type TEXT NOT NULL,
                tags TEXT,
                description TEXT,
                uploaded_at TEXT NOT NULL,
                metadata TEXT
            )
        """)

        await self.database.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                agent_name TEXT,
                status TEXT NOT NULL,
                request TEXT NOT NULL,
                result TEXT,
                error TEXT,
                artifacts TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT,
                metadata TEXT
            )
        """)

        await self.database.execute("""
            CREATE TABLE IF NOT EXISTS agent_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                agent_name TEXT,
                task_id TEXT,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                metadata TEXT
            )
        """)

        # Create indexes for common queries
        await self.database.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_agent_id
            ON tasks(agent_id)
        """)

        await self.database.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_status
            ON tasks(status)
        """)

        await self.database.execute("""
            CREATE INDEX IF NOT EXISTS idx_logs_agent_id
            ON agent_logs(agent_id)
        """)

        await self.database.execute("""
            CREATE INDEX IF NOT EXISTS idx_logs_task_id
            ON agent_logs(task_id)
        """)

    async def save_artifact(
        self,
        filename: str,
        s3_key: str,
        s3_url: str,
        presigned_url: str,
        bucket: str,
        size: int,
        content_type: str,
        tags: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Save artifact metadata to database

        Returns:
            artifact_id
        """
        query = """
            INSERT INTO artifacts
            (filename, s3_key, s3_url, presigned_url, bucket, size, content_type,
             tags, description, uploaded_at, metadata)
            VALUES
            (:filename, :s3_key, :s3_url, :presigned_url, :bucket, :size, :content_type,
             :tags, :description, :uploaded_at, :metadata)
        """

        values = {
            "filename": filename,
            "s3_key": s3_key,
            "s3_url": s3_url,
            "presigned_url": presigned_url,
            "bucket": bucket,
            "size": size,
            "content_type": content_type,
            "tags": tags,
            "description": description,
            "uploaded_at": datetime.utcnow().isoformat(),
            "metadata": json.dumps(metadata) if metadata else None
        }

        return await self.database.execute(query=query, values=values)

    async def get_artifacts(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get all artifacts with pagination

        Returns:
            List of artifact records
        """
        query = """
            SELECT * FROM artifacts
            ORDER BY uploaded_at DESC
            LIMIT :limit OFFSET :offset
        """

        rows = await self.database.fetch_all(
            query=query,
            values={"limit": limit, "offset": offset}
        )

        return [dict(row) for row in rows]

    async def save_task(
        self,
        task_id: str,
        agent_id: str,
        agent_name: Optional[str],
        status: str,
        request: str,
        result: Optional[str] = None,
        error: Optional[str] = None,
        artifacts: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Save or update task in database

        Returns:
            task_id
        """
        now = datetime.utcnow().isoformat()

        # Check if task exists
        existing = await self.database.fetch_one(
            "SELECT id FROM tasks WHERE id = :task_id",
            values={"task_id": task_id}
        )

        if existing:
            # Update existing task
            query = """
                UPDATE tasks
                SET status = :status,
                    result = :result,
                    error = :error,
                    artifacts = :artifacts,
                    updated_at = :updated_at,
                    completed_at = :completed_at,
                    metadata = :metadata
                WHERE id = :task_id
            """

            values = {
                "task_id": task_id,
                "status": status,
                "result": result,
                "error": error,
                "artifacts": json.dumps(artifacts) if artifacts else None,
                "updated_at": now,
                "completed_at": now if status in ["completed", "error"] else None,
                "metadata": json.dumps(metadata) if metadata else None
            }
        else:
            # Insert new task
            query = """
                INSERT INTO tasks
                (id, agent_id, agent_name, status, request, result, error,
                 artifacts, created_at, updated_at, completed_at, metadata)
                VALUES
                (:task_id, :agent_id, :agent_name, :status, :request, :result, :error,
                 :artifacts, :created_at, :updated_at, :completed_at, :metadata)
            """

            values = {
                "task_id": task_id,
                "agent_id": agent_id,
                "agent_name": agent_name,
                "status": status,
                "request": request,
                "result": result,
                "error": error,
                "artifacts": json.dumps(artifacts) if artifacts else None,
                "created_at": now,
                "updated_at": now,
                "completed_at": now if status in ["completed", "error"] else None,
                "metadata": json.dumps(metadata) if metadata else None
            }

        await self.database.execute(query=query, values=values)
        return task_id

    async def get_tasks(
        self,
        agent_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get tasks with optional filters

        Returns:
            List of task records
        """
        conditions = []
        values = {"limit": limit, "offset": offset}

        if agent_id:
            conditions.append("agent_id = :agent_id")
            values["agent_id"] = agent_id

        if status:
            conditions.append("status = :status")
            values["status"] = status

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        query = f"""
            SELECT * FROM tasks
            {where_clause}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """

        rows = await self.database.fetch_all(query=query, values=values)

        # Parse JSON fields
        tasks = []
        for row in rows:
            task = dict(row)
            if task.get('artifacts'):
                task['artifacts'] = json.loads(task['artifacts'])
            if task.get('metadata'):
                task['metadata'] = json.loads(task['metadata'])
            tasks.append(task)

        return tasks

    async def get_task_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a single task by ID

        Returns:
            Task record or None
        """
        query = "SELECT * FROM tasks WHERE id = :task_id"
        row = await self.database.fetch_one(query=query, values={"task_id": task_id})

        if not row:
            return None

        task = dict(row)
        if task.get('artifacts'):
            task['artifacts'] = json.loads(task['artifacts'])
        if task.get('metadata'):
            task['metadata'] = json.loads(task['metadata'])

        return task

    async def save_log(
        self,
        agent_id: str,
        agent_name: Optional[str],
        level: str,
        message: str,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Save agent log entry

        Returns:
            log_id
        """
        query = """
            INSERT INTO agent_logs
            (agent_id, agent_name, task_id, level, message, timestamp, metadata)
            VALUES
            (:agent_id, :agent_name, :task_id, :level, :message, :timestamp, :metadata)
        """

        values = {
            "agent_id": agent_id,
            "agent_name": agent_name,
            "task_id": task_id,
            "level": level,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": json.dumps(metadata) if metadata else None
        }

        return await self.database.execute(query=query, values=values)

    async def get_logs(
        self,
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None,
        level: Optional[str] = None,
        limit: int = 500,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get logs with optional filters

        Returns:
            List of log records
        """
        conditions = []
        values = {"limit": limit, "offset": offset}

        if agent_id:
            conditions.append("agent_id = :agent_id")
            values["agent_id"] = agent_id

        if task_id:
            conditions.append("task_id = :task_id")
            values["task_id"] = task_id

        if level:
            conditions.append("level = :level")
            values["level"] = level

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        query = f"""
            SELECT * FROM agent_logs
            {where_clause}
            ORDER BY timestamp DESC
            LIMIT :limit OFFSET :offset
        """

        rows = await self.database.fetch_all(query=query, values=values)

        # Parse JSON fields
        logs = []
        for row in rows:
            log = dict(row)
            if log.get('metadata'):
                log['metadata'] = json.loads(log['metadata'])
            logs.append(log)

        return logs
