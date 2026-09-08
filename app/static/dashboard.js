'use strict';
const $ = (selector) => document.querySelector(selector);
const state = {view: 'maintenance', properties: [], maintenance: [], approvals: [], audit: [], config: null, loaded: false, detailId: null, detailVersion: 0, busy: false};
const views = {
  maintenance: ['Maintenance', 'Keep every issue moving, from report to decision.', 'Request queue', 'Review issues and decide the next step.', '+ New request'],
  properties: ['Properties', 'A clear view of the places you manage.', 'Your portfolio', 'Properties and their pending maintenance requests.', '+ Add property'],
  approvals: ['Approvals', 'Review the work before it goes ahead.', 'Decision queue', 'Open a request to approve or reject proposed work.', null],
  audit: ['Audit history', 'A record of the decisions made in your workspace.', 'Decision history', 'Approval and rejection events, newest first.', null],
};
const escapeHTML = (value) => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const badge = (value) => `<span class="badge ${['pending','approved','rejected','high','medium','low','active'].includes(value) ? value : ''}">${escapeHTML(value)}</span>`;
const property = (id) => state.properties.find(item => item.id === id);
const request = (id) => state.maintenance.find(item => item.id === id);
function message(selector, text) { $(selector).textContent = text; $(selector).hidden = !text; }
async function api(path, body) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 60000);
  try {
    const response = await fetch(path, {signal: controller.signal, ...(body !== undefined ? {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)} : {})});
    const data = await response.json();
    if (!response.ok) {
      const detail = data.detail;
      throw new Error(typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map(x => x.msg).join('. ') : `Request failed (${response.status}).`);
    }
    return data;
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('The request timed out. Refresh before trying again to check whether it was saved.');
    if (error instanceof TypeError) throw new Error('Cannot reach PropertyOps. Check that the app is running, then refresh.');
    throw error;
  } finally { clearTimeout(timeout); }
}
async function load() {
  $('#refresh').disabled = true;
  $('#records').setAttribute('aria-busy', 'true');
  try {
    const [properties, maintenance, approvals, audit, config] = await Promise.all([
      api('/properties'), api('/maintenance'), api('/approvals'), api('/audit-logs'),
      api('/triage-config').catch(error => ({error: error.message})),
    ]);
    Object.assign(state, {properties, maintenance, approvals, audit, config, loaded:true});
    $('#primary-action').disabled = false;
    $('#stat-properties').textContent = properties.length;
    $('#stat-maintenance').textContent = maintenance.filter(x => x.status === 'pending').length;
    $('#stat-approvals').textContent = approvals.filter(x => x.status === 'pending').length;
    $('#nav-count').textContent = approvals.filter(x => x.status === 'pending').length;
    $('#mode-name').textContent = config.error ? 'Unavailable' : config.mode === 'rules' ? 'Rules mode' : 'AI mode';
    $('#mode-description').textContent = config.error ? 'Check triage configuration' : config.mode === 'rules' ? 'No API credit needed' : config.configured ? 'API credit required · human review' : 'API key required';
    render();
    return true;
  } catch (error) {
    message('#error', `${error.message}${state.loaded ? ' Showing the last loaded records.' : ''}`);
    if (!state.loaded) $('#records').innerHTML = empty('Workspace unavailable', 'Use Refresh to try loading your records again.');
    return false;
  } finally {
    $('#refresh').disabled = false;
    $('#records').setAttribute('aria-busy', 'false');
  }
}
function empty(title, description, action) {
  return `<div class="empty"><span class="empty-icon" aria-hidden="true">▦</span><h3>${escapeHTML(title)}</h3><p>${escapeHTML(description)}</p>${action ? `<button class="primary" data-create="${action}">${action === 'property' ? '+ Add property' : '+ New request'}</button>` : ''}</div>`;
}
function table(headers, rows) { return `<div class="table-scroll"><table><thead><tr>${headers.map(h => `<th scope="col">${h}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`; }
function render() {
  const query = $('#search').value.trim().toLowerCase();
  const status = $('#status-filter').value;
  const data = state[state.view];
  const filtered = [...data].reverse().filter(item => {
    const linked = state.view === 'approvals' ? request(item.maintenance_request_id) : item;
    const prop = state.view === 'properties' ? item : property(linked?.property_id);
    const text = [item.id, item.issue, item.reason, item.name, item.address, item.actor, item.new_status, item.resource_id, linked?.issue, prop?.name, prop?.address].join(' ').toLowerCase();
    return text.includes(query) && (state.view === 'properties' || state.view === 'audit' || status === 'all' || item.status === status);
  });
  $('#record-count').textContent = `${filtered.length} of ${data.length}`;
  if (!filtered.length) {
    const defaults = {
      maintenance: ['No maintenance requests yet', state.properties.length ? 'Report an issue to start tracking maintenance and review its next steps.' : 'Add your first property, then report a maintenance issue.', state.properties.length ? 'maintenance' : 'property'],
      properties: ['Your portfolio starts here', 'Add a property to begin managing maintenance and approvals.', 'property'],
      approvals: ['No approvals to review', 'Open a maintenance request and choose Request approval to add it here.'],
      audit: ['No decisions recorded yet', 'Approving or rejecting a request will add an event to this history.'],
    };
    $('#records').innerHTML = query || (status !== 'all' && ['maintenance','approvals'].includes(state.view)) ? empty('No matching records', 'Try a different search or status filter.') : empty(...defaults[state.view]);
    return;
  }
  let headers, rows;
  if (state.view === 'maintenance') {
    headers = ['Request', 'Property', 'Priority', 'Status', ''];
    rows = filtered.map(item => `<tr><td><button class="row-link request-title" data-detail="${item.id}">${escapeHTML(item.issue)}</button><small>Request #${item.id}</small></td><td>${escapeHTML(property(item.property_id)?.name || `Property #${item.property_id}`)}</td><td>${badge(item.priority)}</td><td>${badge(item.status)}</td><td><button class="row-link" data-detail="${item.id}" aria-label="Review request ${item.id}">Review →</button></td></tr>`);
  } else if (state.view === 'properties') {
    headers = ['Property', 'Address', 'Status', 'Pending requests'];
    rows = filtered.map(item => `<tr><td><strong>${escapeHTML(item.name)}</strong><small>Property #${item.id}</small></td><td>${escapeHTML(item.address)}</td><td>${badge(item.status)}</td><td>${state.maintenance.filter(x => x.property_id === item.id && x.status === 'pending').length}</td></tr>`);
  } else if (state.view === 'approvals') {
    headers = ['Request', 'Reason for approval', 'Status', ''];
    rows = filtered.map(item => `<tr><td><button class="row-link request-title" data-detail="${item.maintenance_request_id}">${escapeHTML(request(item.maintenance_request_id)?.issue || `Request #${item.maintenance_request_id}`)}</button><small>Approval #${item.id} · Request #${item.maintenance_request_id}</small></td><td>${escapeHTML(item.reason)}</td><td>${badge(item.status)}</td><td><button class="row-link" data-detail="${item.maintenance_request_id}">Review →</button></td></tr>`);
  } else {
    headers = ['Event', 'Approval', 'From', 'Decision', 'Actor'];
    rows = filtered.map(item => `<tr><td><strong>Approval decision</strong><small>Event #${item.id}</small></td><td>#${item.resource_id}</td><td>${badge(item.old_status || '—')}</td><td>${badge(item.new_status || '—')}</td><td>${escapeHTML(item.actor)}</td></tr>`);
  }
  $('#records').innerHTML = table(headers, rows);
}
function setView(view) {
  if (!views[view]) return;
  state.view = view;
  const [title, description, listTitle, listDescription, action] = views[view];
  $('#page-title').textContent = title; $('#breadcrumb').textContent = title.toUpperCase();
  $('#page-description').textContent = description; $('#list-title').textContent = listTitle; $('#list-description').textContent = listDescription;
  $('#primary-action').textContent = action || ''; $('#primary-action').hidden = !action;
  $('#status-control').hidden = !['maintenance', 'approvals'].includes(view);
  $('#search').value = ''; $('#status-filter').value = 'all';
  $('#search').placeholder = view === 'properties' ? 'Search properties or addresses' : view === 'audit' ? 'Search events or decisions' : 'Search requests or properties';
  document.querySelectorAll('.nav').forEach(button => { button.classList.toggle('active', button.dataset.view === view); if (button.dataset.view === view) button.setAttribute('aria-current','page'); else button.removeAttribute('aria-current'); });
  if (state.loaded) render();
}
const field = (label, control, hint = '') => `<label class="field">${label}${control}${hint ? `<small>${hint}</small>` : ''}</label>`;
function openEditor(type) {
  if (!state.loaded || state.busy) return;
  if (type === 'maintenance' && !state.properties.length) {
    type = 'property'; message('#notice', 'Add a property first. You can then create a maintenance request.');
  }
  $('#editor-form').dataset.type = type;
  $('#editor-title').textContent = type === 'property' ? 'Add property' : 'New maintenance request';
  $('#editor-fields').innerHTML = type === 'property'
    ? field('Property name', '<input name="name" required maxlength="160" placeholder="e.g. Riverside House" autocomplete="off">') + field('Address', '<textarea name="address" required maxlength="500" placeholder="Street, town and postcode" autocomplete="street-address"></textarea>')
    : field('Property', `<select name="property_id" required>${state.properties.map(p => `<option value="${p.id}">${escapeHTML(p.name)}</option>`).join('')}</select>`) + field('Issue', '<textarea name="issue" required maxlength="8000" placeholder="Describe the issue, its location and what you have observed."></textarea>') + field('Priority', '<select name="priority"><option value="low">Low</option><option value="medium" selected>Medium</option><option value="high">High</option></select>', 'Triage can suggest a priority; it will not change this value.');
  message('#form-error',''); $('#editor').showModal();
}
async function showDetail(id) {
  const item = request(id);
  if (!item) { message('#error','This request is no longer available. Refresh your workspace.'); return; }
  state.detailId = id;
  const version = ++state.detailVersion;
  $('#detail-reference').textContent = `MAINTENANCE / REQUEST #${id}`;
  $('#detail-title').textContent = property(item.property_id)?.name || `Property #${item.property_id}`;
  const approvals = [...state.approvals].reverse().filter(x => x.maintenance_request_id === id);
  const pending = approvals.some(x => x.status === 'pending');
  $('#detail-content').innerHTML = `<div class="detail-summary"><p>${escapeHTML(item.issue)}</p><div class="meta">${badge(item.status)} ${badge(item.priority)} <span>Recorded priority</span></div></div><p id="detail-error" class="error" role="alert" hidden></p><div class="section-heading"><h3>Triage suggestions</h3><button id="run-triage" class="secondary">Generate suggestion</button></div><p class="section-note">${state.config?.mode === 'rules' ? 'Keyword rules · no API credit needed.' : state.config?.error ? 'Triage configuration is unavailable.' : 'AI mode · uses API credit.'} Suggestions require human review.</p><div id="suggestions" aria-live="polite">Loading suggestions…</div><div class="section-heading"><h3>Approval history</h3></div>${approvals.map(a => `<div class="approval-item">${badge(a.status)} <small>Approval #${a.id}</small><p>${escapeHTML(a.reason)}</p>${a.status === 'pending' ? `<div class="inline-actions"><button class="primary" data-decision="approve" data-approval="${a.id}">Approve</button><button class="secondary danger" data-decision="reject" data-approval="${a.id}">Reject</button></div>` : ''}</div>`).join('') || '<p class="no-records">No approval has been requested.</p>'}${!pending && item.status === 'pending' ? '<form id="approval-form">' + field('Reason for approval', '<textarea name="reason" required maxlength="2000" placeholder="What work needs approval, and why?"></textarea>') + '<button class="primary" type="submit">Request approval</button></form>' : ''}`;
  if (!$('#detail').open) $('#detail').showModal();
  try {
    const suggestions = await api(`/maintenance/${id}/triage`);
    if (version !== state.detailVersion || !$('#detail').open) return;
    $('#suggestions').innerHTML = [...suggestions].reverse().map(s => `<article class="suggestion"><div class="suggestion-heading">${badge(s.suggested_priority)} ${escapeHTML(s.suggested_trade)}</div><p>${escapeHTML(s.recommended_action)}</p><p class="muted">${escapeHTML(s.rationale)}</p><small>Suggestion #${s.id} · ${escapeHTML(s.source)}</small></article>`).join('') || '<p class="no-records">No suggestions yet. Generate one to help plan the next step.</p>';
  } catch (error) {
    if (version === state.detailVersion && $('#detail').open) { $('#suggestions').textContent = 'Suggestion history could not be loaded.'; message('#detail-error',error.message); }
  }
}
async function mutate(button, errorSelector, work) {
  if (state.busy) return;
  state.busy = true;
  button.disabled = true;
  message(errorSelector, '');
  const closeButtons = [...document.querySelectorAll('dialog[open] [data-close]')];
  closeButtons.forEach(x => x.disabled = true);
  try { await work(); } catch(error) { message(errorSelector,error.message); }
  finally { state.busy = false; button.disabled = false; closeButtons.forEach(x => x.disabled = false); }
}
$('#editor-form').addEventListener('submit', event => {
  event.preventDefault();
  const form = event.currentTarget;
  const data = Object.fromEntries(new FormData(form));
  for (const key of Object.keys(data)) data[key] = data[key].trim();
  if (Object.values(data).some(value => !value)) { message('#form-error', 'Please complete every field with more than spaces.'); return; }
  if (data.property_id) data.property_id = Number(data.property_id);
  const type = form.dataset.type;
  mutate($('#save'),'#form-error', async () => {
    await api(type === 'property' ? '/properties' : '/maintenance', data);
    $('#editor').close();
    message('#notice', type === 'property' ? 'Property added.' : 'Maintenance request created.');
    setView(type === 'property' ? 'properties' : 'maintenance');
    await load();
  });
});
$('#detail').addEventListener('submit', event => {
  if (event.target.id !== 'approval-form') return;
  event.preventDefault();
  const reason = new FormData(event.target).get('reason').trim();
  if (!reason) { message('#detail-error','Enter a reason for approval.'); return; }
  const id = state.detailId;
  mutate(event.submitter,'#detail-error', async () => {
    await api('/approvals', {maintenance_request_id:id, reason});
    if (await load()) await showDetail(id); else $('#detail').close();
    message('#notice','Approval requested. Review it in the Approvals queue.');
  });
});
document.addEventListener('click', event => {
  const button = event.target.closest('button');
  if (!button) return;
  if (button.dataset.close) { if (!state.busy) $(`#${button.dataset.close}`).close(); return; }
  if (button.dataset.view) { setView(button.dataset.view); return; }
  if (button.dataset.create) { openEditor(button.dataset.create); return; }
  if (button.dataset.detail) { if (!state.busy) showDetail(Number(button.dataset.detail)); return; }
  if (button.id === 'run-triage') {
    const id = state.detailId;
    mutate(button,'#detail-error', async () => { await api(`/maintenance/${id}/triage`, {}); await showDetail(id); });
  }
  if (button.dataset.decision) {
    const id = state.detailId;
    const decision = button.dataset.decision;
    mutate(button,'#detail-error', async () => {
      await api(`/approvals/${Number(button.dataset.approval)}/${decision}`, {});
      if (await load()) await showDetail(id); else $('#detail').close();
      message('#notice', `${decision === 'approve' ? 'Approved' : 'Rejected'}. The decision has been recorded in audit history.`);
    });
  }
});
$('#primary-action').addEventListener('click', () => openEditor(state.view === 'properties' ? 'property' : 'maintenance'));
$('#refresh').addEventListener('click', () => { message('#error',''); message('#notice',''); load(); });
$('#search').addEventListener('input', () => { if (state.loaded) render(); });
$('#status-filter').addEventListener('change', () => { if (state.loaded) render(); });
document.querySelectorAll('dialog').forEach(dialog => dialog.addEventListener('cancel', event => { if (state.busy) event.preventDefault(); }));
$('#detail').addEventListener('close', () => { state.detailVersion++; });
load();
