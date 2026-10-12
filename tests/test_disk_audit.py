"""Metadata-only disk inspection; never execute cleanup actions."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'audit-disk.py'


@pytest.fixture
def auditor():
    spec = importlib.util.spec_from_file_location('disk_audit', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ranks_folders_files_and_dev_directories_without_modifying_inputs(auditor, tmp_path):
    (tmp_path/'project/node_modules').mkdir(parents=True)
    (tmp_path/'Downloads').mkdir()
    (tmp_path/'project/node_modules/package.bin').write_bytes(b'a'*100)
    (tmp_path/'Downloads/video.mp4').write_bytes(b'v'*200)
    (tmp_path/'root.txt').write_bytes(b'r'*20)
    before = {p: p.stat().st_mtime_ns for p in tmp_path.rglob('*')}
    result = auditor.scan(tmp_path, top=2, progress=None)
    assert result['accessible_file_bytes'] == 320
    assert result['file_count'] == 3
    assert [(r['path'], r['bytes']) for r in result['root_folders']] == [('Downloads',200),('project',100)]
    assert result['largest_files'][0]['path'] == 'Downloads/video.mp4'
    assert result['largest_files'][0]['bytes'] == 200
    assert len(result['largest_files']) == 2
    assert any(r['path']=='project/node_modules' and r['bytes']==100 for r in result['development_and_cache_folders'])
    assert result['file_types'][0] == {'extension':'.mp4','bytes':200,'files':1}
    assert before == {p: p.stat().st_mtime_ns for p in tmp_path.rglob('*')}


def test_symlinks_and_windows_cloud_placeholders_are_not_followed(auditor, tmp_path):
    root = tmp_path/'root'; root.mkdir()
    outside = tmp_path/'outside'; outside.mkdir()
    (outside/'secret.txt').write_bytes(b'secret')
    try:
        (root/'link').symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip('Symlink creation privilege unavailable')
    result = auditor.scan(root, progress=None)
    assert result['file_count'] == 0
    assert result['skipped_links_or_placeholders'] == 1
    from types import SimpleNamespace
    assert auditor.skip_metadata(SimpleNamespace(st_file_attributes=0x400))
    assert auditor.skip_metadata(SimpleNamespace(st_file_attributes=0x1000))


def test_hardlinked_files_count_once(auditor, tmp_path):
    import os
    original=tmp_path/'one.bin'; original.write_bytes(b'x'*50)
    try:
        os.link(original,tmp_path/'two.bin')
    except OSError:
        pytest.skip('Hardlink creation unavailable')
    result=auditor.scan(tmp_path,progress=None)
    assert result['accessible_file_bytes']==50
    assert result['skipped_duplicate_hardlinks']==1


def test_windows_zeroed_directory_entry_identity_uses_real_stat(auditor, tmp_path, monkeypatch):
    import os
    from types import SimpleNamespace
    original=tmp_path/'one.bin'; original.write_bytes(b'x'*50)
    try:
        os.link(original,tmp_path/'two.bin')
    except OSError:
        pytest.skip('Hardlink creation unavailable')
    real_scandir=os.scandir
    class Entry:
        def __init__(self, entry):
            self.path=entry.path; self.entry=entry
        def stat(self, **kwargs):
            info=self.entry.stat(**kwargs)
            return SimpleNamespace(st_mode=info.st_mode, st_size=info.st_size,
                                   st_nlink=0, st_ino=0, st_dev=0,
                                   st_file_attributes=getattr(info,'st_file_attributes',0))
    class Directory:
        def __init__(self,path):self.iterator=real_scandir(path)
        def __next__(self):return Entry(next(self.iterator))
        def close(self):self.iterator.close()
    monkeypatch.setattr(auditor.os,'scandir',Directory)
    result=auditor.scan(tmp_path,progress=None)
    assert result['accessible_file_bytes']==50
    assert result['skipped_duplicate_hardlinks']==1


def test_missing_root_fails_clearly(auditor, tmp_path):
    with pytest.raises(ValueError, match='directory'):
        auditor.scan(tmp_path/'missing',progress=None)


def test_cli_saves_report_outside_scan_and_leaves_files_intact(tmp_path):
    root=tmp_path/'root'; root.mkdir(); (root/'keep.txt').write_text('keep')
    output=tmp_path/'report.json'
    command=[sys.executable,str(SCRIPT),'--root',str(root),'--output',str(output),'--top','5']
    run=subprocess.run(command,capture_output=True,text=True,timeout=15)
    assert run.returncode==0,run.stderr
    report=json.loads(output.read_text())
    assert report['accessible_file_bytes']==4
    assert 'Largest files' in run.stdout
    assert 'no files were deleted' in run.stdout.lower()
    assert (root/'keep.txt').read_text()=='keep'
    assert subprocess.run(command,capture_output=True,text=True,timeout=15).returncode!=0
    assert json.loads(output.read_text())==report
