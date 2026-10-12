import json
import os
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def cli(tmp_path,*args):
    return subprocess.run([sys.executable,str(ROOT/'main.py'),'--data-dir',str(tmp_path/'data'),'--workspace',str(tmp_path/'workspace'),*args],capture_output=True,text=True,cwd=ROOT,timeout=20)


def test_cli_initialization_and_dynamic_agent_creation(tmp_path):
    for _ in range(2):
        result=cli(tmp_path,'init')
        assert result.returncode==0,result.stderr
    result=cli(tmp_path,'agents','list')
    agents = json.loads(result.stdout)
    assert len(agents)==5
    assert any(a['id']=='assistant' for a in agents)
    config=tmp_path/'agent.json'
    config.write_text(json.dumps({'id':'seo','name':'SEO','description':'SEO audit','instructions':'Audit','model_id':'local'}))
    result=cli(tmp_path,'agents','add',str(config))
    assert result.returncode==0,result.stderr
    assert json.loads(cli(tmp_path,'agents','show','seo').stdout)['name']=='SEO'
    assert cli(tmp_path,'agents','disable','seo').returncode==0
    assert not json.loads(cli(tmp_path,'agents','show','seo').stdout)['enabled']
    assert cli(tmp_path,'agents','enable','seo').returncode==0
    assert cli(tmp_path,'agents','update','seo','--permission','2','--tools','document_read').returncode==0
    assert json.loads(cli(tmp_path,'agents','show','seo').stdout)['tools']==['document_read']
    assert len(json.loads(cli(tmp_path,'tools','list').stdout))==5


def test_cli_failures_are_nonzero_and_actionable(tmp_path):
    assert cli(tmp_path,'init').returncode==0
    result=cli(tmp_path,'agents','show','missing')
    assert result.returncode!=0
    assert 'unknown' in result.stderr
    result=cli(tmp_path,'task','missing')
    assert result.returncode!=0
    assert 'unknown' in result.stderr


def test_cli_requires_explicit_trusted_test_execution(tmp_path):
    result=cli(tmp_path,'test-workspace')
    assert result.returncode!=0
    assert '--trust-workspace-code' in result.stderr


def test_agent_update_revalidates_dependencies(tmp_path):
    from app.database import Database
    from app.core.registry import Registry
    from app.agents.defaults import seed
    import pytest
    r=Registry(Database(tmp_path/'db'))
    seed(r)
    with pytest.raises(ValueError,match='model'):
        r.update_agent('developer',model_id='missing')
    with pytest.raises(ValueError):
        r.update_agent('developer',permission_level=3)
    assert r.get_agent('developer').permission_level==2


def test_explicit_test_runner_executes_tests_and_audits_exit_status(tmp_path):
    import os
    workspace=tmp_path/'workspace'
    workspace.mkdir()
    (workspace/'test_demo.py').write_text('def test_demo():\n    assert 2 + 2 == 4\n')
    initial_stat = (workspace/'test_demo.py').stat()
    result=cli(tmp_path,'test-workspace','--trust-workspace-code')
    assert result.returncode==0,result.stderr
    record=json.loads(result.stdout)
    assert '1 passed' in record['output']
    task=json.loads(cli(tmp_path,'task',record['task_id']).stdout)
    assert task['tool_calls'][0]['data']['exit_code']==0
    assert task['tool_calls'][0]['data']['command'][-2:]==['pytest','-q']
    (workspace/'test_demo.py').write_text('def test_demo():\n    assert 2 + 2 == 5\n')
    # Same-size edits with the same timestamp must never reuse a passing cache.
    os.utime(workspace/'test_demo.py', ns=(initial_stat.st_atime_ns, initial_stat.st_mtime_ns))
    result=cli(tmp_path,'test-workspace','--trust-workspace-code')
    assert result.returncode==1
    assert '1 failed' in json.loads(result.stdout)['output']


def test_cli_timeout_is_configurable(tmp_path):
    result=cli(tmp_path,'--timeout','300','init')
    assert result.returncode==0,result.stderr
    result=cli(tmp_path,'--timeout','0','init')
    assert result.returncode!=0


def test_cli_backup_restore_round_trip(tmp_path):
    assert cli(tmp_path, 'init').returncode == 0
    (tmp_path / 'workspace/evidence.txt').write_text('A transferable artifact')
    bundle = tmp_path / 'transfer.localagent.zip'
    created = cli(tmp_path, 'backup', 'create', '--output', str(bundle), '--offline')
    assert created.returncode == 0, created.stderr
    assert json.loads(created.stdout)['file_count'] == 2
    inspected = cli(tmp_path / 'inspection-only', 'backup', 'inspect', str(bundle))
    assert inspected.returncode == 0, inspected.stderr
    assert not (tmp_path / 'inspection-only').exists()
    destination = tmp_path / 'restored'
    restored = cli(tmp_path / 'unrelated', 'backup', 'restore', str(bundle),
                   '--destination', str(destination), '--offline')
    assert restored.returncode == 0, restored.stderr
    assert not (tmp_path / 'unrelated').exists()
    assert (destination / 'workspace/evidence.txt').read_text() == 'A transferable artifact'
    assert json.loads(cli(destination, 'agents', 'show', 'developer').stdout)['model_id'] == 'local'


def test_cli_invalid_restore_creates_no_application_state(tmp_path):
    invalid = tmp_path / 'invalid.localagent.zip'
    invalid.write_bytes(b'Not an archive')
    destination = tmp_path / 'new-parent' / 'restored'
    result = cli(tmp_path / 'unrelated', 'backup', 'restore', str(invalid),
                 '--destination', str(destination), '--offline')
    assert result.returncode != 0
    assert 'zip' in result.stderr.lower()
    assert not (tmp_path / 'unrelated').exists()
    assert not destination.parent.exists()


def test_cli_backup_requires_offline_and_existing_output_is_preserved(tmp_path):
    assert cli(tmp_path, 'init').returncode == 0
    bundle = tmp_path / 'snapshot.localagent.zip'
    result = cli(tmp_path, 'backup', 'create', '--output', str(bundle))
    assert result.returncode != 0
    assert 'offline' in result.stderr
    assert not bundle.exists()
    bundle.write_bytes(b'An existing backup')
    result = cli(tmp_path, 'backup', 'create', '--output', str(bundle), '--offline')
    assert result.returncode != 0
    assert 'exists' in result.stderr
    assert bundle.read_bytes() == b'An existing backup'
