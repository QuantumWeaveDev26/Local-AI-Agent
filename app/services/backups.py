"""Offline snapshots and private transfer previews for the local platform."""
import hashlib
import json
import os
import sqlite3
import stat
import tempfile
import zipfile
from contextlib import closing
from pathlib import Path

from filelock import FileLock, Timeout

from app.database import now
from app.services import backup_format as fmt


def _workspace_files(root, omitted):
    pending = [root]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                path = Path(entry.path)
                relative = path.relative_to(root).as_posix()
                metadata = entry.stat(follow_symlinks=False)
                attributes = getattr(metadata, 'st_file_attributes', 0)
                if (stat.S_ISLNK(metadata.st_mode)
                        or attributes & (0x400 | 0x1000 | 0x40000 | 0x400000)):
                    omitted.append({'path': relative, 'reason': 'link or cloud placeholder'})
                    continue
                try:
                    fmt.portable_path(relative)
                except ValueError:
                    omitted.append({'path': relative, 'reason': 'sensitive, runtime or nonportable path'})
                    continue
                if stat.S_ISDIR(metadata.st_mode):
                    pending.append(path)
                elif stat.S_ISREG(metadata.st_mode):
                    yield relative, path
                else:
                    omitted.append({'path': relative, 'reason': 'not a regular file'})


def _write_payload(archive, name, path):
    before = path.stat(follow_symlinks=False)
    if not stat.S_ISREG(before.st_mode):
        raise ValueError('snapshot payload is not a regular file')
    if before.st_size > fmt.MAX_FILE_BYTES:
        raise ValueError('snapshot payload exceeds file size limit')
    size, digest = 0, hashlib.sha256()
    with path.open('rb') as source, archive.open(name, 'w') as target:
        while chunk := source.read(fmt.CHUNK_BYTES):
            size += len(chunk)
            if size > fmt.MAX_FILE_BYTES:
                raise ValueError('snapshot payload exceeds file size limit')
            target.write(chunk)
            digest.update(chunk)
    after = path.stat(follow_symlinks=False)
    identity = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
    if size != before.st_size or identity(before) != identity(after):
        raise ValueError('source file changed during snapshot; stop writers and retry')
    return {'path': name, 'bytes': size, 'sha256': digest.hexdigest()}


def create_bundle(data_dir, workspace, output, offline=False):
    if not offline:
        raise ValueError('backup requires --offline after stopping the service, CLI writers and editors')
    data_dir, workspace, output = map(fmt.checked_path, (data_dir, workspace, output))
    database_path = fmt.checked_path(data_dir / 'platform.sqlite')
    if not database_path.is_file() or not workspace.is_dir():
        raise ValueError('backup needs an existing platform database and workspace')
    if not output.name.endswith('.localagent.zip'):
        raise ValueError('private backup output must end in .localagent.zip')
    if output.exists():
        raise FileExistsError('backup output already exists; choose a new filename')
    if (output.is_relative_to(workspace) or data_dir.is_relative_to(workspace)
            or workspace.is_relative_to(data_dir)):
        raise ValueError('backup data, workspace and output paths must not overlap')
    if not output.parent.is_dir():
        raise ValueError('backup output parent directory must already exist')
    created = False
    try:
        with FileLock(data_dir / 'workspace-service.lock', timeout=0):
            with tempfile.TemporaryDirectory(prefix='local-agent-backup-') as directory:
                staged = Path(directory) / 'platform.sqlite'
                with closing(fmt.read_only_db(database_path)) as source, closing(sqlite3.connect(staged)) as target:
                    source.backup(target)
                database = fmt.validate_database(staged)
                with closing(fmt.read_only_db(staged)) as connection:
                    if connection.execute("SELECT count(*) FROM tasks WHERE status='running'").fetchone()[0]:
                        raise ValueError('running tasks prevent an offline snapshot; stop or resolve them first')
                manifest = {'format': fmt.FORMAT, 'format_version': fmt.FORMAT_VERSION,
                            'source_version': '0.1.0', 'created_at': now(), 'files': [],
                            'omitted': [], 'models': database['models']}
                # Exclusive creation never overwrites an existing or concurrently created file.
                with output.open('xb') as stream:
                    created = True
                    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_STORED) as archive:
                        manifest['files'].append(_write_payload(archive, 'data/platform.sqlite', staged))
                        total = manifest['files'][0]['bytes']
                        aliases = {}
                        fmt.register_path('data/platform.sqlite', aliases)
                        for relative, path in _workspace_files(workspace, manifest['omitted']):
                            name = 'workspace/' + relative
                            fmt.register_path(name, aliases)
                            if len(manifest['files']) >= fmt.MAX_FILES:
                                raise ValueError('snapshot file count exceeds limit')
                            if total + path.stat().st_size > fmt.MAX_TOTAL_BYTES:
                                raise ValueError('snapshot total size exceeds limit')
                            record = _write_payload(archive, name, path)
                            manifest['files'].append(record)
                            total += record['bytes']
                            if total > fmt.MAX_TOTAL_BYTES:
                                raise ValueError('snapshot total size exceeds limit')
                        encoded = json.dumps(manifest, ensure_ascii=False).encode('utf-8')
                        if len(encoded) > fmt.MAX_MANIFEST_BYTES:
                            raise ValueError('snapshot manifest exceeds size limit')
                        archive.writestr('manifest.json', encoded)
                return {**database, 'output': str(output), 'format_version': fmt.FORMAT_VERSION,
                        'file_count': len(manifest['files']), 'bytes': total,
                        'omitted': manifest['omitted']}
    except Timeout as error:
        raise ValueError('workspace service is active; stop it before an offline backup') from error
    except BaseException:
        if created:
            output.unlink(missing_ok=True)
        raise


def inspect_bundle(bundle):
    with tempfile.TemporaryDirectory(prefix='local-agent-inspect-') as directory:
        return fmt.unpack_validated(Path(bundle), Path(directory))
