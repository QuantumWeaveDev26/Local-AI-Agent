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
    assert len(json.loads(result.stdout))==4
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
    workspace=tmp_path/'workspace'
    workspace.mkdir()
    (workspace/'test_demo.py').write_text('def test_demo():\n    assert 2 + 2 == 4\n')
    result=cli(tmp_path,'test-workspace','--trust-workspace-code')
    assert result.returncode==0,result.stderr
    record=json.loads(result.stdout)
    assert '1 passed' in record['output']
    task=json.loads(cli(tmp_path,'task',record['task_id']).stdout)
    assert task['tool_calls'][0]['data']['exit_code']==0
    assert task['tool_calls'][0]['data']['command'][-2:]==['pytest','-q']
    (workspace/'test_demo.py').write_text('def test_demo():\n    assert 2 + 2 == 5\n')
    result=cli(tmp_path,'test-workspace','--trust-workspace-code')
    assert result.returncode==1
    assert '1 failed' in json.loads(result.stdout)['output']


def test_cli_timeout_is_configurable(tmp_path):
    result=cli(tmp_path,'--timeout','300','init')
    assert result.returncode==0,result.stderr
    result=cli(tmp_path,'--timeout','0','init')
    assert result.returncode!=0
