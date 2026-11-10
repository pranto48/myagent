/* ==============================================================================
 * Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
 * Made By Arif (https://arifmahmud.com/)
 * Project: MyAgent | Version: 3.4.0
 * Visual n8n-Style Autonomous Workflow Studio, AI Architect & Live Runner
 * ============================================================================== */

let wfState = {
  workflows: [],
  workflowsList: [],
  variables: [],
  telegram: null,
  telegramLogs: [],
  templates: [],
  nodeCatalog: [],
  tools: [],
  subagents: [],
  models: [],
  recentRuns: [],
  activeWorkflow: null,
  activeRun: null,
  liveProgress: null,
  isRunningUI: false,
  selectedNodeId: null,
  connectingFrom: null,
  draggingNodeId: null,
  dragOffsetX: 0,
  dragOffsetY: 0,
  lastFocusedFieldId: null,
  subTab: 'studio',
  inspectorTab: 'node',
  dirty: false,
  zoom: 1.0,
  mouseCanvasX: 0,
  mouseCanvasY: 0,
};

// ------------------------------------------------------------------------------
// Auth & Utility Helpers
// ------------------------------------------------------------------------------
function wfGetToken() {
  return (
    localStorage.getItem('myagent_access_token') ||
    localStorage.getItem('myagent_token') ||
    (typeof getAuthToken === 'function' ? getAuthToken() : '') ||
    ''
  );
}

async function wfFetch(url, options = {}) {
  const token = wfGetToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {})
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return fetch(url, { ...options, headers });
}

function wfEsc(str) {
  if (typeof escapeHtml === 'function') return escapeHtml(str == null ? '' : String(str));
  return String(str == null ? '' : str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function wfToast(msg, type = 'info') {
  if (typeof showToast === 'function') {
    showToast(msg, type);
  } else {
    console.log(`[WorkflowStudio][${type}] ${msg}`);
  }
}

function wfClone(obj) {
  return JSON.parse(JSON.stringify(obj));
}

function wfNodeMeta(type) {
  const found = (wfState.nodeCatalog || []).find(c => c.type === type);
  if (found) return found;
  const fallback = {
    trigger_daily: { icon: '⏰', label_bn: 'দৈনিক শিডিউল', label_en: 'Daily Trigger', color: '#06b6d4', category: 'trigger' },
    trigger_webhook: { icon: '🌐', label_bn: 'ওয়েবহুক ট্রিগার', label_en: 'Webhook Trigger', color: '#0ea5e9', category: 'trigger' },
    ai_agent: { icon: '🧠', label_bn: 'এআই এজেন্ট', label_en: 'AI Agent', color: '#a855f7', category: 'ai' },
    subagent: { icon: '🤖', label_bn: 'সাব-এজেন্ট', label_en: 'Sub-Agent', color: '#8b5cf6', category: 'ai' },
    tool_call: { icon: '🛠️', label_bn: 'টুল এক্সিকিউট', label_en: 'Agent Tool', color: '#3b82f6', category: 'action' },
    python_transform: { icon: '🐍', label_bn: 'পাইথন ট্রান্সফর্ম', label_en: 'Python Transform', color: '#eab308', category: 'action' },
    loop_foreach: { icon: '🔁', label_bn: 'ব্যাচ লুপ (ForEach)', label_en: 'ForEach Loop', color: '#6366f1', category: 'logic' },
    delay_wait: { icon: '⏳', label_bn: 'অপেক্ষা টাইমার', label_en: 'Delay Timer', color: '#64748b', category: 'logic' },
    condition: { icon: '🔀', label_bn: 'শর্ত (IF/Else)', label_en: 'IF/Else', color: '#f59e0b', category: 'logic' },
    http_request: { icon: '📡', label_bn: 'HTTP রিকোয়েস্ট', label_en: 'HTTP Request', color: '#0284c7', category: 'action' },
    save_report: { icon: '📄', label_bn: 'AI রিপোর্ট সেভ', label_en: 'Save Report', color: '#10b981', category: 'output' },
    memory_save: { icon: '💾', label_bn: 'মেমোরি সেভ', label_en: 'Save Memory', color: '#14b8a6', category: 'output' },
    notify_channel: { icon: '📣', label_bn: 'চ্যাট/চ্যানেল নোটিফাই', label_en: 'Notify Digest', color: '#ec4899', category: 'output' },
    merge_combine: { icon: '🤝', label_bn: 'ব্রাঞ্চ মার্জ (Join)', label_en: 'Merge Branches', color: '#14b8a6', category: 'logic' },
    switch_router: { icon: '🚦', label_bn: 'সুইচ রাউটার (৩+ শাখা)', label_en: 'Switch Router', color: '#f97316', category: 'logic' },
    sub_workflow: { icon: '🔗', label_bn: 'সাব-ওয়ার্কফ্লো কল', label_en: 'Sub-Workflow', color: '#8b5cf6', category: 'action' },
    knowledge_db_query: { icon: '🗄️', label_bn: 'SQLite ও নলেজ সার্চ', label_en: 'DB & RAG Query', color: '#0ea5e9', category: 'action' },
  };
  return fallback[type] || { icon: '⚙️', label_bn: type, label_en: type, color: '#64748b', category: 'action' };
}

// ------------------------------------------------------------------------------
// Data Loading
// ------------------------------------------------------------------------------
async function loadWorkflowsStudio(preserveActiveId = null) {
  const listEl = document.getElementById('wf-list-container');
  if (listEl && !wfState.workflows.length) {
    listEl.innerHTML = '<div class="wf-empty-hint">লোড হচ্ছে...</div>';
  }

  try {
    const [wfRes, tplRes, varsRes, tgRes] = await Promise.all([
      wfFetch('/api/workflows'),
      wfFetch('/api/workflows/templates'),
      wfFetch('/api/workflows/vars/list'),
      wfFetch('/api/workflows/telegram/status')
    ]);

    const wfData = await wfRes.json();
    if (!wfRes.ok || !wfData.success) {
      throw new Error(wfData.detail || 'Failed to fetch workflows');
    }

    wfState.workflows = wfData.workflows || [];
    wfState.recentRuns = wfData.recent_runs || [];

    if (tplRes && tplRes.ok) {
      const tplData = await tplRes.json();
      if (tplData && tplData.success) {
        const hadPalette = wfState.nodeCatalog.length > 0;
        wfState.templates = tplData.templates || [];
        wfState.nodeCatalog = tplData.node_catalog || [];
        wfState.tools = tplData.tools || [];
        wfState.workflowsList = tplData.workflows_list || [];
        wfState.subagents = tplData.subagents || [];
        wfState.models = tplData.models || [];
        if (!hadPalette) populateQuickModelSelect();
        renderNodePalette();
        renderTemplatesLibrary();
      }
    }

    if (varsRes && varsRes.ok) {
      const vData = await varsRes.json();
      if (vData && vData.success) {
        wfState.variables = vData.variables || [];
      }
    }

    if (tgRes && tgRes.ok) {
      const tgData = await tgRes.json();
      if (tgData && tgData.success) {
        wfState.telegram = tgData.telegram || null;
        renderTelegramStatusUI();
      }
    }

    updateWorkflowKpis(wfData.stats || {});
    renderWorkflowsSidebar();
    renderExecutionHistoryTable();

    const targetId = preserveActiveId || (wfState.activeWorkflow ? wfState.activeWorkflow.id : null);
    let nextSelected = targetId ? wfState.workflows.find(w => w.id === targetId) : null;
    if (!nextSelected && wfState.workflows.length > 0) {
      nextSelected = wfState.workflows[0];
    }

    if (nextSelected) {
      await selectWorkflow(nextSelected.id, true);
    } else {
      wfState.activeWorkflow = null;
      renderWorkflowToolbar();
      renderNextRunsStrip();
      renderWorkflowCanvas();
      renderNodeInspector();
    }
  } catch (err) {
    console.error('loadWorkflowsStudio error:', err);
    if (listEl) {
      listEl.innerHTML = `<div class="wf-empty-hint" style="color:#f43f5e;">লোড ত্রুটি: ${wfEsc(err.message)}</div>`;
    }
    wfToast('ওয়ার্কফ্লো স্টুডিও লোড করতে সমস্যা হয়েছে: ' + err.message, 'error');
  }
}

function updateWorkflowKpis(stats) {
  const setText = (id, v) => {
    const el = document.getElementById(id);
    if (el) el.innerText = v;
  };
  setText('wf-kpi-total', stats.total_workflows ?? wfState.workflows.length ?? 0);
  setText('wf-kpi-active', stats.active_workflows ?? wfState.workflows.filter(w => w.is_enabled).length);
  setText('wf-kpi-runs', stats.total_runs ?? 0);
  setText('wf-kpi-success', `${stats.success_rate ?? 100}%`);
}

function populateQuickModelSelect() {
  const sel = document.getElementById('wf-quick-model');
  if (!sel) return;
  sel.innerHTML = (wfState.models || []).map(m =>
    `<option value="${wfEsc(m.id)}">${wfEsc(m.label || m.id)}</option>`
  ).join('');
}

// ------------------------------------------------------------------------------
// Sub-tabs, Quick Builder & AI Workflow Architect
// ------------------------------------------------------------------------------
function switchWorkflowsSubTab(tabName) {
  wfState.subTab = tabName;
  ['studio', 'history', 'templates', 'telegram'].forEach(t => {
    const pane = document.getElementById(`wf-subtab-${t}`);
    const btn = document.getElementById(`wf-tabbtn-${t}`);
    if (pane) pane.style.display = t === tabName ? '' : 'none';
    if (btn) btn.classList.toggle('active', t === tabName);
  });

  if (tabName === 'studio') {
    setTimeout(drawWorkflowEdges, 40);
  } else if (tabName === 'history') {
    refreshRecentWorkflowRuns();
  } else if (tabName === 'telegram') {
    refreshWorkflowTelegramLogs(true);
  }
}

function switchWfInspectorTab(tabName) {
  wfState.inspectorTab = tabName;
  ['node', 'run'].forEach(t => {
    const pane = document.getElementById(`wf-inspector-${t}`);
    const btn = document.getElementById(`wf-insp-btn-${t}`);
    if (pane) pane.style.display = t === tabName ? 'flex' : 'none';
    if (btn) btn.classList.toggle('active', t === tabName);
  });
}

function toggleQuickDailyBuilder() {
  const body = document.getElementById('wf-quick-builder-body');
  if (!body) return;
  body.style.display = body.style.display === 'none' ? 'block' : 'none';
}

function applyQuickDailyPreset(presetKey) {
  const nameEl = document.getElementById('wf-quick-name');
  const instEl = document.getElementById('wf-quick-instruction');
  const timeEl = document.getElementById('wf-quick-time');
  const freqEl = document.getElementById('wf-quick-frequency');
  const repEl = document.getElementById('wf-quick-save-report');
  const memEl = document.getElementById('wf-quick-save-memory');

  if (presetKey === 'health') {
    if (nameEl) nameEl.value = 'দৈনিক সার্ভার ফ্লিট ও নেটওয়ার্ক অডিট';
    if (instEl) instEl.value = '192.168.9.1, 192.168.9.5, 192.168.9.9, 8.8.8.8 পিং ও পোর্ট স্ক্যান করে Python দিয়ে হেলথ স্কোর বের করো; কোনো সমস্যা থাকলে Telegram ও চ্যাটে অ্যালার্ট পাঠাও, নাহলে রিপোর্ট সেভ করো।';
    if (timeEl) timeEl.value = '09:00';
    if (freqEl) freqEl.value = 'daily';
    if (repEl) repEl.checked = true;
    if (memEl) memEl.checked = false;
  } else if (presetKey === 'project') {
    if (nameEl) nameEl.value = 'দৈনিক প্রজেক্ট মেমোরি ও কাজ রিভিউ';
    if (instEl) instEl.value = 'সংরক্ষিত প্রজেক্ট মেমোরি ও SQLite ডাটাবেস চেক করে আজকের অগ্রাধিকারভিত্তিক কাজের তালিকা (Action Plan) এবং প্রজেক্ট স্ট্যাটাস সারাংশ তৈরি ও মেমোরিতে সংরক্ষণ করো।';
    if (timeEl) timeEl.value = '10:00';
    if (freqEl) freqEl.value = 'daily';
    if (repEl) repEl.checked = true;
    if (memEl) memEl.checked = true;
  } else if (presetKey === 'research') {
    if (nameEl) nameEl.value = 'দৈনিক এআই টেক ও API ইনসাইট ডাইজেস্ট';
    if (instEl) instEl.value = 'কোম্পানি নলেজ বেজ ও প্রজেক্ট নোট পর্যালোচনা করে গুরুত্বপূর্ণ ইনসাইট, রিস্ক এবং আজকের টিমের জন্য করণীয় টিপস তৈরি করো।';
    if (timeEl) timeEl.value = '11:00';
    if (freqEl) freqEl.value = 'daily';
    if (repEl) repEl.checked = true;
    if (memEl) memEl.checked = true;
  } else if (presetKey === 'security') {
    if (nameEl) nameEl.value = 'রাতের সিকিউরিটি পোর্ট ও DLP অডিট';
    if (instEl) instEl.value = 'সার্ভার 192.168.9.9 ও লোকাল পোর্ট স্ক্যান এবং সিকিউরিটি DLP অডিট চালিয়ে যদি কোনো warning বা critical পাও তবে সতর্কবার্তা পাঠাও, নাহলে সিকিউরিটি রিপোর্ট সেভ করো।';
    if (timeEl) timeEl.value = '22:00';
    if (freqEl) freqEl.value = 'daily';
    if (repEl) repEl.checked = true;
    if (memEl) memEl.checked = false;
  }

  const body = document.getElementById('wf-quick-builder-body');
  if (body && body.style.display === 'none') body.style.display = 'block';
}

async function submitQuickDailyTask(event) {
  if (event) event.preventDefault();
  const instructionEl = document.getElementById('wf-quick-instruction');
  const instruction = instructionEl ? instructionEl.value.trim() : '';
  if (!instruction) {
    wfToast('অনুগ্রহ করে এজেন্ট প্রতিদিন কী কাজ করবে তা লিখুন।', 'error');
    if (instructionEl) instructionEl.focus();
    return;
  }

  const name = (document.getElementById('wf-quick-name')?.value || '').trim() || instruction.slice(0, 44);
  const daily_time = document.getElementById('wf-quick-time')?.value || '09:00';
  const frequency = document.getElementById('wf-quick-frequency')?.value || 'daily';
  const model = document.getElementById('wf-quick-model')?.value || '';
  const project_name = (document.getElementById('wf-quick-project')?.value || '').trim();
  const save_report = !!document.getElementById('wf-quick-save-report')?.checked;
  const save_memory = !!document.getElementById('wf-quick-save-memory')?.checked;
  const post_to_chat = !!document.getElementById('wf-quick-post-chat')?.checked;
  const notify_channels = !!document.getElementById('wf-quick-notify-channels')?.checked;
  const run_immediately = !!document.getElementById('wf-quick-run-now')?.checked;

  const btn = document.getElementById('btn-wf-quick-create');
  const origHtml = btn ? btn.innerHTML : '';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = run_immediately ? '⏳ তৈরি ও লাইভ রান হচ্ছে...' : '⏳ তৈরি হচ্ছে...';
  }

  try {
    const res = await wfFetch('/api/workflows/quick-daily', {
      method: 'POST',
      body: JSON.stringify({
        name,
        instruction,
        daily_time,
        frequency,
        timezone: 'Asia/Dhaka',
        model,
        project_name,
        save_report,
        save_memory,
        post_to_chat,
        notify_channels,
        run_immediately,
        language: typeof getAppLanguage === 'function' ? getAppLanguage() : 'bn'
      })
    });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.detail || 'Workflow creation failed');

    wfToast(`✅ "${data.workflow.name}" অ্যাক্টিভেট হয়েছে! (${daily_time} Asia/Dhaka)`, 'success');
    if (instructionEl) instructionEl.value = '';
    const nameEl = document.getElementById('wf-quick-name');
    if (nameEl) nameEl.value = '';

    await loadWorkflowsStudio(data.workflow.id);
    switchWorkflowsSubTab('studio');

    if (data.run_result) {
      wfState.activeRun = data.run_result;
      renderWorkflowCanvas();
      renderRunOutputPanel();
      switchWfInspectorTab('run');
    }
  } catch (err) {
    wfToast('কুইক ডেইলি টাস্ক তৈরি ব্যর্থ: ' + err.message, 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origHtml;
    }
  }
}

async function architectWorkflowFromBuilder() {
  const instructionEl = document.getElementById('wf-quick-instruction');
  const goal = instructionEl ? instructionEl.value.trim() : '';
  if (!goal) {
    wfToast('AI Multi-Node Architect চালানোর জন্য কাজের বিবরণ (Goal) লিখুন অথবা উদাহরণ প্রিসেটে ক্লিক করুন।', 'warning');
    if (instructionEl) instructionEl.focus();
    return;
  }

  const name = (document.getElementById('wf-quick-name')?.value || '').trim();
  const daily_time = document.getElementById('wf-quick-time')?.value || '09:00';
  const frequency = document.getElementById('wf-quick-frequency')?.value || 'daily';
  const model = document.getElementById('wf-quick-model')?.value || '';
  const project_name = (document.getElementById('wf-quick-project')?.value || '').trim();

  const btn = document.getElementById('btn-wf-ai-architect');
  const origHtml = btn ? btn.innerHTML : '';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '🧠 ডিজাইন করছে...';
  }

  try {
    const res = await wfFetch('/api/workflows/ai-architect', {
      method: 'POST',
      body: JSON.stringify({
        goal,
        name,
        daily_time,
        frequency,
        timezone: 'Asia/Dhaka',
        model,
        project_name,
        is_enabled: true
      })
    });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.detail || 'Architect failed');

    wfToast(`🧠 AI Architect "${data.workflow.name}"-এর জন্য ${(data.workflow.nodes || []).length}-নোডের পূর্ণাঙ্গ DAG তৈরি করেছে!`, 'success');
    await loadWorkflowsStudio(data.workflow.id);
    switchWorkflowsSubTab('studio');
  } catch (err) {
    wfToast('AI Architect ত্রুটি: ' + err.message, 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origHtml;
    }
  }
}

// ------------------------------------------------------------------------------
// Workflows Sidebar, Search & Selection
// ------------------------------------------------------------------------------
function renderWorkflowsSidebar() {
  const container = document.getElementById('wf-list-container');
  const countBadge = document.getElementById('wf-sidebar-count');
  if (!container) return;

  const q = (document.getElementById('wf-search-input')?.value || '').trim().toLowerCase();
  let list = wfState.workflows || [];
  if (q) {
    list = list.filter(w =>
      (w.name || '').toLowerCase().includes(q) ||
      (w.description || '').toLowerCase().includes(q)
    );
  }
  if (countBadge) countBadge.innerText = `${list.length}`;

  if (!list.length) {
    container.innerHTML = '<div class="wf-empty-hint">কোনো ওয়ার্কফ্লো পাওয়া যায়নি।</div>';
    return;
  }

  const activeId = wfState.activeWorkflow ? wfState.activeWorkflow.id : '';
  container.innerHTML = list.map(wf => {
    const isSel = wf.id === activeId;
    const statusCls = (wf.last_status || 'IDLE').toLowerCase();
    const sched = wf.trigger_type === 'webhook'
      ? '🌐 Webhook'
      : wf.trigger_type === 'manual'
        ? '👆 Manual'
        : `⏰ ${wf.daily_time || wf.schedule_expr || 'Scheduled'}`;
    const nodeCount = (wf.nodes || []).length;

    return `
      <div class="wf-list-item ${isSel ? 'selected' : ''}" onclick="selectWorkflow('${wfEsc(wf.id)}')">
        <div class="wf-list-top">
          <div class="wf-list-title-wrap">
            <span class="wf-list-icon">${wfEsc(wf.icon || '⚡')}</span>
            <div>
              <div class="wf-list-name">${wfEsc(wf.name)}</div>
              <div class="wf-list-meta">${wfEsc(sched)} • ${nodeCount} nodes • ${wf.run_count || 0} runs</div>
            </div>
          </div>
          <label class="cyber-switch" onclick="event.stopPropagation()">
            <input type="checkbox" ${wf.is_enabled ? 'checked' : ''} onchange="toggleWorkflowById('${wfEsc(wf.id)}')">
            <span class="slider"></span>
          </label>
        </div>
        <div class="wf-list-bottom">
          <span class="wf-status-pill ${statusCls}">${wfEsc(wf.last_status || 'IDLE')}</span>
          <span class="wf-next-hint">${wf.next_run ? 'Next: ' + wfEsc(wf.next_run.slice(5, 16)) : ''}</span>
        </div>
      </div>
    `;
  }).join('');
}

async function selectWorkflow(workflowId, skipPrompt = false) {
  if (!skipPrompt && wfState.dirty && wfState.activeWorkflow && wfState.activeWorkflow.id !== workflowId) {
    wfToast('সতর্কতা: পূর্বের অসংরক্ষিত পরিবর্তন বাতিল হয়েছে (Save করুন)।', 'warning');
  }

  try {
    const res = await wfFetch(`/api/workflows/${encodeURIComponent(workflowId)}`);
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.detail || 'Workflow not found');

    wfState.activeWorkflow = wfClone(data.workflow);
    wfState.recentRuns = data.runs && data.runs.length
      ? mergeRuns(wfState.recentRuns, data.runs)
      : wfState.recentRuns;
    wfState.activeRun = data.runs && data.runs.length ? data.runs[0] : null;
    wfState.liveProgress = null;
    wfState.selectedNodeId = (wfState.activeWorkflow.nodes && wfState.activeWorkflow.nodes[0])
      ? wfState.activeWorkflow.nodes[0].id
      : null;
    wfState.connectingFrom = null;
    wfState.dirty = false;

    renderWorkflowsSidebar();
    renderWorkflowToolbar();
    renderNextRunsStrip();
    renderWorkflowCanvas();
    renderNodeInspector();
    renderRunOutputPanel();
  } catch (err) {
    wfToast('ওয়ার্কফ্লো লোড ব্যর্থ: ' + err.message, 'error');
  }
}

function mergeRuns(existing, incoming) {
  const map = new Map();
  [...incoming, ...existing].forEach(r => { if (r && r.id) map.set(r.id, r); });
  return Array.from(map.values()).slice(0, 40);
}

async function toggleWorkflowById(workflowId) {
  try {
    const res = await wfFetch(`/api/workflows/${encodeURIComponent(workflowId)}/toggle`, { method: 'PUT' });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.detail || 'Toggle failed');

    if (wfState.activeWorkflow && wfState.activeWorkflow.id === workflowId) {
      wfState.activeWorkflow.is_enabled = data.is_enabled;
      wfState.activeWorkflow.next_run = data.workflow.next_run;
      wfState.activeWorkflow.next_runs_preview = data.workflow.next_runs_preview || [];
      renderWorkflowToolbar();
      renderNextRunsStrip();
    }
    wfToast(data.is_enabled ? '⚡ অটো শিডিউল সক্রিয় হয়েছে!' : '⏸️ ওয়ার্কফ্লো পজ করা হয়েছে।', 'info');
    await loadWorkflowsStudio(wfState.activeWorkflow ? wfState.activeWorkflow.id : null);
  } catch (err) {
    wfToast('টগল ব্যর্থ: ' + err.message, 'error');
  }
}

async function createBlankWorkflow() {
  const defaultWf = {
    name: `নতুন কাস্টম ওয়ার্কফ্লো #${wfState.workflows.length + 1}`,
    description: 'Visual multi-node daily AI agent workflow',
    icon: '⚡',
    trigger_type: 'daily',
    daily_time: '09:00',
    timezone: 'Asia/Dhaka',
    is_enabled: false
  };
  try {
    const res = await wfFetch('/api/workflows', {
      method: 'POST',
      body: JSON.stringify(defaultWf)
    });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.detail || 'Failed to create workflow');
    wfToast('নতুন ওয়ার্কফ্লো ক্যানভাসে তৈরি হয়েছে!', 'success');
    await loadWorkflowsStudio(data.workflow.id);
    switchWorkflowsSubTab('studio');
  } catch (err) {
    wfToast('নতুন ওয়ার্কফ্লো তৈরি ব্যর্থ: ' + err.message, 'error');
  }
}

async function duplicateActiveWorkflow() {
  const wf = wfState.activeWorkflow;
  if (!wf) return;
  try {
    const res = await wfFetch(`/api/workflows/${encodeURIComponent(wf.id)}/duplicate`, { method: 'POST' });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.detail || 'Duplicate failed');
    wfToast(`📋 "${data.workflow.name}" ক্লোন হয়েছে!`, 'success');
    await loadWorkflowsStudio(data.workflow.id);
  } catch (err) {
    wfToast('ক্লোন ব্যর্থ: ' + err.message, 'error');
  }
}

async function exportActiveWorkflow() {
  const wf = wfState.activeWorkflow;
  if (!wf) return;
  try {
    const res = await wfFetch(`/api/workflows/${encodeURIComponent(wf.id)}/export`);
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.detail || 'Export failed');
    const blob = new Blob([JSON.stringify(data.workflow, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `${wf.id}_workflow.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    wfToast('⬇️ ওয়ার্কফ্লো JSON এক্সপোর্ট সম্পন্ন হয়েছে!', 'success');
  } catch (err) {
    wfToast('এক্সপোর্ট ব্যর্থ: ' + err.message, 'error');
  }
}

async function importWorkflowFromFile(event) {
  const file = event?.target?.files?.[0];
  if (!file) return;
  try {
    const text = await file.text();
    const parsed = JSON.parse(text);
    const res = await wfFetch('/api/workflows/import', {
      method: 'POST',
      body: JSON.stringify(parsed)
    });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.detail || 'Import failed');
    wfToast(`📥 "${data.workflow.name}" ইমপোর্ট সম্পন্ন হয়েছে!`, 'success');
    await loadWorkflowsStudio(data.workflow.id);
    switchWorkflowsSubTab('studio');
  } catch (err) {
    wfToast('JSON ইমপোর্ট ব্যর্থ: ' + err.message, 'error');
  } finally {
    if (event && event.target) event.target.value = '';
  }
}

// ------------------------------------------------------------------------------
// Palette, Canvas Actions, Zoom & Layout
// ------------------------------------------------------------------------------
function renderNodePalette() {
  const el = document.getElementById('wf-node-palette');
  if (!el) return;
  el.innerHTML = (wfState.nodeCatalog || []).map(item => `
    <button type="button" class="wf-palette-chip" style="--node-color:${item.color};" onclick="addNodeToCanvas('${wfEsc(item.type)}')" title="${wfEsc(item.label_en)} যোগ করুন">
      <span class="wf-palette-dot" style="background:${item.color};"></span>
      <span>${wfEsc(item.icon)} ${wfEsc(item.label_bn || item.label_en)}</span>
      <span class="wf-palette-plus">+</span>
    </button>
  `).join('');
}

function addNodeToCanvas(nodeType) {
  if (!wfState.activeWorkflow) {
    wfToast('প্রথমে একটি ওয়ার্কফ্লো নির্বাচন করুন বা তৈরি করুন।', 'warning');
    return;
  }

  const meta = wfNodeMeta(nodeType);
  const nodes = wfState.activeWorkflow.nodes || [];
  const edges = wfState.activeWorkflow.edges || [];

  let maxIdx = nodes.length;
  nodes.forEach(n => {
    const m = /^node_(\d+)$/.exec(n.id || '');
    if (m) maxIdx = Math.max(maxIdx, parseInt(m[1], 10));
  });
  const newId = `node_${maxIdx + 1}`;

  const anchor = nodes.find(n => n.id === wfState.selectedNodeId) || nodes[nodes.length - 1];
  const baseX = anchor ? (Number(anchor.x || 50) + 290) : 50;
  let targetY = anchor ? Number(anchor.y || 140) : 140;
  while (nodes.some(n => Math.abs((n.x || 0) - baseX) < 160 && Math.abs((n.y || 0) - targetY) < 95)) {
    targetY += 130;
  }

  const newNode = {
    id: newId,
    type: nodeType,
    title: meta.label_bn || meta.label_en || nodeType,
    x: baseX,
    y: targetY,
    disabled: false,
    config: wfClone(meta.default_config || {})
  };
  nodes.push(newNode);

  if (anchor && !nodeType.startsWith('trigger_')) {
    let cond = '';
    if (anchor.type === 'condition') {
      const hasTrue = edges.some(e => e.source === anchor.id && e.condition === 'true');
      cond = hasTrue ? 'false' : 'true';
    }
    edges.push({
      id: `e_${Date.now().toString(36)}`,
      source: anchor.id,
      target: newId,
      condition: cond
    });
  }

  wfState.activeWorkflow.nodes = nodes;
  wfState.activeWorkflow.edges = edges;
  wfState.selectedNodeId = newId;
  markWfDirty();

  renderWorkflowCanvas();
  renderNodeInspector();
  switchWfInspectorTab('node');
}

function duplicateNodeById(event, nodeId) {
  if (event) event.stopPropagation();
  const wf = wfState.activeWorkflow;
  if (!wf) return;
  const src = (wf.nodes || []).find(n => n.id === nodeId);
  if (!src) return;

  let maxIdx = wf.nodes.length;
  wf.nodes.forEach(n => {
    const m = /^node_(\d+)$/.exec(n.id || '');
    if (m) maxIdx = Math.max(maxIdx, parseInt(m[1], 10));
  });
  const newNode = wfClone(src);
  newNode.id = `node_${maxIdx + 1}`;
  newNode.title = `${src.title || src.type} (Copy)`;
  newNode.x = Number(src.x || 50) + 40;
  newNode.y = Number(src.y || 140) + 125;
  wf.nodes.push(newNode);
  wfState.selectedNodeId = newNode.id;
  markWfDirty();
  renderWorkflowCanvas();
  renderNodeInspector();
  wfToast(`❐ নোড "${src.title}" ডুপ্লিকেট হয়েছে।`, 'info');
}

function toggleNodeDisabled(event, nodeId) {
  if (event) event.stopPropagation();
  const wf = wfState.activeWorkflow;
  if (!wf) return;
  const node = (wf.nodes || []).find(n => n.id === nodeId);
  if (!node) return;
  node.disabled = !node.disabled;
  node.config = node.config || {};
  node.config.disabled = node.disabled;
  markWfDirty();
  renderWorkflowCanvas();
  if (wfState.selectedNodeId === nodeId) renderNodeInspector();
  wfToast(node.disabled ? '⏸️ নোড সাময়িকভাবে মিউট/বাইপাস করা হয়েছে।' : '▶️ নোড পুনরায় সক্রিয় হয়েছে।', 'info');
}

function copyNodeVarRef(event, nodeId) {
  if (event) event.stopPropagation();
  const token = `{{nodes.${nodeId}.output}}`;
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(token);
  }
  wfToast(`📋 কপি হয়েছে: ${token}`, 'info');
}

function setCanvasZoom(deltaOrReset) {
  if (deltaOrReset === 0) {
    wfState.zoom = 1.0;
  } else {
    wfState.zoom = Math.max(0.6, Math.min(1.4, Number((wfState.zoom + deltaOrReset).toFixed(2))));
  }
  renderWorkflowToolbar();
  renderWorkflowCanvas();
}

function autoLayoutWorkflow() {
  const wf = wfState.activeWorkflow;
  if (!wf || !wf.nodes || !wf.nodes.length) return;

  const nodes = wf.nodes;
  const edges = wf.edges || [];
  const inDeg = {};
  const adj = {};
  nodes.forEach(n => { inDeg[n.id] = 0; adj[n.id] = []; });
  edges.forEach(e => {
    if (inDeg[e.target] !== undefined && adj[e.source]) {
      inDeg[e.target]++;
      adj[e.source].push(e);
    }
  });

  const levelMap = {};
  const queue = nodes.filter(n => inDeg[n.id] === 0).map(n => n.id);
  if (!queue.length) queue.push(nodes[0].id);
  queue.forEach(id => { levelMap[id] = 0; });

  let head = 0;
  while (head < queue.length) {
    const u = queue[head++];
    const lv = levelMap[u] || 0;
    (adj[u] || []).forEach(e => {
      const v = e.target;
      if (levelMap[v] === undefined || levelMap[v] < lv + 1) {
        levelMap[v] = lv + 1;
        queue.push(v);
      }
    });
  }

  nodes.forEach(n => { if (levelMap[n.id] === undefined) levelMap[n.id] = 0; });
  const byLevel = {};
  nodes.forEach(n => {
    const lv = levelMap[n.id];
    if (!byLevel[lv]) byLevel[lv] = [];
    byLevel[lv].push(n);
  });

  Object.keys(byLevel).forEach(lvStr => {
    const lv = Number(lvStr);
    const grp = byLevel[lv];
    const startY = grp.length === 1 ? 155 : 55;
    grp.forEach((n, idx) => {
      n.x = 45 + lv * 290;
      n.y = startY + idx * 170;
    });
  });

  markWfDirty();
  renderWorkflowCanvas();
  wfToast('📐 ক্যানভাস অটো-অ্যালাইন সম্পন্ন হয়েছে।', 'info');
}

function markWfDirty() {
  wfState.dirty = true;
  const saveBtn = document.getElementById('btn-wf-save');
  if (saveBtn) saveBtn.classList.add('wf-save-dirty');
}

function renderWorkflowToolbar() {
  const bar = document.getElementById('wf-canvas-toolbar');
  if (!bar) return;
  const wf = wfState.activeWorkflow;
  if (!wf) {
    bar.innerHTML = '<div style="color:var(--text-muted); font-size:0.85rem;">বাম পাশ থেকে একটি ওয়ার্কফ্লো সিলেক্ট করুন।</div>';
    return;
  }

  const schedBadge = wf.trigger_type === 'webhook'
    ? '🌐 Webhook'
    : `⏰ ${wf.daily_time || 'Scheduled'}`;
  const zoomPct = Math.round((wfState.zoom || 1) * 100);

  bar.innerHTML = `
    <div class="wf-tb-left">
      <span class="wf-tb-icon">${wfEsc(wf.icon || '⚡')}</span>
      <input type="text" id="wf-active-name-input" class="wf-tb-name-input" value="${wfEsc(wf.name)}"
             onchange="updateActiveWorkflowMeta('name', this.value)" title="ওয়ার্কফ্লোর নাম এডিট করুন">
      <span class="wf-tb-sched-pill" title="${wfEsc(wf.human_bn || wf.schedule_expr || '')}">${wfEsc(schedBadge)}</span>
    </div>
    <div class="wf-tb-right">
      <label class="wf-tb-toggle" title="অটো শিডিউল চালু/বন্ধ">
        <input type="checkbox" ${wf.is_enabled ? 'checked' : ''} onchange="updateActiveWorkflowMeta('is_enabled', this.checked)">
        <span>${wf.is_enabled ? 'ON' : 'OFF'}</span>
      </label>
      <div class="wf-zoom-group">
        <button type="button" class="wf-tb-btn wf-btn-mini" onclick="setCanvasZoom(-0.1)" title="Zoom Out">-</button>
        <button type="button" class="wf-tb-btn wf-btn-mini" onclick="setCanvasZoom(0)" title="Reset Zoom">${zoomPct}%</button>
        <button type="button" class="wf-tb-btn wf-btn-mini" onclick="setCanvasZoom(0.1)" title="Zoom In">+</button>
      </div>
      <button type="button" class="wf-tb-btn" onclick="autoLayoutWorkflow()" title="অটো-লেআউট">📐</button>
      <button type="button" class="wf-tb-btn" onclick="openWorkflowVersionsModal()" title="ভার্সন হিস্ট্রি ও রোলব্যাক">🕒</button>
      <button type="button" class="wf-tb-btn" onclick="duplicateActiveWorkflow()" title="ক্লোন ওয়ার্কফ্লো">📋</button>
      <button type="button" class="wf-tb-btn" onclick="exportActiveWorkflow()" title="Export JSON">⬇️</button>
      <button type="button" class="wf-tb-btn" onclick="copyWorkflowWebhookUrl()" title="Webhook URL কপি">🔗</button>
      <button type="button" class="wf-tb-btn" onclick="openWorkflowPayloadModal()" title="কাস্টম JSON পেলোড বা Dry-Run">{ } Test</button>
      <button type="button" id="btn-wf-save" class="wf-tb-btn wf-btn-save ${wfState.dirty ? 'wf-save-dirty' : ''}" onclick="saveActiveWorkflow()">💾 Save</button>
      ${wfState.isRunningUI
        ? `<button type="button" id="btn-wf-stop-now" class="wf-tb-btn wf-btn-stop" onclick="stopActiveWorkflow()">🛑 Stop</button>`
        : `<button type="button" id="btn-wf-run-now" class="wf-tb-btn wf-btn-run" onclick="runActiveWorkflowNow()">▶ Run Now</button>`
      }
      <button type="button" class="wf-tb-btn wf-btn-del" onclick="deleteActiveWorkflow()" title="ডিলিট">🗑️</button>
    </div>
  `;
}

function renderNextRunsStrip() {
  const strip = document.getElementById('wf-next-runs-strip');
  if (!strip) return;
  const wf = wfState.activeWorkflow;
  if (!wf) {
    strip.style.display = 'none';
    return;
  }
  const upcoming = wf.next_runs_preview || [];
  if (!wf.is_enabled || wf.trigger_type === 'webhook' || wf.trigger_type === 'manual') {
    strip.style.display = 'flex';
    strip.innerHTML = wf.is_enabled
      ? `<span>🌐 ট্রিগার মোড: <strong>${wfEsc(wf.human_bn || wf.trigger_type)}</strong></span>`
      : `<span>⏸️ শিডিউল পজ করা আছে — অটোমেটিক দৈনিক রানের জন্য <strong>ON</strong> সুইচ চালু করে Save করুন।</span>`;
    return;
  }
  strip.style.display = 'flex';
  const chips = upcoming.length
    ? upcoming.map(dt => `<span class="wf-upcoming-chip">📅 ${wfEsc(dt)}</span>`).join('')
    : (wf.next_run ? `<span class="wf-upcoming-chip">📅 ${wfEsc(wf.next_run)}</span>` : '');
  strip.innerHTML = `<span>⏱️ আসন্ন অটোমেটিক রান (${wfEsc(wf.timezone || 'Asia/Dhaka')}):</span> ${chips}`;
}

function updateActiveWorkflowMeta(key, value) {
  if (!wfState.activeWorkflow) return;
  wfState.activeWorkflow[key] = value;
  markWfDirty();
  if (key === 'is_enabled') {
    renderWorkflowToolbar();
    renderNextRunsStrip();
  }
}

async function saveActiveWorkflow() {
  const wf = wfState.activeWorkflow;
  if (!wf) return;

  const trig = (wf.nodes || []).find(n => (n.type || '').startsWith('trigger_'));
  if (trig) {
    if (trig.type === 'trigger_daily') {
      const cfg = trig.config || {};
      const dt = cfg.daily_time || wf.daily_time || '09:00';
      const freq = cfg.frequency || 'daily';
      const tz = cfg.timezone || wf.timezone || 'Asia/Dhaka';
      wf.trigger_type = freq === 'daily' ? 'daily' : 'cron';
      wf.daily_time = dt;
      wf.timezone = tz;
      const parts = dt.split(':');
      const hh = Math.max(0, Math.min(23, parseInt(parts[0] || '9', 10)));
      const mm = Math.max(0, Math.min(59, parseInt(parts[1] || '0', 10)));
      if (freq === 'every_15m') wf.schedule_expr = '*/15 * * * *';
      else if (freq === 'hourly') wf.schedule_expr = `${mm} * * * *`;
      else if (freq === 'every_6h') wf.schedule_expr = `${mm} */6 * * *`;
      else if (freq === 'weekly') wf.schedule_expr = `${mm} ${hh} * * 0`;
      else wf.schedule_expr = `${mm} ${hh} * * *`;
    } else if (trig.type === 'trigger_webhook') {
      wf.trigger_type = 'webhook';
      wf.schedule_expr = '';
    }
  }

  const btn = document.getElementById('btn-wf-save');
  if (btn) { btn.disabled = true; btn.innerText = '⏳ Saving...'; }

  try {
    const res = await wfFetch(`/api/workflows/${encodeURIComponent(wf.id)}`, {
      method: 'PUT',
      body: JSON.stringify({
        name: wf.name,
        description: wf.description,
        icon: wf.icon,
        trigger_type: wf.trigger_type,
        schedule_expr: wf.schedule_expr,
        daily_time: wf.daily_time,
        timezone: wf.timezone,
        nodes: wf.nodes,
        edges: wf.edges,
        is_enabled: wf.is_enabled
      })
    });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.detail || 'Save failed');

    wfState.activeWorkflow = wfClone(data.workflow);
    wfState.dirty = false;
    wfToast('✅ ওয়ার্কফ্লো গ্রাফ ও শিডিউল সংরক্ষিত হয়েছে!', 'success');
    await loadWorkflowsStudio(wf.id);
  } catch (err) {
    wfToast('সংরক্ষণ ব্যর্থ: ' + err.message, 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.innerText = '💾 Save'; }
  }
}

async function runActiveWorkflowNow(customPayload = null, dryRun = false) {
  const wf = wfState.activeWorkflow;
  if (!wf) return;

  if (wfState.dirty) {
    await saveActiveWorkflow();
  }

  wfState.isRunningUI = true;
  renderWorkflowToolbar();

  wfState.liveProgress = {
    current_node_id: wf.nodes?.[0]?.id || null,
    active_node_ids: wf.nodes?.[0]?.id ? [wf.nodes[0].id] : [],
    node_results: []
  };
  renderWorkflowCanvas();

  // Live step progress polling every 600ms showing concurrent wave animation
  const pollTimer = setInterval(async () => {
    try {
      const pRes = await wfFetch(`/api/workflows/${encodeURIComponent(wf.id)}/live-status`);
      if (pRes.ok) {
        const pData = await pRes.json();
        if (pData && pData.progress) {
          wfState.liveProgress = pData.progress;
          wfState.activeRun = {
            id: pData.progress.run_id,
            status: pData.progress.status,
            trigger_source: dryRun ? 'manual[DRY]' : 'manual',
            duration_ms: 0,
            node_results: pData.progress.node_results || []
          };
          renderWorkflowCanvas();
          renderRunOutputPanel();
        }
      }
    } catch (_) {}
  }, 600);

  try {
    const payloadObj = customPayload && typeof customPayload === 'object' ? customPayload : { triggered_by: 'studio_ui' };
    const res = await wfFetch(`/api/workflows/${encodeURIComponent(wf.id)}/run`, {
      method: 'POST',
      body: JSON.stringify({ payload: payloadObj, dry_run: !!dryRun })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Execution error');

    clearInterval(pollTimer);
    wfState.liveProgress = null;
    wfState.isRunningUI = false;
    wfState.activeRun = data;

    if (data.status === 'SUCCESS') {
      wfToast(`${dryRun ? '🧪 Dry-Run' : '✅ ওয়ার্কফ্লো'} সফল (${data.duration_ms} ms)!`, 'success');
    } else if (data.status === 'PARTIAL') {
      wfToast(`⚠️ আংশিক সফল (${data.duration_ms} ms) — Run Trace দেখুন।`, 'warning');
    } else if (data.status === 'CANCELLED') {
      wfToast('🛑 ওয়ার্কফ্লো রান ব্যবহারকারী কর্তৃক থামানো হয়েছে।', 'warning');
    } else {
      wfToast(`❌ রান ব্যর্থ: ${data.error_message || data.status}`, 'error');
    }

    await loadWorkflowsStudio(wf.id);
    wfState.activeRun = data;
    renderWorkflowCanvas();
    renderRunOutputPanel();
    switchWfInspectorTab('run');
  } catch (err) {
    wfToast('রান ব্যর্থ: ' + err.message, 'error');
    wfState.liveProgress = null;
    wfState.isRunningUI = false;
    renderWorkflowCanvas();
  } finally {
    clearInterval(pollTimer);
    wfState.isRunningUI = false;
    renderWorkflowToolbar();
  }
}

async function stopActiveWorkflow() {
  const wf = wfState.activeWorkflow;
  if (!wf) return;
  try {
    const res = await wfFetch(`/api/workflows/${encodeURIComponent(wf.id)}/stop`, { method: 'POST' });
    const data = await res.json();
    wfToast(data.stopped ? '🛑 ওয়ার্কফ্লো থামানোর সিগন্যাল পাঠানো হয়েছে...' : 'ওয়ার্কফ্লো এখন চলছে না।', 'warning');
  } catch (err) {
    wfToast('Stop ত্রুটি: ' + err.message, 'error');
  }
}

async function deleteActiveWorkflow() {
  const wf = wfState.activeWorkflow;
  if (!wf) return;
  if (!confirm(`আপনি কি "${wf.name}" ওয়ার্কফ্লোটি স্থায়ীভাবে মুছে ফেলতে চান?`)) return;

  try {
    const res = await wfFetch(`/api/workflows/${encodeURIComponent(wf.id)}`, { method: 'DELETE' });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.detail || 'Delete failed');
    wfState.activeWorkflow = null;
    wfState.activeRun = null;
    wfState.selectedNodeId = null;
    wfToast('ওয়ার্কফ্লো মুছে ফেলা হয়েছে।', 'info');
    await loadWorkflowsStudio();
  } catch (err) {
    wfToast('ডিলিট ব্যর্থ: ' + err.message, 'error');
  }
}

function copyWorkflowWebhookUrl() {
  const wf = wfState.activeWorkflow;
  if (!wf) return;
  const url = `${window.location.origin}/api/workflows/webhook/${wf.id}${wf.webhook_secret ? `?secret=${wf.webhook_secret}` : ''}`;
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(url);
  }
  wfToast(`🔗 Webhook URL কপি হয়েছে!\n${url}`, 'success');
}

// ------------------------------------------------------------------------------
// Visual Canvas Rendering, Live Animation, Dragging & SVG Connectors
// ------------------------------------------------------------------------------
function getNodeSummaryLine(node) {
  const c = node.config || {};
  if (node.disabled || c.disabled) return '⏸️ Muted / Bypassed (skips execution)';
  switch (node.type) {
    case 'trigger_daily':
      return `${c.frequency || 'daily'} @ ${c.daily_time || '09:00'} (${c.timezone || 'Asia/Dhaka'})`;
    case 'trigger_webhook':
      return `${c.method || 'POST'} /webhook/${wfState.activeWorkflow ? wfState.activeWorkflow.id : '...'}`;
    case 'ai_agent':
      return `${c.model || 'Default AI'} • ${(c.prompt || '').slice(0, 42)}...`;
    case 'subagent':
      return `Agent: ${c.agent_id || 'swarm'}`;
    case 'tool_call':
      return `Tool: ${c.tool_name || 'system_info'}`;
    case 'python_transform':
      return `Python: ${(c.code || '').split('\n').slice(0, 2).join(' ')}`;
    case 'loop_foreach': {
      const cnt = (c.items_text || '').split(/[\r\n,]+/).filter(x => x.trim()).length;
      return `${c.action_type || 'ping'} loop • ${cnt} items`;
    }
    case 'delay_wait':
      return `Pause ${c.seconds || 3}s before next node`;
    case 'condition':
      return `IF ${c.target || 'prev'} ${c.operator || 'contains'} "${c.value || ''}"`;
    case 'http_request':
      return `${c.method || 'POST'} ${c.url || ''}`;
    case 'save_report':
      return `Report: ${c.title || 'Summary'}`;
    case 'memory_save':
      return `Project: ${c.project_name || 'myagent'} / ${c.key || 'note'}`;
    case 'notify_channel':
      return `To: ${c.target || 'chat_and_channels'}`;
    case 'merge_combine':
      return `Join all branches (${c.mode || 'markdown'})`;
    case 'switch_router':
      return `R1: ${c.route1_val || '-'} | R2: ${c.route2_val || '-'}`;
    case 'sub_workflow':
      return `Call WF: ${c.target_workflow_id || '(select)'}`;
    case 'knowledge_db_query':
      return c.query_mode === 'rag' ? `RAG: ${c.rag_query || ''}` : `SQL (${c.db_name || 'ops.db'}): ${(c.sql_query || '').slice(0, 32)}`;
    default:
      return node.type;
  }
}

function renderWorkflowCanvas() {
  const nodesLayer = document.getElementById('wf-nodes-layer');
  const svgLayer = document.getElementById('wf-edges-svg');
  const stage = document.getElementById('wf-canvas-stage');
  if (!nodesLayer || !svgLayer) return;

  const wf = wfState.activeWorkflow;
  if (!wf) {
    nodesLayer.innerHTML = '<div class="wf-canvas-empty">কোনো ওয়ার্কফ্লো সিলেক্ট করা হয়নি।</div>';
    svgLayer.innerHTML = '';
    return;
  }

  const nodes = wf.nodes || [];
  let maxX = 1200, maxY = 540;
  nodes.forEach(n => {
    maxX = Math.max(maxX, (Number(n.x) || 0) + 320);
    maxY = Math.max(maxY, (Number(n.y) || 0) + 220);
  });
  if (stage) {
    stage.style.width = `${maxX}px`;
    stage.style.height = `${maxY}px`;
    stage.style.transform = `scale(${wfState.zoom || 1})`;
    stage.style.transformOrigin = 'top left';
  }

  const runMap = {};
  const sourceRun = wfState.liveProgress || wfState.activeRun;
  if (sourceRun && Array.isArray(sourceRun.node_results)) {
    sourceRun.node_results.forEach(r => { if (r && r.node_id) runMap[r.node_id] = r; });
  }
  const activeWaveSet = new Set(
    (wfState.liveProgress && Array.isArray(wfState.liveProgress.active_node_ids) && wfState.liveProgress.active_node_ids.length)
      ? wfState.liveProgress.active_node_ids
      : (wfState.liveProgress && wfState.liveProgress.current_node_id ? [wfState.liveProgress.current_node_id] : [])
  );

  nodesLayer.innerHTML = nodes.map(node => {
    const meta = wfNodeMeta(node.type);
    const isSelected = wfState.selectedNodeId === node.id;
    const isCond = node.type === 'condition';
    const isSwitch = node.type === 'switch_router';
    const isTrig = (node.type || '').startsWith('trigger_');
    const isDisabled = !!(node.disabled || node.config?.disabled);
    const isPinned = !!(node.config?.use_pinned && node.config?.pinned_output);
    const isLiveRunning = activeWaveSet.has(node.id);
    const nr = runMap[node.id];

    let runStatusCls = nr ? `wf-status-${(nr.status || '').toLowerCase()}` : '';
    if (isLiveRunning) runStatusCls = 'wf-status-running';
    if (isDisabled) runStatusCls += ' wf-node-disabled';
    if (isPinned) runStatusCls += ' wf-node-pinned';

    const statusBadge = isLiveRunning
      ? `<span class="wf-node-run-badge running">RUNNING...</span>`
      : isPinned
        ? `<span class="wf-node-run-badge pinned">📌 PINNED</span>`
        : nr
          ? `<span class="wf-node-run-badge ${(nr.status || '').toLowerCase()}">${wfEsc(nr.status)} ${nr.duration_ms || 0}ms</span>`
          : `<span class="wf-node-id-badge wf-var-copy" onclick="copyNodeVarRef(event, '${wfEsc(node.id)}')" title="ক্লিক করে {{nodes.${wfEsc(node.id)}.output}} কপি করুন">${wfEsc(node.id)} 📋</span>`;

    const portsOutHtml = isCond
      ? `
        <div class="wf-port-out wf-port-true" data-node="${wfEsc(node.id)}" data-cond="true"
             onclick="onOutputPortClick(event, '${wfEsc(node.id)}', 'true')" title="TRUE শাখা কানেক্ট করুন">T</div>
        <div class="wf-port-out wf-port-false" data-node="${wfEsc(node.id)}" data-cond="false"
             onclick="onOutputPortClick(event, '${wfEsc(node.id)}', 'false')" title="FALSE শাখা কানেক্ট করুন">F</div>
      `
      : isSwitch
        ? `
          <div class="wf-port-out wf-port-r1" data-node="${wfEsc(node.id)}" data-cond="route_1"
               onclick="onOutputPortClick(event, '${wfEsc(node.id)}', 'route_1')" title="Route 1 কানেক্ট করুন">R1</div>
          <div class="wf-port-out wf-port-r2" data-node="${wfEsc(node.id)}" data-cond="route_2"
               onclick="onOutputPortClick(event, '${wfEsc(node.id)}', 'route_2')" title="Route 2 কানেক্ট করুন">R2</div>
          <div class="wf-port-out wf-port-def" data-node="${wfEsc(node.id)}" data-cond="default"
               onclick="onOutputPortClick(event, '${wfEsc(node.id)}', 'default')" title="Default শাখা কানেক্ট করুন">D</div>
        `
        : `
          <div class="wf-port-out" data-node="${wfEsc(node.id)}" data-cond=""
               onclick="onOutputPortClick(event, '${wfEsc(node.id)}', '')" title="পরবর্তী নোডের ইনপুট পোর্টে সংযুক্ত করুন"></div>
        `;

    const portInHtml = isTrig
      ? ''
      : `<div class="wf-port-in ${wfState.connectingFrom ? 'wf-port-target-hint' : ''}"
              data-node="${wfEsc(node.id)}"
              onclick="onInputPortClick(event, '${wfEsc(node.id)}')"
              title="এখানে সংযুক্ত করুন"></div>`;

    return `
      <div class="wf-node-card ${isSelected ? 'selected' : ''} ${runStatusCls}"
           id="wf-card-${wfEsc(node.id)}"
           style="left:${Number(node.x || 50)}px; top:${Number(node.y || 120)}px; --node-accent:${meta.color};"
           onmousedown="onNodeMouseDown(event, '${wfEsc(node.id)}')"
           onclick="onNodeCardClick(event, '${wfEsc(node.id)}')">
        ${portInHtml}
        <div class="wf-node-header">
          <div class="wf-node-head-left">
            <span class="wf-node-icon">${wfEsc(meta.icon)}</span>
            <span class="wf-node-title">${wfEsc(node.title || meta.label_bn)}</span>
          </div>
          <div class="wf-node-head-actions">
            ${!isTrig ? `<button type="button" class="wf-node-mini-btn" onclick="toggleNodeDisabled(event, '${wfEsc(node.id)}')" title="${isDisabled ? 'সক্রিয় করুন' : 'মিউট/বাইপাস করুন'}">${isDisabled ? '▶️' : '⏸️'}</button>` : ''}
            <button type="button" class="wf-node-mini-btn" onclick="duplicateNodeById(event, '${wfEsc(node.id)}')" title="নোড ডুপ্লিকেট">❐</button>
            <button type="button" class="wf-node-del-btn" onclick="deleteNodeById(event, '${wfEsc(node.id)}')" title="নোড মুছুন">&times;</button>
          </div>
        </div>
        <div class="wf-node-body">
          <div class="wf-node-summary">${wfEsc(getNodeSummaryLine(node))}</div>
          <div class="wf-node-footer">
            <span class="wf-node-type-pill">${wfEsc(meta.label_en || node.type)}</span>
            ${statusBadge}
          </div>
        </div>
        ${portsOutHtml}
      </div>
    `;
  }).join('');

  drawWorkflowEdges();
}

function drawWorkflowEdges() {
  const svg = document.getElementById('wf-edges-svg');
  const stage = document.getElementById('wf-canvas-stage');
  if (!svg || !stage || !wfState.activeWorkflow) return;

  const nodes = wfState.activeWorkflow.nodes || [];
  const edges = wfState.activeWorkflow.edges || [];
  const nodeMap = {};
  nodes.forEach(n => { nodeMap[n.id] = n; });
  const isFlowActive = !!wfState.liveProgress;

  const defs = `
    <defs>
      <marker id="wf-arrow-cyan" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
        <path d="M0,1 L7,4 L0,7 Z" fill="#38bdf8"></path>
      </marker>
      <marker id="wf-arrow-true" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
        <path d="M0,1 L7,4 L0,7 Z" fill="#10b981"></path>
      </marker>
      <marker id="wf-arrow-false" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
        <path d="M0,1 L7,4 L0,7 Z" fill="#f59e0b"></path>
      </marker>
      <marker id="wf-arrow-r2" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
        <path d="M0,1 L7,4 L0,7 Z" fill="#a855f7"></path>
      </marker>
    </defs>
  `;

  const paths = edges.map(edge => {
    const srcEl = document.getElementById(`wf-card-${edge.source}`);
    const tgtEl = document.getElementById(`wf-card-${edge.target}`);
    const srcNode = nodeMap[edge.source];
    const tgtNode = nodeMap[edge.target];
    if (!srcNode || !tgtNode) return '';

    const w = srcEl ? srcEl.offsetWidth : 235;
    const h = srcEl ? srcEl.offsetHeight : 98;
    const th = tgtEl ? tgtEl.offsetHeight : 98;

    const cond = (edge.condition || '').toLowerCase();
    let sy = Number(srcNode.y || 0) + h / 2;
    if (srcNode.type === 'condition') {
      sy = Number(srcNode.y || 0) + (cond === 'false' ? h * 0.72 : h * 0.32);
    } else if (srcNode.type === 'switch_router') {
      sy = Number(srcNode.y || 0) + (cond === 'route_1' ? h * 0.24 : cond === 'route_2' ? h * 0.52 : h * 0.80);
    }
    const sx = Number(srcNode.x || 0) + w;
    const tx = Number(tgtNode.x || 0);
    const ty = Number(tgtNode.y || 0) + th / 2;

    const dx = Math.max(55, Math.abs(tx - sx) * 0.48);
    const d = `M ${sx} ${sy} C ${sx + dx} ${sy}, ${tx - dx} ${ty}, ${tx} ${ty}`;

    const color = (cond === 'true' || cond === 'route_1')
      ? '#10b981'
      : cond === 'route_2'
        ? '#a855f7'
        : (cond === 'false' || cond === 'default')
          ? '#f59e0b'
          : '#38bdf8';
    const marker = (cond === 'true' || cond === 'route_1')
      ? 'url(#wf-arrow-true)'
      : cond === 'route_2'
        ? 'url(#wf-arrow-r2)'
        : (cond === 'false' || cond === 'default')
          ? 'url(#wf-arrow-false)'
          : 'url(#wf-arrow-cyan)';

    const mx = (sx + tx) / 2;
    const my = (sy + ty) / 2;
    const badgeLabel = cond ? cond.replace('route_', 'R').toUpperCase() : '✕';

    return `
      <g class="wf-edge-group" onclick="removeEdgeById('${wfEsc(edge.id)}')" title="সংযোগ মুছে ফেলতে ক্লিক করুন">
        <path class="wf-edge-hit" d="${d}" fill="none" stroke="transparent" stroke-width="16"></path>
        <path class="wf-edge-path ${isFlowActive ? 'wf-edge-animated' : ''}" d="${d}" fill="none" stroke="${color}" stroke-width="2.4" marker-end="${marker}"></path>
        <g class="wf-edge-label" transform="translate(${mx}, ${my})">
          <rect x="-18" y="-10" width="36" height="20" rx="10" fill="#0f172a" stroke="${color}" stroke-width="1.4"></rect>
          <text x="0" y="4" text-anchor="middle" fill="${color}" font-size="9.5" font-weight="700" font-family="Fira Code, monospace">${wfEsc(badgeLabel)}</text>
        </g>
      </g>
    `;
  }).join('');

  let tempWire = '';
  if (wfState.connectingFrom && nodeMap[wfState.connectingFrom.nodeId]) {
    const srcNode = nodeMap[wfState.connectingFrom.nodeId];
    const srcEl = document.getElementById(`wf-card-${srcNode.id}`);
    const w = srcEl ? srcEl.offsetWidth : 235;
    const h = srcEl ? srcEl.offsetHeight : 98;
    const sx = Number(srcNode.x || 0) + w;
    let sy = Number(srcNode.y || 0) + h / 2;
    if (srcNode.type === 'condition') {
      sy = Number(srcNode.y || 0) + (wfState.connectingFrom.condition === 'false' ? h * 0.72 : h * 0.32);
    }
    const tx = wfState.mouseCanvasX || (sx + 80);
    const ty = wfState.mouseCanvasY || sy;
    tempWire = `<path d="M ${sx} ${sy} L ${tx} ${ty}" stroke="#38bdf8" stroke-width="2" stroke-dasharray="5,5" fill="none"></path>`;
  }

  svg.setAttribute('width', stage.offsetWidth || 1400);
  svg.setAttribute('height', stage.offsetHeight || 600);
  svg.innerHTML = defs + paths + tempWire;
}

// Dragging & Port Wiring with Zoom scaling
function onNodeMouseDown(event, nodeId) {
  if (
    event.target.closest('.wf-port-out') ||
    event.target.closest('.wf-port-in') ||
    event.target.closest('.wf-node-del-btn') ||
    event.target.closest('.wf-node-mini-btn') ||
    event.target.closest('.wf-var-copy')
  ) {
    return;
  }
  event.stopPropagation();
  const wf = wfState.activeWorkflow;
  const stage = document.getElementById('wf-canvas-stage');
  const node = wf ? (wf.nodes || []).find(n => n.id === nodeId) : null;
  if (!node || !stage) return;

  const zoom = wfState.zoom || 1.0;
  const stageRect = stage.getBoundingClientRect();
  wfState.draggingNodeId = nodeId;
  wfState.dragOffsetX = (event.clientX - stageRect.left) / zoom - Number(node.x || 0);
  wfState.dragOffsetY = (event.clientY - stageRect.top) / zoom - Number(node.y || 0);
}

document.addEventListener('mousemove', (event) => {
  const stage = document.getElementById('wf-canvas-stage');
  if (!stage) return;
  const zoom = wfState.zoom || 1.0;

  if (wfState.draggingNodeId && wfState.activeWorkflow) {
    const node = (wfState.activeWorkflow.nodes || []).find(n => n.id === wfState.draggingNodeId);
    if (!node) return;
    const stageRect = stage.getBoundingClientRect();
    const nx = Math.max(12, Math.round((event.clientX - stageRect.left) / zoom - wfState.dragOffsetX));
    const ny = Math.max(12, Math.round((event.clientY - stageRect.top) / zoom - wfState.dragOffsetY));
    node.x = nx;
    node.y = ny;

    const card = document.getElementById(`wf-card-${node.id}`);
    if (card) {
      card.style.left = `${nx}px`;
      card.style.top = `${ny}px`;
    }
    markWfDirty();
    drawWorkflowEdges();
  } else if (wfState.connectingFrom) {
    const stageRect = stage.getBoundingClientRect();
    wfState.mouseCanvasX = (event.clientX - stageRect.left) / zoom;
    wfState.mouseCanvasY = (event.clientY - stageRect.top) / zoom;
    drawWorkflowEdges();
  }
});

document.addEventListener('mouseup', () => {
  if (wfState.draggingNodeId) wfState.draggingNodeId = null;
});

document.addEventListener('keydown', (e) => {
  const viewWf = document.getElementById('view-workflows');
  if (!viewWf || !viewWf.classList.contains('active')) return;

  if (e.key === 'Escape' && wfState.connectingFrom) {
    wfState.connectingFrom = null;
    renderWorkflowCanvas();
    return;
  }

  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
    e.preventDefault();
    saveActiveWorkflow();
    return;
  }

  const tag = (document.activeElement?.tagName || '').toLowerCase();
  if ((e.key === 'Delete' || e.key === 'Backspace') && !['input', 'textarea', 'select'].includes(tag)) {
    if (wfState.selectedNodeId) {
      deleteNodeById(null, wfState.selectedNodeId);
    }
  }
});

function onNodeCardClick(event, nodeId) {
  event.stopPropagation();
  if (wfState.connectingFrom) {
    if (wfState.connectingFrom.nodeId !== nodeId) {
      connectNodes(wfState.connectingFrom.nodeId, nodeId, wfState.connectingFrom.condition);
    }
    wfState.connectingFrom = null;
    drawWorkflowEdges();
    return;
  }

  wfState.selectedNodeId = nodeId;
  document.querySelectorAll('.wf-node-card').forEach(el => el.classList.remove('selected'));
  const card = document.getElementById(`wf-card-${nodeId}`);
  if (card) card.classList.add('selected');
  renderNodeInspector();
  switchWfInspectorTab('node');
}

function onOutputPortClick(event, nodeId, condition = '') {
  event.stopPropagation();
  wfState.connectingFrom = { nodeId, condition };
  wfToast('এখন লক্ষ্য নোডের বাম ইনপুট পোর্টে (●) ক্লিক করুন (Esc চাপলে বাতিল)।', 'info');
  renderWorkflowCanvas();
}

function onInputPortClick(event, targetNodeId) {
  event.stopPropagation();
  if (!wfState.connectingFrom) return;
  const { nodeId, condition } = wfState.connectingFrom;
  if (nodeId === targetNodeId) {
    wfState.connectingFrom = null;
    drawWorkflowEdges();
    return;
  }
  connectNodes(nodeId, targetNodeId, condition);
  wfState.connectingFrom = null;
  renderWorkflowCanvas();
  renderNodeInspector();
}

function onCanvasBackgroundClick() {
  if (wfState.connectingFrom) {
    wfState.connectingFrom = null;
    renderWorkflowCanvas();
  }
}

function connectNodes(sourceId, targetId, condition = '') {
  const wf = wfState.activeWorkflow;
  if (!wf) return;
  wf.edges = wf.edges || [];
  const exists = wf.edges.some(e => e.source === sourceId && e.target === targetId && (e.condition || '') === (condition || ''));
  if (!exists) {
    wf.edges.push({
      id: `e_${Date.now().toString(36)}_${Math.floor(Math.random() * 100)}`,
      source: sourceId,
      target: targetId,
      condition: condition || ''
    });
    markWfDirty();
    wfToast(`🔗 সংযোগ তৈরি হয়েছে (${sourceId} → ${targetId})`, 'success');
  }
  renderWorkflowCanvas();
  renderNodeInspector();
}

function removeEdgeById(edgeId) {
  const wf = wfState.activeWorkflow;
  if (!wf) return;
  wf.edges = (wf.edges || []).filter(e => e.id !== edgeId);
  markWfDirty();
  renderWorkflowCanvas();
  renderNodeInspector();
}

function deleteNodeById(event, nodeId) {
  if (event) event.stopPropagation();
  const wf = wfState.activeWorkflow;
  if (!wf) return;
  wf.nodes = (wf.nodes || []).filter(n => n.id !== nodeId);
  wf.edges = (wf.edges || []).filter(e => e.source !== nodeId && e.target !== nodeId);
  if (wfState.selectedNodeId === nodeId) {
    wfState.selectedNodeId = wf.nodes[0] ? wf.nodes[0].id : null;
  }
  markWfDirty();
  renderWorkflowCanvas();
  renderNodeInspector();
}

// ------------------------------------------------------------------------------
// Node Inspector (Including Python, ForEach, Delay & Retry/Error Policies)
// ------------------------------------------------------------------------------
function renderNodeInspector() {
  const el = document.getElementById('wf-inspector-node');
  if (!el) return;

  const wf = wfState.activeWorkflow;
  const node = wf ? (wf.nodes || []).find(n => n.id === wfState.selectedNodeId) : null;
  if (!wf || !node) {
    el.innerHTML = '<div class="wf-empty-hint">ক্যানভাস থেকে যেকোনো একটি নোডে ক্লিক করে সেটিংস দেখুন।</div>';
    return;
  }

  const meta = wfNodeMeta(node.type);
  const c = node.config || {};
  const isTrig = (node.type || '').startsWith('trigger_');
  const varsListChips = (wfState.variables || []).map(v => `{{vars.${v.key}}}`);
  const varsHtml = `
    <div class="wf-var-chips">
      <span style="font-size:0.7rem; color:var(--text-muted);">ভেরিয়েবল:</span>
      ${['{{prev.output}}', '{{prev.output|500}}', '{{trigger.date}}', '{{trigger.payload}}', ...varsListChips]
        .map(v => `<button type="button" class="wf-var-chip" onclick="insertTemplateVar('${wfEsc(v)}')">${wfEsc(v)}</button>`).join('')}
    </div>
  `;

  let fieldsHtml = '';
  if (node.type === 'trigger_daily') {
    fieldsHtml = `
      <div class="wf-field-group">
        <label>ফ্রিকোয়েন্সি (Frequency)</label>
        <select class="text-input" onchange="updateNodeCfg('frequency', this.value)">
          <option value="daily" ${c.frequency === 'daily' ? 'selected' : ''}>প্রতিদিন (Daily)</option>
          <option value="hourly" ${c.frequency === 'hourly' ? 'selected' : ''}>প্রতি ঘণ্টায় (Hourly)</option>
          <option value="every_6h" ${c.frequency === 'every_6h' ? 'selected' : ''}>প্রতি ৬ ঘণ্টায় (Every 6h)</option>
          <option value="weekly" ${c.frequency === 'weekly' ? 'selected' : ''}>সাপ্তাহিক (Weekly)</option>
          <option value="every_15m" ${c.frequency === 'every_15m' ? 'selected' : ''}>প্রতি ১৫ মিনিটে (Every 15m)</option>
        </select>
      </div>
      <div class="wf-field-row">
        <div class="wf-field-group">
          <label>সময় (HH:MM)</label>
          <input type="time" class="text-input" value="${wfEsc(c.daily_time || '09:00')}" onchange="updateNodeCfg('daily_time', this.value)">
        </div>
        <div class="wf-field-group">
          <label>টাইমজোন</label>
          <input type="text" class="text-input" value="${wfEsc(c.timezone || 'Asia/Dhaka')}" onchange="updateNodeCfg('timezone', this.value)">
        </div>
      </div>
    `;
  } else if (node.type === 'trigger_webhook') {
    const whUrl = `${window.location.origin}/api/workflows/webhook/${wf.id}?secret=${wf.webhook_secret || ''}`;
    fieldsHtml = `
      <div class="wf-field-group">
        <label>Webhook POST Endpoint</label>
        <input type="text" class="text-input" readonly value="${wfEsc(whUrl)}" style="font-family:'Fira Code', monospace; font-size:0.75rem;">
      </div>
    `;
  } else if (node.type === 'ai_agent') {
    const modelOpts = (wfState.models || []).map(m =>
      `<option value="${wfEsc(m.id)}" ${(c.model || '') === m.id ? 'selected' : ''}>${wfEsc(m.label || m.id)}</option>`
    ).join('');
    fieldsHtml = `
      <div class="wf-field-group">
        <label>AI মডেল নির্বাচন</label>
        <select class="text-input" onchange="updateNodeCfg('model', this.value)">${modelOpts}</select>
      </div>
      <div class="wf-field-group">
        <label>টাস্ক প্রম্পট (Task Prompt)</label>
        <textarea id="wf-cfg-prompt" class="text-input wf-code-textarea" rows="4"
                  onfocus="wfState.lastFocusedFieldId='wf-cfg-prompt'"
                  onchange="updateNodeCfg('prompt', this.value)">${wfEsc(c.prompt || '')}</textarea>
        ${varsHtml}
      </div>
      <div class="wf-field-group">
        <label>সিস্টেম নির্দেশনা</label>
        <textarea id="wf-cfg-sys" class="text-input" rows="2"
                  onfocus="wfState.lastFocusedFieldId='wf-cfg-sys'"
                  onchange="updateNodeCfg('system_instruction', this.value)">${wfEsc(c.system_instruction || '')}</textarea>
      </div>
      <div class="wf-field-row">
        <div class="wf-field-group">
          <label>প্রজেক্ট মেমোরি স্কোপ</label>
          <input type="text" class="text-input" value="${wfEsc(c.project_name || '')}" placeholder="e.g. myagent" onchange="updateNodeCfg('project_name', this.value)">
        </div>
        <div class="wf-field-group">
          <label>Max Tool Turns</label>
          <input type="number" min="1" max="10" class="text-input" value="${Number(c.max_turns || 5)}" onchange="updateNodeCfg('max_turns', parseInt(this.value || 5, 10))">
        </div>
      </div>
      <div class="wf-check-row">
        <label><input type="checkbox" ${c.enable_tools !== false ? 'checked' : ''} onchange="updateNodeCfg('enable_tools', this.checked)"> 🛠️ Tools</label>
        <label><input type="checkbox" ${c.use_memory !== false ? 'checked' : ''} onchange="updateNodeCfg('use_memory', this.checked)"> 🧠 RAG Memory</label>
        <label title="যদি লোকাল LLM সার্ভার অফলাইন থাকে তবে আপস্ট্রিম টেলিমেট্রি দিয়ে ডাইজেস্ট তৈরি করবে"><input type="checkbox" ${c.fallback_on_error ? 'checked' : ''} onchange="updateNodeCfg('fallback_on_error', this.checked)"> 🛡️ Offline Digest Fallback</label>
      </div>
    `;
  } else if (node.type === 'subagent') {
    const subOpts = (wfState.subagents || []).map(s =>
      `<option value="${wfEsc(s.id)}" ${(c.agent_id || 'net_ping_subagent') === s.id ? 'selected' : ''}>${wfEsc(s.name)}</option>`
    ).join('');
    fieldsHtml = `
      <div class="wf-field-group">
        <label>টার্গেট সাব-এজেন্ট / সোয়ার্ম</label>
        <select class="text-input" onchange="updateNodeCfg('agent_id', this.value)">${subOpts}</select>
      </div>
      <div class="wf-field-group">
        <label>টাস্ক নির্দেশনা</label>
        <textarea id="wf-cfg-subtask" class="text-input" rows="3"
                  onfocus="wfState.lastFocusedFieldId='wf-cfg-subtask'"
                  onchange="updateNodeCfg('task', this.value)">${wfEsc(c.task || '')}</textarea>
        ${varsHtml}
      </div>
    `;
  } else if (node.type === 'tool_call') {
    const toolOpts = (wfState.tools || []).map(t =>
      `<option value="${wfEsc(t.name)}" ${(c.tool_name || 'system_info') === t.name ? 'selected' : ''}>${wfEsc(t.name)}</option>`
    ).join('');
    fieldsHtml = `
      <div class="wf-field-group">
        <label>টুল নির্বাচন (Agent Tool)</label>
        <select class="text-input" onchange="updateNodeCfg('tool_name', this.value)">${toolOpts}</select>
      </div>
      <div class="wf-field-group">
        <label>আর্গুমেন্ট JSON</label>
        <textarea id="wf-cfg-args" class="text-input wf-code-textarea" rows="3"
                  onfocus="wfState.lastFocusedFieldId='wf-cfg-args'"
                  onchange="updateNodeCfg('args_json', this.value)">${wfEsc(typeof c.args_json === 'string' ? c.args_json : JSON.stringify(c.args_json || {}, null, 2))}</textarea>
      </div>
    `;
  } else if (node.type === 'python_transform') {
    fieldsHtml = `
      <div class="wf-field-group">
        <label>🐍 Python Transform Code (<code>prev_output</code>, <code>nodes_data</code>, <code>trigger</code> ইনজেক্টেড)</label>
        <textarea id="wf-cfg-pycode" class="text-input wf-code-textarea" rows="6"
                  onchange="updateNodeCfg('code', this.value)">${wfEsc(c.code || '')}</textarea>
      </div>
    `;
  } else if (node.type === 'loop_foreach') {
    const toolOpts = (wfState.tools || []).map(t =>
      `<option value="${wfEsc(t.name)}" ${(c.tool_name || 'network_port_scan') === t.name ? 'selected' : ''}>${wfEsc(t.name)}</option>`
    ).join('');
    fieldsHtml = `
      <div class="wf-field-group">
        <label>আইটেম তালিকা (প্রতি লাইনে বা কমা দিয়ে, সর্বোচ্চ ২৫টি)</label>
        <textarea class="text-input wf-code-textarea" rows="3" onchange="updateNodeCfg('items_text', this.value)">${wfEsc(c.items_text || '')}</textarea>
      </div>
      <div class="wf-field-group">
        <label>ব্যাচ অ্যাকশন ধরন</label>
        <select class="text-input" onchange="updateNodeCfg('action_type', this.value); renderNodeInspector();">
          <option value="ping" ${(c.action_type || 'ping') === 'ping' ? 'selected' : ''}>🌐 ICMP / TCP Server Ping</option>
          <option value="tool" ${c.action_type === 'tool' ? 'selected' : ''}>🛠️ Run Agent Tool per Item</option>
          <option value="http" ${c.action_type === 'http' ? 'selected' : ''}>📡 HTTP Request per Item</option>
        </select>
      </div>
      ${(c.action_type === 'tool') ? `
        <div class="wf-field-group">
          <label>Tool Name</label>
          <select class="text-input" onchange="updateNodeCfg('tool_name', this.value)">${toolOpts}</select>
        </div>
        <div class="wf-field-group">
          <label>Args Template JSON (<code>{{item}}</code>)</label>
          <input type="text" class="text-input wf-code-textarea" value="${wfEsc(c.args_template_json || '{\"target\": \"{{item}}\"}')}" onchange="updateNodeCfg('args_template_json', this.value)">
        </div>
      ` : (c.action_type === 'http') ? `
        <div class="wf-field-group">
          <label>URL Template (<code>{{item}}</code>)</label>
          <input type="text" class="text-input" value="${wfEsc(c.http_url || '')}" onchange="updateNodeCfg('http_url', this.value)">
        </div>
      ` : ''}
    `;
  } else if (node.type === 'delay_wait') {
    fieldsHtml = `
      <div class="wf-field-group">
        <label>অপেক্ষার সময় (সেকেন্ড, ১ - ৬০)</label>
        <input type="number" min="0.5" max="60" step="0.5" class="text-input" value="${Number(c.seconds || 3)}" onchange="updateNodeCfg('seconds', parseFloat(this.value || 3))">
      </div>
    `;
  } else if (node.type === 'condition') {
    fieldsHtml = `
      <div class="wf-field-group">
        <label>টার্গেট ডেটা</label>
        <input id="wf-cfg-target" type="text" class="text-input" value="${wfEsc(c.target || '{{prev.output}}')}"
               onfocus="wfState.lastFocusedFieldId='wf-cfg-target'"
               onchange="updateNodeCfg('target', this.value)">
      </div>
      <div class="wf-field-row">
        <div class="wf-field-group">
          <label>অপারেটর</label>
          <select class="text-input" onchange="updateNodeCfg('operator', this.value)">
            <option value="contains" ${c.operator === 'contains' ? 'selected' : ''}>Contains</option>
            <option value="not_contains" ${c.operator === 'not_contains' ? 'selected' : ''}>Not Contains</option>
            <option value="equals" ${c.operator === 'equals' ? 'selected' : ''}>Equals</option>
            <option value="not_empty" ${c.operator === 'not_empty' ? 'selected' : ''}>Not Empty</option>
            <option value="regex" ${c.operator === 'regex' ? 'selected' : ''}>Regex Match</option>
            <option value="greater_than" ${c.operator === 'greater_than' ? 'selected' : ''}>Number &gt;</option>
            <option value="less_than" ${c.operator === 'less_than' ? 'selected' : ''}>Number &lt;</option>
          </select>
        </div>
        <div class="wf-field-group">
          <label>তুলনীয় মান</label>
          <input type="text" class="text-input" value="${wfEsc(c.value || '')}" onchange="updateNodeCfg('value', this.value)">
        </div>
      </div>
    `;
  } else if (node.type === 'http_request') {
    fieldsHtml = `
      <div class="wf-field-row">
        <div class="wf-field-group">
          <label>Method</label>
          <select class="text-input" onchange="updateNodeCfg('method', this.value)">
            ${['GET', 'POST', 'PUT', 'PATCH', 'DELETE'].map(m => `<option value="${m}" ${(c.method || 'POST') === m ? 'selected' : ''}>${m}</option>`).join('')}
          </select>
        </div>
        <div class="wf-field-group">
          <label>URL</label>
          <input type="text" class="text-input" value="${wfEsc(c.url || '')}" onchange="updateNodeCfg('url', this.value)">
        </div>
      </div>
      <div class="wf-field-group">
        <label>Body JSON</label>
        <textarea id="wf-cfg-httpbody" class="text-input wf-code-textarea" rows="3"
                  onfocus="wfState.lastFocusedFieldId='wf-cfg-httpbody'"
                  onchange="updateNodeCfg('body_json', this.value)">${wfEsc(c.body_json || '{}')}</textarea>
        ${varsHtml}
      </div>
    `;
  } else if (node.type === 'save_report') {
    fieldsHtml = `
      <div class="wf-field-group">
        <label>রিপোর্টের শিরোনাম</label>
        <input type="text" class="text-input" value="${wfEsc(c.title || '')}" onchange="updateNodeCfg('title', this.value)">
      </div>
      <div class="wf-field-group">
        <label>রিপোর্ট কনটেন্ট</label>
        <textarea id="wf-cfg-rpt" class="text-input" rows="3"
                  onfocus="wfState.lastFocusedFieldId='wf-cfg-rpt'"
                  onchange="updateNodeCfg('content', this.value)">${wfEsc(c.content || '{{prev.output}}')}</textarea>
        ${varsHtml}
      </div>
    `;
  } else if (node.type === 'memory_save') {
    fieldsHtml = `
      <div class="wf-field-row">
        <div class="wf-field-group">
          <label>Project Name</label>
          <input type="text" class="text-input" value="${wfEsc(c.project_name || 'myagent')}" onchange="updateNodeCfg('project_name', this.value)">
        </div>
        <div class="wf-field-group">
          <label>Memory Key</label>
          <input type="text" class="text-input" value="${wfEsc(c.key || '')}" onchange="updateNodeCfg('key', this.value)">
        </div>
      </div>
      <div class="wf-field-group">
        <label>কনটেন্ট</label>
        <textarea id="wf-cfg-mem" class="text-input" rows="3"
                  onfocus="wfState.lastFocusedFieldId='wf-cfg-mem'"
                  onchange="updateNodeCfg('content', this.value)">${wfEsc(c.content || '{{prev.output}}')}</textarea>
        ${varsHtml}
      </div>
    `;
  } else if (node.type === 'notify_channel') {
    const tg = wfState.telegram || {};
    const tgOnline = !!tg.connected;
    const tgPillTxt = tgOnline
      ? `🟢 Connected (${wfEsc(tg.bot_username || 'Bot')}, Chat: ${wfEsc(tg.chat_id || 'Unset')})`
      : (tg.status === 'Error' ? `🟠 Error: ${wfEsc((tg.last_error || '').slice(0, 45))}` : '🔴 Telegram Connected নয়');
    fieldsHtml = `
      <div class="wf-tg-inline-card ${tgOnline ? 'connected' : 'disconnected'}">
        <div style="font-size:0.75rem; font-weight:600;">${tgPillTxt}</div>
        <button type="button" class="wf-chip-btn" onclick="switchWorkflowsSubTab('telegram')">✈️ Telegram কানেকশন ও লগ</button>
      </div>
      <div class="wf-field-group">
        <label>ডেলিভারি টার্গেট</label>
        <select class="text-input" onchange="updateNodeCfg('target', this.value)">
          <option value="chat_and_channels" ${c.target === 'chat_and_channels' ? 'selected' : ''}>💬 Chat Session + 📡 Telegram/Discord/Slack</option>
          <option value="telegram" ${c.target === 'telegram' ? 'selected' : ''}>✈️ শুধুমাত্র Telegram Bot-এ</option>
          <option value="chat_session" ${c.target === 'chat_session' ? 'selected' : ''}>💬 শুধুমাত্র Chat Session-এ</option>
          <option value="channels" ${c.target === 'channels' ? 'selected' : ''}>📡 শুধুমাত্র External Channels-এ</option>
        </select>
      </div>
      <div class="wf-field-group">
        <label>শিরোনাম</label>
        <input type="text" class="text-input" value="${wfEsc(c.title || '')}" onchange="updateNodeCfg('title', this.value)">
      </div>
      <div class="wf-field-group">
        <label>মেসেজ বডি</label>
        <textarea id="wf-cfg-msg" class="text-input" rows="3"
                  onfocus="wfState.lastFocusedFieldId='wf-cfg-msg'"
                  onchange="updateNodeCfg('message', this.value)">${wfEsc(c.message || '{{prev.output}}')}</textarea>
        ${varsHtml}
      </div>
      <div class="wf-field-group">
        <label>Telegram Chat ID Override (ঐচ্ছিক)</label>
        <input type="text" class="text-input" value="${wfEsc(c.telegram_chat_id || '')}" placeholder="খালি রাখলে ডিফল্ট কানেক্টেড Chat ID ব্যবহার হবে" onchange="updateNodeCfg('telegram_chat_id', this.value)">
      </div>
      <div class="wf-field-group">
        <label>Telegram Parse Mode</label>
        <select class="text-input" onchange="updateNodeCfg('parse_mode', this.value)">
          <option value="" ${!c.parse_mode ? 'selected' : ''}>Plain Text (সর্বদা নিরাপদ)</option>
          <option value="Markdown" ${c.parse_mode === 'Markdown' ? 'selected' : ''}>Markdown</option>
          <option value="HTML" ${c.parse_mode === 'HTML' ? 'selected' : ''}>HTML</option>
        </select>
      </div>
      <div class="wf-field-group">
        <label>কাস্টম Webhook URL</label>
        <input type="text" class="text-input" value="${wfEsc(c.custom_webhook_url || '')}" placeholder="https://..." onchange="updateNodeCfg('custom_webhook_url', this.value)">
      </div>
    `;
  } else if (node.type === 'merge_combine') {
    fieldsHtml = `
      <div class="wf-field-group">
        <label>ব্রাঞ্চ মার্জ ফরম্যাট (Merge Format)</label>
        <select class="text-input" onchange="updateNodeCfg('mode', this.value)">
          <option value="markdown_sections" ${(c.mode || 'markdown_sections') === 'markdown_sections' ? 'selected' : ''}>📝 Markdown Sections (সকল ব্রাঞ্চের সমন্বিত রিপোর্ট)</option>
          <option value="json_array" ${c.mode === 'json_array' ? 'selected' : ''}>🧩 JSON Array</option>
        </select>
      </div>
      <label style="font-size:0.78rem;"><input type="checkbox" ${c.include_empty ? 'checked' : ''} onchange="updateNodeCfg('include_empty', this.checked)"> খালি আউটপুটও অন্তর্ভুক্ত করুন</label>
    `;
  } else if (node.type === 'switch_router') {
    const opsList = [['regex', 'Regex'], ['contains', 'Contains'], ['not_contains', 'Not Contains'], ['equals', 'Equals'], ['greater_than', 'Number >']];
    fieldsHtml = `
      <div class="wf-field-group">
        <label>টার্গেট ডেটা</label>
        <input type="text" class="text-input" value="${wfEsc(c.target || '{{prev.output}}')}" onchange="updateNodeCfg('target', this.value)">
      </div>
      <div class="wf-field-row">
        <div class="wf-field-group">
          <label>Route 1 অপারেটর (R1)</label>
          <select class="text-input" onchange="updateNodeCfg('route1_op', this.value)">
            ${opsList.map(([k, l]) => `<option value="${k}" ${(c.route1_op || 'regex') === k ? 'selected' : ''}>${l}</option>`).join('')}
          </select>
        </div>
        <div class="wf-field-group">
          <label>Route 1 ম্যাচ ভ্যালু</label>
          <input type="text" class="text-input" value="${wfEsc(c.route1_val || '')}" onchange="updateNodeCfg('route1_val', this.value)">
        </div>
      </div>
      <div class="wf-field-row">
        <div class="wf-field-group">
          <label>Route 2 অপারেটর (R2)</label>
          <select class="text-input" onchange="updateNodeCfg('route2_op', this.value)">
            ${opsList.map(([k, l]) => `<option value="${k}" ${(c.route2_op || 'regex') === k ? 'selected' : ''}>${l}</option>`).join('')}
          </select>
        </div>
        <div class="wf-field-group">
          <label>Route 2 ম্যাচ ভ্যালু</label>
          <input type="text" class="text-input" value="${wfEsc(c.route2_val || '')}" onchange="updateNodeCfg('route2_val', this.value)">
        </div>
      </div>
    `;
  } else if (node.type === 'sub_workflow') {
    const otherWfs = (wfState.workflowsList || wfState.workflows || []).filter(w => w.id !== wf.id);
    fieldsHtml = `
      <div class="wf-field-group">
        <label>টার্গেট সাব-ওয়ার্কফ্লো নির্বাচন</label>
        <select class="text-input" onchange="updateNodeCfg('target_workflow_id', this.value)">
          <option value="">-- Select Target Workflow --</option>
          ${otherWfs.map(w => `<option value="${wfEsc(w.id)}" ${c.target_workflow_id === w.id ? 'selected' : ''}>${wfEsc(w.icon || '⚡')} ${wfEsc(w.name)}</option>`).join('')}
        </select>
      </div>
      <div class="wf-field-group">
        <label>ইনপুট JSON পেলোড (<code>{{trigger.payload}}</code>)</label>
        <textarea class="text-input wf-code-textarea" rows="3" onchange="updateNodeCfg('payload_json', this.value)">${wfEsc(typeof c.payload_json === 'string' ? c.payload_json : JSON.stringify(c.payload_json || {}, null, 2))}</textarea>
      </div>
    `;
  } else if (node.type === 'knowledge_db_query') {
    const dbs = ['ops.db', 'chat_history.db', 'reports.db', 'project_memory.db', 'security_audit.db'];
    fieldsHtml = `
      <div class="wf-field-group">
        <label>কোয়েরি মোড</label>
        <select class="text-input" onchange="updateNodeCfg('query_mode', this.value); renderNodeInspector();">
          <option value="sqlite" ${(c.query_mode || 'sqlite') === 'sqlite' ? 'selected' : ''}>🗄️ SQLite Read-Only Query</option>
          <option value="rag" ${c.query_mode === 'rag' ? 'selected' : ''}>🧠 Hybrid Vector RAG Search</option>
        </select>
      </div>
      ${(c.query_mode || 'sqlite') === 'rag' ? `
        <div class="wf-field-group">
          <label>RAG সার্চ কুয়েরি</label>
          <input type="text" class="text-input" value="${wfEsc(c.rag_query || '')}" onchange="updateNodeCfg('rag_query', this.value)">
        </div>
        <div class="wf-field-group">
          <label>Top K ফলাফল</label>
          <input type="number" min="1" max="12" class="text-input" value="${Number(c.top_k || 5)}" onchange="updateNodeCfg('top_k', parseInt(this.value || 5, 10))">
        </div>
      ` : `
        <div class="wf-field-group">
          <label>ডাটাবেস ফাইল</label>
          <select class="text-input" onchange="updateNodeCfg('db_name', this.value)">
            ${dbs.map(d => `<option value="${d}" ${(c.db_name || 'ops.db') === d ? 'selected' : ''}>${d}</option>`).join('')}
          </select>
        </div>
        <div class="wf-field-group">
          <label>Read-Only SQL (SELECT / PRAGMA)</label>
          <textarea class="text-input wf-code-textarea" rows="3" onchange="updateNodeCfg('sql_query', this.value)">${wfEsc(c.sql_query || 'SELECT name, last_status, run_count FROM ops_workflows LIMIT 10;')}</textarea>
        </div>
      `}
    `;
  }

  const otherNodes = (wf.nodes || []).filter(n => n.id !== node.id);
  const outgoingEdges = (wf.edges || []).filter(e => e.source === node.id);

  el.innerHTML = `
    <div class="wf-insp-head">
      <span style="font-size:1.25rem;">${wfEsc(meta.icon)}</span>
      <div style="flex:1;">
        <input type="text" class="text-input" style="font-weight:700; padding:6px 8px;" value="${wfEsc(node.title || meta.label_bn)}"
               onchange="updateSelectedNodeTitle(this.value)">
        <div style="font-size:0.7rem; color:var(--text-muted); margin-top:2px;">ID: <code>${wfEsc(node.id)}</code> • Type: ${wfEsc(node.type)}</div>
      </div>
    </div>

    ${fieldsHtml}

    ${!isTrig ? `
      <div class="wf-insp-box">
        <div style="font-size:0.76rem; font-weight:700; margin-bottom:6px; color:var(--text-secondary);">🛡️ নির্ভরযোগ্যতা ও এরর পলিসি (Resilience)</div>
        <div class="wf-field-row" style="align-items:center;">
          <div class="wf-field-group">
            <label>Auto Retries (0-3)</label>
            <input type="number" min="0" max="3" class="text-input" value="${Number(c.retry_count || 0)}" onchange="updateNodeCfg('retry_count', parseInt(this.value || 0, 10))">
          </div>
          <div style="display:flex; flex-direction:column; gap:4px; padding-top:14px; font-size:0.75rem;">
            <label><input type="checkbox" ${c.continue_on_fail ? 'checked' : ''} onchange="updateNodeCfg('continue_on_fail', this.checked)"> Continue on Fail</label>
            <label><input type="checkbox" ${(node.disabled || c.disabled) ? 'checked' : ''} onchange="toggleNodeDisabled(null, '${wfEsc(node.id)}')"> Mute / Bypass</label>
            <label><input type="checkbox" ${c.use_pinned ? 'checked' : ''} onchange="updateNodeCfg('use_pinned', this.checked)"> 📌 Use Pinned Data</label>
          </div>
        </div>
        ${c.use_pinned ? `
          <div class="wf-field-group" style="margin-top:6px;">
            <label>📌 Pinned Sample / Mock Output</label>
            <textarea class="text-input wf-code-textarea" rows="3" onchange="updateNodeCfg('pinned_output', this.value)">${wfEsc(c.pinned_output || '')}</textarea>
          </div>
        ` : ''}
      </div>
    ` : ''}

    <div class="wf-insp-box">
      <div style="font-size:0.78rem; font-weight:700; margin-bottom:6px; color:var(--text-secondary);">🔗 পরবর্তী নোডের সংযোগ (Connections)</div>
      <div style="display:flex; gap:6px; flex-wrap:wrap; margin-bottom:8px;">
        <select id="wf-quick-connect-tgt" class="text-input" style="flex:1; min-width:120px; padding:5px 8px;">
          ${otherNodes.map(n => `<option value="${wfEsc(n.id)}">${wfEsc(n.title || n.id)} (${wfEsc(n.id)})</option>`).join('')}
        </select>
        ${node.type === 'condition' ? `
          <select id="wf-quick-connect-cond" class="text-input" style="width:92px; padding:5px 6px;">
            <option value="true">TRUE ✓</option>
            <option value="false">FALSE ✕</option>
          </select>` : node.type === 'switch_router' ? `
          <select id="wf-quick-connect-cond" class="text-input" style="width:96px; padding:5px 6px;">
            <option value="route_1">Route 1</option>
            <option value="route_2">Route 2</option>
            <option value="default">Default</option>
          </select>` : ''}
        <button type="button" class="btn-sm-action-cyber" onclick="connectFromInspector()">+ যুক্ত করুন</button>
      </div>
      <div class="wf-edge-chips">
        ${outgoingEdges.length
          ? outgoingEdges.map(e => {
              const tNode = (wf.nodes || []).find(n => n.id === e.target);
              return `<span class="wf-edge-chip">${e.condition ? `[${e.condition.toUpperCase()}] ` : ''}→ ${wfEsc(tNode ? tNode.title : e.target)} <b onclick="removeEdgeById('${wfEsc(e.id)}')">×</b></span>`;
            }).join('')
          : '<span style="font-size:0.73rem; color:var(--text-muted);">কোনো আউটগোয়িং সংযোগ নেই।</span>'
        }
      </div>
    </div>

    <div class="wf-insp-box">
      <div style="font-size:0.78rem; font-weight:700; margin-bottom:6px; color:#38bdf8;">🧪 সিঙ্গেল-নোড লাইভ টেস্ট (Node Test)</div>
      <input type="text" id="wf-node-test-input" class="text-input" placeholder="ঐচ্ছিক টেস্ট ইনপুট ({{prev.output}})" style="margin-bottom:6px;">
      <button type="button" id="btn-wf-test-node" class="btn-sm-action-cyber" style="width:100%;" onclick="testSelectedNode()">⚡ এই নোডটি টেস্ট করুন</button>
      <pre id="wf-node-test-output" class="wf-node-test-pre" style="display:none;"></pre>
    </div>
  `;
}

function updateSelectedNodeTitle(val) {
  const wf = wfState.activeWorkflow;
  const node = wf ? (wf.nodes || []).find(n => n.id === wfState.selectedNodeId) : null;
  if (!node) return;
  node.title = val;
  markWfDirty();
  renderWorkflowCanvas();
}

function updateNodeCfg(key, val) {
  const wf = wfState.activeWorkflow;
  const node = wf ? (wf.nodes || []).find(n => n.id === wfState.selectedNodeId) : null;
  if (!node) return;
  node.config = node.config || {};
  node.config[key] = val;
  if (node.type === 'trigger_daily') {
    if (key === 'daily_time') wf.daily_time = val;
    if (key === 'timezone') wf.timezone = val;
  }
  markWfDirty();
  renderWorkflowCanvas();
  if (node.type === 'trigger_daily') {
    renderWorkflowToolbar();
    renderNextRunsStrip();
  }
}

function insertTemplateVar(varToken) {
  const fid = wfState.lastFocusedFieldId;
  const field = fid ? document.getElementById(fid) : null;
  if (!field) {
    if (navigator.clipboard) navigator.clipboard.writeText(varToken);
    wfToast(`📋 ${varToken} ক্লিপবোর্ডে কপি হয়েছে!`, 'info');
    return;
  }
  const start = field.selectionStart || field.value.length;
  const end = field.selectionEnd || start;
  field.value = field.value.slice(0, start) + varToken + field.value.slice(end);
  field.focus();
  field.dispatchEvent(new Event('change'));
}

function connectFromInspector() {
  const tgt = document.getElementById('wf-quick-connect-tgt')?.value;
  const condEl = document.getElementById('wf-quick-connect-cond');
  const cond = condEl ? condEl.value : '';
  if (!tgt || !wfState.selectedNodeId) return;
  connectNodes(wfState.selectedNodeId, tgt, cond);
}

async function testSelectedNode() {
  const wf = wfState.activeWorkflow;
  const node = wf ? (wf.nodes || []).find(n => n.id === wfState.selectedNodeId) : null;
  if (!node) return;

  const btn = document.getElementById('btn-wf-test-node');
  const outEl = document.getElementById('wf-node-test-output');
  const sampleInput = document.getElementById('wf-node-test-input')?.value || '';
  if (btn) { btn.disabled = true; btn.innerText = '⏳ Testing Node...'; }

  try {
    const res = await wfFetch('/api/workflows/node/test', {
      method: 'POST',
      body: JSON.stringify({ node, sample_input: sampleInput })
    });
    const data = await res.json();
    const r = data.result || {};
    if (outEl) {
      outEl.style.display = 'block';
      outEl.textContent = `[${r.status || 'DONE'} • ${r.duration_ms || 0} ms]\n${r.output || JSON.stringify(data, null, 2)}`;
    }
  } catch (err) {
    if (outEl) {
      outEl.style.display = 'block';
      outEl.textContent = 'Test Error: ' + err.message;
    }
  } finally {
    if (btn) { btn.disabled = false; btn.innerText = '⚡ এই নোডটি টেস্ট করুন'; }
  }
}

// ------------------------------------------------------------------------------
// Execution Output Trace Panel, History & Templates
// ------------------------------------------------------------------------------
function renderRunOutputPanel() {
  const el = document.getElementById('wf-inspector-run');
  if (!el) return;
  const run = wfState.activeRun;
  if (!run) {
    el.innerHTML = '<div class="wf-empty-hint">এই ওয়ার্কফ্লোটি এখনও রান হয়নি। উপরের "▶ Run Now" বাটনে ক্লিক করে লাইভ এক্সিকিউশন দেখুন।</div>';
    return;
  }

  const steps = run.node_results || [];
  const statusCls = (run.status || 'IDLE').toLowerCase();

  el.innerHTML = `
    <div class="wf-run-summary-card">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <span class="wf-status-pill ${statusCls}">${wfEsc(run.status)}</span>
        <span style="font-size:0.75rem; color:var(--text-muted); font-family:'Fira Code', monospace;">${run.duration_ms || 0} ms • ${wfEsc(run.trigger_source || 'manual')}</span>
      </div>
      <div style="font-size:0.75rem; color:var(--text-secondary); margin-top:6px;">
        Run ID: <code>${wfEsc(run.id || run.run_id || '-')}</code>
      </div>
      <div style="display:flex; gap:6px; margin-top:8px; flex-wrap:wrap;">
        <button type="button" class="mini-btn-copy" onclick="switchTab('reports')">📄 AI Reports দেখুন</button>
        <button type="button" class="mini-btn-copy" onclick="switchTab('chat')">💬 Chat Digest দেখুন</button>
      </div>
    </div>

    <div class="wf-trace-list">
      ${steps.map((st, idx) => `
        <div class="wf-trace-step ${(st.status || '').toLowerCase()}">
          <div class="wf-trace-top">
            <span class="wf-trace-title">${idx + 1}. ${wfEsc(wfNodeMeta(st.type).icon)} ${wfEsc(st.title || st.node_id)}</span>
            <div style="display:flex; align-items:center; gap:5px;">
              ${st.status === 'SUCCESS' ? `<button type="button" class="mini-btn-copy" onclick="pinNodeOutputFromRun('${wfEsc(st.node_id)}')" title="এই আউটপুট পিন করে রাখুন যাতে পরের ধাপ দ্রুত টেস্ট করা যায়">📌 Pin</button>` : ''}
              <span class="wf-status-pill ${(st.status || '').toLowerCase()}">${wfEsc(st.status)} (${st.duration_ms || 0}ms)</span>
            </div>
          </div>
          ${st.summary ? `<div class="wf-trace-sub">${wfEsc(st.summary)}</div>` : ''}
          <pre class="wf-trace-pre">${wfEsc((st.output || '').slice(0, 1800))}</pre>
        </div>
      `).join('')}
    </div>
  `;
}

async function refreshRecentWorkflowRuns() {
  try {
    const res = await wfFetch('/api/workflows/runs/recent?limit=35');
    const data = await res.json();
    if (data && data.success) {
      wfState.recentRuns = data.runs || [];
      renderExecutionHistoryTable();
    }
  } catch (err) {
    console.warn('refreshRecentWorkflowRuns error:', err);
  }
}

function renderExecutionHistoryTable() {
  const tbody = document.getElementById('wf-runs-history-tbody');
  if (!tbody) return;
  const runs = wfState.recentRuns || [];
  tbody.innerHTML = !runs.length
    ? '<tr><td colspan="7" style="padding:18px; text-align:center; color:var(--text-muted);">এখনও কোনো রান ইতিহাস নেই।</td></tr>'
    : runs.map(r => `
    <tr style="border-bottom:1px solid var(--border-subtle);">
      <td style="padding:10px 14px; font-family:'Fira Code', monospace; font-size:0.75rem;">${wfEsc(r.id)}</td>
      <td style="padding:10px 14px; font-weight:600;">${wfEsc(r.workflow_name || r.workflow_id)}</td>
      <td style="padding:10px 14px;"><span class="wf-source-badge">${wfEsc(r.trigger_source || 'manual')}</span></td>
      <td style="padding:10px 14px;"><span class="wf-status-pill ${(r.status || '').toLowerCase()}">${wfEsc(r.status)}</span></td>
      <td style="padding:10px 14px; font-family:'Fira Code', monospace; font-size:0.78rem;">${r.duration_ms || 0} ms</td>
      <td style="padding:10px 14px; font-size:0.78rem; color:var(--text-muted);">${wfEsc(r.started_at || '')}</td>
      <td style="padding:10px 14px; text-align:right;">
        <button type="button" class="btn-sm-action-cyber" onclick="inspectHistoricalRun('${wfEsc(r.id)}')">🔍 Trace দেখুন</button>
      </td>
    </tr>
  `).join('');
}

async function inspectHistoricalRun(runId) {
  const found = (wfState.recentRuns || []).find(r => r.id === runId);
  if (!found) return;
  await selectWorkflow(found.workflow_id, true);
  wfState.activeRun = found;
  renderWorkflowCanvas();
  renderRunOutputPanel();
  switchWorkflowsSubTab('studio');
  switchWfInspectorTab('run');
}

function renderTemplatesLibrary() {
  const grid = document.getElementById('wf-templates-grid');
  if (!grid) return;
  const templates = wfState.templates || [];
  if (!templates.length) {
    grid.innerHTML = '<div class="wf-empty-hint">কোনো টেমপ্লেট পাওয়া যায়নি।</div>';
    return;
  }

  grid.innerHTML = templates.map(tpl => {
    const chain = (tpl.nodes || []).map(n => wfNodeMeta(n.type).icon).join(' → ');
    return `
      <div class="wf-template-card">
        <div class="wf-tpl-top">
          <span class="wf-tpl-icon">${wfEsc(tpl.icon || '⚡')}</span>
          <div>
            <h4>${wfEsc(tpl.name)}</h4>
            <span class="wf-tpl-sched">${tpl.trigger_type === 'webhook' ? '🌐 Webhook' : `⏰ Daily ${tpl.daily_time || '09:00'}`}</span>
          </div>
        </div>
        <p class="wf-tpl-desc">${wfEsc(tpl.description || '')}</p>
        <div class="wf-tpl-chain">${wfEsc(chain)} (${(tpl.nodes || []).length} Nodes)</div>
        <button type="button" class="btn-primary" style="width:100%; justify-content:center;" onclick="installWorkflowTemplate('${wfEsc(tpl.id)}')">
          ➕ ইনস্টল ও কাস্টমাইজ করুন
        </button>
      </div>
    `;
  }).join('');
}

async function installWorkflowTemplate(templateId) {
  try {
    const res = await wfFetch(`/api/workflows/templates/${encodeURIComponent(templateId)}/install`, { method: 'POST' });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.detail || 'Install failed');
    wfToast(`✅ "${data.workflow.name}" ইনস্টল হয়েছে!`, 'success');
    await loadWorkflowsStudio(data.workflow.id);
    switchWorkflowsSubTab('studio');
  } catch (err) {
    wfToast('টেমপ্লেট ইনস্টল ব্যর্থ: ' + err.message, 'error');
  }
}

// ------------------------------------------------------------------------------
// Pin Output, Global Encrypted Secrets Vault, Versioning & Custom Payload Runner
// ------------------------------------------------------------------------------
function pinNodeOutputFromRun(nodeId) {
  const wf = wfState.activeWorkflow;
  const run = wfState.activeRun;
  if (!wf || !run) return;
  const step = (run.node_results || []).find(s => s.node_id === nodeId);
  const node = (wf.nodes || []).find(n => n.id === nodeId);
  if (!step || !node) return;

  node.config = node.config || {};
  node.config.use_pinned = true;
  node.config.pinned_output = step.output || '';
  markWfDirty();
  wfState.selectedNodeId = nodeId;
  renderWorkflowCanvas();
  renderNodeInspector();
  wfToast(`📌 নোড '${node.title}'-এর আউটপুট পিন করা হয়েছে! (Save বাটনে ক্লিক করুন)`, 'success');
}

async function openWorkflowVarsModal() {
  const modal = document.getElementById('wf-vars-modal');
  if (modal) modal.style.display = 'flex';
  await refreshWorkflowVarsList();
}

function closeWorkflowVarsModal() {
  const modal = document.getElementById('wf-vars-modal');
  if (modal) modal.style.display = 'none';
}

async function refreshWorkflowVarsList() {
  const listEl = document.getElementById('wf-vars-list');
  if (!listEl) return;
  listEl.innerHTML = '<div class="wf-empty-hint">লোড হচ্ছে...</div>';
  try {
    const res = await wfFetch('/api/workflows/vars/list');
    const data = await res.json();
    const vars = data.variables || [];
    wfState.variables = vars;
    if (!vars.length) {
      listEl.innerHTML = '<div class="wf-empty-hint">এখনও কোনো ভেরিয়েবল/সিক্রেট সংরক্ষিত নেই।</div>';
      return;
    }
    listEl.innerHTML = vars.map(v => `
      <div class="wf-modal-list-row">
        <div>
          <code style="color:#34d399; font-weight:700;">{{vars.${wfEsc(v.key)}}}</code>
          <span style="margin-left:8px; font-family:'Fira Code', monospace; font-size:0.76rem; color:var(--text-secondary);">${wfEsc(v.value_preview)}</span>
          ${v.description ? `<div style="font-size:0.72rem; color:var(--text-muted);">${wfEsc(v.description)}</div>` : ''}
        </div>
        <button type="button" class="wf-node-del-btn" onclick="deleteWorkflowVar('${wfEsc(v.key)}')" title="মুছুন">🗑️</button>
      </div>
    `).join('');
    if (wfState.selectedNodeId) renderNodeInspector();
  } catch (err) {
    listEl.innerHTML = `<div style="color:#f43f5e;">${wfEsc(err.message)}</div>`;
  }
}

async function submitWorkflowVar(event) {
  if (event) event.preventDefault();
  const key = document.getElementById('wf-var-key')?.value?.trim();
  const value = document.getElementById('wf-var-val')?.value || '';
  const is_secret = !!document.getElementById('wf-var-secret')?.checked;
  const description = document.getElementById('wf-var-desc')?.value?.trim() || '';
  if (!key) return;
  try {
    const res = await wfFetch('/api/workflows/vars/save', {
      method: 'POST',
      body: JSON.stringify({ key, value, is_secret, description })
    });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.detail || 'Save failed');
    document.getElementById('wf-var-key').value = '';
    document.getElementById('wf-var-val').value = '';
    document.getElementById('wf-var-desc').value = '';
    wfToast(`🔐 ভেরিয়েবল {{vars.${data.variable.key}}} সংরক্ষিত হয়েছে!`, 'success');
    await refreshWorkflowVarsList();
  } catch (err) {
    wfToast('সংরক্ষণ ব্যর্থ: ' + err.message, 'error');
  }
}

async function deleteWorkflowVar(key) {
  try {
    const res = await wfFetch(`/api/workflows/vars/${encodeURIComponent(key)}`, { method: 'DELETE' });
    if (res.ok) {
      wfToast(`ভেরিয়েবল '${key}' মুছে ফেলা হয়েছে।`, 'info');
      await refreshWorkflowVarsList();
    }
  } catch (err) {
    wfToast('ডিলিট ব্যর্থ: ' + err.message, 'error');
  }
}

async function openWorkflowVersionsModal() {
  const wf = wfState.activeWorkflow;
  if (!wf) return;
  const modal = document.getElementById('wf-versions-modal');
  const listEl = document.getElementById('wf-versions-list');
  if (modal) modal.style.display = 'flex';
  if (listEl) listEl.innerHTML = '<div class="wf-empty-hint">ভার্সন হিস্ট্রি লোড হচ্ছে...</div>';
  try {
    const res = await wfFetch(`/api/workflows/${encodeURIComponent(wf.id)}/versions`);
    const data = await res.json();
    const vers = data.versions || [];
    if (!vers.length) {
      listEl.innerHTML = '<div class="wf-empty-hint">এখনও কোনো পূর্ববর্তী ভার্সন নেই (প্রতিবার Save করলে স্বয়ংক্রিয়ভাবে স্ন্যাপশট তৈরি হয়)।</div>';
      return;
    }
    listEl.innerHTML = vers.map(v => `
      <div class="wf-modal-list-row">
        <div>
          <div style="font-weight:700; font-size:0.84rem; color:var(--text-primary);">v${v.version_num} — ${wfEsc(v.name)}</div>
          <div style="font-size:0.73rem; color:var(--text-muted);">🕒 ${wfEsc(v.saved_at)} • ${v.nodes_count} nodes • ${v.edges_count} edges</div>
        </div>
        <button type="button" class="btn-sm-action-cyber" onclick="restoreWorkflowVersion('${wfEsc(v.id)}')">↩️ Restore</button>
      </div>
    `).join('');
  } catch (err) {
    if (listEl) listEl.innerHTML = `<div style="color:#f43f5e;">${wfEsc(err.message)}</div>`;
  }
}

function closeWorkflowVersionsModal() {
  const modal = document.getElementById('wf-versions-modal');
  if (modal) modal.style.display = 'none';
}

async function restoreWorkflowVersion(versionId) {
  const wf = wfState.activeWorkflow;
  if (!wf) return;
  try {
    const res = await wfFetch(`/api/workflows/${encodeURIComponent(wf.id)}/versions/${encodeURIComponent(versionId)}/restore`, { method: 'POST' });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.detail || 'Restore failed');
    closeWorkflowVersionsModal();
    wfToast('✅ নির্বাচিত পূর্ববর্তী ভার্সন রিস্টোর করা হয়েছে!', 'success');
    await loadWorkflowsStudio(wf.id);
  } catch (err) {
    wfToast('রিস্টোর ব্যর্থ: ' + err.message, 'error');
  }
}

function openWorkflowPayloadModal() {
  if (!wfState.activeWorkflow) return;
  const modal = document.getElementById('wf-payload-modal');
  if (modal) modal.style.display = 'flex';
}

function closeWorkflowPayloadModal() {
  const modal = document.getElementById('wf-payload-modal');
  if (modal) modal.style.display = 'none';
}

async function executeWorkflowWithCustomPayload(dryRun = false) {
  const raw = document.getElementById('wf-payload-json-input')?.value || '{}';
  let parsed = {};
  try {
    parsed = JSON.parse(raw);
  } catch (e) {
    wfToast('JSON ফরম্যাট সঠিক নয়: ' + e.message, 'error');
    return;
  }
  closeWorkflowPayloadModal();
  await runActiveWorkflowNow(parsed, dryRun);
}

// ------------------------------------------------------------------------------
// Telegram Connection System, Connected Status & Live Log View
// ------------------------------------------------------------------------------
function renderTelegramStatusUI() {
  const tg = wfState.telegram || {};
  const isConnected = !!tg.connected;
  const isErr = tg.status === 'Error';
  const stateCls = isConnected ? 'connected' : (isErr ? 'error' : 'disconnected');

  // 1. Header Pill
  const pill = document.getElementById('wf-tg-status-pill');
  const pillText = document.getElementById('wf-tg-pill-text');
  if (pill) {
    pill.className = `wf-tg-status-pill ${stateCls}`;
  }
  if (pillText) {
    if (isConnected) {
      pillText.textContent = `✈️ Telegram: Connected${tg.bot_username ? ' (' + tg.bot_username + ')' : ''}`;
    } else if (isErr) {
      pillText.textContent = '✈️ Telegram: Error';
    } else {
      pillText.textContent = '✈️ Telegram: Disconnected';
    }
  }

  // 2. Sub-tab indicator dot
  const tabDot = document.getElementById('wf-tab-tg-dot');
  if (tabDot) tabDot.className = `wf-tg-dot-mini ${stateCls}`;

  // 3. Subtab Big Status Banner
  const banner = document.getElementById('wf-tg-status-banner');
  const bigBadge = document.getElementById('wf-tg-big-badge');
  const botIdent = document.getElementById('wf-tg-bot-identity');
  const metaEl = document.getElementById('wf-tg-status-meta');
  if (banner) banner.className = `wf-tg-status-banner ${stateCls}`;
  if (bigBadge) {
    bigBadge.className = `wf-tg-big-badge ${stateCls}`;
    bigBadge.textContent = isConnected ? '🟢 CONNECTED' : (isErr ? '🟠 ERROR' : '🔴 DISCONNECTED');
  }
  if (botIdent) {
    if (isConnected) {
      botIdent.textContent = `${tg.bot_first_name || 'Telegram Bot'} ${tg.bot_username ? '(' + tg.bot_username + ')' : ''}`.trim();
    } else if (isErr) {
      botIdent.textContent = `কানেকশন সমস্যা${tg.bot_username ? ' (' + tg.bot_username + ')' : ''}`;
    } else {
      botIdent.textContent = tg.has_token ? 'টোকেন সেভ করা আছে (পজ/বিচ্ছিন্ন)' : 'Telegram Bot সংযুক্ত নয়';
    }
  }
  if (metaEl) {
    const parts = [];
    if (tg.chat_id) parts.push(`Chat ID: <code>${wfEsc(tg.chat_id)}</code>`);
    if (tg.token_preview) parts.push(`Token: <code>${wfEsc(tg.token_preview)}</code>`);
    parts.push(`Sent: <strong style="color:#10b981;">${tg.sent_count || 0}</strong> • Failed: <strong style="color:#f43f5e;">${tg.failed_count || 0}</strong>`);
    if (tg.last_verified_at) parts.push(`Verified: ${wfEsc(tg.last_verified_at)}`);
    if (tg.last_tested_at) parts.push(`Tested: ${wfEsc(tg.last_tested_at)}`);
    if (tg.last_error) parts.push(`<span style="color:#fda4af;">ত্রুটি: ${wfEsc(tg.last_error)}</span>`);
    metaEl.innerHTML = parts.length ? parts.join(' &nbsp;|&nbsp; ') : 'নিচের ফর্মে @BotFather টোকেন ও Chat ID দিয়ে কানেক্ট করুন।';
  }

  // 4. Populate Form Inputs safely
  const tokenInput = document.getElementById('wf-tg-token-input');
  const tokenHint = document.getElementById('wf-tg-token-hint');
  const chatInput = document.getElementById('wf-tg-chatid-input');
  const enChk = document.getElementById('wf-tg-enabled-chk');

  if (tokenInput && tg.has_token) {
    tokenInput.placeholder = `Saved: ${tg.token_preview} (নতুন না দিলে এটিই থাকবে)`;
  } else if (tokenInput) {
    tokenInput.placeholder = '1234567890:ABCdefGHIjklMNOpqrSTUvwxyz';
  }
  if (tokenHint) {
    tokenHint.innerHTML = tg.has_token
      ? `✅ এনক্রিপ্টেড টোকেন সংরক্ষিত (<code>${wfEsc(tg.token_preview)}</code>)। পরিবর্তন করতে চাইলে নতুন টোকেন দিন।`
      : 'টোকেন AES-256 এনক্রিপশনসহ সুরক্ষিত থাকবে।';
  }
  if (chatInput && document.activeElement !== chatInput && !chatInput.value && tg.chat_id) {
    chatInput.value = tg.chat_id;
  }
  if (enChk) {
    enChk.checked = tg.has_token ? !!tg.is_enabled : true;
  }
}

function toggleTelegramTokenVisibility() {
  const inp = document.getElementById('wf-tg-token-input');
  const btn = document.getElementById('wf-tg-token-vis-btn');
  if (!inp) return;
  const show = inp.type === 'password';
  inp.type = show ? 'text' : 'password';
  if (btn) btn.textContent = show ? '🙈' : '👁️';
}

async function refreshWorkflowTelegramStatus(liveCheck = false) {
  try {
    const res = await wfFetch(`/api/workflows/telegram/status?live_check=${liveCheck ? 'true' : 'false'}`);
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.detail || 'Failed to read status');
    wfState.telegram = data.telegram;
    renderTelegramStatusUI();
    if (wfState.selectedNodeId) renderNodeInspector();
    if (liveCheck) {
      if (data.telegram.connected) {
        wfToast(`🟢 Telegram Connected (${data.telegram.bot_username || 'Bot'})!`, 'success');
      } else {
        wfToast(`⚠️ Telegram Status: ${data.telegram.status}${data.telegram.last_error ? ' — ' + data.telegram.last_error : ''}`, 'warning');
      }
      await refreshWorkflowTelegramLogs(false);
    }
  } catch (err) {
    wfToast('Telegram স্ট্যাটাস চেক ব্যর্থ: ' + err.message, 'error');
  }
}

async function connectWorkflowTelegram(event) {
  if (event) event.preventDefault();
  const bot_token = document.getElementById('wf-tg-token-input')?.value?.trim() || '';
  const chat_id = document.getElementById('wf-tg-chatid-input')?.value?.trim() || '';
  const is_enabled = !!document.getElementById('wf-tg-enabled-chk')?.checked;
  const verify_live = !!document.getElementById('wf-tg-verify-chk')?.checked;

  const btn = document.getElementById('btn-wf-tg-connect');
  if (btn) { btn.disabled = true; btn.textContent = '⏳ যাচাই ও কানেক্ট হচ্ছে...'; }

  try {
    const res = await wfFetch('/api/workflows/telegram/connect', {
      method: 'POST',
      body: JSON.stringify({ bot_token, chat_id, is_enabled, verify_live })
    });
    const data = await res.json();
    if (data.telegram) {
      wfState.telegram = data.telegram;
      renderTelegramStatusUI();
      if (data.telegram.chat_id) {
        const cidEl = document.getElementById('wf-tg-chatid-input');
        if (cidEl) cidEl.value = data.telegram.chat_id;
      }
    }
    const tokEl = document.getElementById('wf-tg-token-input');
    if (tokEl && data.success) tokEl.value = '';

    if (res.ok && data.success) {
      wfToast(`🟢 Telegram সফলভাবে কানেক্ট হয়েছে${data.telegram?.bot_username ? ' (' + data.telegram.bot_username + ')' : ''}!`, 'success');
      renderDetectedChatsChips(data.detected_chats || []);
    } else {
      wfToast('❌ Telegram কানেক্ট ব্যর্থ: ' + (data.error || data.detail || 'Verification error'), 'error');
    }
    await refreshWorkflowTelegramLogs(false);
    if (wfState.selectedNodeId) renderNodeInspector();
  } catch (err) {
    wfToast('কানেকশন ত্রুটি: ' + err.message, 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '🔗 Connect & Verify Bot'; }
  }
}

function renderDetectedChatsChips(chats) {
  const box = document.getElementById('wf-tg-detected-chats');
  if (!box) return;
  if (!chats || !chats.length) {
    box.style.display = 'none';
    box.innerHTML = '';
    return;
  }
  box.style.display = 'flex';
  box.innerHTML = `<span style="font-size:0.74rem; color:var(--text-muted); width:100%;">শনাক্তকৃত চ্যাট (ক্লিক করে সিলেক্ট করুন):</span>` +
    chats.map(c => `
      <button type="button" class="wf-chip-btn" onclick="pickDetectedTelegramChat('${wfEsc(c.chat_id)}')">
        💬 ${wfEsc(c.title)} (${wfEsc(c.chat_id)})
      </button>
    `).join('');
}

function pickDetectedTelegramChat(chatId) {
  const inp = document.getElementById('wf-tg-chatid-input');
  if (inp) inp.value = chatId;
  wfToast(`Chat ID সেট করা হয়েছে: ${chatId} — এবার "Connect & Verify Bot" ক্লিক করে সেভ করুন।`, 'info');
}

async function detectWorkflowTelegramChats() {
  const bot_token = document.getElementById('wf-tg-token-input')?.value?.trim() || '';
  try {
    const res = await wfFetch('/api/workflows/telegram/detect-chat', {
      method: 'POST',
      body: JSON.stringify({ bot_token })
    });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.error || data.detail || 'Detection failed');
    const chats = data.chats || [];
    if (!chats.length) {
      wfToast('কোনো সাম্প্রতিক চ্যাট পাওয়া যায়নি। টেলিগ্রামে আপনার বটকে /start মেসেজ পাঠিয়ে আবার ক্লিক করুন।', 'warning');
      renderDetectedChatsChips([]);
    } else {
      renderDetectedChatsChips(chats);
      if (!document.getElementById('wf-tg-chatid-input')?.value?.trim()) {
        document.getElementById('wf-tg-chatid-input').value = chats[0].chat_id;
      }
      wfToast(`✅ ${chats.length}টি Telegram চ্যাট পাওয়া গেছে!`, 'success');
    }
    await refreshWorkflowTelegramLogs(false);
  } catch (err) {
    wfToast('Chat ID খুঁজতে ব্যর্থ: ' + err.message, 'error');
  }
}

async function testWorkflowTelegramMessage() {
  const bot_token = document.getElementById('wf-tg-token-input')?.value?.trim() || '';
  const chat_id = document.getElementById('wf-tg-chatid-input')?.value?.trim() || '';
  const message = document.getElementById('wf-tg-test-msg')?.value?.trim() || '';
  try {
    const res = await wfFetch('/api/workflows/telegram/test', {
      method: 'POST',
      body: JSON.stringify({ bot_token, chat_id, message })
    });
    const data = await res.json();
    if (data.telegram) {
      wfState.telegram = data.telegram;
      renderTelegramStatusUI();
    }
    if (res.ok && data.success) {
      wfToast(`📨 টেলিগ্রামে টেস্ট মেসেজ পাঠানো হয়েছে (Msg ID: ${data.delivery?.telegram_message_id || 'OK'}, ${data.delivery?.latency_ms || 0}ms)!`, 'success');
    } else {
      wfToast('❌ টেস্ট মেসেজ পাঠাতে ব্যর্থ: ' + (data.delivery?.error || data.detail || 'Failed'), 'error');
    }
    await refreshWorkflowTelegramLogs(false);
  } catch (err) {
    wfToast('টেস্ট সেন্ড ব্যর্থ: ' + err.message, 'error');
  }
}

async function disconnectWorkflowTelegram() {
  try {
    const res = await wfFetch('/api/workflows/telegram/disconnect', {
      method: 'POST',
      body: JSON.stringify({ clear_token: false })
    });
    const data = await res.json();
    if (data.telegram) {
      wfState.telegram = data.telegram;
      renderTelegramStatusUI();
    }
    wfToast('🔌 Telegram কানেকশন ডিসকানেক্ট করা হয়েছে।', 'info');
    await refreshWorkflowTelegramLogs(false);
    if (wfState.selectedNodeId) renderNodeInspector();
  } catch (err) {
    wfToast('ডিসকানেক্ট ব্যর্থ: ' + err.message, 'error');
  }
}

async function refreshWorkflowTelegramLogs(alsoRefreshStatus = true) {
  const tbody = document.getElementById('wf-tg-logs-tbody');
  const filter = document.getElementById('wf-tg-log-filter')?.value || 'ALL';
  try {
    const res = await wfFetch(`/api/workflows/telegram/logs?limit=80&status=${encodeURIComponent(filter)}`);
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.detail || 'Logs fetch failed');
    wfState.telegramLogs = data.logs || [];
    if (alsoRefreshStatus && data.telegram) {
      wfState.telegram = data.telegram;
      renderTelegramStatusUI();
    }
    renderTelegramLogsTable();
  } catch (err) {
    if (tbody) tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:#f43f5e; padding:18px;">${wfEsc(err.message)}</td></tr>`;
  }
}

function renderTelegramLogsTable() {
  const tbody = document.getElementById('wf-tg-logs-tbody');
  const cntEl = document.getElementById('wf-tg-log-counts');
  const logs = wfState.telegramLogs || [];
  if (cntEl) cntEl.textContent = `(${logs.length} টি লগ)`;
  if (!tbody) return;

  if (!logs.length) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:26px; color:var(--text-muted);">এখনও কোনো টেলিগ্রাম কানেকশন বা মেসেজ লগ নেই।</td></tr>';
    return;
  }

  tbody.innerHTML = logs.map(l => {
    const st = String(l.status || '').toUpperCase();
    const cls = (st === 'SENT' || st === 'SUCCESS' || st === 'CONNECTED') ? 'ok' : (st === 'DISCONNECTED' ? 'muted' : 'err');
    const evMap = {
      connect: '🔗 Connect',
      verify: '🛡️ Verify',
      test_send: '📨 Test Send',
      workflow_notify: '⚡ Workflow Alert',
      detect_chat: '🔍 Detect Chat',
      disconnect: '🔌 Disconnect'
    };
    const evLabel = evMap[l.event_type] || l.event_type;
    const srcLabel = l.workflow_name
      ? `${wfEsc(l.workflow_name)}${l.node_id ? ' (' + wfEsc(l.node_id) + ')' : ''}`
      : (l.bot_username || 'Telegram Studio');
    const detail = l.error_detail
      ? `<span style="color:#fda4af;">${wfEsc(l.error_detail)}</span>`
      : `<span>${wfEsc(l.message_preview || '-')}</span>`;
    const metaParts = [];
    if (l.http_status) metaParts.push(`HTTP ${l.http_status}`);
    if (l.telegram_message_id) metaParts.push(`msg#${l.telegram_message_id}`);
    if (l.latency_ms) metaParts.push(`${l.latency_ms}ms`);
    const metaStr = metaParts.length ? `<div style="font-size:0.68rem; color:var(--text-muted); margin-top:2px;">${wfEsc(metaParts.join(' • '))}</div>` : '';

    return `
      <tr>
        <td style="white-space:nowrap; font-size:0.74rem; color:var(--text-muted);">${wfEsc(l.created_at)}</td>
        <td style="white-space:nowrap; font-size:0.78rem; font-weight:600;">${wfEsc(evLabel)}</td>
        <td style="font-size:0.78rem;">${srcLabel}</td>
        <td><code>${wfEsc(l.chat_id || '-')}</code></td>
        <td style="font-size:0.77rem; max-width:280px;">${detail}${metaStr}</td>
        <td><span class="wf-tg-log-badge ${cls}">${wfEsc(st)}</span></td>
      </tr>
    `;
  }).join('');
}

async function clearWorkflowTelegramLogs() {
  try {
    const res = await wfFetch('/api/workflows/telegram/logs', { method: 'DELETE' });
    if (res.ok) {
      wfToast('🗑️ টেলিগ্রাম লগ মুছে ফেলা হয়েছে।', 'info');
      await refreshWorkflowTelegramLogs(true);
    }
  } catch (err) {
    wfToast('লগ মুছতে ব্যর্থ: ' + err.message, 'error');
  }
}

// Global exports
window.loadWorkflowsStudio = loadWorkflowsStudio;
window.switchWorkflowsSubTab = switchWorkflowsSubTab;
window.switchWfInspectorTab = switchWfInspectorTab;
window.toggleQuickDailyBuilder = toggleQuickDailyBuilder;
window.applyQuickDailyPreset = applyQuickDailyPreset;
window.submitQuickDailyTask = submitQuickDailyTask;
window.architectWorkflowFromBuilder = architectWorkflowFromBuilder;
window.renderWorkflowsSidebar = renderWorkflowsSidebar;
window.selectWorkflow = selectWorkflow;
window.toggleWorkflowById = toggleWorkflowById;
window.createBlankWorkflow = createBlankWorkflow;
window.duplicateActiveWorkflow = duplicateActiveWorkflow;
window.exportActiveWorkflow = exportActiveWorkflow;
window.importWorkflowFromFile = importWorkflowFromFile;
window.addNodeToCanvas = addNodeToCanvas;
window.duplicateNodeById = duplicateNodeById;
window.toggleNodeDisabled = toggleNodeDisabled;
window.copyNodeVarRef = copyNodeVarRef;
window.setCanvasZoom = setCanvasZoom;
window.autoLayoutWorkflow = autoLayoutWorkflow;
window.updateActiveWorkflowMeta = updateActiveWorkflowMeta;
window.saveActiveWorkflow = saveActiveWorkflow;
window.runActiveWorkflowNow = runActiveWorkflowNow;
window.stopActiveWorkflow = stopActiveWorkflow;
window.deleteActiveWorkflow = deleteActiveWorkflow;
window.copyWorkflowWebhookUrl = copyWorkflowWebhookUrl;
window.onNodeMouseDown = onNodeMouseDown;
window.onNodeCardClick = onNodeCardClick;
window.onOutputPortClick = onOutputPortClick;
window.onInputPortClick = onInputPortClick;
window.onCanvasBackgroundClick = onCanvasBackgroundClick;
window.removeEdgeById = removeEdgeById;
window.deleteNodeById = deleteNodeById;
window.updateSelectedNodeTitle = updateSelectedNodeTitle;
window.updateNodeCfg = updateNodeCfg;
window.insertTemplateVar = insertTemplateVar;
window.connectFromInspector = connectFromInspector;
window.testSelectedNode = testSelectedNode;
window.pinNodeOutputFromRun = pinNodeOutputFromRun;
window.openWorkflowVarsModal = openWorkflowVarsModal;
window.closeWorkflowVarsModal = closeWorkflowVarsModal;
window.submitWorkflowVar = submitWorkflowVar;
window.deleteWorkflowVar = deleteWorkflowVar;
window.openWorkflowVersionsModal = openWorkflowVersionsModal;
window.closeWorkflowVersionsModal = closeWorkflowVersionsModal;
window.restoreWorkflowVersion = restoreWorkflowVersion;
window.openWorkflowPayloadModal = openWorkflowPayloadModal;
window.closeWorkflowPayloadModal = closeWorkflowPayloadModal;
window.executeWorkflowWithCustomPayload = executeWorkflowWithCustomPayload;
window.refreshRecentWorkflowRuns = refreshRecentWorkflowRuns;
window.inspectHistoricalRun = inspectHistoricalRun;
window.installWorkflowTemplate = installWorkflowTemplate;
window.toggleTelegramTokenVisibility = toggleTelegramTokenVisibility;
window.refreshWorkflowTelegramStatus = refreshWorkflowTelegramStatus;
window.connectWorkflowTelegram = connectWorkflowTelegram;
window.detectWorkflowTelegramChats = detectWorkflowTelegramChats;
window.pickDetectedTelegramChat = pickDetectedTelegramChat;
window.testWorkflowTelegramMessage = testWorkflowTelegramMessage;
window.disconnectWorkflowTelegram = disconnectWorkflowTelegram;
window.refreshWorkflowTelegramLogs = refreshWorkflowTelegramLogs;
window.clearWorkflowTelegramLogs = clearWorkflowTelegramLogs;
