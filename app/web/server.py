"""Loopback-only API. Host/Origin/token checks protect the local user's authority."""
import base64
import binascii
import json
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlsplit

from app.core.agent_factory import AgentFactory
from app.database import redact_data

STATIC = {'/': ('index.html', 'text/html'), '/app.js': ('app.js', 'text/javascript'), '/style.css': ('style.css', 'text/css')}
MAX_BODY = 7_000_000
CSP = "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"


def create_server(store, registry, port=8765):
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(15)

        def log_message(self, *_):
            pass  # Prompt and file paths must not enter ordinary HTTP access logs.

        def reply(self, status, data, content_type='application/json', extra=None):
            body = data if isinstance(data, bytes) else json.dumps(redact_data(data), ensure_ascii=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', content_type + ('; charset=utf-8' if content_type != 'application/octet-stream' else ''))
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', CSP)
            self.send_header('Referrer-Policy', 'no-referrer')
            for key, value in (extra or {}).items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)

        def authorized(self, path):
            origins = {f'http://127.0.0.1:{self.server.server_port}', f'http://localhost:{self.server.server_port}'}
            hosts = {urlsplit(o).netloc for o in origins}
            origin = self.headers.get('Origin')
            if self.headers.get('Host') not in hosts or (origin is not None and origin not in origins):
                return False
            if self.headers.get('Sec-Fetch-Site') not in (None, 'same-origin', 'none'):
                return False
            if self.command == 'POST' and origin not in origins:
                return False
            if path.startswith('/api/') and path != '/api/bootstrap':
                return secrets.compare_digest(self.headers.get('X-Workspace-Token', ''), self.server.token)
            return True

        def body(self, required=(), optional=()):
            if self.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
                raise ValueError('Content-Type must be application/json')
            if self.headers.get('Transfer-Encoding'):
                raise ValueError('chunked bodies are unsupported')
            length = int(self.headers.get('Content-Length', '-1'))
            if length < 0 or length > MAX_BODY:
                raise ValueError('request body exceeds limit or is missing')
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValueError('incomplete body')
            data = json.loads(raw)
            if not isinstance(data, dict) or set(required) - set(data) or set(data) - set(required) - set(optional):
                raise ValueError('invalid request fields')
            return data

        def agents(self):
            available = []
            for agent in registry.list_agents(enabled_only=True):
                if agent.id == 'manager':
                    continue
                try:
                    runtime = AgentFactory(registry).load(agent.id)
                except ValueError:
                    continue
                available.append({'id': agent.id, 'name': agent.name, 'description': agent.description,
                                  'model_id': runtime.model.id, 'tools': agent.tools})
            return available

        def do_GET(self):
            self.handle_request()

        def do_POST(self):
            self.handle_request()

        def handle_request(self):
            try:
                self.route()
            except FileExistsError:
                self.reply(409, {'error': 'File already exists; use a different filename'})
            except FileNotFoundError:
                self.reply(404, {'error': 'File not found'})
            except PermissionError as error:
                self.reply(403, {'error': str(error)})
            except (ValueError, TypeError, binascii.Error) as error:
                self.reply(400, {'error': str(error)})
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception:
                self.reply(500, {'error': 'Local service error; inspect the task audit if available'})

        def route(self):
            parsed = urlsplit(self.path)
            path = parsed.path
            if not self.authorized(path):
                self.reply(403, {'error': 'Local request authority rejected'})
                return
            parts = path.strip('/').split('/')
            if self.command == 'GET':
                if path in STATIC:
                    filename, mime = STATIC[path]
                    self.reply(200, (Path(__file__).parent / 'static' / filename).read_bytes(), mime)
                    return
                if path == '/api/bootstrap':
                    self.reply(200, {'token': self.server.token, 'projects': store.projects(), 'agents': self.agents()})
                    return
                if path == '/api/agents':
                    self.reply(200, self.agents())
                    return
                if path == '/api/projects':
                    self.reply(200, store.projects())
                    return
                if len(parts) == 4 and parts[:2] == ['api', 'projects']:
                    if parts[3] == 'sessions':
                        self.reply(200, store.sessions(parts[2]))
                        return
                    if parts[3] == 'files':
                        self.reply(200, store.files(parts[2]))
                        return
                if len(parts) == 5 and parts[:2] == ['api', 'projects'] and parts[3:] == ['files', 'download']:
                    filename = parse_qs(parsed.query).get('path', [''])[0]
                    workspace = store.workspace(parts[2])
                    target = workspace.path(filename)
                    with target.open('rb') as file:
                        data = file.read(workspace.max_bytes + 1)
                    if len(data) > workspace.max_bytes:
                        raise ValueError('file exceeds download limit')
                    self.reply(200, data, 'application/octet-stream', {'Content-Disposition': "attachment; filename=download; filename*=UTF-8''" + quote(target.name, safe='')})
                    return
                if len(parts) == 3 and parts[:2] == ['api', 'sessions']:
                    self.reply(200, {'session': store.session(parts[2]), 'tasks': store.history(parts[2])})
                    return
                if len(parts) == 3 and parts[:2] == ['api', 'tasks']:
                    self.reply(200, store.task(parts[2]))
                    return
            if self.command == 'POST':
                if path == '/api/projects':
                    self.reply(201, store.create_project(self.body(['name'])['name']))
                    return
                if len(parts) == 4 and parts[:2] == ['api', 'projects']:
                    if parts[3] == 'sessions':
                        self.reply(201, store.create_session(parts[2], self.body(['title'])['title']))
                        return
                    if parts[3] == 'files':
                        data = self.body(['path', 'content'])
                        if not isinstance(data['content'], str) or not isinstance(data['path'], str):
                            raise ValueError('upload path and base64 content must be strings')
                        self.reply(201, store.upload(parts[2], data['path'], base64.b64decode(data['content'], validate=True)))
                        return
                if len(parts) == 4 and parts[:2] == ['api', 'sessions'] and parts[3] == 'tasks':
                    data = self.body(['key', 'prompt'], ['agent_id', 'attachments'])
                    agent_id = data.get('agent_id')
                    def validate_new_submission():
                        if agent_id is not None:
                            if not isinstance(agent_id, str) or agent_id == 'manager':
                                raise ValueError('choose a specialist or automatic routing')
                            AgentFactory(registry).load(agent_id)
                        else:
                            AgentFactory(registry).load('manager')
                    self.reply(202, store.submit(parts[2], data['key'], data['prompt'], agent_id, data.get('attachments', []), validate=validate_new_submission))
                    return
                if len(parts) == 4 and parts[:2] == ['api', 'tasks'] and parts[3] == 'cancel':
                    self.body()
                    self.reply(200, store.cancel(parts[2]))
                    return
            self.reply(404, {'error': 'Unknown route'})

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.token = secrets.token_urlsafe(32)
    return server
