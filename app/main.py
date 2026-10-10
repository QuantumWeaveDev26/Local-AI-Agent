"""Local CLI. Return nonzero for failed tasks and missing prerequisites."""
import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import tempfile
from pathlib import Path

import httpx
import psutil

from app.config import DEFAULT_DATA, DEFAULT_WORKSPACE
from app.database import Database, redact, redact_data
from app.core.registry import Registry
from app.core.schemas import Agent, Model
from app.core.llm import LLM
from app.tools.workspace import Workspace, ToolExecutor
from app.services.tasks import TaskService
from app.agents.defaults import seed


def emit(data):
    if hasattr(data,'model_dump'):
        data=data.model_dump()
    if isinstance(data,list):
        data=[v.model_dump() if hasattr(v,'model_dump') else v for v in data]
    print(json.dumps(redact_data(data),indent=2,ensure_ascii=False,default=str))


def parser():
    p=argparse.ArgumentParser(description='Local-first configurable AI agent platform')
    p.add_argument('--data-dir',type=Path,default=DEFAULT_DATA)
    p.add_argument('--workspace',type=Path,default=DEFAULT_WORKSPACE)
    p.add_argument('--timeout',type=float,default=300,help='Maximum seconds per provider call or inference queue wait')
    p.add_argument('--allow-remote-models',action='store_true',help='Explicitly allow HTTPS remote providers; documents may leave this machine')
    sub=p.add_subparsers(dest='command',required=True)
    init=sub.add_parser('init',help='Initialize SQLite and seed starter configs without overwriting existing records')
    init.add_argument('--model',default='qwen3:1.7b')
    init.add_argument('--router-model',default='qwen3:4b')
    init.add_argument('--base-url',default='http://127.0.0.1:11434')
    for group in ('agents','models','tools'):
        g=sub.add_parser(group).add_subparsers(dest='action',required=True)
        g.add_parser('list')
        show=g.add_parser('show'); show.add_argument('id')
        if group!='tools':
            add=g.add_parser('add'); add.add_argument('config',type=Path)
        for action in ('enable','disable'):
            toggle=g.add_parser(action); toggle.add_argument('id')
        if group=='agents':
            update=g.add_parser('update'); update.add_argument('id')
            update.add_argument('--model',dest='model_id')
            update.add_argument('--fallback',dest='fallback_model_id')
            update.add_argument('--tools',nargs='*')
            update.add_argument('--permission',dest='permission_level',type=int,choices=[1,2])
    run=sub.add_parser('run'); run.add_argument('request'); run.add_argument('--agent'); run.add_argument('--attach',action='append',default=[])
    recruit=sub.add_parser('recruit'); recruit.add_argument('cv'); recruit.add_argument('job_description'); recruit.add_argument('--agent',default='recruitment')
    task=sub.add_parser('task'); task.add_argument('id')
    doctor=sub.add_parser('doctor'); doctor.add_argument('--model',default='local')
    bench=sub.add_parser('benchmark'); bench.add_argument('--model',default='local'); bench.add_argument('--output',type=Path)
    test=sub.add_parser('test-workspace',help='Run fixed pytest command in a trusted workspace; never exposed to agents')
    test.add_argument('--trust-workspace-code',action='store_true')
    serve=sub.add_parser('serve',help='Start the local project/conversation browser workspace')
    serve.add_argument('--port',type=int,default=8765)
    serve.add_argument('--open-browser',action='store_true')
    return p


def doctor(registry, llm, model_id):
    model=registry.get_model(model_id)
    llm._check(model)
    report={'platform':platform.platform(),'python':platform.python_version(),'ram_gib':round(psutil.virtual_memory().total/2**30,2),'disk_free_gib':round(shutil.disk_usage(registry.db.path.parent).free/2**30,2),'gpu_command_present':bool(shutil.which('nvidia-smi')),'model_id':model.id,'model_name':model.model_name,'provider':model.provider}
    with httpx.Client(timeout=10,trust_env=False) as client:
        if model.provider=='ollama':
            version=client.get(model.base_url+'/api/version'); version.raise_for_status()
            tags=client.get(model.base_url+'/api/tags'); tags.raise_for_status()
            report['ollama_version']=version.json()['version']
            report['model_installed']=model.model_name in {m['name'] for m in tags.json().get('models',[])}
            if not report['model_installed']:
                raise RuntimeError(f'Ollama is running but {model.model_name} is not installed; run ollama pull {model.model_name}')
        else:
            report['provider_note']='Run a task to validate the OpenAI-compatible endpoint'
    return report


def ollama_rss_gib():
    processes=[]
    for process in psutil.process_iter(['pid','ppid','name','memory_info']):
        try:
            processes.append(process.info)
        except (psutil.NoSuchProcess,psutil.AccessDenied):
            pass
    included={p['pid'] for p in processes if 'ollama' in (p['name'] or '').lower()}
    while True:
        children={p['pid'] for p in processes if p['ppid'] in included}
        if children.issubset(included):
            break
        included.update(children)
    return sum(p['memory_info'].rss for p in processes if p['pid'] in included and p['memory_info'])/2**30


def benchmark(registry, llm, model_id):
    model=registry.get_model(model_id)
    report={'platform':platform.platform(),'python':platform.python_version(),'model':model.model_dump(),'ram_total_gib':round(psutil.virtual_memory().total/2**30,2),'cpu_count':psutil.cpu_count(),'checks':[]}
    probes=[('reasoning','A train travels 60 km in 1 hour, then 30 km in 30 minutes. What is its average speed in km/h? Explain briefly.',None,None),
            ('structured','Return JSON with city equal to Delhi and count equal to 3.',{'type':'object','properties':{'city':{'type':'string'},'count':{'type':'integer'}},'required':['city','count'],'additionalProperties':False},None),
            ('coding','Write a Python function unique_in_order(values) that removes duplicates while keeping order. Include one example.',None,None),
            ('tool_calling','Use document_read to read candidate.txt. Do not answer from memory.',None,[{'type':'function','function':{'name':'document_read','description':'Read a workspace document','parameters':{'type':'object','properties':{'path':{'type':'string'}},'required':['path'],'additionalProperties':False}}}])]
    from threading import Event, Thread
    for name,prompt,schema,tools in probes:
        stop=Event(); samples=[]
        psutil.cpu_percent(interval=None)
        def sample():
            while not stop.wait(0.1):
                samples.append({'cpu_percent':psutil.cpu_percent(),'system_used_gib':psutil.virtual_memory().used/2**30,'ollama_rss_gib':ollama_rss_gib()})
        thread=Thread(target=sample,daemon=True); thread.start()
        started=time.perf_counter()
        try:
            response=llm.chat(model,[{'role':'user','content':prompt}],tools=tools,schema=schema)
            check={'name':name,'status':'completed','result':response.content,'tool_calls':response.tool_calls,'metrics':response.metrics}
            if name=='structured':
                check['valid']=json.loads(response.content)=={'city':'Delhi','count':3}
            elif name=='tool_calling':
                check['valid']=bool(response.tool_calls) and response.tool_calls[0]['name']=='document_read' and response.tool_calls[0]['arguments']=={'path':'candidate.txt'}
            else:
                check['quality']='Requires human review; generated code was not executed'
        except Exception as e:
            check={'name':name,'status':'failed','error':str(e)}
        finally:
            stop.set(); thread.join()
        check['elapsed_seconds']=time.perf_counter()-started
        if samples:
            check['peak_system_used_gib']=max(s['system_used_gib'] for s in samples)
            check['peak_ollama_rss_gib']=max(s['ollama_rss_gib'] for s in samples)
            check['mean_host_cpu_percent']=sum(s['cpu_percent'] for s in samples)/len(samples)
        report['checks'].append(check)
    if shutil.which('nvidia-smi'):
        gpu=subprocess.run(['nvidia-smi','--query-gpu=name,memory.total,memory.used,utilization.gpu','--format=csv,noheader'],capture_output=True,text=True,timeout=15)
        report['gpu_snapshot']=gpu.stdout.strip() if gpu.returncode==0 else 'nvidia-smi failed'
    else:
        report['gpu_snapshot']='No NVIDIA GPU is available; VRAM and GPU utilization are unmeasured'
    return report


def main(argv=None):
    args=parser().parse_args(argv)
    try:
        if args.timeout <= 0:
            raise ValueError('timeout must be positive')
        args.data_dir.mkdir(parents=True,exist_ok=True)
        registry=Registry(Database(args.data_dir/'platform.sqlite'))
        workspace=Workspace(args.workspace)
        llm=LLM(args.data_dir/'inference.lock',timeout=args.timeout,allow_remote=args.allow_remote_models)
        service=TaskService(registry,ToolExecutor(workspace),llm)
        if args.command=='init':
            seed(registry,args.model,args.base_url,args.router_model)
            emit({'status':'initialized','database':registry.db.path,'workspace':workspace.root})
        elif args.command=='serve':
            import webbrowser
            from filelock import FileLock
            from app.services.sessions import SessionStore
            from app.services.jobs import JobWorker
            from app.web.server import create_server
            if not 1 <= args.port <= 65535:
                raise ValueError('port must be between 1 and 65535')
            with FileLock(args.data_dir/'workspace-service.lock', timeout=0):
                seed(registry)
                store=SessionStore(registry.db, workspace.root)
                server=create_server(store, registry, args.port)
                worker=JobWorker(store, registry, llm)
                worker.start()
                print(f'Local workspace listening on port {server.server_port}. Press Ctrl+C to stop.',flush=True)
                if args.open_browser:
                    webbrowser.open(f'http://127.0.0.1:{server.server_port}')
                try:
                    server.serve_forever()
                except KeyboardInterrupt:
                    print('Stopping; waiting for any in-flight model request to finish.',flush=True)
                finally:
                    server.server_close()
                    worker.close()
        elif args.command in ('agents','models','tools'):
            if args.action=='list':
                emit(getattr(registry,'list_'+args.command)())
            elif args.action=='show':
                emit(getattr(registry,'get_'+args.command[:-1])(args.id))
            elif args.action=='add':
                cls=Agent if args.command=='agents' else Model
                record=cls.model_validate_json(args.config.read_text(encoding='utf-8'))
                emit(getattr(registry,'add_'+args.command[:-1])(record))
            elif args.action=='update':
                changes={k:getattr(args,k) for k in ('model_id','fallback_model_id','tools','permission_level') if getattr(args,k) is not None}
                emit(registry.update_agent(args.id,**changes))
            else:
                registry.set_enabled(args.command,args.id,args.action=='enable')
                emit({'id':args.id,'enabled':args.action=='enable'})
        elif args.command in ('run','recruit'):
            task=service.run(args.request,agent_id=args.agent,attachments=args.attach) if args.command=='run' else service.recruit(args.cv,args.job_description,args.agent)
            emit({'task_id':task['id'],'selected_agent':task['assigned_agent_id'],'models_used':[r['data']['model_id'] for r in task['task_runs']],'status':task['status'],'result':task['result'],'error':task['error']})
            return 0 if task['status']=='completed' else 1
        elif args.command=='task':
            emit(registry.db.task(args.id))
        elif args.command=='doctor':
            emit(doctor(registry,llm,args.model))
        elif args.command=='benchmark':
            report=benchmark(registry,llm,args.model)
            if args.output:
                args.output.parent.mkdir(parents=True,exist_ok=True)
                args.output.write_text(json.dumps(redact_data(report),indent=2),encoding='utf-8')
            emit(report)
            return 0 if all(c['status']=='completed' and c.get('valid',True) for c in report['checks']) else 1
        elif args.command=='test-workspace':
            if not args.trust_workspace_code:
                raise PermissionError('tests execute arbitrary code; use --trust-workspace-code only for code you trust')
            task_id=registry.db.create_task('User-authorized workspace pytest run')
            command=[sys.executable,'-m','pytest','-q']
            try:
                # Python timestamp caches can miss same-size edits made in one second.
                # Isolate each authorized run instead of deleting user cache directories.
                with tempfile.TemporaryDirectory(prefix='local-agent-pycache-') as cache:
                    env = dict(os.environ, PYTHONPYCACHEPREFIX=cache)
                    result=subprocess.run(command,cwd=workspace.root,env=env,capture_output=True,text=True,timeout=120)
                registry.db.event('tool_calls',task_id,{'tool_id':'user_test_runner','command':command,'status':'completed' if result.returncode==0 else 'failed','exit_code':result.returncode,'output':(result.stdout+result.stderr)[-20000:]})
                registry.db.finish_task(task_id,'completed' if result.returncode==0 else 'failed',result=result.stdout[-20000:])
                emit({'task_id':task_id,'exit_code':result.returncode,'output':result.stdout[-20000:],'stderr':result.stderr[-20000:]})
                return result.returncode
            except Exception as e:
                service._finish_error(task_id,e)
                raise
        return 0
    except Exception as e:
        print(redact(str(e)),file=sys.stderr)
        return 1
