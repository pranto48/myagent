/* ==============================================================================
 * Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
 * Made By Arif (https://arifmahmud.com/)
 * Project: MyAgent | Version: 3.3.0
 * Unified Chat AI & WORKFLOWS (Auto) History Hub Manager
 * ============================================================================== */

const histState = {
  subTab: 'all', // 'all' | 'chat' | 'workflow' | 'telegram'
  query: '',
  workflowId: '',
  status: 'ALL',
  role: 'ALL',
  limit: 80,
  data: null,
  workflowsCatalog: [],
  detailPayload: null,
  detailKind: null,
  searchTimer: null,
};

function histEsc(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function histToken() {
  return (
    localStorage.getItem('myagent_access_token') ||
    localStorage.getItem('myagent_token') ||
    (typeof getAuthToken === 'function' ? getAuthToken() : '') ||
    ''
  );
}

async function histFetch(url, options = {}) {
  const token = histToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return fetch(url, { ...options, headers });
}

function histToast(msg, type = 'info') {
  if (typeof showToast === 'function') showToast(msg, type);
}

function histDownloadFile(filename, content, mime = 'application/json;charset=utf-8;') {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function histStatusPill(status) {
  const s = String(status || 'INFO').toUpperCase();
  let cls = 'info';
  if (s === 'SUCCESS' || s === 'COMPLETED' || s === 'ONLINE') cls = 'success';
  else if (s === 'FAILED' || s === 'ERROR') cls = 'failed';
  else if (s === 'RUNNING') cls = 'running';
  else if (s === 'STOPPED') cls = 'stopped';
  else if (s === 'AUTOMATION') cls = 'automation';
  return `<span class="hist-pill ${cls}">${histEsc(s)}</span>`;
}

// ------------------------------------------------------------------------------
// Hub Data Loading & Filters
// ------------------------------------------------------------------------------
async function loadHistoryHub(forceSubTab = null) {
  if (forceSubTab) {
    histState.subTab = forceSubTab;
    syncHistorySubTabButtons();
  }

  const root = document.getElementById('hist-main-content');
  if (root && !histState.data) {
    root.innerHTML = '<div class="wf-empty-hint" style="padding:28px;">ইতিহাস লোড হচ্ছে...</div>';
  }

  try {
    const params = new URLSearchParams({
      kind: histState.subTab || 'all',
      limit: String(histState.limit || 80),
    });
    if (histState.query.trim()) params.set('q', histState.query.trim());
    if (histState.workflowId) params.set('workflow_id', histState.workflowId);
    if (histState.status && histState.status !== 'ALL') params.set('status', histState.status);
    if (histState.role && histState.role !== 'ALL') params.set('role', histState.role);

    const [histRes, wfRes] = await Promise.all([
      histFetch(`/api/workflows/history/unified?${params.toString()}`),
      histState.workflowsCatalog.length
        ? Promise.resolve(null)
        : histFetch('/api/workflows'),
    ]);

    if (wfRes && wfRes.ok) {
      const wfJson = await wfRes.json();
      histState.workflowsCatalog = wfJson.workflows || [];
      populateHistoryWorkflowFilter();
    } else if (!histState.workflowsCatalog.length && typeof wfState !== 'undefined' && wfState.workflows?.length) {
      histState.workflowsCatalog = wfState.workflows;
      populateHistoryWorkflowFilter();
    }

    const data = await histRes.json();
    if (!histRes.ok || !data.success) {
      throw new Error(data.detail || 'History load failed');
    }

    histState.data = data;
    updateHistoryKpis(data.summary || {});
    renderHistoryContent();
  } catch (err) {
    console.error('loadHistoryHub error:', err);
    if (root) {
      root.innerHTML = `<div class="wf-empty-hint" style="color:#f43f5e; padding:24px;">ইতিহাস লোড করতে সমস্যা হয়েছে: ${histEsc(err.message)}</div>`;
    }
  }
}

function populateHistoryWorkflowFilter() {
  const sel = document.getElementById('hist-filter-workflow');
  if (!sel) return;
  const cur = histState.workflowId || '';
  const opts = ['<option value="">সব ওয়ার্কফ্লো (All Workflows)</option>'];
  (histState.workflowsCatalog || []).forEach(w => {
    opts.push(`<option value="${histEsc(w.id)}">${histEsc(w.icon || '⚡')} ${histEsc(w.name)}</option>`);
  });
  sel.innerHTML = opts.join('');
  sel.value = cur;
}

function updateHistoryKpis(summary) {
  const setText = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = String(val);
  };
  setText('hist-kpi-sessions', summary.total_chat_sessions ?? 0);
  setText('hist-kpi-messages', summary.total_chat_messages ?? 0);
  setText('hist-kpi-runs', summary.total_workflow_runs ?? 0);
  setText('hist-kpi-success', `${summary.workflow_success_rate ?? 100}%`);
  setText('hist-kpi-telegram', summary.total_telegram_chats ?? 0);
}

function syncHistorySubTabButtons() {
  ['all', 'chat', 'workflow', 'telegram'].forEach(k => {
    const btn = document.getElementById(`hist-tab-${k}`);
    if (btn) btn.classList.toggle('active', histState.subTab === k);
  });
  const wfWrap = document.getElementById('hist-filter-workflow');
  const stWrap = document.getElementById('hist-filter-status');
  const roleWrap = document.getElementById('hist-filter-role');
  if (wfWrap) wfWrap.style.display = histState.subTab === 'chat' || histState.subTab === 'telegram' ? 'none' : '';
  if (stWrap) stWrap.style.display = histState.subTab === 'chat' ? 'none' : '';
  if (roleWrap) roleWrap.style.display = histState.subTab === 'workflow' || histState.subTab === 'telegram' ? 'none' : '';
}

function switchHistorySubTab(subTab) {
  histState.subTab = subTab || 'all';
  syncHistorySubTabButtons();
  loadHistoryHub();
}

function onHistorySearchInput(val) {
  histState.query = val || '';
  clearTimeout(histState.searchTimer);
  histState.searchTimer = setTimeout(() => loadHistoryHub(), 220);
}

function onHistoryFilterChange() {
  const wfSel = document.getElementById('hist-filter-workflow');
  const stSel = document.getElementById('hist-filter-status');
  const roleSel = document.getElementById('hist-filter-role');
  if (wfSel) histState.workflowId = wfSel.value || '';
  if (stSel) histState.status = stSel.value || 'ALL';
  if (roleSel) histState.role = roleSel.value || 'ALL';
  loadHistoryHub();
}

// ------------------------------------------------------------------------------
// Sub-Views Rendering
// ------------------------------------------------------------------------------
function renderHistoryContent() {
  syncHistorySubTabButtons();
  const root = document.getElementById('hist-main-content');
  if (!root || !histState.data) return;

  if (histState.subTab === 'all') {
    root.innerHTML = renderUnifiedTimelineHtml(histState.data.timeline || []);
  } else if (histState.subTab === 'chat') {
    root.innerHTML = renderChatHistoryHtml(histState.data.chat_sessions || [], histState.data.chat_messages || {});
  } else if (histState.subTab === 'workflow') {
    root.innerHTML = renderWorkflowRunsHtml(histState.data.workflow_runs || {});
  } else if (histState.subTab === 'telegram') {
    root.innerHTML = renderTelegramHistoryHtml(histState.data.telegram_chats || []);
  }
}

function renderUnifiedTimelineHtml(items) {
  if (!items.length) {
    return '<div class="wf-empty-hint" style="padding:36px;">কোনো Chat AI বা WORKFLOWS (Auto) ইতিহাস পাওয়া যায়নি।</div>';
  }
  return `
    <div class="hist-timeline-list">
      ${items.map(it => {
        const icon = it.kind === 'chat' ? '💬' : (it.kind === 'workflow' ? '⚡' : '✈️');
        const kindLabel = it.kind === 'chat' ? 'Chat AI' : (it.kind === 'workflow' ? 'WORKFLOW (Auto)' : 'Telegram Bot');
        let actionsHtml = '';
        if (it.kind === 'chat') {
          actionsHtml = `
            <button type="button" class="btn-sm-action-cyber" onclick="openChatSessionDetailModal('${histEsc(it.session_id)}')">👁️ ট্রান্সক্রিপ্ট</button>
            <button type="button" class="btn-sm-action-cyber" onclick="histOpenSessionInChat('${histEsc(it.session_id)}')">💬 চ্যাটে খুলুন</button>
          `;
        } else if (it.kind === 'workflow') {
          actionsHtml = `
            <button type="button" class="btn-sm-action-cyber" onclick="openWorkflowRunDetailModal('${histEsc(it.raw_id)}')">🔍 ফুল ট্রেস</button>
            <button type="button" class="btn-sm-action-cyber" onclick="histOpenRunInStudio('${histEsc(it.workflow_id || '')}', '${histEsc(it.raw_id)}')">🎨 স্টুডিও</button>
            <button type="button" class="btn-sm-action-cyber" onclick="histRerunWorkflow('${histEsc(it.workflow_id || '')}')">▶ Re-Run</button>
          `;
        } else {
          actionsHtml = `
            <button type="button" class="btn-sm-action-cyber" onclick="openTelegramChatDetailModal('${histEsc(it.raw_id)}')">✈️ বিস্তারিত</button>
          `;
        }

        return `
          <div class="hist-timeline-card kind-${histEsc(it.kind)}">
            <div class="hist-card-top">
              <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
                <span class="hist-kind-badge kind-${histEsc(it.kind)}">${icon} ${kindLabel}</span>
                <strong style="font-size:0.9rem; color:var(--text-primary);">${histEsc(it.title)}</strong>
                ${histStatusPill(it.status)}
              </div>
              <span class="hist-ts">🕒 ${histEsc(it.timestamp || '')}</span>
            </div>
            <div class="hist-card-sub">${histEsc(it.subtitle || '')}</div>
            ${it.preview ? `<pre class="hist-preview-pre">${histEsc(it.preview)}</pre>` : ''}
            <div class="hist-card-actions">${actionsHtml}</div>
          </div>
        `;
      }).join('')}
    </div>
  `;
}

function renderChatHistoryHtml(sessions, messagesData) {
  const items = messagesData.items || [];
  const totalMsgs = messagesData.total ?? items.length;

  const sessionsHtml = !sessions.length
    ? '<div class="wf-empty-hint" style="padding:18px;">কোনো চ্যাট সেশন পাওয়া যায়নি।</div>'
    : sessions.map(s => `
      <div class="hist-session-card">
        <div style="flex:1; min-width:200px;">
          <div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap;">
            <strong>${s.source === 'automation' || String(s.id).startsWith('session_daily') ? '📅' : '💬'} ${histEsc(s.title || 'Untitled')}</strong>
            <span class="hist-meta-chip">${s.msg_count || 0} msgs</span>
            <span class="hist-meta-chip">${histEsc(s.model_name || 'AI')}</span>
            ${s.is_archived ? '<span class="hist-pill stopped">ARCHIVED</span>' : ''}
          </div>
          <div class="hist-card-sub" style="margin-top:4px;">Updated: ${histEsc(s.updated_at || '')} • ID: <code>${histEsc(s.id)}</code></div>
          ${s.last_snippet ? `<div class="hist-snippet-line">${histEsc(s.last_snippet)}</div>` : ''}
        </div>
        <div class="hist-card-actions" style="margin-top:0;">
          <button type="button" class="btn-sm-action-cyber" onclick="openChatSessionDetailModal('${histEsc(s.id)}')">👁️ দেখুন</button>
          <button type="button" class="btn-sm-action-cyber" onclick="histOpenSessionInChat('${histEsc(s.id)}')">💬 খুলুন</button>
          <button type="button" class="btn-sm-action-cyber" onclick="exportChatSessionById('${histEsc(s.id)}', 'md')">📝 MD</button>
          <button type="button" class="btn-sm-action-cyber" onclick="histRenameChatSession('${histEsc(s.id)}', '${histEsc(s.title || '')}')">✏️</button>
          <button type="button" class="btn-sm-action-cyber danger" onclick="histDeleteChatSession('${histEsc(s.id)}')">🗑️</button>
        </div>
      </div>
    `).join('');

  const msgsHtml = !items.length
    ? '<div class="wf-empty-hint" style="padding:18px;">মিলে যাওয়া কোনো চ্যাট মেসেজ পাওয়া যায়নি।</div>'
    : items.map(m => `
      <div class="hist-msg-row role-${histEsc(m.role)}">
        <div class="hist-card-top">
          <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
            <span class="hist-pill ${m.role === 'assistant' ? 'success' : 'info'}">${m.role === 'assistant' ? '🤖 AI' : '👤 USER'}</span>
            <strong>${histEsc(m.session_title || m.session_id)}</strong>
            <span class="hist-meta-chip">${histEsc(m.model_name || 'AI')}</span>
          </div>
          <div style="display:flex; align-items:center; gap:8px;">
            <span class="hist-ts">${histEsc(m.created_at || '')}</span>
            <button type="button" class="mini-btn-copy" onclick="openChatSessionDetailModal('${histEsc(m.session_id)}')">👁️ সেশন</button>
            <button type="button" class="mini-btn-copy danger" onclick="histDeleteChatMessage('${histEsc(m.session_id)}', ${Number(m.id)})">🗑️</button>
          </div>
        </div>
        <pre class="hist-preview-pre">${histEsc((m.content || '').slice(0, 750))}</pre>
      </div>
    `).join('');

  return `
    <div class="hist-split-grid">
      <div class="ops-card" style="padding:14px;">
        <div class="hist-section-title">
          <span>💬 সংরক্ষিত Chat AI সেশন (${sessions.length})</span>
        </div>
        <div class="hist-scroll-col">${sessionsHtml}</div>
      </div>
      <div class="ops-card" style="padding:14px;">
        <div class="hist-section-title">
          <span>🔍 চ্যাট মেসেজ ইতিহাস (${totalMsgs})</span>
        </div>
        <div class="hist-scroll-col">${msgsHtml}</div>
      </div>
    </div>
  `;
}

function renderWorkflowRunsHtml(runsData) {
  const runs = runsData.runs || [];
  const stats = runsData.stats || {};
  const headerBar = `
    <div class="hist-wf-bar">
      <div class="hist-wf-stats">
        <span>মোট: <strong>${stats.total ?? runs.length}</strong></span>
        <span style="color:#34d399;">সফল: <strong>${stats.success ?? 0}</strong></span>
        <span style="color:#fb7185;">ব্যর্থ: <strong>${stats.failed ?? 0}</strong></span>
        <span style="color:#fbbf24;">বন্ধ: <strong>${stats.stopped ?? 0}</strong></span>
        <span style="color:#38bdf8;">গড় সময়: <strong>${stats.avg_duration_ms ?? 0} ms</strong></span>
      </div>
      <div style="display:flex; gap:6px; flex-wrap:wrap;">
        <button type="button" class="btn-sm-action-cyber" onclick="histClearWorkflowRuns('failed')">🧹 ব্যর্থ রান ক্লিন</button>
        <button type="button" class="btn-sm-action-cyber" onclick="histClearWorkflowRuns('older_30d')">🗑️ ৩০+ দিনের পুরনো ক্লিন</button>
      </div>
    </div>
  `;

  if (!runs.length) {
    return `${headerBar}<div class="wf-empty-hint" style="padding:28px;">ফিল্টার অনুযায়ী কোনো WORKFLOWS (Auto) রান ইতিহাস পাওয়া যায়নি।</div>`;
  }

  return `
    ${headerBar}
    <div class="ops-card" style="padding:0; overflow:hidden;">
      <div style="overflow-x:auto;">
        <table style="width:100%; border-collapse:collapse; font-size:0.83rem; text-align:left;">
          <thead>
            <tr style="background:rgba(255,255,255,0.03); color:var(--text-muted); font-size:0.74rem; text-transform:uppercase;">
              <th style="padding:10px 12px;">Workflow &amp; Output</th>
              <th style="padding:10px 12px;">Trigger</th>
              <th style="padding:10px 12px;">Status</th>
              <th style="padding:10px 12px;">Nodes / Time</th>
              <th style="padding:10px 12px;">Started At</th>
              <th style="padding:10px 12px; text-align:right;">Actions</th>
            </tr>
          </thead>
          <tbody>
            ${runs.map(r => {
              const steps = r.node_results || [];
              const preview = (r.error_message || r.final_output || '').replace(/\s+/g, ' ').trim().slice(0, 110);
              return `
                <tr style="border-bottom:1px solid var(--border-subtle);">
                  <td style="padding:10px 12px;">
                    <div style="font-weight:700; color:var(--text-primary);">${histEsc(r.workflow_name || r.workflow_id)}</div>
                    <div style="font-size:0.72rem; color:var(--text-muted); font-family:'Fira Code', monospace;">${histEsc(r.id)}</div>
                    ${preview ? `<div style="font-size:0.75rem; color:var(--text-secondary); margin-top:3px;">${histEsc(preview)}</div>` : ''}
                  </td>
                  <td style="padding:10px 12px;"><span class="wf-source-badge">${histEsc(r.trigger_source || 'manual')}</span></td>
                  <td style="padding:10px 12px;">${histStatusPill(r.status)}</td>
                  <td style="padding:10px 12px; font-family:'Fira Code', monospace; font-size:0.76rem;">
                    ${steps.length} nodes • ${r.duration_ms || 0} ms
                  </td>
                  <td style="padding:10px 12px; font-size:0.76rem; color:var(--text-muted);">${histEsc(r.started_at || '')}</td>
                  <td style="padding:10px 12px; text-align:right; white-space:nowrap;">
                    <button type="button" class="btn-sm-action-cyber" onclick="openWorkflowRunDetailModal('${histEsc(r.id)}')">🔍 ট্রেস</button>
                    <button type="button" class="btn-sm-action-cyber" onclick="histOpenRunInStudio('${histEsc(r.workflow_id || '')}', '${histEsc(r.id)}')">🎨</button>
                    <button type="button" class="btn-sm-action-cyber" onclick="histRerunWorkflow('${histEsc(r.workflow_id || '')}')">▶</button>
                    <button type="button" class="btn-sm-action-cyber danger" onclick="histDeleteWorkflowRun('${histEsc(r.id)}')">🗑️</button>
                  </td>
                </tr>
              `;
            }).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function renderTelegramHistoryHtml(chats) {
  if (!chats.length) {
    return '<div class="wf-empty-hint" style="padding:28px;">কোনো Telegram চ্যাট বা রিপোর্ট ইতিহাস পাওয়া যায়নি।</div>';
  }
  return `
    <div class="hist-timeline-list">
      ${chats.map(c => `
        <div class="hist-timeline-card kind-telegram">
          <div class="hist-card-top">
            <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
              <span class="hist-kind-badge kind-telegram">✈️ ${histEsc(c.intent || 'chat')}</span>
              <strong>${histEsc(c.sender_name || c.chat_id || 'Telegram')}</strong>
              ${histStatusPill(c.status)}
              <span class="hist-meta-chip">${c.latency_ms || 0} ms</span>
            </div>
            <span class="hist-ts">🕒 ${histEsc(c.created_at || '')}</span>
          </div>
          ${c.user_message ? `<div style="font-size:0.82rem; color:#93c5fd; margin-top:6px;">👤 <strong>কমান্ড:</strong> ${histEsc(c.user_message)}</div>` : ''}
          ${c.reply_message ? `<pre class="hist-preview-pre">${histEsc(c.reply_message)}</pre>` : ''}
          <div class="hist-card-actions">
            <button type="button" class="btn-sm-action-cyber" onclick="openTelegramChatDetailModal('${histEsc(c.id)}')">🔍 সম্পূর্ণ রিপোর্ট</button>
          </div>
        </div>
      `).join('')}
    </div>
  `;
}

// ------------------------------------------------------------------------------
// Full Trace & Chat Transcript Detail Modal
// ------------------------------------------------------------------------------
async function openChatSessionDetailModal(sessionId) {
  const modal = document.getElementById('history-detail-modal');
  const titleEl = document.getElementById('hist-detail-title');
  const subEl = document.getElementById('hist-detail-sub');
  const bodyEl = document.getElementById('hist-detail-body');
  const actionsEl = document.getElementById('hist-detail-actions');
  if (!modal || !bodyEl) return;

  modal.style.display = 'flex';
  if (titleEl) titleEl.textContent = '💬 Chat AI সেশন ট্রান্সক্রিপ্ট';
  if (subEl) subEl.textContent = `Session ID: ${sessionId}`;
  bodyEl.innerHTML = '<div class="wf-empty-hint">সেশন লোড হচ্ছে...</div>';
  if (actionsEl) actionsEl.innerHTML = '';

  try {
    const res = await histFetch(`/api/sessions/${encodeURIComponent(sessionId)}`);
    const data = await res.json();
    const sess = data.session || { id: sessionId, title: sessionId };
    const msgs = data.messages || [];

    histState.detailPayload = { session: sess, messages: msgs };
    histState.detailKind = 'chat';

    if (titleEl) titleEl.textContent = `💬 ${sess.title || sessionId}`;
    if (subEl) {
      subEl.textContent = `${msgs.length}টি মেসেজ • মডেল: ${sess.model_name || 'AI'} • আপডেট: ${sess.updated_at || '-'}`;
    }
    if (actionsEl) {
      actionsEl.innerHTML = `
        <button type="button" class="btn-sm-action-cyber" onclick="histOpenSessionInChat('${histEsc(sessionId)}'); closeHistoryDetailModal();">💬 লাইভ চ্যাটে খুলুন</button>
        <button type="button" class="btn-sm-action-cyber" onclick="exportChatSessionById('${histEsc(sessionId)}', 'md')">📝 Export MD</button>
        <button type="button" class="btn-sm-action-cyber" onclick="exportDetailModalJson()">⬇️ Export JSON</button>
      `;
    }

    bodyEl.innerHTML = !msgs.length
      ? '<div class="wf-empty-hint">এই সেশনে এখনও কোনো মেসেজ নেই।</div>'
      : msgs.map((m, idx) => `
        <div class="hist-modal-msg role-${histEsc(m.role)}">
          <div class="hist-card-top">
            <div style="display:flex; align-items:center; gap:6px;">
              <span class="hist-pill ${m.role === 'assistant' ? 'success' : 'info'}">${idx + 1}. ${m.role === 'assistant' ? '🤖 Assistant' : '👤 User'}</span>
              ${m.model_name ? `<span class="hist-meta-chip">${histEsc(m.model_name)}</span>` : ''}
            </div>
            <div style="display:flex; align-items:center; gap:6px;">
              <span class="hist-ts">${histEsc(m.created_at || '')}</span>
              <button type="button" class="mini-btn-copy danger" onclick="histDeleteChatMessage('${histEsc(sessionId)}', ${Number(m.id)}, true)">🗑️</button>
            </div>
          </div>
          <pre class="hist-detail-pre">${histEsc(m.content || '')}</pre>
          ${Array.isArray(m.sources) && m.sources.length ? `<div class="hist-card-sub">📎 Sources: ${m.sources.length}</div>` : ''}
        </div>
      `).join('');
  } catch (err) {
    bodyEl.innerHTML = `<div class="wf-empty-hint" style="color:#f43f5e;">লোড ব্যর্থ: ${histEsc(err.message)}</div>`;
  }
}

async function openWorkflowRunDetailModal(runId) {
  const modal = document.getElementById('history-detail-modal');
  const titleEl = document.getElementById('hist-detail-title');
  const subEl = document.getElementById('hist-detail-sub');
  const bodyEl = document.getElementById('hist-detail-body');
  const actionsEl = document.getElementById('hist-detail-actions');
  if (!modal || !bodyEl) return;

  modal.style.display = 'flex';
  if (titleEl) titleEl.textContent = '⚡ WORKFLOW (Auto) এক্সিকিউশন ট্রেস';
  if (subEl) subEl.textContent = `Run ID: ${runId}`;
  bodyEl.innerHTML = '<div class="wf-empty-hint">ট্রেস লোড হচ্ছে...</div>';
  if (actionsEl) actionsEl.innerHTML = '';

  try {
    const res = await histFetch(`/api/workflows/runs/${encodeURIComponent(runId)}`);
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.detail || 'Run not found');
    const r = data.run;
    const steps = r.node_results || [];

    histState.detailPayload = r;
    histState.detailKind = 'workflow';

    if (titleEl) titleEl.textContent = `⚡ ${r.workflow_name || r.workflow_id}`;
    if (subEl) {
      subEl.innerHTML = `${histStatusPill(r.status)} &nbsp; Run: <code>${histEsc(r.id)}</code> • Trigger: <strong>${histEsc(r.trigger_source || 'manual')}</strong> • Duration: <strong>${r.duration_ms || 0} ms</strong> • Started: ${histEsc(r.started_at || '')}`;
    }
    if (actionsEl) {
      actionsEl.innerHTML = `
        <button type="button" class="btn-sm-action-cyber" onclick="histOpenRunInStudio('${histEsc(r.workflow_id || '')}', '${histEsc(r.id)}'); closeHistoryDetailModal();">🎨 স্টুডিওতে দেখুন</button>
        <button type="button" class="btn-sm-action-cyber" onclick="histRerunWorkflow('${histEsc(r.workflow_id || '')}')">▶ Re-Run</button>
        <button type="button" class="btn-sm-action-cyber" onclick="exportDetailModalJson()">⬇️ Export JSON</button>
      `;
    }

    const finalOutHtml = r.final_output
      ? `<div class="hist-modal-msg"><strong>🏁 চূড়ান্ত আউটপুট (Final Output):</strong><pre class="hist-detail-pre">${histEsc(r.final_output)}</pre></div>`
      : '';
    const errHtml = r.error_message
      ? `<div class="hist-modal-msg" style="border-color:rgba(244,63,94,0.45);"><strong style="color:#fda4af;">❌ ত্রুটি (Error):</strong><pre class="hist-detail-pre">${histEsc(r.error_message)}</pre></div>`
      : '';

    const stepsHtml = !steps.length
      ? '<div class="wf-empty-hint">কোনো নোড স্টেপ লগ পাওয়া যায়নি।</div>'
      : steps.map((st, idx) => `
        <div class="hist-modal-msg">
          <div class="hist-card-top">
            <div style="display:flex; align-items:center; gap:8px;">
              <strong>${idx + 1}. ${histEsc(st.title || st.node_id)}</strong>
              <span class="hist-meta-chip">${histEsc(st.type || '')}</span>
            </div>
            <div style="display:flex; align-items:center; gap:8px;">
              <span class="hist-ts">${st.duration_ms || 0} ms</span>
              ${histStatusPill(st.status)}
            </div>
          </div>
          ${st.summary ? `<div class="hist-card-sub">${histEsc(st.summary)}</div>` : ''}
          ${st.error ? `<pre class="hist-detail-pre" style="color:#fda4af;">Error: ${histEsc(st.error)}</pre>` : ''}
          <pre class="hist-detail-pre">${histEsc(st.output || '')}</pre>
        </div>
      `).join('');

    bodyEl.innerHTML = `${errHtml}${finalOutHtml}<div style="font-size:0.8rem; font-weight:700; color:var(--text-muted); margin:6px 0;">🧩 ধাপসমূহ (${steps.length} Nodes)</div>${stepsHtml}`;
  } catch (err) {
    bodyEl.innerHTML = `<div class="wf-empty-hint" style="color:#f43f5e;">ট্রেস লোড ব্যর্থ: ${histEsc(err.message)}</div>`;
  }
}

function openTelegramChatDetailModal(tgId) {
  const chats = histState.data?.telegram_chats || [];
  const c = chats.find(x => x.id === tgId);
  if (!c) return;
  const modal = document.getElementById('history-detail-modal');
  const titleEl = document.getElementById('hist-detail-title');
  const subEl = document.getElementById('hist-detail-sub');
  const bodyEl = document.getElementById('hist-detail-body');
  const actionsEl = document.getElementById('hist-detail-actions');
  if (!modal || !bodyEl) return;

  histState.detailPayload = c;
  histState.detailKind = 'telegram';
  modal.style.display = 'flex';
  if (titleEl) titleEl.textContent = `✈️ Telegram Chat & Report (${c.intent || 'chat'})`;
  if (subEl) subEl.textContent = `${c.sender_name || c.chat_id} • ${c.created_at || ''} • ${c.latency_ms || 0} ms`;
  if (actionsEl) {
    actionsEl.innerHTML = `<button type="button" class="btn-sm-action-cyber" onclick="exportDetailModalJson()">⬇️ Export JSON</button>`;
  }
  bodyEl.innerHTML = `
    ${c.user_message ? `<div class="hist-modal-msg"><strong>👤 ব্যবহারকারীর মেসেজ:</strong><pre class="hist-detail-pre">${histEsc(c.user_message)}</pre></div>` : ''}
    ${c.reply_message ? `<div class="hist-modal-msg"><strong>🤖 বটের উত্তর ও রিপোর্ট:</strong><pre class="hist-detail-pre">${histEsc(c.reply_message)}</pre></div>` : ''}
    ${c.workflow_status_summary ? `<div class="hist-modal-msg"><strong>⚡ সংযুক্ত Workflow স্ট্যাটাস সারাংশ:</strong><pre class="hist-detail-pre">${histEsc(c.workflow_status_summary)}</pre></div>` : ''}
  `;
}

function closeHistoryDetailModal() {
  const modal = document.getElementById('history-detail-modal');
  if (modal) modal.style.display = 'none';
}

function exportDetailModalJson() {
  if (!histState.detailPayload) return;
  histDownloadFile(`myagent_${histState.detailKind || 'history'}_${Date.now()}.json`, JSON.stringify(histState.detailPayload, null, 2));
  histToast('JSON এক্সপোর্ট সম্পন্ন হয়েছে।', 'success');
}

// ------------------------------------------------------------------------------
// Actions: Open, Re-run, Rename, Export, Delete & Clear
// ------------------------------------------------------------------------------
async function histOpenSessionInChat(sessionId) {
  if (typeof switchTab === 'function') switchTab('chat');
  if (typeof switchSession === 'function') {
    await switchSession(sessionId);
  }
}

async function histOpenRunInStudio(workflowId, runId) {
  if (typeof switchTab === 'function') switchTab('workflows');
  if (typeof inspectHistoricalRun === 'function') {
    await inspectHistoricalRun(runId);
  } else if (workflowId && typeof selectWorkflow === 'function') {
    await selectWorkflow(workflowId, true);
  }
}

async function histRerunWorkflow(workflowId) {
  if (!workflowId) return;
  try {
    const res = await histFetch(`/api/workflows/${encodeURIComponent(workflowId)}/run`, {
      method: 'POST',
      body: JSON.stringify({ trigger_source: 'manual', dry_run: false }),
    });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.detail || 'Run failed');
    histToast('✅ ওয়ার্কফ্লো সফলভাবে পুনরায় চালু হয়েছে!', 'success');
    await loadHistoryHub();
    if (typeof refreshRecentWorkflowRuns === 'function') refreshRecentWorkflowRuns();
  } catch (err) {
    histToast('Re-Run ব্যর্থ: ' + err.message, 'error');
  }
}

async function histDeleteWorkflowRun(runId) {
  if (!confirm('এই ওয়ার্কফ্লো রান ইতিহাসটি মুছে ফেলতে চান?')) return;
  try {
    const res = await histFetch(`/api/workflows/runs/${encodeURIComponent(runId)}`, { method: 'DELETE' });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.detail || 'Delete failed');
    histToast('🗑️ রান ইতিহাস মুছে ফেলা হয়েছে।', 'info');
    if (document.getElementById('view-history')?.classList.contains('active')) {
      await loadHistoryHub();
    }
    if (typeof refreshRecentWorkflowRuns === 'function') {
      await refreshRecentWorkflowRuns();
    }
  } catch (err) {
    histToast('ডিলিট ব্যর্থ: ' + err.message, 'error');
  }
}

async function histClearWorkflowRuns(mode) {
  let payload = {};
  let msg = 'পুরনো রান ইতিহাস মুছে ফেলতে চান?';
  if (mode === 'failed') {
    payload = { status: 'FAILED' };
    msg = 'সকল ব্যর্থ (FAILED) ওয়ার্কফ্লো রান ইতিহাস মুছে ফেলতে চান?';
  } else if (mode === 'older_7d') {
    payload = { older_than_days: 7 };
    msg = '৭ দিনের বেশি পুরনো ওয়ার্কফ্লো রান ইতিহাস মুছে ফেলতে চান?';
  } else if (mode === 'older_30d') {
    payload = { older_than_days: 30 };
    msg = '৩০ দিনের বেশি পুরনো ওয়ার্কফ্লো রান ইতিহাস মুছে ফেলতে চান?';
  }
  if (!confirm(msg)) return;

  try {
    const res = await histFetch('/api/workflows/runs/clear', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.detail || 'Clear failed');
    histToast(`🧹 ${data.deleted || 0}টি রান ইতিহাস পরিষ্কার হয়েছে।`, 'success');
    if (document.getElementById('view-history')?.classList.contains('active')) {
      await loadHistoryHub();
    }
    if (typeof refreshRecentWorkflowRuns === 'function') {
      await refreshRecentWorkflowRuns();
    }
  } catch (err) {
    histToast('ক্লিন ব্যর্থ: ' + err.message, 'error');
  }
}

async function histDeleteChatSession(sessionId) {
  if (!confirm('এই Chat AI সেশনটি এবং তার সব মেসেজ মুছে ফেলতে চান?')) return;
  try {
    const res = await histFetch(`/api/sessions/${encodeURIComponent(sessionId)}`, { method: 'DELETE' });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.detail || 'Delete failed');
    histToast('🗑️ চ্যাট সেশন মুছে ফেলা হয়েছে।', 'info');
    await loadHistoryHub();
    if (typeof loadChatSessions === 'function') loadChatSessions();
  } catch (err) {
    histToast('ডিলিট ব্যর্থ: ' + err.message, 'error');
  }
}

async function histDeleteChatMessage(sessionId, messageId, fromModal = false) {
  if (!confirm('এই নির্দিষ্ট চ্যাট মেসেজটি মুছে ফেলতে চান?')) return;
  try {
    const res = await histFetch(`/api/sessions/${encodeURIComponent(sessionId)}/messages/${Number(messageId)}`, {
      method: 'DELETE',
    });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.detail || 'Delete failed');
    histToast('🗑️ মেসেজ মুছে ফেলা হয়েছে।', 'info');
    if (fromModal) await openChatSessionDetailModal(sessionId);
    await loadHistoryHub();
  } catch (err) {
    histToast('মেসেজ ডিলিট ব্যর্থ: ' + err.message, 'error');
  }
}

async function histRenameChatSession(sessionId, currentTitle) {
  const nextTitle = prompt('নতুন চ্যাট সেশনের নাম লিখুন:', currentTitle || '');
  if (!nextTitle || !nextTitle.trim()) return;
  try {
    const res = await histFetch(`/api/sessions/${encodeURIComponent(sessionId)}`, {
      method: 'PUT',
      body: JSON.stringify({ title: nextTitle.trim() }),
    });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.detail || 'Rename failed');
    histToast('✏️ সেশনের নাম আপডেট হয়েছে।', 'success');
    await loadHistoryHub();
    if (typeof loadChatSessions === 'function') loadChatSessions();
  } catch (err) {
    histToast('রিনেম ব্যর্থ: ' + err.message, 'error');
  }
}

async function exportChatSessionById(sessionId, format = 'md') {
  try {
    const res = await histFetch(`/api/sessions/${encodeURIComponent(sessionId)}/export`);
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.detail || 'Export failed');
    const sess = data.session;
    if (format === 'json') {
      histDownloadFile(`chat_${sessionId}.json`, JSON.stringify(sess, null, 2));
    } else {
      const lines = [
        `# ${sess.title || sessionId}`,
        `- Session ID: ${sess.id}`,
        `- Model: ${sess.model_name || 'AI'}`,
        `- Created: ${sess.created_at || ''}`,
        `- Updated: ${sess.updated_at || ''}`,
        '',
        '---',
        '',
      ];
      (sess.messages || []).forEach(m => {
        const who = m.role === 'assistant' ? '🤖 MyAgent' : '👤 User';
        lines.push(`### ${who} (${m.created_at || ''})\n\n${m.content || ''}\n`);
      });
      histDownloadFile(`chat_${sessionId}.md`, lines.join('\n'), 'text/markdown;charset=utf-8;');
    }
    histToast('✅ চ্যাট সেশন এক্সপোর্ট হয়েছে!', 'success');
  } catch (err) {
    histToast('এক্সপোর্ট ব্যর্থ: ' + err.message, 'error');
  }
}

function exportUnifiedHistory(format = 'json') {
  if (!histState.data) {
    histToast('এক্সপোর্ট করার মতো ডেটা লোড হয়নি।', 'info');
    return;
  }
  if (format === 'json') {
    histDownloadFile(`myagent_unified_history_${Date.now()}.json`, JSON.stringify(histState.data, null, 2));
    histToast('✅ সম্পূর্ণ ইতিহাস (JSON) এক্সপোর্ট হয়েছে!', 'success');
    return;
  }

  const timeline = histState.data.timeline || [];
  const lines = [
    '# MyAgent — Unified Chat AI & WORKFLOWS (Auto) History',
    `Exported At: ${new Date().toLocaleString()}`,
    `Filter Kind: ${histState.subTab}`,
    '',
    '---',
    '',
  ];
  timeline.forEach((it, idx) => {
    lines.push(`## ${idx + 1}. [${String(it.kind || '').toUpperCase()}] ${it.title || ''}`);
    lines.push(`- Time: ${it.timestamp || ''}`);
    lines.push(`- Status: ${it.status || ''}`);
    lines.push(`- Meta: ${it.subtitle || ''}`);
    if (it.content) {
      lines.push('', '```text', it.content, '```');
    }
    lines.push('');
  });
  histDownloadFile(`myagent_unified_history_${Date.now()}.md`, lines.join('\n'), 'text/markdown;charset=utf-8;');
  histToast('✅ সম্পূর্ণ ইতিহাস (Markdown) এক্সপোর্ট হয়েছে!', 'success');
}

// Expose globals cleanly
window.loadHistoryHub = loadHistoryHub;
window.switchHistorySubTab = switchHistorySubTab;
window.onHistorySearchInput = onHistorySearchInput;
window.onHistoryFilterChange = onHistoryFilterChange;
window.openChatSessionDetailModal = openChatSessionDetailModal;
window.openWorkflowRunDetailModal = openWorkflowRunDetailModal;
window.openTelegramChatDetailModal = openTelegramChatDetailModal;
window.closeHistoryDetailModal = closeHistoryDetailModal;
window.exportDetailModalJson = exportDetailModalJson;
window.histOpenSessionInChat = histOpenSessionInChat;
window.histOpenRunInStudio = histOpenRunInStudio;
window.histRerunWorkflow = histRerunWorkflow;
window.histDeleteWorkflowRun = histDeleteWorkflowRun;
window.histClearWorkflowRuns = histClearWorkflowRuns;
window.histDeleteChatSession = histDeleteChatSession;
window.histDeleteChatMessage = histDeleteChatMessage;
window.histRenameChatSession = histRenameChatSession;
window.exportChatSessionById = exportChatSessionById;
window.exportUnifiedHistory = exportUnifiedHistory;
