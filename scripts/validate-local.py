"""Real Ollama checks, intentionally separate from isolated automated tests.

Run from the repository root with .venv/bin/python scripts/validate-local.py.
Uses fictional files in the approved workspace and writes evidence under data/.
No fixture provider is used. Failed checks produce a nonzero exit status.
"""
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.database import Database, redact_data
from app.core.registry import Registry
from app.core.llm import LLM
from app.services.tasks import TaskService
from app.tools.workspace import Workspace, ToolExecutor
from app.agents.defaults import seed
from app.core.schemas import Agent, Assessment
from reportlab.pdfgen.canvas import Canvas


def main():
    data=ROOT/'data'
    registry=Registry(Database(data/'validation.sqlite'))
    seed(registry)
    registry.add_agent(Agent.model_validate_json((ROOT/'examples/seo-agent.json').read_text())) if not any(a.id=='seo' for a in registry.list_agents()) else None
    workspace=Workspace(ROOT/'workspace'/'validation')
    service=TaskService(registry,ToolExecutor(workspace),LLM(data/'inference.lock',timeout=300))
    checks=[]
    for request,expected in [
        ('Evaluate this candidate for our developer role.','recruitment'),
        ('Create a Meta Ads campaign strategy for a restaurant.','marketing'),
        ('Inspect this codebase and explain the bug.','developer'),
        ('Prepare a technical SEO audit and keyword plan.','seo'),
    ]:
        task=registry.db.create_task(request)
        try:
            selected=service._route(task,request)
            registry.db.finish_task(task,'completed',result=selected)
            checks.append({'name':'routing','request':request,'expected':expected,'selected':selected,'passed':selected==expected,'task_id':task})
        except Exception as e:
            service._finish_error(task,e)
            checks.append({'name':'routing','request':request,'passed':False,'error':str(e),'task_id':task})
    workspace.write('candidate.txt',(ROOT/'examples/candidate.txt').read_text())
    workspace.write('job-description.md',(ROOT/'examples/job-description.md').read_text())
    pdf=Canvas(str(workspace.path('candidate.pdf')))
    for i,line in enumerate((ROOT/'examples/candidate.txt').read_text().splitlines()):
        pdf.drawString(40,750-18*i,line)
    pdf.save()
    task=service.recruit('candidate.pdf','job-description.md')
    passed=task['status']=='completed'
    if passed:
        Assessment.model_validate_json(task['result'])
        passed=len(task['tool_calls'])==3 and 'Alex' in task['result']
    checks.append({'name':'pdf_recruitment','passed':passed,'status':task['status'],'task_id':task['id'],'error':task['error']})
    task=service.run('Use document_read to read candidate.txt, then summarize its documented skills in one sentence.',agent_id='recruitment')
    checks.append({'name':'native_tool_execution','passed':task['status']=='completed' and any(c['data']['tool_id']=='document_read' for c in task['tool_calls']),'task_id':task['id'],'status':task['status'],'error':task['error']})
    workspace.write('sample.py','def divide(a, b):\n    return a / b\n\nprint(divide(1, 0))\n')
    task=service.run('Use filesystem_read to read sample.py and explain the bug in one sentence. Do not change the file.',agent_id='developer')
    checks.append({'name':'developer_file_inspection','passed':task['status']=='completed' and any(c['data']['tool_id']=='filesystem_read' for c in task['tool_calls']),'task_id':task['id'],'status':task['status'],'error':task['error']})
    task=service.run('Create a concise Meta Ads campaign plan for a vegetarian restaurant in Pune with a monthly budget of INR 15000. State assumptions; no file output needed.')
    checks.append({'name':'marketing_workflow','passed':task['status']=='completed' and task['assigned_agent_id']=='marketing','task_id':task['id'],'status':task['status'],'error':task['error']})
    result={'provider':'real local Ollama','models':{a.id:registry.get_model(a.model_id).model_name for a in registry.list_agents()},'checks':checks,'all_passed':all(c['passed'] for c in checks)}
    path=data/'local-validation.json'
    path.write_text(json.dumps(redact_data(result),indent=2))
    print(json.dumps(result,indent=2))
    return 0 if result['all_passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
