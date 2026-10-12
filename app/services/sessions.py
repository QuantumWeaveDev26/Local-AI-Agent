"""Project-scoped conversations and durable web submissions, using the shared DB."""
from contextlib import closing
import hashlib
import json
import uuid
from pathlib import Path

from app.database import now, redact, redact_data
from app.tools.workspace import Workspace


def label(value, maximum=120):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f'text must contain 1 to {maximum} characters')
    return redact(value.strip())


class SessionStore:
    def __init__(self, db, workspace):
        self.db = db
        self.root = Workspace(workspace)
        with closing(db.connect()) as c, c:
            c.executescript('''
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
                    title TEXT NOT NULL, created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS web_jobs (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT UNIQUE NOT NULL REFERENCES tasks(id),
                    session_id TEXT NOT NULL REFERENCES sessions(id), request_key TEXT NOT NULL,
                    payload TEXT NOT NULL, payload_digest TEXT, cancel_requested INTEGER NOT NULL DEFAULT 0,
                    UNIQUE(session_id, request_key));
                CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project_id);
                CREATE INDEX IF NOT EXISTS idx_web_jobs_session ON web_jobs(session_id, sequence);
            ''')
            columns = {row['name'] for row in c.execute('PRAGMA table_info(web_jobs)')}
            if 'payload_digest' not in columns:
                c.execute('ALTER TABLE web_jobs ADD COLUMN payload_digest TEXT')
            # Older workspace builds stored redacted keys/content only. Preserve jobs
            # and compare their retained input conservatively; never recover secrets.
            for row in c.execute('SELECT sequence,request_key,payload FROM web_jobs WHERE payload_digest IS NULL').fetchall():
                digest = hashlib.sha256(row['payload'].encode('utf-8')).hexdigest()
                key_digest = hashlib.sha256(row['request_key'].encode('utf-8')).hexdigest()
                c.execute('UPDATE web_jobs SET request_key=?,payload_digest=? WHERE sequence=?', (key_digest, digest, row['sequence']))

    def projects(self):
        with closing(self.db.connect()) as c, c:
            return [dict(r) for r in c.execute('SELECT * FROM projects ORDER BY created_at')]

    def project(self, project_id):
        with closing(self.db.connect()) as c, c:
            row = c.execute('SELECT * FROM projects WHERE id=?', (project_id,)).fetchone()
        if not row:
            raise ValueError('unknown project')
        return dict(row)

    def create_project(self, name):
        name = label(name)
        project_id = uuid.uuid4().hex
        with closing(self.db.connect()) as c, c:
            c.execute('INSERT INTO projects VALUES(?,?,?)', (project_id, name, now()))
        return self.project(project_id)

    def workspace(self, project_id):
        self.project(project_id)
        return Workspace(self.root.path(f'projects/{project_id}'))

    def sessions(self, project_id):
        self.project(project_id)
        with closing(self.db.connect()) as c, c:
            return [dict(r) for r in c.execute('SELECT * FROM sessions WHERE project_id=? ORDER BY created_at', (project_id,))]

    def session(self, session_id):
        with closing(self.db.connect()) as c, c:
            row = c.execute('SELECT * FROM sessions WHERE id=?', (session_id,)).fetchone()
        if not row:
            raise ValueError('unknown session')
        return dict(row)

    def create_session(self, project_id, title):
        self.project(project_id)
        session_id = uuid.uuid4().hex
        with closing(self.db.connect()) as c, c:
            c.execute('INSERT INTO sessions VALUES(?,?,?,?)', (session_id, project_id, label(title), now()))
        return self.session(session_id)

    def submit(self, session_id, key, prompt, agent_id=None, attachments=None, *, validate=None):
        session = self.session(session_id)
        label(key, 128)
        key = hashlib.sha256(key.strip().encode('utf-8')).hexdigest()
        raw_prompt, raw_agent_id = prompt, agent_id
        prompt = label(prompt, 20_000)
        if agent_id is not None:
            agent_id = label(agent_id, 64)
        if not isinstance(attachments, list) or len(attachments) > 8 or any(not isinstance(p, str) for p in attachments):
            raise ValueError('attachments must be a list of at most eight paths')
        original = json.dumps({'prompt': raw_prompt, 'agent_id': raw_agent_id, 'attachments': attachments}, sort_keys=True)
        digest = hashlib.sha256(original.encode('utf-8')).hexdigest()
        payload = json.dumps(redact_data({'prompt': prompt, 'agent_id': agent_id, 'attachments': attachments}), sort_keys=True)
        with closing(self.db.connect()) as c, c:
            c.execute('BEGIN IMMEDIATE')
            previous = c.execute('SELECT task_id,payload_digest FROM web_jobs WHERE session_id=? AND request_key=?', (session_id, key)).fetchone()
            if previous:
                if previous['payload_digest'] != digest:
                    raise ValueError('request key already used with different input')
                task_id = previous['task_id']
            else:
                if validate:
                    validate()
                workspace = self.workspace(session['project_id'])
                for path in attachments:
                    target = workspace.path(path)
                    if not target.is_file():
                        raise FileNotFoundError('attachment not found')
                    if target.stat().st_size > workspace.max_bytes:
                        raise ValueError('attachment is too large')
                count = c.execute("SELECT count(*) FROM web_jobs j JOIN tasks t ON t.id=j.task_id WHERE t.status IN ('queued','running')").fetchone()[0]
                if count >= 100:
                    raise ValueError('queue is full; wait for existing tasks')
                task_id = uuid.uuid4().hex
                c.execute('INSERT INTO tasks(id,user_request,status,created_at) VALUES(?,?,?,?)', (task_id, prompt, 'queued', now()))
                c.execute('INSERT INTO web_jobs(task_id,session_id,request_key,payload,payload_digest) VALUES(?,?,?,?,?)', (task_id, session_id, key, payload, digest))
        return self.task(task_id)

    def history(self, session_id):
        self.session(session_id)
        with closing(self.db.connect()) as c, c:
            rows = c.execute('''SELECT t.*,j.cancel_requested,j.request_key AS request_key_digest FROM web_jobs j JOIN tasks t ON t.id=j.task_id
                WHERE j.session_id=? ORDER BY j.sequence DESC LIMIT 1000''', (session_id,)).fetchall()
        return [dict(r) for r in reversed(rows)]

    def context(self, session_id):
        # Only completed turns, assembled when dequeued rather than when submitted.
        with closing(self.db.connect()) as c, c:
            rows = c.execute('''SELECT t.user_request,t.result FROM web_jobs j JOIN tasks t ON t.id=j.task_id
                WHERE j.session_id=? AND t.status='completed' ORDER BY j.sequence DESC LIMIT 6''', (session_id,)).fetchall()
        messages, remaining = [], 12_000
        for row in rows:
            for role, content in [('assistant', row['result']), ('user', row['user_request'])]:
                text = (content or '')[-min(remaining, 2000):] if remaining else ''
                if text:
                    messages.append({'role': role, 'content': text})
                    remaining -= len(text)
        return list(reversed(messages))

    def job(self, task_id):
        with closing(self.db.connect()) as c, c:
            row = c.execute('SELECT * FROM web_jobs WHERE task_id=?', (task_id,)).fetchone()
        if not row:
            raise ValueError('unknown workspace task')
        result = dict(row)
        result['payload'] = json.loads(result['payload'])
        return result

    def task(self, task_id):
        job = self.job(task_id)
        return {**self.db.task(task_id), 'session_id': job['session_id'], 'cancel_requested': bool(job['cancel_requested'])}

    def cancel(self, task_id):
        self.job(task_id)
        with closing(self.db.connect()) as c, c:
            c.execute('BEGIN IMMEDIATE')
            status = c.execute('SELECT status FROM tasks WHERE id=?', (task_id,)).fetchone()[0]
            if status in ('queued', 'running'):
                c.execute('UPDATE web_jobs SET cancel_requested=1 WHERE task_id=?', (task_id,))
            if status == 'queued':
                c.execute("UPDATE tasks SET status='cancelled',completed_at=? WHERE id=?", (now(), task_id))
        return self.task(task_id)

    def upload(self, project_id, path, content):
        workspace = self.workspace(project_id)
        target = workspace.path(path)
        if target.suffix.lower() not in ('.txt', '.md', '.pdf', '.docx'):
            raise ValueError('uploads support TXT, MD, PDF and DOCX')
        if len(content) > workspace.max_bytes:
            raise ValueError('upload is too large')
        target.parent.mkdir(parents=True, exist_ok=True)
        target = workspace.path(path)
        with target.open('xb') as f:
            f.write(content)
        return {'path': str(target.relative_to(workspace.root)).replace('\\', '/'), 'bytes': len(content)}

    def files(self, project_id):
        workspace = self.workspace(project_id)
        files = []
        for path in workspace.root.rglob('*'):
            relative = path.relative_to(workspace.root).as_posix()
            try:
                safe = workspace.path(relative)
                if safe.is_file():
                    files.append({'path': relative, 'bytes': safe.stat().st_size})
            except (PermissionError, OSError):
                continue
            if len(files) >= 1000:
                break
        return sorted(files, key=lambda f: f['path'])
