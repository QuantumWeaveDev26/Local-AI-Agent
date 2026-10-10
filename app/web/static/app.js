'use strict';
const $ = id => document.getElementById(id);
const state = {token: '', projects: [], project: null, session: null, sessions: [], selected: new Set(), inspected: null, fingerprint: '', fileFingerprint: '', submitting: false};
let saved;
try { saved = JSON.parse(localStorage.getItem('local-agent-workspace') || '{}'); } catch { saved = {}; }
saved.pending = saved.pending || {};
function persist() { localStorage.setItem('local-agent-workspace', JSON.stringify(saved)); }
function element(tag, text, className) { const node = document.createElement(tag); if (text !== undefined) node.textContent = text; if (className) node.className = className; return node; }
function error(message) { $('error').textContent = message; $('error').hidden = false; }
function act(fn) { return (...args) => Promise.resolve().then(() => fn(...args)).catch(e => error(e.message)); }
async function api(path, body, retry = true) {
  const headers = {'X-Workspace-Token': state.token};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  const response = await fetch(path, {method: body === undefined ? 'GET' : 'POST', headers, body: body === undefined ? undefined : JSON.stringify(body), cache: 'no-store'});
  const data = await response.json();
  if (response.status === 403 && retry && path !== '/api/bootstrap') {
    state.token = (await api('/api/bootstrap', undefined, false)).token;
    return api(path, body, false);
  }
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}
function selection() { $('attachments-label').textContent = state.selected.size ? `${state.selected.size} file(s) attached` : 'No attachments selected'; }
function composer() {
  const pending = saved.pending[state.session];
  $('message').disabled = !state.session || !!pending || state.submitting;
  $('send').disabled = !state.session || state.submitting;
  $('send').textContent = pending ? 'Retry submission' : 'Send';
  if (pending) $('message').value = pending.prompt;
  $('new-session').disabled = !state.project;
  $('upload').disabled = !state.project;
}
function navigation() {
  $('projects').replaceChildren();
  for (const project of state.projects) {
    const button = element('button', project.name, project.id === state.project ? 'active' : '');
    button.onclick = act(() => chooseProject(project.id)); $('projects').append(button);
  }
  $('sessions').replaceChildren();
  for (const session of state.sessions) {
    const button = element('button', session.title, session.id === state.session ? 'active' : '');
    button.onclick = act(() => chooseSession(session.id)); $('sessions').append(button);
  }
}
async function chooseProject(id) {
  state.project = id; state.session = null; state.selected.clear(); state.inspected = null;
  state.sessions = await api(`/api/projects/${id}/sessions`);
  if (state.project !== id) return;
  saved.project = id; $('project-title').textContent = state.projects.find(p => p.id === id).name;
  await chooseSession(state.sessions.some(s => s.id === saved.session) ? saved.session : state.sessions[0]?.id || null);
}
async function chooseSession(id) {
  state.session = id; state.inspected = null; state.fingerprint = ''; state.fileFingerprint = '';
  saved.session = id; persist(); $('message').value = ''; $('activity').replaceChildren(element('p', 'Inspect a task to see its agent, model and tool receipts.', 'footnote'));
  $('session-title').textContent = state.sessions.find(s => s.id === id)?.title || 'Create a conversation to begin.';
  navigation(); composer(); selection(); await refresh();
}
function renderTasks(tasks) {
  const fingerprint = JSON.stringify(tasks);
  if (state.fingerprint === fingerprint) return;
  state.fingerprint = fingerprint;
  $('conversation').replaceChildren();
  if (!tasks.length) $('conversation').append(element('div', 'Start with a question, an idea, or a document. Your conversation stays with this project.', 'empty'));
  for (const task of tasks) {
    const card = element('article', undefined, 'task'); card.dataset.taskId = task.id;
    card.append(element('p', task.user_request, 'question'));
    const meta = element('div', undefined, 'task-meta');
    let status = task.status[0].toUpperCase() + task.status.slice(1);
    if (task.cancel_requested && task.status === 'running') status = 'Cancellation requested · waiting for model call';
    meta.append(element('span', status, `task-status ${task.status}`), element('span', task.assigned_agent_id || 'Awaiting selection'));
    const inspect = element('button', 'Inspect task'); inspect.onclick = act(async () => { state.inspected = task.id; await activity(task.id); }); meta.append(inspect);
    if (['queued', 'running'].includes(task.status)) {
      const cancel = element('button', 'Cancel task'); cancel.disabled = !!task.cancel_requested;
      cancel.onclick = act(async () => { await api(`/api/tasks/${task.id}/cancel`, {}); await refresh(); }); meta.append(cancel);
    }
    card.append(meta);
    if (task.result !== null) card.append(element('pre', task.result, 'answer'));
    if (task.error) card.append(element('p', task.error, 'task-error'));
    $('conversation').append(card);
  }
}
async function activity(id) {
  const task = await api(`/api/tasks/${id}`);
  if (state.inspected !== id) return;
  const pane = $('activity'); pane.replaceChildren(element('p', `${task.status} · ${task.assigned_agent_id || 'unassigned'}`, 'footnote'));
  const models = [...new Set(task.task_runs.map(run => run.data.model_id))];
  pane.append(element('p', `Models: ${models.join(', ') || 'not yet called'}`, 'footnote'), element('p', `Task ${task.id}`, 'footnote'));
  const events = [];
  for (const table of ['messages', 'task_runs', 'tool_calls', 'outputs', 'errors']) {
    for (const event of task[table]) events.push({...event, table});
  }
  events.sort((a, b) => a.created_at.localeCompare(b.created_at) || a.id - b.id);
  for (const event of events) {
    const box = element('details', undefined, 'event');
    box.append(element('summary', `${event.table} · ${event.data.tool_id || event.data.model_id || event.data.role || event.data.status || 'result'}`));
    const text = JSON.stringify(event.data, null, 2);
    box.append(element('pre', text.length > 20000 ? text.slice(0, 20000) + '\n[Display truncated; full event remains in the database]' : text)); pane.append(box);
  }
}
function renderFiles(files) {
  const fingerprint = JSON.stringify(files);
  if (state.fileFingerprint === fingerprint) return;
  state.fileFingerprint = fingerprint;
  const names = new Set(files.map(file => file.path)); state.selected = new Set([...state.selected].filter(path => names.has(path))); selection();
  $('files').replaceChildren();
  if (!files.length) $('files').append(element('p', 'No files yet.', 'footnote'));
  for (const file of files) {
    const row = element('div', undefined, 'file'), label = element('label'), check = element('input');
    check.type = 'checkbox'; check.checked = state.selected.has(file.path); check.setAttribute('aria-label', `Attach ${file.path}`);
    check.onchange = () => { check.checked ? state.selected.add(file.path) : state.selected.delete(file.path); selection(); };
    label.append(check, document.createTextNode(file.path));
    const download = element('button', 'Download');
    const project = state.project;
    download.onclick = act(async () => {
      const response = await fetch(`/api/projects/${project}/files/download?path=${encodeURIComponent(file.path)}`, {headers: {'X-Workspace-Token': state.token}});
      if (!response.ok) throw new Error((await response.json()).error);
      const href = URL.createObjectURL(await response.blob()), link = element('a'); link.href = href; link.download = file.path.split('/').pop(); link.click(); setTimeout(() => URL.revokeObjectURL(href), 1000);
    }); row.append(label, download); $('files').append(row);
  }
}
async function refresh() {
  const session = state.session, project = state.project;
  if (!project) return;
  const [data, files] = await Promise.all([session ? api(`/api/sessions/${session}`) : Promise.resolve({tasks: []}), api(`/api/projects/${project}/files`)]);
  if (session !== state.session || project !== state.project) return;
  renderTasks(data.tasks); renderFiles(files);
  // Recover an accepted submission whose HTTP reply was lost, without resending it.
  if (saved.pending[session]) {
    const pending = saved.pending[session];
    // Retrying uses the persisted key; matching prompts alone would be ambiguous.
    if (pending.accepted) { delete saved.pending[session]; persist(); composer(); }
  }
  if (state.inspected) await activity(state.inspected);
  $('connection').textContent = 'Connected';
}
$('new-project').onclick = () => { $('project-dialog').showModal(); $('project-name').focus(); };
$('close-dialog').onclick = () => $('project-dialog').close();
$('project-form').onsubmit = act(async event => {
  event.preventDefault(); const project = await api('/api/projects', {name: $('project-name').value});
  state.projects.push(project); $('project-dialog').close(); $('project-form').reset(); await chooseProject(project.id); await newSession();
});
async function newSession() {
  const project = state.project;
  const session = await api(`/api/projects/${project}/sessions`, {title: `Conversation ${state.sessions.length + 1}`});
  if (project !== state.project) return;
  state.sessions.push(session); await chooseSession(session.id);
}
$('new-session').onclick = act(newSession);
$('composer').onsubmit = act(async event => {
  event.preventDefault(); const session = state.session;
  if (!session || state.submitting) return;
  const pending = saved.pending[session] || {key: crypto.randomUUID(), prompt: $('message').value, agent_id: $('agent').value || null, attachments: [...state.selected]};
  if (!pending.prompt.trim()) return;
  saved.pending[session] = pending; persist(); state.submitting = true; composer(); $('error').hidden = true;
  try {
    await api(`/api/sessions/${session}/tasks`, pending); delete saved.pending[session]; persist();
    if (state.session === session) { $('message').value = ''; state.selected.clear(); state.fileFingerprint = ''; selection(); await refresh(); }
  } finally { state.submitting = false; composer(); }
});
$('upload').onchange = act(async () => {
  const file = $('upload').files[0], project = state.project;
  if (!file || !project) return;
  if (file.size > 5000000) throw new Error('Document exceeds 5 MB');
  const content = await new Promise((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(reader.result.split(',')[1]); reader.onerror = () => reject(new Error('Could not read the selected file')); reader.readAsDataURL(file); });
  await api(`/api/projects/${project}/files`, {path: file.name, content}); $('upload').value = ''; state.fileFingerprint = ''; await refresh();
});
act(async () => {
  const boot = await api('/api/bootstrap'); state.token = boot.token; state.projects = boot.projects;
  for (const agent of boot.agents) { const option = element('option', agent.name); option.value = agent.id; $('agent').append(option); }
  if (boot.agents.some(agent => agent.id === 'assistant')) $('agent').value = 'assistant';
  if (state.projects.length) await chooseProject(state.projects.some(project => project.id === saved.project) ? saved.project : state.projects[0].id);
  else { navigation(); composer(); }
  $('connection').textContent = 'Connected';
  async function poll() { try { await refresh(); } catch (e) { $('connection').textContent = 'Reconnecting…'; error(e.message); } finally { setTimeout(poll, 1500); } }
  setTimeout(poll, 1500);
})();
