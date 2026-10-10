"""Real persistence/scope tests; inference fixture exists only in tests."""
import concurrent.futures
import json

import pytest

from app.agents.defaults import seed
from app.core.llm import Response
from app.core.registry import Registry
from app.database import Database
from app.services.sessions import SessionStore
from app.services.jobs import JobWorker


class ScriptedLLM:
    def __init__(self, replies):
        self.replies = iter(replies)
        self.calls = []

    def chat(self, model, messages, tools=None, schema=None):
        self.calls.append(list(messages))
        reply = next(self.replies)
        return reply() if callable(reply) else reply


@pytest.fixture
def setup(tmp_path):
    db = Database(tmp_path / 'data' / 'platform.sqlite')
    registry = Registry(db)
    seed(registry)
    store = SessionStore(db, tmp_path / 'workspace')
    project = store.create_project('My project')
    session = store.create_session(project['id'], 'Conversation')
    return store, registry, project, session


def submit(store, session, key='one', prompt='My name is Alex', **kwargs):
    return store.submit(session['id'], key, prompt, kwargs.pop('agent_id', 'marketing'), kwargs.pop('attachments', []))


def test_duplicate_concurrent_submission_is_one_task(setup):
    store, _, _, session = setup
    with concurrent.futures.ThreadPoolExecutor(4) as pool:
        ids = list(pool.map(lambda _: submit(store, session)['id'], range(8)))
    assert len(set(ids)) == 1
    assert len(store.history(session['id'])) == 1
    with pytest.raises(ValueError, match='different'):
        submit(store, session, prompt='different request')


def test_distinct_secret_inputs_still_conflict_without_persisting_secrets(setup):
    store, _, _, session = setup
    first = submit(store, session, prompt='Use Bearer abcdefghijklmnop')
    with pytest.raises(ValueError, match='different'):
        submit(store, session, prompt='Use Bearer differentsecret')
    assert 'abcdefghijklmnop' not in json.dumps(store.task(first['id']))
    with store.db.connect() as c:
        assert 'abcdefghijklmnop' not in c.execute('SELECT payload FROM web_jobs').fetchone()[0]


def test_context_survives_restart_and_is_project_scoped(setup):
    store, registry, project, session = setup
    first = submit(store, session)
    second = submit(store, session, 'two', 'What is my name?')
    llm = ScriptedLLM([Response('Hello Alex'), Response('Your name is Alex'), Response('Other project')])
    worker = JobWorker(store, registry, llm)
    assert worker.run_next()
    restored = SessionStore(Database(store.db.path), store.root.root)
    worker = JobWorker(restored, registry, llm)
    assert worker.run_next()
    assert {'role': 'assistant', 'content': 'Hello Alex'} in llm.calls[1]
    assert restored.task(first['id'])['result'] == 'Hello Alex'
    assert restored.task(second['id'])['status'] == 'completed'
    other = restored.create_project('Other')
    other_session = restored.create_session(other['id'], 'Other conversation')
    submit(restored, other_session)
    assert worker.run_next()
    assert 'Hello Alex' not in json.dumps(llm.calls[2])
    assert restored.workspace(project['id']).root != restored.workspace(other['id']).root


def test_manager_receives_previous_turns(setup):
    store, registry, _, session = setup
    submit(store, session)
    llm = ScriptedLLM([Response('Hello Alex'), Response('{"reason":"Follow up","agent_id":"marketing"}'), Response('Alex')])
    worker = JobWorker(store, registry, llm)
    worker.run_next()
    submit(store, session, 'two', 'Who am I?', agent_id=None)
    worker.run_next()
    assert 'Hello Alex' in json.dumps(llm.calls[1])
    assert store.history(session['id'])[-1]['result'] == 'Alex'


def test_restart_interrupts_running_jobs_without_replay(setup):
    store, registry, _, session = setup
    task = submit(store, session)
    with store.db.connect() as c:
        c.execute("UPDATE tasks SET status='running' WHERE id=?", (task['id'],))
    worker = JobWorker(store, registry, ScriptedLLM([]))
    assert store.task(task['id'])['status'] == 'interrupted'
    assert not worker.run_next()


def test_cancel_queued_never_calls_model(setup):
    store, registry, _, session = setup
    task = submit(store, session)
    store.cancel(task['id'])
    worker = JobWorker(store, registry, ScriptedLLM([]))
    assert not worker.run_next()
    assert store.task(task['id'])['status'] == 'cancelled'


def test_running_cancel_prevents_tool_after_inference(setup):
    store, registry, project, session = setup
    task = submit(store, session)
    def cancel_then_write():
        store.cancel(task['id'])
        return Response('', [{'id': 'x', 'name': 'filesystem_write', 'arguments': {'path': 'bad.txt', 'content': 'bad'}}])
    worker = JobWorker(store, registry, ScriptedLLM([cancel_then_write]))
    worker.run_next()
    assert store.task(task['id'])['status'] == 'cancelled'
    assert not (store.workspace(project['id']).root / 'bad.txt').exists()


def test_files_are_scoped_and_existing_uploads_are_preserved(setup):
    store, registry, project, session = setup
    store.upload(project['id'], 'cv.txt', b'Alex knows Python')
    with pytest.raises(FileExistsError):
        store.upload(project['id'], 'cv.txt', b'overwrite')
    with pytest.raises(PermissionError):
        store.upload(project['id'], '../outside.txt', b'bad')
    with pytest.raises(ValueError):
        store.upload(project['id'], 'large.txt', b'x' * 5_000_001)
    with pytest.raises(ValueError):
        store.upload(project['id'], 'run.exe', b'bad')
    assert store.files(project['id']) == [{'path': 'cv.txt', 'bytes': 17}]
    task = submit(store, session, attachments=['cv.txt'])
    llm = ScriptedLLM([Response('Python')])
    JobWorker(store, registry, llm).run_next()
    assert 'Alex knows Python' in json.dumps(llm.calls)
    assert store.task(task['id'])['tool_calls'][0]['data']['tool_id'] == 'document_read'
    other = store.create_project('Other')
    assert store.files(other['id']) == []


def test_history_context_is_bounded(setup):
    store, _, _, session = setup
    for i in range(15):
        task = submit(store, session, str(i), 'prompt' * 2000)
        store.db.finish_task(task['id'], 'completed', result='answer' * 2000)
    messages = store.context(session['id'])
    assert len(messages) <= 12
    assert sum(len(m['content']) for m in messages) <= 12_000
    assert messages[-1]['role'] == 'assistant'


def test_invalid_session_and_missing_file_fail_before_queue(setup):
    store, _, _, session = setup
    with pytest.raises(ValueError):
        store.submit('missing', 'one', 'hello', 'marketing', [])
    with pytest.raises(FileNotFoundError):
        submit(store, session, attachments=['missing.txt'])
    assert store.history(session['id']) == []
