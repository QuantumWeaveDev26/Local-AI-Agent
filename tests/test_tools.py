import subprocess
from pathlib import Path

import pytest
from docx import Document
from reportlab.pdfgen.canvas import Canvas
from app.tools.workspace import Workspace, ToolExecutor, builtin_tools
from app.core.schemas import Agent


def test_read_write_and_document_extraction(tmp_path):
    w = Workspace(tmp_path)
    w.write('notes/example.md', 'Hello local world')
    assert w.read('notes/example.md') == 'Hello local world'
    doc = Document()
    doc.add_paragraph('Candidate knows Python')
    doc.add_table(rows=1, cols=1).cell(0, 0).text = 'SQLite'
    doc.save(tmp_path / 'candidate.docx')
    assert 'Python' in w.read('candidate.docx')
    assert 'SQLite' in w.read('candidate.docx')
    pdf = Canvas(str(tmp_path / 'candidate.pdf'))
    pdf.drawString(40, 750, 'Candidate: Alex. Python developer, 3 years.')
    pdf.save()
    assert 'Alex' in w.read('candidate.pdf')


@pytest.mark.parametrize('path', ['../outside.txt', '/etc/passwd', '.env', '.ssh/id_rsa', '.git/config', 'folder/.env.local', 'CON.txt', 'x:stream', 'folder/.aws/credentials'])
def test_unsafe_paths_rejected(tmp_path, path):
    with pytest.raises((PermissionError, ValueError)):
        Workspace(tmp_path).write(path, 'must not write')


def test_symlink_escape_and_size_limits(tmp_path):
    root = tmp_path / 'root'
    root.mkdir()
    outside = tmp_path / 'outside.txt'
    outside.write_text('private')
    try:
        (root / 'link.txt').symlink_to(outside)
    except OSError as error:
        if __import__('os').name == 'nt' and error.winerror == 1314:
            pytest.skip('Symlink privilege unavailable on this Windows host')
        raise
    with pytest.raises(PermissionError):
        Workspace(root).read('link.txt')


def test_size_limit_applies_without_symlink_privileges(tmp_path):
    root = tmp_path
    (root / 'large.txt').write_text('x' * 100)
    with pytest.raises(ValueError, match='large'):
        Workspace(root, max_bytes=20).read('large.txt')


def test_tool_assignment_and_level_enforced(tmp_path):
    executor = ToolExecutor(Workspace(tmp_path))
    agent = Agent(id='a', name='A', description='A', instructions='A', model_id='m', tools=['filesystem_write'])
    tools = {t.id: t for t in builtin_tools()}
    with pytest.raises(PermissionError):
        executor.execute(agent, tools['filesystem_write'], {'path':'file.txt','content':'x'})
    writer = agent.model_copy(update={'permission_level':2})
    executor.execute(writer, tools['filesystem_write'], {'path':'file.txt','content':'x'})
    assert (tmp_path / 'file.txt').read_text() == 'x'
    with pytest.raises(PermissionError):
        executor.execute(writer, tools['document_read'], {'path':'file.txt'})
    with pytest.raises(ValueError):
        executor.execute(writer, tools['filesystem_write'], {'path':'bad.txt','content':'x','extra':'x'})


def test_readonly_git_tools(tmp_path):
    subprocess.run(['git','init',str(tmp_path)], check=True, capture_output=True)
    (tmp_path / 'sample.txt').write_text('hello')
    w = Workspace(tmp_path)
    assert 'sample.txt' in w.git_status()
    assert w.git_diff() == ''


def test_blank_pdf_is_actionable(tmp_path):
    pdf = Canvas(str(tmp_path / 'scan.pdf'))
    pdf.showPage()
    pdf.save()
    with pytest.raises(ValueError, match='OCR'):
        Workspace(tmp_path).read('scan.pdf')


def test_git_diff_does_not_expose_sensitive_tracked_files(tmp_path):
    subprocess.run(['git','init',str(tmp_path)],check=True,capture_output=True)
    (tmp_path/'.ssh').mkdir()
    (tmp_path/'.ssh'/'id_rsa').write_text('old secret')
    (tmp_path/'code.py').write_text('old code')
    subprocess.run(['git','add','.'],cwd=tmp_path,check=True,capture_output=True)
    subprocess.run(['git','-c','user.name=Test','-c','user.email=test@example.invalid','commit','-m','fixture'],cwd=tmp_path,check=True,capture_output=True)
    (tmp_path/'.ssh'/'id_rsa').write_text('new private key')
    (tmp_path/'code.py').write_text('new code')
    diff=Workspace(tmp_path).git_diff()
    assert 'new private key' not in diff
    assert 'new code' in diff


@pytest.mark.parametrize('path',['.git./config','.ssh /id_rsa','folder./file','folder /file','file?.txt','file*.txt','file|.txt'])
def test_windows_alias_paths_rejected_on_every_host(tmp_path,path):
    with pytest.raises(PermissionError):
        Workspace(tmp_path).write(path,'private')


def test_git_paths_are_literal_not_wildcards(tmp_path):
    subprocess.run(['git','init',str(tmp_path)],check=True,capture_output=True)
    (tmp_path/'[ab]').write_text('old')
    (tmp_path/'.ssh').mkdir()
    (tmp_path/'.ssh'/'id_rsa').write_text('old private')
    (tmp_path/'a').write_text('old ordinary')
    subprocess.run(['git','add','.'],cwd=tmp_path,check=True,capture_output=True)
    subprocess.run(['git','-c','user.name=Test','-c','user.email=test@example.invalid','commit','-m','fixture'],cwd=tmp_path,check=True,capture_output=True)
    (tmp_path/'[ab]').write_text('literal modification')
    # Wildcard [ab] would match 'a' rather than the literal filename.
    diff=Workspace(tmp_path).git_diff()
    assert 'literal modification' in diff


def test_git_wildcard_filename_cannot_expand_to_private_keys(tmp_path):
    if __import__('os').name=='nt':
        pytest.skip('Windows cannot create a literal star filename')
    subprocess.run(['git','init',str(tmp_path)],check=True,capture_output=True)
    (tmp_path/'*').write_text('old')
    (tmp_path/'.ssh').mkdir()
    (tmp_path/'.ssh'/'id_rsa').write_text('old private')
    subprocess.run(['git','add','.'],cwd=tmp_path,check=True,capture_output=True)
    subprocess.run(['git','-c','user.name=Test','-c','user.email=test@example.invalid','commit','-m','fixture'],cwd=tmp_path,check=True,capture_output=True)
    (tmp_path/'*').write_text('new')
    (tmp_path/'.ssh'/'id_rsa').write_text('new private key')
    assert 'new private key' not in Workspace(tmp_path).git_diff()
