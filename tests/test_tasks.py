import json

import pytest
from app.database import Database
from app.core.registry import Registry
from app.core.schemas import Agent, Model
from app.core.llm import Response
from app.core.agent_factory import AgentFactory
from app.services.tasks import TaskService
from app.tools.workspace import Workspace, ToolExecutor, builtin_tools
from app.agents.defaults import seed


class ScriptedLLM:
    """Test-only protocol fixture, never a production inference provider."""
    def __init__(self, replies):
        self.replies=list(replies)
        self.calls=[]
    def chat(self,model,messages,tools=None,schema=None):
        self.calls.append({'model':model.id,'messages':list(messages),'tools':tools,'schema':schema})
        reply=self.replies.pop(0)
        if isinstance(reply,Exception):
            raise reply
        return reply


@pytest.fixture
def system(tmp_path):
    db=Database(tmp_path/'db.sqlite')
    r=Registry(db)
    seed(r)
    w=Workspace(tmp_path/'workspace')
    return r,w


def service(system,replies):
    r,w=system
    llm=ScriptedLLM(replies)
    return TaskService(r,ToolExecutor(w),llm),llm


def test_generic_vertical_slice_persists_messages_runs_and_output(system):
    s,llm=service(system,[Response('A useful answer',metrics={'completion_tokens':3})])
    task=s.run('Explain local execution',agent_id='marketing')
    assert task['status']=='completed'
    assert task['assigned_agent_id']=='marketing'
    assert task['result']=='A useful answer'
    assert task['task_runs'][0]['data']['model_id']=='local'
    assert task['outputs'][0]['data']['content']=='A useful answer'
    assert len(task['messages'])>=3
    assert llm.calls[0]['model']=='local'


def test_manager_discovers_new_agent_without_core_changes(system):
    r,w=system
    r.add_agent(Agent(id='seo',name='SEO',description='Search engine audits',instructions='Audit SEO',model_id='local'))
    s,llm=service(system,[Response('{"reason":"Capability match","agent_id":"seo"}'),Response('SEO report')])
    task=s.run('Audit search rankings')
    assert task['assigned_agent_id']=='seo'
    assert 'Search engine audits' in str(llm.calls[0]['messages'])
    r.set_enabled('agents','seo',False)
    s,llm=service(system,[Response('{"reason":"Capability match","agent_id":"seo"}')])
    task=s.run('Audit again')
    assert task['status']=='failed'
    assert 'seo' not in {a['id'] for a in json.loads(llm.calls[0]['messages'][-1]['content'])['available_agents']}


def test_factory_rejects_disabled_model_or_agent(system):
    r,w=system
    r.set_enabled('agents','marketing',False)
    with pytest.raises(ValueError,match='disabled'):
        AgentFactory(r).load('marketing')
    r.set_enabled('models','local',False)
    with pytest.raises(ValueError,match='disabled'):
        AgentFactory(r).load('developer')


def test_tool_calls_logged_and_assignment_enforced(system):
    r,w=system
    w.write('cv.txt','Alex knows Python')
    call={'id':'c1','name':'document_read','arguments':{'path':'cv.txt'}}
    s,llm=service(system,[Response('',[call]),Response('Python experience')])
    task=s.run('Read cv.txt',agent_id='recruitment')
    assert task['status']=='completed'
    assert task['tool_calls'][0]['data']['status']=='completed'
    assert 'Alex knows Python' in str(llm.calls[1]['messages'])
    r.add_agent(Agent(id='reader',name='Reader',description='Read only',instructions='Read',model_id='local',tools=['document_read']))
    s,llm=service(system,[Response('',[{'id':'x','name':'filesystem_write','arguments':{'path':'bad.txt','content':'x'}}])])
    task=s.run('write',agent_id='reader')
    assert task['status']=='failed'
    assert task['tool_calls'][0]['data']['status']=='failed'
    assert not (w.root/'bad.txt').exists()


def test_model_errors_persist_and_explicit_fallback_is_logged(system):
    r,w=system
    r.add_model(Model(id='fallback',name='Fallback',model_name='other'))
    r.add_agent(Agent(id='helper',name='Helper',description='Help',instructions='Help',model_id='local',fallback_model_id='fallback'))
    s,llm=service(system,[RuntimeError('offline'),Response('fallback result')])
    task=s.run('help',agent_id='helper')
    assert task['status']=='completed'
    assert [run['data']['model_id'] for run in task['task_runs']]==['local','fallback']
    assert task['errors'][0]['data']['error']=='offline'
    s,llm=service(system,[RuntimeError('offline')])
    task=s.run('help',agent_id='marketing')
    assert task['status']=='failed'
    assert task['error']=='offline'


def test_recruitment_reads_documents_validates_and_saves(system):
    r,w=system
    w.write('cv.txt','Alex, three years of Python')
    w.write('jd.md','Python developer, SQLite required')
    assessment={'candidate':'Alex','role':'Python developer','experience':'3 years','relevant_skills':['Python'],'strengths':['Python'],'gaps':['SQLite not documented'],'concerns':[],'questions_to_verify':['SQLite experience?'],'recommended_practical_test_areas':['Python'],'assessment_summary':'Verify SQLite'}
    s,llm=service(system,[Response(json.dumps(assessment))])
    task=s.recruit('cv.txt','jd.md')
    assert task['status']=='completed'
    assert len(task['tool_calls'])==3
    assert task['tool_calls'][2]['data']['tool_id']=='filesystem_write'
    assert 'Alex' in (w.root/'reports'/f"{task['id']}.json").read_text()
    assert 'three years' in str(llm.calls[0]['messages'])
    assert llm.calls[0]['schema']['additionalProperties'] is False


def test_malformed_assessment_fails_without_report(system):
    r,w=system
    w.write('cv.txt','CV')
    w.write('jd.md','JD')
    s,llm=service(system,[Response('{"candidate":"Alex"}')])
    task=s.recruit('cv.txt','jd.md')
    assert task['status']=='failed'
    assert task['errors']
    assert not (w.root/'reports').exists()


def test_tool_loop_is_bounded(system):
    r,w=system
    w.write('cv.txt','CV')
    call={'id':'x','name':'document_read','arguments':{'path':'cv.txt'}}
    s,llm=service(system,[Response('',[call]) for _ in range(3)])
    s.max_rounds=2
    task=s.run('keep reading',agent_id='recruitment')
    assert task['status']=='failed'
    assert 'limit' in task['error']


def test_manager_does_not_advertise_agents_with_disabled_tools(system):
    r,w=system
    r.set_enabled('tools','git_status',False)
    s,llm=service(system,[Response('{"reason":"Capability match","agent_id":"marketing"}'),Response('plan')])
    task=s.run('make a campaign')
    available=json.loads(llm.calls[0]['messages'][-1]['content'])['available_agents']
    assert 'developer' not in {a['id'] for a in available}
    assert task['status']=='completed'


def test_manager_decision_requires_capability_reason(system):
    s,llm=service(system,[Response('{"agent_id":"recruitment"}')])
    task=s.run('evaluate a candidate')
    assert task['status']=='failed'
    assert 'reason' in task['error']


def test_manager_uses_its_assigned_model_independently_of_specialists(system):
    r,w=system
    r.add_model(Model(id='custom-router',name='Router',model_name='larger-local'))
    r.update_agent('manager',model_id='custom-router',settings={'thinking':False})
    s,llm=service(system,[Response('{"reason":"Candidate evaluation","agent_id":"recruitment"}'),Response('assessment')])
    task=s.run('evaluate candidate')
    assert task['status']=='completed'
    assert [call['model'] for call in llm.calls]==['custom-router','local']
