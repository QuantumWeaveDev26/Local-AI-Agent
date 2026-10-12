"""Retain real SQLite handles so garbage collection cannot hide leaked locks."""
import sqlite3

import pytest

from app.agents.defaults import seed
from app.core.registry import Registry
from app.database import Database
from app.services.backup_format import _expected_schema
from app.services.jobs import JobWorker
from app.services.sessions import SessionStore


@pytest.fixture
def connections(monkeypatch):
    original = sqlite3.connect
    retained = []

    def capture(*args, **kwargs):
        connection = original(*args, **kwargs)
        retained.append(connection)
        return connection

    monkeypatch.setattr(sqlite3, 'connect', capture)
    yield retained
    for connection in retained:
        connection.close()


def assert_closed(connections):
    assert connections
    for connection in connections:
        with pytest.raises(sqlite3.ProgrammingError, match='closed database'):
            connection.execute('SELECT 1')


def test_schema_reference_releases_all_database_handles(connections):
    _expected_schema.cache_clear()
    try:
        tables, indexes = _expected_schema()
        assert 'web_jobs' in tables
        assert 'idx_sessions_project' in indexes
        assert_closed(connections)
    finally:
        _expected_schema.cache_clear()


def test_database_operations_close_handles_and_preserve_transactions(tmp_path, connections):
    db = Database(tmp_path / 'platform.sqlite')
    registry = Registry(db)
    seed(registry)
    model = registry.get_model('local')
    with pytest.raises(ValueError, match='already exists'):
        registry.add_model(model)
    assert registry.get_model('local') == model
    store = SessionStore(db, tmp_path / 'workspace')
    project = store.create_project('Lock regression')
    session = store.create_session(project['id'], 'Conversation')
    job = store.submit(session['id'], 'request-1', 'Hello', 'marketing', [])
    db.assign(job['id'], 'marketing')
    db.event('messages', job['id'], {'content': 'Committed message'})
    db.finish_task(job['id'], 'completed', result='Committed result')
    assert db.task(job['id'])['result'] == 'Committed result'
    assert store.context(session['id'])
    worker = JobWorker(store, registry, None)
    assert worker.run_next() is False
    assert_closed(connections)
