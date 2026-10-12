// Run with: node --test tests/web-artifacts.test.cjs
// Exercise the shipped UI in a DOM harness; no browser or inference dependency.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.join(__dirname, '..');

class Node {
  constructor() { this.children = []; this.value = ''; this._text = ''; this.dataset = {}; }
  get textContent() { return this._text + this.children.map(c => c.textContent || '').join(''); }
  set textContent(value) { this._text = String(value); this.children = []; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; this._text = ''; }
  setAttribute() {}
}

async function ui() {
  const html = fs.readFileSync(path.join(root, 'app/web/static/index.html'), 'utf8');
  const nodes = new Map([...html.matchAll(/id="([^"]+)"/g)].map(match => [match[1], new Node()]));
  const storage = new Map();
  const context = vm.createContext({
    document: {getElementById: id => { assert.ok(nodes.has(id), id); return nodes.get(id); },
      createElement: () => new Node(), createTextNode: text => ({textContent: text})},
    localStorage: {getItem: key => storage.get(key) || null, setItem: (key, value) => storage.set(key, value)},
    crypto: require('node:crypto').webcrypto, TextEncoder,
    setTimeout: () => 0,
    fetch: async () => ({ok: true, status: 200, json: async () => ({token: 'fixture', projects: [], agents: []})}),
  });
  vm.runInContext(fs.readFileSync(path.join(root, 'app/web/static/app.js'), 'utf8'), context);
  await new Promise(resolve => setImmediate(resolve));
  vm.runInContext("state.project = 'project-1'; state.session = 'session-1'; refresh = async () => {}; composer();", context);
  return {context, nodes, storage};
}

test('submits explicit files with the selected Developer and clears the composer', async () => {
  const {context, nodes} = await ui();
  nodes.get('message').value = 'Create dedupe and tests';
  nodes.get('agent').value = 'developer';
  nodes.get('required-files').value = ' dedupe.py \n test_dedupe.py\n';
  vm.runInContext('let sent; api = async (url, body) => { sent = body; };', context);
  await nodes.get('composer').onsubmit({type: 'submit', preventDefault() {}});
  const sent = JSON.parse(vm.runInContext('JSON.stringify(sent)', context));
  assert.equal(sent.agent_id, 'developer');
  assert.deepEqual(sent.required_files, ['dedupe.py', 'test_dedupe.py']);
  assert.equal(nodes.get('required-files').value, '');
});

test('uncertain submission retries preserve original filenames and agent', async () => {
  const {context, nodes, storage} = await ui();
  nodes.get('message').value = 'Create file';
  nodes.get('agent').value = 'developer';
  nodes.get('required-files').value = 'hello.py';
  vm.runInContext("api = async () => { throw new Error('Network lost'); };", context);
  await nodes.get('composer').onsubmit({type: 'submit', preventDefault() {}});
  assert.ok(nodes.get('required-files').disabled);
  const first = JSON.parse(storage.get('local-agent-workspace')).pending['session-1'];
  nodes.get('agent').value = 'assistant';
  nodes.get('required-files').value = 'different.py';
  vm.runInContext('let retried; api = async (url, body) => { retried = body; };', context);
  await nodes.get('composer').onsubmit({type: 'submit', preventDefault() {}});
  const retried = JSON.parse(vm.runInContext('JSON.stringify(retried)', context));
  assert.deepEqual(retried, first);
});

test('ordinary replies show no tool actions and do not claim file verification', async () => {
  const {context, nodes} = await ui();
  vm.runInContext(`renderTasks([{id:'task-1',user_request:'Create file',status:'completed',
    assigned_agent_id:'developer',required_files:[],successful_tool_calls:0,result:'Created file'}]);`, context);
  const text = nodes.get('conversation').textContent;
  assert.ok(text.includes('Response only · no tool actions recorded'));
  assert.ok(!text.includes('File delivery verified'));
});

test('verified delivery label separates file bytes from code correctness', async () => {
  const {context, nodes} = await ui();
  vm.runInContext(`renderTasks([{id:'task-1',user_request:'Create file',status:'completed',
    assigned_agent_id:'developer',required_files:['hello.py'],successful_tool_calls:1,result:'Created'}]);`, context);
  assert.ok(nodes.get('conversation').textContent.includes('File delivery verified at completion · code not tested'));
});

test('failed requirements never show verified delivery', async () => {
  const {context, nodes} = await ui();
  vm.runInContext(`renderTasks([{id:'task-1',user_request:'Create file',status:'failed',
    assigned_agent_id:'developer',required_files:['hello.py'],successful_tool_calls:0,result:null,
    error:'Required output not verified: hello.py'}]);`, context);
  assert.ok(!nodes.get('conversation').textContent.includes('File delivery verified'));
  assert.ok(nodes.get('conversation').textContent.includes('Required output not verified'));
});

test('activity shows agent identity separately from the AI message role', async () => {
  const {context, nodes} = await ui();
  vm.runInContext(`state.inspected='task-1'; api=async()=>({id:'task-1',status:'completed',
    assigned_agent_id:'developer',task_runs:[],tool_calls:[],outputs:[],errors:[],
    messages:[{id:1,created_at:'2026-10-13',data:{role:'assistant',content:'Hello'}}]});`, context);
  await vm.runInContext("activity('task-1')", context);
  const text = nodes.get('activity').textContent;
  assert.ok(text.includes('Agent: developer'));
  assert.ok(text.includes('messages · AI response'));
  assert.ok(text.includes('No file delivery verification recorded'));
});
