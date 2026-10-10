"""Provider adapters with a single normalized result and cross-process queuing."""
import ipaddress
import json
import os
import time
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx
from filelock import FileLock


@dataclass
class Response:
    content: str
    tool_calls: list[dict] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    message: dict = field(default_factory=dict)


class LLM:
    def __init__(self, lock_path, timeout=180, allow_remote=False):
        self.lock = FileLock(str(lock_path), timeout=timeout)
        self.timeout = timeout
        self.allow_remote = allow_remote

    def _check(self, model):
        if not model.enabled:
            raise ValueError(f'model {model.id} is disabled')
        hostname = urlparse(model.base_url).hostname
        local = hostname == 'localhost'
        try:
            local = local or ipaddress.ip_address(hostname).is_loopback
        except ValueError:
            pass
        if not local and not self.allow_remote:
            raise PermissionError('remote model endpoints require explicit --allow-remote-models opt-in')
        if not local and urlparse(model.base_url).scheme != 'https':
            raise PermissionError('remote model endpoints must use HTTPS')
        return local

    def chat(self, model, messages, tools=None, schema=None):
        local = self._check(model)
        headers = {}
        if model.api_key_env:
            key = os.environ.get(model.api_key_env)
            if not key:
                raise ValueError(f'required credential binding is missing: {model.api_key_env}')
            headers['Authorization'] = f'Bearer {key}'
        body = {'model':model.model_name, 'messages':messages, 'stream':False}
        if tools:
            body['tools'] = tools
        if model.provider == 'ollama':
            url = model.base_url + '/api/chat'
            body.update(think=model.thinking, keep_alive='10m', options={'temperature':0,'num_ctx':model.context_length,'num_predict':1200,'num_thread':min(os.cpu_count() or 4, 8)})
            if schema:
                body['format'] = schema
        else:
            url = model.base_url + ('/chat/completions' if model.base_url.endswith('/v1') else '/v1/chat/completions')
            body.update(temperature=0, max_tokens=1200)
            if schema:
                body['response_format'] = {'type':'json_schema','json_schema':{'name':'result','strict':True,'schema':schema}}
            # Convert our provider-neutral assistant/tool messages to OpenAI wire format.
            body['messages'] = []
            for message in messages:
                m = dict(message)
                if m.get('tool_calls'):
                    m['tool_calls'] = [{'id':call['id'],'type':'function','function':{'name':call['function']['name'],'arguments':json.dumps(call['function']['arguments'])}} for call in m['tool_calls']]
                m.pop('tool_name',None)
                body['messages'].append(m)
        started = time.perf_counter()
        with self.lock:
            with httpx.Client(timeout=self.timeout,trust_env=not local,follow_redirects=False) as client:
                try:
                    response = client.post(url,json=body,headers=headers)
                except httpx.TimeoutException as error:
                    raise RuntimeError(f'{model.provider} request timed out after {self.timeout} seconds; reduce context/output or increase timeout') from error
                if response.status_code >= 400:
                    # Do not persist raw error bodies that may include provider credentials.
                    raise RuntimeError(f'{model.provider} HTTP {response.status_code}; check endpoint, model and service logs')
                data = response.json()
        if model.provider == 'ollama':
            message = data['message']
            count = data.get('eval_count',0)
            duration = data.get('eval_duration',0)/1e9
            metrics = {'completion_tokens':count,'tokens_per_second':count/duration if duration else None,'load_seconds':data.get('load_duration',0)/1e9,'generation_seconds':duration}
        else:
            message = data['choices'][0]['message']
            metrics = {'completion_tokens':data.get('usage',{}).get('completion_tokens')}
        metrics['elapsed_seconds'] = time.perf_counter()-started
        calls = []
        normalized = {'role':'assistant','content':message.get('content') or ''}
        for i,call in enumerate(message.get('tool_calls') or []):
            function = call['function']
            args = function.get('arguments',{})
            if isinstance(args,str):
                args = json.loads(args)
            if not isinstance(args,dict):
                raise ValueError('model returned invalid tool arguments')
            calls.append({'id':call.get('id',f'call_{i}'),'name':function['name'],'arguments':args})
        if calls:
            normalized['tool_calls'] = [{'id':c['id'],'type':'function','function':{'name':c['name'],'arguments':c['arguments']}} for c in calls]
        return Response(normalized['content'],calls,metrics,normalized)
