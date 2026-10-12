import hashlib
import importlib
import json
import sqlite3
import zipfile
from pathlib import Path

import pytest
from filelock import FileLock

from app.agents.defaults import seed
from app.core.registry import Registry
from app.database import Database
from app.services.sessions import SessionStore


@pytest.fixture
def source(tmp_path):
    data, workspace = tmp_path / 'source-data', tmp_path / 'source-workspace'
    db = Database(data / 'platform.sqlite')
    seed(Registry(db))
    store = SessionStore(db, workspace)
    project = store.create_project('Portable project')
    session = store.create_session(project['id'], 'Conversation')
    store.upload(project['id'], 'notes.txt', b'Portable evidence\n')
    job = store.submit(session['id'], 'first', 'Remember portability', 'assistant', [])
    db.finish_task(job['id'], 'completed', result='Remembered portability')
    return data, workspace, db, store, project, session


def api():
    return importlib.import_module('app.services.backups')


def bundle(source, tmp_path):
    output = tmp_path / 'snapshot.localagent.zip'
    api().create_bundle(source[0], source[1], output, offline=True)
    return output


def rewrite(path, mutate):
    with zipfile.ZipFile(path) as z:
        entries = {item.filename: z.read(item) for item in z.infolist()}
    manifest = json.loads(entries['manifest.json'])
    mutate(entries, manifest)
    manifest['files'] = [
        {'path': name, 'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()}
        for name, content in entries.items() if name != 'manifest.json'
    ]
    entries['manifest.json'] = json.dumps(manifest).encode()
    with zipfile.ZipFile(path, 'w') as z:
        for name, content in entries.items():
            z.writestr(name, content)


def test_snapshot_and_inspection_preserve_wal_rows_and_file_bytes(source, tmp_path):
    data, workspace, db, store, project, session = source
    # Keep a reader open so committed data can remain in the source WAL.
    connection = db.connect()
    try:
        connection.execute('BEGIN')
        connection.execute('SELECT * FROM tasks').fetchall()
        store.create_session(project['id'], 'A committed WAL row')
        output = bundle(source, tmp_path)
    finally:
        connection.close()
    report = api().inspect_bundle(output)
    assert report['format_version'] == 1
    assert report['counts']['sessions'] == 2
    assert report['counts']['tasks'] == 1
    assert {m['model_name'] for m in report['models']} == {'qwen3:1.7b', 'qwen3:4b'}
    with zipfile.ZipFile(output) as z:
        assert z.read(f"workspace/projects/{project['id']}/notes.txt") == b'Portable evidence\n'
        manifest = json.loads(z.read('manifest.json'))
        for item in manifest['files']:
            assert hashlib.sha256(z.read(item['path'])).hexdigest() == item['sha256']


def test_snapshot_excludes_credentials_runtime_and_links(source, tmp_path):
    workspace = source[1]
    for relative in ['.env', '.ssh/id_rsa', '.venv/private.txt', '.ollama/models/model',
                     'node_modules/package/index.js', 'credentials.json', 'private.pem']:
        path = workspace / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('DO NOT EXPORT')
    try:
        (workspace / 'linked-file').symlink_to(workspace / '.env')
    except OSError:
        pass
    output = bundle(source, tmp_path)
    with zipfile.ZipFile(output) as z:
        assert all(b'DO NOT EXPORT' not in z.read(name) for name in z.namelist())
    report = api().inspect_bundle(output)
    assert any(entry['path'] == '.env' for entry in report['omitted'])
    assert any(entry['path'] == 'node_modules' for entry in report['omitted'])


def test_snapshot_requires_offline_and_preserves_existing_output(source, tmp_path):
    output = tmp_path / 'snapshot.localagent.zip'
    with pytest.raises(ValueError, match='offline'):
        api().create_bundle(source[0], source[1], output)
    assert not output.exists()
    output.write_bytes(b'Existing private backup')
    with pytest.raises(FileExistsError):
        api().create_bundle(source[0], source[1], output, offline=True)
    assert output.read_bytes() == b'Existing private backup'


def test_snapshot_refuses_active_service_or_running_task(source, tmp_path):
    output = tmp_path / 'snapshot.localagent.zip'
    with FileLock(source[0] / 'workspace-service.lock', timeout=0):
        with pytest.raises(ValueError, match='service|offline'):
            api().create_bundle(source[0], source[1], output, offline=True)
    source[2].create_task('A running CLI task')
    with pytest.raises(ValueError, match='running'):
        api().create_bundle(source[0], source[1], output, offline=True)
    assert not output.exists()


@pytest.mark.parametrize('name', [
    'workspace/../../escape.txt', 'workspace/C:/escape.txt', '/absolute.txt',
    'workspace/folder\\escape.txt', 'workspace/CON.txt', 'workspace/.env',
    'workspace/file:stream', 'workspace/trailing. ', 'unexpected/file.txt',
])
def test_inspection_rejects_unsafe_members(source, tmp_path, name):
    output = bundle(source, tmp_path)
    rewrite(output, lambda entries, manifest: entries.update({name: b'bad'}))
    with pytest.raises((ValueError, PermissionError), match='path|member|sensitive|portable'):
        api().inspect_bundle(output)
    assert not (tmp_path / 'escape.txt').exists()


def test_inspection_rejects_hash_mismatch(source, tmp_path):
    output = bundle(source, tmp_path)
    with zipfile.ZipFile(output) as z:
        entries = {name: z.read(name) for name in z.namelist()}
    workspace_file = next(name for name in entries if name.startswith('workspace/'))
    entries[workspace_file] = b'Corrupted evidence'
    with zipfile.ZipFile(output, 'w') as z:
        for name, content in entries.items():
            z.writestr(name, content)
    with pytest.raises(ValueError, match='hash|checksum|size'):
        api().inspect_bundle(output)


def test_inspection_rejects_case_collision_duplicate_and_link(source, tmp_path):
    output = bundle(source, tmp_path)
    rewrite(output, lambda entries, manifest: entries.update({
        'workspace/Case.txt': b'a', 'workspace/case.txt': b'b'}))
    with pytest.raises(ValueError, match='collision|duplicate'):
        api().inspect_bundle(output)
    output.unlink()
    output = bundle(source, tmp_path)
    with zipfile.ZipFile(output, 'a') as z:
        link = zipfile.ZipInfo('workspace/link')
        link.create_system = 3
        link.external_attr = 0o120777 << 16
        z.writestr(link, b'../../escape.txt')
    with pytest.raises(ValueError, match='link|member|regular'):
        api().inspect_bundle(output)
    output.unlink()
    output = bundle(source, tmp_path)
    with pytest.warns(UserWarning, match='Duplicate'):
        with zipfile.ZipFile(output, 'a') as z:
            z.writestr('data/platform.sqlite', b'bad')
    with pytest.raises(ValueError, match='collision|duplicate'):
        api().inspect_bundle(output)


@pytest.mark.parametrize('sql', [
    'PRAGMA user_version=999',
    'CREATE TABLE unsupported (value TEXT)',
    'CREATE TRIGGER surprise AFTER INSERT ON tasks BEGIN DELETE FROM tasks; END',
    'ALTER TABLE tasks ADD COLUMN unsupported TEXT',
])
def test_snapshot_rejects_incompatible_database(source, tmp_path, sql):
    with source[2].connect() as c:
        c.execute(sql)
    with pytest.raises(ValueError, match='schema|version|trigger|table|column'):
        bundle(source, tmp_path)
    assert not (tmp_path / 'snapshot.localagent.zip').exists()


def test_inspection_enforces_real_payload_limits(source, tmp_path, monkeypatch):
    output = bundle(source, tmp_path)
    fmt = importlib.import_module('app.services.backup_format')
    monkeypatch.setattr(fmt, 'MAX_TOTAL_BYTES', 100)
    with pytest.raises(ValueError, match='limit|large'):
        api().inspect_bundle(output)


def test_snapshot_accepts_cli_only_database(tmp_path):
    data, workspace = tmp_path / 'data', tmp_path / 'workspace'
    workspace.mkdir()
    db = Database(data / 'platform.sqlite')
    seed(Registry(db))
    output = tmp_path / 'cli.localagent.zip'
    api().create_bundle(data, workspace, output, offline=True)
    assert api().inspect_bundle(output)['counts']['tasks'] == 0


def test_snapshot_rejects_linked_root(source, tmp_path):
    linked = tmp_path / 'linked'
    try:
        linked.symlink_to(source[1], target_is_directory=True)
    except OSError:
        pytest.skip('symlink privilege unavailable')
    with pytest.raises((ValueError, PermissionError), match='link|reparse'):
        api().create_bundle(source[0], linked, tmp_path / 'snapshot.localagent.zip', offline=True)


def test_snapshot_rejects_changing_file_and_removes_partial_output(source, tmp_path, monkeypatch):
    target = source[1] / 'changing.txt'
    target.write_text('Initial bytes')
    original = zipfile.ZipFile.open

    class ChangingWriter:
        def __init__(self, wrapped):
            self.wrapped = wrapped

        def __enter__(self):
            self.wrapped.__enter__()
            return self

        def __exit__(self, *args):
            return self.wrapped.__exit__(*args)

        def write(self, content):
            result = self.wrapped.write(content)
            target.write_text('Changed while backing up')
            return result

    def intercepted(archive, name, mode='r', *args, **kwargs):
        stream = original(archive, name, mode, *args, **kwargs)
        return ChangingWriter(stream) if name == 'workspace/changing.txt' and mode == 'w' else stream

    monkeypatch.setattr(zipfile.ZipFile, 'open', intercepted)
    with pytest.raises(ValueError, match='changed'):
        bundle(source, tmp_path)
    assert not (tmp_path / 'snapshot.localagent.zip').exists()
    assert target.read_text() == 'Changed while backing up'


def test_snapshot_releases_database_handles(source, tmp_path, monkeypatch):
    fmt = importlib.import_module('app.services.backup_format')
    connections = []
    original = fmt.read_only_db

    def tracked(path):
        connection = original(path)
        connections.append(connection)
        return connection

    monkeypatch.setattr(fmt, 'read_only_db', tracked)
    output = bundle(source, tmp_path)
    api().inspect_bundle(output)
    for connection in connections:
        with pytest.raises(sqlite3.ProgrammingError, match='closed'):
            connection.execute('SELECT 1')


def test_inspection_rejects_modified_database_even_with_matching_hash(source, tmp_path):
    output = bundle(source, tmp_path)

    def add_trigger(entries, manifest):
        database = tmp_path / 'modified.sqlite'
        database.write_bytes(entries['data/platform.sqlite'])
        with sqlite3.connect(database) as connection:
            connection.execute('CREATE TRIGGER unexpected AFTER INSERT ON tasks BEGIN DELETE FROM tasks; END')
        connection.close()
        entries['data/platform.sqlite'] = database.read_bytes()

    rewrite(output, add_trigger)
    with pytest.raises(ValueError, match='trigger'):
        api().inspect_bundle(output)


def test_snapshot_rejects_missing_request_uniqueness(source, tmp_path):
    with source[2].connect() as connection:
        table_sql = connection.execute("SELECT sql FROM sqlite_master WHERE name='web_jobs'").fetchone()[0]
        index_sql = connection.execute("SELECT sql FROM sqlite_master WHERE name='idx_web_jobs_session'").fetchone()[0]
        connection.execute('DROP TABLE web_jobs')
        connection.execute(table_sql.replace('UNIQUE(session_id, request_key)', 'CHECK(1)'))
        connection.execute(index_sql)
    with pytest.raises(ValueError, match='schema|index|constraint'):
        bundle(source, tmp_path)


def test_snapshot_rejects_hidden_generated_column(source, tmp_path):
    with source[2].connect() as connection:
        connection.execute('ALTER TABLE tasks ADD COLUMN hidden_extra TEXT GENERATED ALWAYS AS (user_request) VIRTUAL')
    with pytest.raises(ValueError, match='schema|column'):
        bundle(source, tmp_path)


def test_inspection_rejects_case_colliding_directory_prefixes(source, tmp_path):
    output = bundle(source, tmp_path)
    rewrite(output, lambda entries, manifest: entries.update({
        'workspace/Folder/a.txt': b'a', 'workspace/folder/b.txt': b'b'}))
    with pytest.raises(ValueError, match='collision|colliding'):
        api().inspect_bundle(output)
