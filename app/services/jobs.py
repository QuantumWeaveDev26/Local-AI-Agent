"""Single durable workspace queue; uncertain actions are never replayed."""
import threading

from app.database import now
from app.services.tasks import TaskService
from app.tools.workspace import ToolExecutor


class JobWorker:
    def __init__(self, store, registry, llm):
        self.store, self.registry, self.llm = store, registry, llm
        self.stop = threading.Event()
        self.thread = None
        # The service process holds its lock before constructing this worker.
        with store.db.connect() as c:
            c.execute('''UPDATE tasks SET status='interrupted',completed_at=?,
                error='Service stopped during execution; review receipts before resubmitting'
                WHERE status='running' AND id IN (SELECT task_id FROM web_jobs)''', (now(),))

    def run_next(self):
        with self.store.db.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row = c.execute('''SELECT j.task_id FROM web_jobs j JOIN tasks t ON t.id=j.task_id
                WHERE t.status='queued' ORDER BY j.sequence LIMIT 1''').fetchone()
            if row is None:
                return False
            task_id = row['task_id']
            c.execute("UPDATE tasks SET status='running' WHERE id=?", (task_id,))
        try:
            job = self.store.job(task_id)
            session = self.store.session(job['session_id'])
            payload = job['payload']
            service = TaskService(self.registry, ToolExecutor(self.store.workspace(session['project_id'])), self.llm)
            service.run(payload['prompt'], agent_id=payload['agent_id'], attachments=payload['attachments'],
                        task_id=task_id, history=self.store.context(session['id']),
                        cancelled=lambda: self.stop.is_set() or bool(self.store.job(task_id)['cancel_requested']))
        except Exception as error:
            self.store.db.event('errors', task_id, {'error': str(error)})
            self.store.db.finish_task(task_id, 'failed', error=str(error))
        return True

    def start(self):
        def loop():
            while not self.stop.is_set():
                if not self.run_next():
                    self.stop.wait(0.25)
        self.thread = threading.Thread(target=loop, name='workspace-worker', daemon=True)
        self.thread.start()

    def close(self):
        self.stop.set()
        if self.thread:
            self.thread.join()
