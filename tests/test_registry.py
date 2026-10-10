from pathlib import Path

import pytest

from app.database import Database
from app.core.registry import Registry
from app.core.schemas import Agent, Model, Tool


def registry(tmp_path):
    return Registry(Database(tmp_path / 'state.sqlite'))


def test_dynamic_registration_survives_restart(tmp_path):
    r = registry(tmp_path)
    r.add_model(Model(id='small', name='Small', model_name='any-local-model'))
    r.add_model(Model(id='code', name='Coder', model_name='different-model'))
    r.add_tool(Tool(id='read', description='Read', permission_level=1))
    r.add_agent(Agent(id='seo', name='SEO', description='SEO audits', instructions='Audit',
                      model_id='small', tools=['read'], settings={'memory': True}))
    r.add_agent(Agent(id='dev', name='Developer', description='Code', instructions='Code', model_id='code'))
    r.add_agent(Agent(id='other', name='Other', description='Other', instructions='Other', model_id='small'))
    restored = registry(tmp_path)
    assert restored.get_agent('seo').tools == ['read']
    assert restored.get_agent('seo').settings == {'memory': True}
    assert len(restored.list_agents()) == 3
    assert restored.get_model('code').model_name == 'different-model'
    restored.set_enabled('agents', 'seo', False)
    assert restored.get_agent('seo').enabled is False
    assert {a.id for a in restored.list_agents(enabled_only=True)} == {'dev', 'other'}


def test_registry_rejects_unknown_dependencies_and_duplicates(tmp_path):
    r = registry(tmp_path)
    a = Agent(id='a', name='A', description='A', instructions='A', model_id='missing')
    with pytest.raises(ValueError, match='model'):
        r.add_agent(a)
    r.add_model(Model(id='m', name='M', model_name='m'))
    with pytest.raises(ValueError, match='already'):
        r.add_model(Model(id='m', name='M', model_name='m'))
    with pytest.raises(ValueError, match='tool'):
        r.add_agent(a.model_copy(update={'model_id': 'm', 'tools': ['missing']}))


@pytest.mark.parametrize('field,value', [('permission_level', 3), ('id', '../escape')])
def test_invalid_agent_configuration_rejected(field, value):
    data = dict(id='a', name='A', description='A', instructions='A', model_id='m')
    data[field] = value
    with pytest.raises(ValueError):
        Agent(**data)


def test_model_urls_and_provider_validation():
    with pytest.raises(ValueError):
        Model(id='m', name='M', model_name='m', provider='unknown')
    with pytest.raises(ValueError):
        Model(id='m', name='M', model_name='m', base_url='https://user:secret@example.com')


def test_persistence_records_events_and_redacts_known_secrets(tmp_path, monkeypatch):
    monkeypatch.setenv('TEST_API_KEY', 'private-value-123')
    db = Database(tmp_path / 'state.sqlite')
    task = db.create_task('request private-value-123')
    db.event('errors', task, {'error': 'Bearer private-value-123'})
    db.finish_task(task, 'failed', error='private-value-123')
    record = db.task(task)
    assert record['status'] == 'failed'
    assert 'private-value-123' not in str(record)
    assert record['errors'][0]['data']['error'] == 'Bearer [REDACTED]'


def test_redaction_preserves_json_with_escaped_secrets(tmp_path, monkeypatch):
    monkeypatch.setenv('SPECIAL_API_KEY', 'secret"with\\slashes')
    db=Database(tmp_path/'db.sqlite')
    task=db.create_task('test')
    db.event('messages',task,{'role':'user','content':'secret"with\\slashes'})
    assert db.task(task)['messages'][0]['data']['content']=='[REDACTED]'


def test_redaction_covers_dictionary_keys(tmp_path,monkeypatch):
    from app.database import redact_data
    monkeypatch.setenv('TEST_API_KEY','private-key-abcdef')
    safe=redact_data({'private-key-abcdef':'one','[REDACTED]':'two'})
    assert 'private-key-abcdef' not in str(safe)
    assert set(safe.values())=={'one','two'}


def test_starter_profile_separates_verified_routing_and_execution(tmp_path):
    from app.agents.defaults import seed
    r = registry(tmp_path)
    seed(r)
    assert r.get_model('local').model_name == 'qwen3:1.7b'
    assert r.get_model('router').model_name == 'qwen3:4b'
    assert r.get_agent('manager').model_id == 'router'
    assert r.get_agent('developer').model_id == 'local'
    r.update_agent('manager', model_id='local')
    seed(r)
    assert r.get_agent('manager').model_id == 'local'
