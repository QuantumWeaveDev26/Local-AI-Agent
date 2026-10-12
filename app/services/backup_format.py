"""Portable private-bundle validation; archive contents never execute code."""
import hashlib
import json
import re
import sqlite3
import stat
import tempfile
import zipfile
from contextlib import closing
from functools import lru_cache
from pathlib import Path

from app.core.schemas import Agent, Model, Tool

FORMAT = 'local-ai-agent-backup'
FORMAT_VERSION = 1
MAX_FILES = 10_000
MAX_FILE_BYTES = 512 * 1024**2
MAX_TOTAL_BYTES = 2 * 1024**3
MAX_MANIFEST_BYTES = 1024**2
CHUNK_BYTES = 1024**2
EXCLUDED_NAMES = {
    '.git', '.ssh', '.aws', '.codex', '.agents', '.gnupg', '.venv', 'venv',
    'node_modules', '.cache', '__pycache__', '.ollama', 'models', 'credentials',
    'id_rsa', 'id_ed25519', '.pytest_cache',
}
# Win32 also reserves console devices, superscript port digits and spaces before
# an extension. Apply the rule on every host, without deprecated pathlib APIs.
RESERVED = re.compile(r'^(con|prn|aux|nul|conin\$|conout\$|com[0-9¹²³]|lpt[0-9¹²³]) *(?:\.|$)', re.I)


def excluded(name):
    lower = name.casefold()
    return (lower in EXCLUDED_NAMES or lower.startswith('.env')
            or lower.startswith('credentials.')
            or Path(lower).suffix in {'.pem', '.key', '.p12', '.pfx', '.kdbx', '.jks'}
            or lower.endswith('.localagent.zip'))


def portable_path(name):
    """Return canonical relative parts or reject portable/sensitive path syntax."""
    if not isinstance(name, str) or not name or '\\' in name or ':' in name:
        raise ValueError('invalid portable path')
    parts = name.split('/')
    if any(not part or part in ('.', '..') or part.endswith(('.', ' '))
           or any(ord(c) < 32 or c in '<>"|?*' for c in part)
           or RESERVED.match(part) for part in parts):
        raise ValueError('invalid portable path')
    if any(excluded(part) for part in parts):
        raise ValueError('sensitive or runtime path is not a bundle member')
    return parts


def register_path(name, aliases):
    """Reject case aliases and file/directory conflicts at every prefix."""
    parts = name.split('/')
    for length in range(1, len(parts) + 1):
        prefix = '/'.join(parts[:length])
        key = prefix.casefold()
        is_file = length == len(parts)
        if key in aliases and aliases[key] != (prefix, is_file):
            raise ValueError('case-colliding or file/directory path collision')
        aliases[key] = (prefix, is_file)


def checked_path(path):
    """Reject links/reparse ancestors before resolving a host path."""
    path = Path(path).absolute()
    for part in (path, *path.parents):
        if part.exists() or part.is_symlink():
            metadata = part.lstat()
            if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, 'st_file_attributes', 0) & 0x400:
                raise ValueError('links and reparse paths are not supported')
    return path


def read_only_db(path):
    connection = sqlite3.connect(Path(path).absolute().as_uri() + '?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA trusted_schema=OFF')
    connection.execute('PRAGMA query_only=ON')
    return connection


def _schema(connection):
    objects = connection.execute('SELECT type,name,tbl_name,sql FROM sqlite_master').fetchall()
    if any(row['type'] in ('trigger', 'view') for row in objects):
        raise ValueError('unsupported database trigger or view schema')
    tables, indexes = {}, {}
    for row in objects:
        name = row['name']
        if row['type'] == 'table':
            # Names originate in SQLite metadata: bind through table-valued pragmas.
            columns = {r['name']: (r['type'], r['notnull'], r['dflt_value'], r['pk'], r['hidden'])
                       for r in connection.execute('SELECT * FROM pragma_table_xinfo(?)', (name,))}
            foreign_keys = [tuple(r) for r in connection.execute('SELECT * FROM pragma_foreign_key_list(?)', (name,))]
            constraints = []
            for index in connection.execute('SELECT * FROM pragma_index_list(?)', (name,)):
                names = tuple(r['name'] for r in connection.execute('SELECT * FROM pragma_index_info(?)', (index['name'],)))
                constraints.append((index['unique'], index['origin'], index['partial'], names))
            tables[name] = {'columns': columns, 'foreign_keys': foreign_keys,
                            'constraints': sorted(constraints)}
        elif row['type'] == 'index' and row['sql'] is not None:
            indexes[name] = ' '.join(row['sql'].split()).casefold()
    return tables, indexes


@lru_cache(maxsize=1)
def _expected_schema():
    from app.database import Database
    from app.services.sessions import SessionStore
    with tempfile.TemporaryDirectory(prefix='local-agent-schema-') as directory:
        db = Database(Path(directory) / 'platform.sqlite')
        SessionStore(db, Path(directory) / 'workspace')
        with closing(db.connect()) as connection:
            return _schema(connection)


def validate_database(path):
    """Inspect current known schema and registry without running imported triggers."""
    try:
        with closing(read_only_db(path)) as connection:
            if connection.execute('PRAGMA user_version').fetchone()[0] != 0:
                raise ValueError('unsupported database schema version')
            actual_tables, actual_indexes = _schema(connection)
            expected_tables, expected_indexes = _expected_schema()
            optional = {'projects', 'sessions', 'web_jobs', 'sqlite_sequence'}
            required = set(expected_tables) - optional
            present = set(actual_tables)
            if not required <= present or present - set(expected_tables):
                raise ValueError('unsupported database table schema')
            if present & optional and not optional <= present:
                raise ValueError('incomplete session database schema')
            for name in present:
                if actual_tables[name] != expected_tables[name]:
                    raise ValueError(f'incompatible database columns/schema: {name}')
            allowed_indexes = {k: v for k, v in expected_indexes.items()
                               if optional <= present or k not in {'idx_sessions_project', 'idx_web_jobs_session'}}
            if actual_indexes != allowed_indexes:
                raise ValueError('incompatible database index schema')
            if connection.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                raise ValueError('database integrity check failed')
            if connection.execute('PRAGMA foreign_key_check').fetchone() is not None:
                raise ValueError('database foreign-key integrity failed')
            counts = {name: connection.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0]
                      for name in present if name != 'sqlite_sequence'}
            models = []
            for table, cls in [('models', Model), ('agents', Agent), ('tools', Tool)]:
                for row in connection.execute(f'SELECT id,data FROM {table}'):
                    record = cls.model_validate_json(row['data'])
                    if record.id != row['id']:
                        raise ValueError('registry ID does not match stored configuration')
                    if table == 'models':
                        models.append({key: getattr(record, key) for key in
                                       ('id', 'provider', 'model_name', 'base_url', 'api_key_env', 'enabled')})
            return {'counts': counts, 'models': models}
    except sqlite3.DatabaseError as error:
        raise ValueError('invalid or incompatible database schema') from error


def _json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate manifest key')
        result[key] = value
    return result


def unpack_validated(bundle, staging):
    """Stream bounded payloads into owned staging; never use ZipFile.extract."""
    bundle = checked_path(bundle)
    if bundle.stat().st_size > MAX_TOTAL_BYTES + MAX_MANIFEST_BYTES + MAX_FILES * 1024:
        raise ValueError('archive size exceeds limit')
    with zipfile.ZipFile(bundle) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_FILES + 1:
            raise ValueError('archive file count exceeds limit')
        seen, aliases, payloads = set(), {}, {}
        for item in infos:
            name = item.filename
            alias = name.casefold()
            if alias in seen:
                raise ValueError('duplicate or case-colliding archive member')
            seen.add(alias)
            register_path(name, aliases)
            mode = item.external_attr >> 16
            if (item.is_dir() or (stat.S_IFMT(mode) not in (0, stat.S_IFREG))
                    or item.flag_bits & 1
                    or item.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)):
                raise ValueError('archive member must be a regular unencrypted file')
            if name == 'manifest.json':
                if item.file_size > MAX_MANIFEST_BYTES:
                    raise ValueError('manifest size exceeds limit')
            else:
                if name != 'data/platform.sqlite':
                    if not name.startswith('workspace/'):
                        raise ValueError('unexpected archive member path')
                    portable_path(name[len('workspace/'):])
                payloads[name] = item
        if 'manifest.json' not in archive.namelist() or 'data/platform.sqlite' not in payloads:
            raise ValueError('required archive members are missing')
        with archive.open('manifest.json') as stream:
            raw_manifest = stream.read(MAX_MANIFEST_BYTES + 1)
        if len(raw_manifest) > MAX_MANIFEST_BYTES:
            raise ValueError('manifest size exceeds limit')
        manifest = json.loads(raw_manifest, object_pairs_hook=_json_object)
        if (not isinstance(manifest, dict) or manifest.get('format') != FORMAT
                or type(manifest.get('format_version')) is not int
                or manifest['format_version'] != FORMAT_VERSION):
            raise ValueError('unsupported bundle format version')
        files = manifest.get('files')
        if not isinstance(files, list) or len(files) != len(payloads):
            raise ValueError('manifest member list mismatch')
        listed, total = set(), 0
        for record in files:
            if not isinstance(record, dict) or set(record) != {'path', 'bytes', 'sha256'}:
                raise ValueError('invalid manifest file record')
            name, size, digest = record['path'], record['bytes'], record['sha256']
            if (not isinstance(name, str) or name in listed or name not in payloads
                    or type(size) is not int or size < 0
                    or not isinstance(digest, str) or not re.fullmatch(r'[a-f0-9]{64}', digest)):
                raise ValueError('invalid manifest member metadata')
            listed.add(name)
            total += size
            if size > MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
                raise ValueError('payload size exceeds limit')
            if payloads[name].file_size != size:
                raise ValueError('manifest member size mismatch')
            target = staging / name
            target.parent.mkdir(parents=True, exist_ok=True)
            measured, checksum = 0, hashlib.sha256()
            with archive.open(payloads[name]) as source, target.open('xb') as output:
                while chunk := source.read(CHUNK_BYTES):
                    measured += len(chunk)
                    if measured > size or measured > MAX_FILE_BYTES:
                        raise ValueError('streamed payload exceeds size limit')
                    checksum.update(chunk)
                    output.write(chunk)
            if measured != size or checksum.hexdigest() != digest:
                raise ValueError('payload checksum/hash or size mismatch')
        if listed != set(payloads):
            raise ValueError('manifest member list mismatch')
        database = validate_database(staging / 'data/platform.sqlite')
        return {**database, 'format_version': FORMAT_VERSION,
                'source_version': manifest.get('source_version'),
                'created_at': manifest.get('created_at'), 'file_count': len(files),
                'bytes': total, 'omitted': manifest.get('omitted', [])}
