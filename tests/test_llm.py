import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest
from app.core.llm import LLM
from app.core.schemas import Model


@pytest.fixture
def endpoint():
    requests = []
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            requests.append((self.path,body))
            if body['model']=='slow':
                __import__('time').sleep(0.1)
            if self.path == '/api/chat':
                result = {'message':{'role':'assistant','content':'hello','tool_calls':[{'function':{'name':'document_read','arguments':{'path':'cv.txt'}}}]}, 'eval_count':12,'eval_duration':2_000_000_000,'load_duration':100_000_000}
            else:
                result = {'choices':[{'message':{'role':'assistant','content':'hello','tool_calls':[{'id':'call_1','type':'function','function':{'name':'document_read','arguments':'{"path":"cv.txt"}'}}]}}],'usage':{'completion_tokens':12}}
            payload=json.dumps(result).encode()
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.end_headers()
            try:
                self.wfile.write(payload)
            except BrokenPipeError:
                pass
        def log_message(self,*args):
            pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=Thread(target=server.serve_forever,daemon=True)
    thread.start()
    yield f'http://127.0.0.1:{server.server_port}', requests
    server.shutdown()
    thread.join()
    server.server_close()


@pytest.mark.parametrize('provider', ['ollama','openai_compatible'])
def test_provider_normalizes_tool_calls(endpoint,tmp_path,provider):
    url,requests=endpoint
    model=Model(id='m',name='M',model_name='local',base_url=url,provider=provider)
    result=LLM(tmp_path/'inference.lock').chat(model,[{'role':'user','content':'hi'}],schema={'type':'object'})
    assert result.content=='hello'
    assert result.tool_calls[0]['name']=='document_read'
    assert result.tool_calls[0]['arguments']=={'path':'cv.txt'}
    assert result.metrics['completion_tokens']==12
    assert requests[0][1]['model']=='local'
    if provider=='ollama':
        assert requests[0][1]['think'] is False
        assert result.metrics['tokens_per_second']==6
    else:
        assert requests[0][0]=='/v1/chat/completions'
        assert requests[0][1]['response_format']['type']=='json_schema'


def test_remote_model_requires_opt_in(tmp_path):
    model=Model(id='m',name='M',model_name='m',base_url='https://example.com')
    with pytest.raises(PermissionError, match='remote'):
        LLM(tmp_path/'lock').chat(model,[])


@pytest.mark.parametrize('base_path', ['/v1', '/api/v3'])
def test_openai_compatible_preserves_explicit_api_version(endpoint, tmp_path, base_path):
    url, requests = endpoint
    model = Model(id='versioned', name='Versioned', provider='openai_compatible',
                  model_name='test-model', base_url=url + base_path)
    result = LLM(tmp_path/'version.lock').chat(model, [{'role':'user','content':'hi'}])
    assert requests[0][0] == base_path + '/chat/completions'
    assert result.content == 'hello'


def test_disabled_model_rejected(tmp_path):
    model=Model(id='m',name='M',model_name='m',enabled=False)
    with pytest.raises(ValueError, match='disabled'):
        LLM(tmp_path/'lock').chat(model,[])


def test_ollama_thinking_can_be_enabled_for_reasoning(endpoint,tmp_path):
    url,requests=endpoint
    model=Model(id='m',name='M',model_name='local',base_url=url,thinking=True)
    LLM(tmp_path/'lock').chat(model,[{'role':'user','content':'reason'}])
    assert requests[0][1]['think'] is True


def test_request_timeout_is_actionable(endpoint,tmp_path):
    url,_=endpoint
    model=Model(id='m',name='M',model_name='slow',base_url=url)
    with pytest.raises(RuntimeError,match='timed out'):
        LLM(tmp_path/'lock',timeout=0.01).chat(model,[{'role':'user','content':'hi'}])
