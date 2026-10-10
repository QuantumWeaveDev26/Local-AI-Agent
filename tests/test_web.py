import base64
import threading

import httpx
import pytest

from app.agents.defaults import seed
from app.core.registry import Registry
from app.database import Database
from app.services.sessions import SessionStore
from app.web.server import create_server


@pytest.fixture
def web(tmp_path):
    registry = Registry(Database(tmp_path / 'data' / 'platform.sqlite'))
    seed(registry)
    store = SessionStore(registry.db, tmp_path / 'workspace')
    server = create_server(store, registry, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f'http://127.0.0.1:{server.server_port}'
    with httpx.Client(base_url=url, trust_env=False, headers={'Origin': url, 'X-Workspace-Token': server.token}) as client:
        yield client, store, server
    server.shutdown()
    server.server_close()
    thread.join()


def create_conversation(client):
    result = client.post('/api/projects', json={'name': 'Project'})
    assert result.status_code == 201, result.text
    project = result.json()
    session = client.post(f"/api/projects/{project['id']}/sessions", json={'title': 'Chat'}).json()
    return project, session


def test_live_api_submit_refresh_and_cancel(web):
    client, store, _ = web
    project, session = create_conversation(client)
    url = f"/api/sessions/{session['id']}/tasks"
    body = {'key': 'stable-key', 'prompt': 'Hello', 'agent_id': 'assistant', 'attachments': []}
    task = client.post(url, json=body).json()
    assert task['status'] == 'queued'
    assert client.post(url, json=body).json()['id'] == task['id']
    restored = client.get(f"/api/sessions/{session['id']}").json()
    assert restored['tasks'][0]['id'] == task['id']
    assert client.post(f"/api/tasks/{task['id']}/cancel", json={}).json()['status'] == 'cancelled'
    assert client.get('/api/bootstrap').json()['projects'][0]['id'] == project['id']
    assert client.get('/api/agents').json()[0]['id'] == 'assistant'


def test_accepted_submission_retries_even_after_agent_disabled(web):
    client, store, _ = web
    _, session = create_conversation(client)
    url = f"/api/sessions/{session['id']}/tasks"
    body = {'key': 'accepted-key', 'prompt': 'Hello', 'agent_id': 'assistant', 'attachments': []}
    task = client.post(url, json=body).json()
    Registry(store.db).set_enabled('agents', 'assistant', False)
    reply = client.post(url, json=body)
    assert reply.status_code == 202, reply.text
    assert reply.json()['id'] == task['id']
    history = client.get(f"/api/sessions/{session['id']}").json()['tasks']
    import hashlib
    assert history[0]['request_key_digest'] == hashlib.sha256(b'accepted-key').hexdigest()


@pytest.mark.parametrize('headers', [
    {'Host': 'evil.example'},
    {'Origin': 'https://evil.example'},
    {'X-Workspace-Token': 'wrong'},
    {'Sec-Fetch-Site': 'cross-site'},
])
def test_api_rejects_cross_site_or_missing_authority(web, headers):
    client, _, _ = web
    response = client.post('/api/projects', json={'name': 'Unauthorized'}, headers=headers)
    assert response.status_code == 403
    assert client.get('/api/projects').json() == []


def test_token_required_on_private_get_and_origin_required_on_post(web):
    client, _, server = web
    client.headers.pop('X-Workspace-Token')
    assert client.get('/api/projects').status_code == 403
    assert client.get('/api/bootstrap').json()['token'] == server.token
    client.headers['X-Workspace-Token'] = server.token
    client.headers.pop('Origin')
    assert client.post('/api/projects', json={'name': 'Bad'}).status_code == 403
    assert client.get('/api/projects').status_code == 200


def test_upload_download_and_scope(web):
    client, _, _ = web
    project, _ = create_conversation(client)
    url = f"/api/projects/{project['id']}/files"
    body = {'path': 'cv.txt', 'content': base64.b64encode(b'Alex knows Python').decode()}
    assert client.post(url, json=body).status_code == 201
    assert client.post(url, json=body).status_code == 409
    assert client.get(url).json() == [{'path': 'cv.txt', 'bytes': 17}]
    response = client.get(url + '/download', params={'path': 'cv.txt'})
    assert response.content == b'Alex knows Python'
    assert 'attachment;' in response.headers['Content-Disposition']
    other, _ = create_conversation(client)
    assert client.get(f"/api/projects/{other['id']}/files/download", params={'path': 'cv.txt'}).status_code == 404
    assert client.post(url, json={**body, 'path': '../escape.txt'}).status_code == 403
    assert client.post(url, json={**body, 'content': 'invalid!'}).status_code == 400
    assert client.post(url, json={**body, 'content': base64.b64encode(b'x'*5_000_001).decode()}).status_code == 400


def test_invalid_inputs_fail_without_job_and_static_paths_are_allowlisted(web):
    client, store, _ = web
    _, session = create_conversation(client)
    url = f"/api/sessions/{session['id']}/tasks"
    assert client.post(url, json={'key': 'x', 'prompt': '', 'agent_id': 'assistant'}).status_code == 400
    assert client.post(url, json={'key': 'x', 'prompt': 'hello', 'agent_id': 'missing'}).status_code == 400
    assert client.post(url, json={'key': 'x', 'prompt': 'hello', 'unexpected': True}).status_code == 400
    assert store.history(session['id']) == []
    assert client.get('/data/platform.sqlite').status_code == 404
    assert client.get('/api/projects', headers={'Host': 'evil.example'}).status_code == 403
    assert client.post('/api/projects', content='[]', headers={'Content-Type': 'application/json'}).status_code == 400
    assert client.post('/api/projects', content='{}', headers={'Content-Type': 'text/plain'}).status_code == 400
