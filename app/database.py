"""SQLite persistence with parameter binding and centralized secret redaction."""
import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

EVENT_TABLES = ('task_runs', 'messages', 'outputs', 'tool_calls', 'errors')


def now():
    return datetime.now(timezone.utc).isoformat()


def redact(value):
    text = str(value)
    for key, secret in os.environ.items():
        if any(word in key.upper() for word in ('TOKEN', 'PASSWORD', 'SECRET', 'API_KEY')) and len(secret) >= 8:
            text = text.replace(secret, '[REDACTED]')
    text = re.sub(r'(?i)(Bearer\s+)[^\s"\']+', r'\1[REDACTED]', text)
    text = re.sub(r'\bsk-[A-Za-z0-9_-]{12,}', '[REDACTED]', text)
    return text


def redact_data(value):
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, dict):
        safe = {}
        for key, child in value.items():
            safe_key = redact(str(key))
            unique_key = safe_key
            suffix = 1
            while unique_key in safe:
                unique_key = f'{safe_key}#{suffix}'
                suffix += 1
            safe[unique_key] = redact_data(child)
        return safe
    if isinstance(value, list):
        return [redact_data(v) for v in value]
    return value


class Database:
    def __init__(self, path):
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as c:
            c.execute('PRAGMA journal_mode=WAL')
            for table in ('models', 'agents', 'tools'):
                c.execute(f'CREATE TABLE IF NOT EXISTS {table} (id TEXT PRIMARY KEY, data TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)')
            c.execute('''CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY, user_request TEXT NOT NULL, assigned_agent_id TEXT,
                status TEXT NOT NULL, created_at TEXT NOT NULL, completed_at TEXT,
                result TEXT, error TEXT)''')
            for table in EVENT_TABLES:
                c.execute(f'''CREATE TABLE IF NOT EXISTS {table} (
                    id INTEGER PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(id),
                    data TEXT NOT NULL, created_at TEXT NOT NULL)''')
                c.execute(f'CREATE INDEX IF NOT EXISTS idx_{table}_task ON {table}(task_id)')

    def connect(self):
        c = sqlite3.connect(self.path, timeout=30)
        c.row_factory = sqlite3.Row
        c.execute('PRAGMA foreign_keys=ON')
        return c

    def create_task(self, request):
        task_id = uuid.uuid4().hex
        with self.connect() as c:
            c.execute('INSERT INTO tasks(id,user_request,status,created_at) VALUES(?,?,?,?)',
                      (task_id, redact(request), 'running', now()))
        return task_id

    def assign(self, task_id, agent_id):
        with self.connect() as c:
            c.execute('UPDATE tasks SET assigned_agent_id=? WHERE id=?', (agent_id, task_id))

    def event(self, table, task_id, data):
        if table not in EVENT_TABLES:
            raise ValueError('unknown event table')
        safe_data = json.dumps(redact_data(data), ensure_ascii=False, default=str)
        with self.connect() as c:
            c.execute(f'INSERT INTO {table}(task_id,data,created_at) VALUES(?,?,?)', (task_id, safe_data, now()))

    def finish_task(self, task_id, status, result=None, error=None):
        with self.connect() as c:
            c.execute('UPDATE tasks SET status=?,result=?,error=?,completed_at=? WHERE id=?',
                      (status, redact(result) if result is not None else None,
                       redact(error) if error is not None else None, now(), task_id))

    def task(self, task_id):
        with self.connect() as c:
            row = c.execute('SELECT * FROM tasks WHERE id=?', (task_id,)).fetchone()
            if row is None:
                raise ValueError(f'unknown task: {task_id}')
            record = dict(row)
            for table in EVENT_TABLES:
                record[table] = [dict(r) for r in c.execute(f'SELECT * FROM {table} WHERE task_id=? ORDER BY id', (task_id,))]
                for event in record[table]:
                    event['data'] = json.loads(event['data'])
            return record
