import hashlib

import pytest

from app.core.llm import Response
from tests.test_tasks import system, service
from app.tools.workspace import Workspace, ToolExecutor


def write(path, content='print("hello")\n'):
    return {'id': path, 'name': 'filesystem_write',
            'arguments': {'path': path, 'content': content}}


def test_claim_without_write_cannot_complete_required_files(system):
    task_service, _ = service(system, [Response('The files have been created.')])
    task = task_service.run('Create two files', agent_id='developer',
                            required_files=['dedupe.py', 'test_dedupe.py'])
    assert task['status'] == 'failed'
    assert 'dedupe.py' in task['error']
    assert not task['outputs']
    assert not task['tool_calls']


def test_actual_writes_verified_against_current_bytes(system):
    content = 'def greet():\n    return "hello"\n'
    task_service, _ = service(system, [Response('', [write('hello.py', content)]), Response('Created')])
    task = task_service.run('Create hello.py', agent_id='developer', required_files=['hello.py'])
    assert task['status'] == 'completed'
    assert task['outputs'][0]['data']['verified_files'] == [{
        'path': 'hello.py', 'bytes': len(content.encode()),
        'sha256': hashlib.sha256(content.encode()).hexdigest()}]
    assert system[1].read('hello.py') == content


def test_existing_file_does_not_substitute_for_a_new_write(system):
    system[1].write('hello.py', 'existing')
    task_service, _ = service(system, [Response('Created hello.py')])
    task = task_service.run('Create hello.py', agent_id='developer', required_files=['hello.py'])
    assert task['status'] == 'failed'
    assert 'successful write' in task['error']
    assert system[1].read('hello.py') == 'existing'


def test_partial_outputs_fail_and_preserve_receipts(system):
    task_service, _ = service(system, [Response('', [write('one.py')]), Response('Both created')])
    task = task_service.run('Create both', agent_id='developer', required_files=['one.py', 'two.py'])
    assert task['status'] == 'failed'
    assert 'two.py' in task['error']
    assert task['tool_calls'][0]['data']['status'] == 'completed'
    assert system[1].read('one.py') == 'print("hello")\n'


@pytest.mark.parametrize('damage', ['change', 'delete', 'fake-handler'])
def test_receipt_alone_is_insufficient_when_bytes_do_not_match(system, damage):
    task_service, _ = service(system, [Response('', [write('hello.py')]), Response('Created')])
    if damage == 'fake-handler':
        task_service.executor.register('filesystem_write', lambda **kw: 'Pretend success')
    else:
        def final_response(model, messages, **kwargs):
            if len(task_service.llm.calls) == 0:
                task_service.llm.calls.append({})
                return Response('', [write('hello.py')])
            if damage == 'delete':
                (system[1].root / 'hello.py').unlink()
            else:
                system[1].write('hello.py', 'changed')
            return Response('Created')
        task_service.llm.chat = final_response
    task = task_service.run('Create hello.py', agent_id='developer', required_files=['hello.py'])
    assert task['status'] == 'failed'
    assert 'hello.py' in task['error']
    assert not task['outputs']


@pytest.mark.parametrize('paths', ['hello.py', [1], ['../escape.py'], ['.env'],
                                  ['CON.py'], ['one.py', 'ONE.py'], ['a', 'a/b'],
                                  ['x.py'] * 9])
def test_invalid_requirements_fail_before_inference(system, paths):
    task_service, llm = service(system, [])
    task = task_service.run('Create files', agent_id='developer', required_files=paths)
    assert task['status'] == 'failed'
    assert not llm.calls


def test_latest_write_and_normalized_relative_path_are_verified(system):
    task_service, _ = service(system, [Response('', [write('src\\hello.py', 'old')]),
                                      Response('', [write('src/hello.py', 'new')]), Response('Created')])
    task = task_service.run('Create file', agent_id='developer', required_files=['src/hello.py'])
    assert task['status'] == 'completed'
    assert task['outputs'][0]['data']['verified_files'][0]['sha256'] == hashlib.sha256(b'new').hexdigest()


def test_required_files_do_not_execute_generated_code(system):
    content = 'raise RuntimeError("Never execute this during verification")\n'
    task_service, _ = service(system, [Response('', [write('hello.py', content)]), Response('Created')])
    task = task_service.run('Create file', agent_id='developer', required_files=['hello.py'])
    assert task['status'] == 'completed'
    assert task['outputs'][0]['data']['verified_files'][0]['bytes'] == len(content.encode())


def test_requirement_lookup_uses_same_resolved_spelling_as_write_receipt(system):
    class CaseNormalizedWorkspace(Workspace):
        # Emulate case-insensitive resolution on Linux; this is not a Windows run.
        def path(self, path):
            return super().path(str(path).lower())

    task_service, _ = service(system, [Response('', [write('SRC/Hello.py', 'hello')]), Response('Created')])
    task_service.executor = ToolExecutor(CaseNormalizedWorkspace(system[1].root))
    task = task_service.run('Create file', agent_id='developer', required_files=['Src/hello.py'])
    assert task['status'] == 'completed'
    assert task['outputs'][0]['data']['verified_files'][0]['path'] == 'Src/hello.py'


def test_required_filename_cannot_be_silently_changed_by_redaction(system):
    task_service, llm = service(system, [])
    task = task_service.run('Create file', agent_id='developer', required_files=['sk-abcdefghijklmnop.py'])
    assert task['status'] == 'failed'
    assert not llm.calls
    assert 'sensitive' in task['error']
    assert 'sk-abcdefghijklmnop' not in str(task)
