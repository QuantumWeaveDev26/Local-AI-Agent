"""Explicit output requirements; verify bytes without executing generated code."""
import hashlib

from app.database import redact
from app.services.backup_format import portable_path, register_path


def required_paths(paths):
    if paths is None:
        return []
    if not isinstance(paths, list) or len(paths) > 8:
        raise ValueError('required_files must be a list of at most eight relative paths')
    result, aliases, seen = [], {}, set()
    for path in paths:
        if not isinstance(path, str) or len(path) > 1024:
            raise ValueError('required file paths must be strings of at most 1024 characters')
        path = path.replace('\\', '/')
        if redact(path) != path:
            raise ValueError('required file names cannot contain sensitive text')
        portable_path(path)
        if path.casefold() in seen:
            raise ValueError('duplicate required file path')
        register_path(path, aliases)
        seen.add(path.casefold())
        result.append(path)
    return result


def written_file(workspace, arguments):
    path = workspace.path(arguments['path']).relative_to(workspace.root).as_posix()
    content = arguments['content'].encode('utf-8')
    return path, {'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()}


def verify_files(workspace, paths, writes):
    verified = []
    for path in paths:
        target = workspace.path(path)
        key = target.relative_to(workspace.root).as_posix()
        expected = writes.get(key)
        if expected is None:
            raise ValueError(f'Required output not verified: {path}; no successful write in this task')
        try:
            with target.open('rb') as stream:
                content = stream.read(workspace.max_bytes + 1)
        except (OSError, PermissionError) as error:
            raise ValueError(f'Required output not verified: {path}; file missing or inaccessible') from error
        actual = {'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()}
        if actual != expected:
            raise ValueError(f'Required output not verified: {path}; bytes differ from the latest write')
        verified.append({'path': path, **actual})
    return verified
