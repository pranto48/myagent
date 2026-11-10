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
  telegramChats: [],
  tgLiveTimer: null,
  templates: [],
  nodeCatalog: [],
  tools: [],
  mcpServers: [],
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
  dragMoved: false,
  dragSnapshotTaken: false,
  panState: null,
  justPanned: false,
  draggingPaletteType: null,
  quickPicker: null,
  undoStack: [],
  redoStack: [],
  snapGrid: true,
  paletteCategory: 'all',
  paletteQuery: '',
  fullscreenCanvas: false,
  leftCollapsed: false,
  rightCollapsed: false,
  lastFocusedFieldId: null,
  subTab: 'studio',
  inspectorTab: 'node',
  dirty: false,
  zoom: 1.0,
  stageWidth: 1200,
  stageHeight: 540,
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
    mcp_tool: { icon: '🔌', label_bn: 'MCP টুল কল', label_en: 'MCP Tool Call', color: '#6366f1', category: 'action' },
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
    const [wfRes, tplRes, varsRes, tgRes, tgChatsRes] = await Promise.all([
      wfFetch('/api/workflows'),
      wfFetch('/api/workflows/templates'),
      wfFetch('/api/workflows/vars/list'),
      wfFetch('/api/workflows/telegram/status'),
      wfFetch('/api/workflows/telegram/chats?limit=25')
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
        wfState.mcpServers = tplData.mcp_servers || [];
        wfState.workflowsList = tplData.workflows_list || [];
        wfState.subagents = tplData.subagents || [];
        wfState.models = tplData.models || [];
        if (!hadPalette) populateQuickModelSelect();
        renderNodePalette();
        renderTemplatesLibrary();
        renderWorkflowMcpStatusPill();
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

    if (tgChatsRes && tgChatsRes.ok) {
      const tgcData = await tgChatsRes.json();
      if (tgcData && tgcData.success) {
        wfState.telegramChats = tgcData.chats || [];
        renderTelegramLatestStrip(tgcData.workflow_digest || null);
        if (wfState.subTab === 'telegram') renderTelegramChatFeed();
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

  if (wfState.tgLiveTimer) {
    clearInterval(wfState.tgLiveTimer);
    wfState.tgLiveTimer = null;
  }

  if (tabName === 'studio') {
    setTimeout(drawWorkflowEdges, 40);
  } else if (tabName === 'history') {
    refreshRecentWorkflowRuns();
  } else if (tabName === 'telegram') {
    refreshWorkflowTelegramChats();
    refreshWorkflowTelegramLogs(true);
    wfState.tgLiveTimer = setInterval(() => {
      if (wfState.subTab === 'telegram') {
        refreshWorkflowTelegramChats();
        refreshWorkflowTelegramLogs(false);
      }
    }, 4500);
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
  const use_mcp = document.getElementById('wf-quick-use-mcp')?.checked !== false;
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
        use_mcp,
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
    wfState.undoStack = [];
    wfState.redoStack = [];
    closeQuickPicker();
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
// Undo/Redo, Grid Snap, Palette Search & Drag-Drop, Layout & Studio Controls
// ------------------------------------------------------------------------------
function snapCoord(val) {
  const num = Number(val || 0);
  if (!wfState.snapGrid) return Math.max(12, Math.round(num));
  return Math.max(20, Math.round(num / 20) * 20);
}

function pushUndoSnapshot() {
  const wf = wfState.activeWorkflow;
  if (!wf) return;
  const snap = JSON.stringify({
    name: wf.name,
    is_enabled: wf.is_enabled,
    nodes: wf.nodes || [],
    edges: wf.edges || [],
    selectedNodeId: wfState.selectedNodeId
  });
  if (wfState.undoStack.length && wfState.undoStack[wfState.undoStack.length - 1] === snap) {
    return;
  }
  wfState.undoStack.push(snap);
  if (wfState.undoStack.length > 30) wfState.undoStack.shift();
  wfState.redoStack = [];
}

function applyHistorySnapshot(snapJson) {
  const wf = wfState.activeWorkflow;
  if (!wf || !snapJson) return;
  const snap = JSON.parse(snapJson);
  wf.name = snap.name;
  wf.is_enabled = snap.is_enabled;
  wf.nodes = wfClone(snap.nodes || []);
  wf.edges = wfClone(snap.edges || []);
  if (snap.selectedNodeId && wf.nodes.some(n => n.id === snap.selectedNodeId)) {
    wfState.selectedNodeId = snap.selectedNodeId;
  } else {
    wfState.selectedNodeId = wf.nodes[0] ? wf.nodes[0].id : null;
  }
  markWfDirty();
  renderWorkflowToolbar();
  renderWorkflowCanvas();
  renderNodeInspector();
}

function undoWorkflowChange() {
  const wf = wfState.activeWorkflow;
  if (!wf || !wfState.undoStack.length) {
    wfToast('Undo করার মতো আর কোনো ধাপ নেই।', 'info');
    return;
  }
  const current = JSON.stringify({
    name: wf.name,
    is_enabled: wf.is_enabled,
    nodes: wf.nodes || [],
    edges: wf.edges || [],
    selectedNodeId: wfState.selectedNodeId
  });
  wfState.redoStack.push(current);
  const prev = wfState.undoStack.pop();
  applyHistorySnapshot(prev);
  wfToast('↩️ পূর্ববর্তী অবস্থা Undo করা হয়েছে।', 'info');
}

function redoWorkflowChange() {
  const wf = wfState.activeWorkflow;
  if (!wf || !wfState.redoStack.length) {
    wfToast('Redo করার মতো কোনো ধাপ নেই।', 'info');
    return;
  }
  const current = JSON.stringify({
    name: wf.name,
    is_enabled: wf.is_enabled,
    nodes: wf.nodes || [],
    edges: wf.edges || [],
    selectedNodeId: wfState.selectedNodeId
  });
  wfState.undoStack.push(current);
  const nxt = wfState.redoStack.pop();
  applyHistorySnapshot(nxt);
  wfToast('↪️ পরিবর্তন পুনরায় Redo করা হয়েছে।', 'info');
}

function onPaletteSearchInput(q) {
  wfState.paletteQuery = String(q || '').trim().toLowerCase();
  renderNodePalette();
}

function setPaletteCategory(cat) {
  wfState.paletteCategory = cat || 'all';
  const wrap = document.getElementById('wf-palette-cat-pills');
  if (wrap) {
    wrap.querySelectorAll('.wf-cat-pill').forEach(btn => {
      const m = /setPaletteCategory\('([^']+)'\)/.exec(btn.getAttribute('onclick') || '');
      btn.classList.toggle('active', m && m[1] === wfState.paletteCategory);
    });
  }
  renderNodePalette();
}

function renderNodePalette() {
  const el = document.getElementById('wf-node-palette');
  const cntEl = document.getElementById('wf-palette-count');
  if (!el) return;
  const q = (wfState.paletteQuery || '').toLowerCase();
  const cat = wfState.paletteCategory || 'all';
  const filtered = (wfState.nodeCatalog || []).filter(item => {
    if (cat !== 'all' && item.category !== cat) return false;
    if (q) {
      const hay = `${item.type} ${item.label_bn || ''} ${item.label_en || ''}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
  if (cntEl) cntEl.textContent = String(filtered.length);
  if (!filtered.length) {
    el.innerHTML = '<div class="wf-empty-hint">মিল পাওয়া যায়নি।</div>';
    return;
  }
  el.innerHTML = filtered.map(item => `
    <button type="button"
            class="wf-palette-chip"
            style="--node-color:${item.color};"
            draggable="true"
            ondragstart="onPaletteDragStart(event, '${wfEsc(item.type)}')"
            onclick="addNodeToCanvas('${wfEsc(item.type)}')"
            title="ক্লিক করে যোগ করুন অথবা ক্যানভাসে ড্র্যাগ-ড্রপ করুন (${wfEsc(item.label_en)})">
      <span class="wf-palette-dot" style="background:${item.color};"></span>
      <span>${wfEsc(item.icon)} ${wfEsc(item.label_bn || item.label_en)}</span>
      <span class="wf-palette-plus">+</span>
    </button>
  `).join('');
}

function onPaletteDragStart(event, nodeType) {
  wfState.draggingPaletteType = nodeType;
  if (event.dataTransfer) {
    event.dataTransfer.setData('text/plain', nodeType);
    event.dataTransfer.effectAllowed = 'copy';
  }
}

function onCanvasDragOver(event) {
  if (wfState.draggingPaletteType || (event.dataTransfer && event.dataTransfer.types.includes('text/plain'))) {
    event.preventDefault();
    if (event.dataTransfer) event.dataTransfer.dropEffect = 'copy';
  }
}

function onCanvasDrop(event) {
  event.preventDefault();
  const nodeType = wfState.draggingPaletteType || (event.dataTransfer ? event.dataTransfer.getData('text/plain') : '');
  wfState.draggingPaletteType = null;
  if (!nodeType || !wfState.activeWorkflow) return;
  const stage = document.getElementById('wf-canvas-stage');
  if (!stage) {
    addNodeToCanvas(nodeType);
    return;
  }
  const rect = stage.getBoundingClientRect();
  const zoom = wfState.zoom || 1.0;
  const dropX = snapCoord((event.clientX - rect.left) / zoom - 110);
  const dropY = snapCoord((event.clientY - rect.top) / zoom - 40);
  addNodeToCanvas(nodeType, dropX, dropY, false);
}

function _nextNodeId(nodes) {
  let maxIdx = nodes.length;
  nodes.forEach(n => {
    const m = /^node_(\d+)$/.exec(n.id || '');
    if (m) maxIdx = Math.max(maxIdx, parseInt(m[1], 10));
  });
  return `node_${maxIdx + 1}`;
}

function addNodeToCanvas(nodeType, customX = null, customY = null, autoWireAnchor = true) {
  if (!wfState.activeWorkflow) {
    wfToast('প্রথমে একটি ওয়ার্কফ্লো নির্বাচন করুন বা তৈরি করুন।', 'warning');
    return null;
  }
  pushUndoSnapshot();

  const meta = wfNodeMeta(nodeType);
  const nodes = wfState.activeWorkflow.nodes || [];
  const edges = wfState.activeWorkflow.edges || [];
  const newId = _nextNodeId(nodes);

  const anchor = nodes.find(n => n.id === wfState.selectedNodeId) || nodes[nodes.length - 1];
  let baseX = customX !== null ? snapCoord(customX) : (anchor ? snapCoord(Number(anchor.x || 40) + 300) : 40);
  let targetY = customY !== null ? snapCoord(customY) : (anchor ? snapCoord(Number(anchor.y || 140)) : 140);
  if (customX === null) {
    while (nodes.some(n => Math.abs((n.x || 0) - baseX) < 160 && Math.abs((n.y || 0) - targetY) < 95)) {
      targetY = snapCoord(targetY + 140);
    }
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

  if (autoWireAnchor && anchor && !nodeType.startsWith('trigger_')) {
    let cond = '';
    if (anchor.type === 'condition') {
      const hasTrue = edges.some(e => e.source === anchor.id && e.condition === 'true');
      cond = hasTrue ? 'false' : 'true';
    } else if (anchor.type === 'switch_router') {
      const hasR1 = edges.some(e => e.source === anchor.id && e.condition === 'route_1');
      const hasR2 = edges.some(e => e.source === anchor.id && e.condition === 'route_2');
      cond = !hasR1 ? 'route_1' : (!hasR2 ? 'route_2' : 'default');
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

  renderWorkflowToolbar();
  renderWorkflowCanvas();
  renderNodeInspector();
  switchWfInspectorTab('node');
  return newNode;
}

function duplicateNodeById(event, nodeId) {
  if (event) event.stopPropagation();
  const wf = wfState.activeWorkflow;
  if (!wf) return;
  const src = (wf.nodes || []).find(n => n.id === nodeId);
  if (!src) return;
  pushUndoSnapshot();

  const newNode = wfClone(src);
  newNode.id = _nextNodeId(wf.nodes);
  newNode.title = `${src.title || src.type} (Copy)`;
  newNode.x = snapCoord(Number(src.x || 40) + 40);
  newNode.y = snapCoord(Number(src.y || 140) + 120);
  wf.nodes.push(newNode);
  wfState.selectedNodeId = newNode.id;
  markWfDirty();
  renderWorkflowToolbar();
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
  pushUndoSnapshot();
  node.disabled = !node.disabled;
  node.config = node.config || {};
  node.config.disabled = node.disabled;
  markWfDirty();
  renderWorkflowToolbar();
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

function toggleGridSnap() {
  wfState.snapGrid = !wfState.snapGrid;
  renderCanvasHud();
  wfToast(wfState.snapGrid ? '🧲 20px গ্রিড স্ন্যাপ চালু।' : 'গ্রিড স্ন্যাপ বন্ধ।', 'info');
}

function toggleStudioPane(which) {
  if (which === 'left') wfState.leftCollapsed = !wfState.leftCollapsed;
  if (which === 'right') wfState.rightCollapsed = !wfState.rightCollapsed;
  applyStudioLayoutClasses();
  renderWorkflowToolbar();
  setTimeout(() => { drawWorkflowEdges(); renderCanvasMinimap(); }, 40);
}

function toggleFullscreenCanvas(forceState = null) {
  wfState.fullscreenCanvas = forceState !== null ? !!forceState : !wfState.fullscreenCanvas;
  applyStudioLayoutClasses();
  renderWorkflowToolbar();
  renderCanvasHud();
  setTimeout(() => { drawWorkflowEdges(); renderCanvasMinimap(); }, 50);
}

function applyStudioLayoutClasses() {
  const studio = document.getElementById('wf-subtab-studio');
  if (!studio) return;
  studio.classList.toggle('wf-studio-fullscreen', !!wfState.fullscreenCanvas);
  studio.classList.toggle('wf-left-collapsed', !!wfState.leftCollapsed);
  studio.classList.toggle('wf-right-collapsed', !!wfState.rightCollapsed);
}

function setCanvasZoom(deltaOrReset) {
  if (deltaOrReset === 0) {
    wfState.zoom = 1.0;
  } else {
    wfState.zoom = Math.max(0.45, Math.min(1.6, Number((wfState.zoom + deltaOrReset).toFixed(2))));
  }
  renderWorkflowToolbar();
  renderWorkflowCanvas();
}

function fitCanvasToView() {
  const wf = wfState.activeWorkflow;
  const vp = document.getElementById('wf-canvas-viewport');
  if (!wf || !wf.nodes || !wf.nodes.length || !vp) {
    setCanvasZoom(0);
    return;
  }
  let minX = Infinity, minY = Infinity, maxX = 0, maxY = 0;
  wf.nodes.forEach(n => {
    const x = Number(n.x || 0);
    const y = Number(n.y || 0);
    minX = Math.min(minX, x);
    minY = Math.min(minY, y);
    maxX = Math.max(maxX, x + 245);
    maxY = Math.max(maxY, y + 125);
  });
  const boxW = Math.max(300, maxX - minX + 90);
  const boxH = Math.max(240, maxY - minY + 90);
  const fitZ = Math.min(vp.clientWidth / boxW, vp.clientHeight / boxH);
  wfState.zoom = Math.max(0.45, Math.min(1.15, Number(fitZ.toFixed(2))));
  renderWorkflowToolbar();
  renderWorkflowCanvas();
  requestAnimationFrame(() => {
    vp.scrollLeft = Math.max(0, (minX - 40) * wfState.zoom);
    vp.scrollTop = Math.max(0, (minY - 40) * wfState.zoom);
    renderCanvasMinimap();
  });
}

function autoLayoutWorkflow() {
  const wf = wfState.activeWorkflow;
  if (!wf || !wf.nodes || !wf.nodes.length) return;
  pushUndoSnapshot();

  const nodes = wf.nodes;
  const edges = wf.edges || [];
  const inDeg = {};
  const adj = {};
  const parents = {};
  nodes.forEach(n => { inDeg[n.id] = 0; adj[n.id] = []; parents[n.id] = []; });
  edges.forEach(e => {
    if (inDeg[e.target] !== undefined && adj[e.source]) {
      inDeg[e.target]++;
      adj[e.source].push(e);
      parents[e.target].push(e);
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
      if (levelMap[v] === undefined || (levelMap[v] < lv + 1 && lv < nodes.length + 2)) {
        levelMap[v] = lv + 1;
        queue.push(v);
      }
    });
  }

  nodes.forEach(n => { if (levelMap[n.id] === undefined) levelMap[n.id] = 0; });
  const nodeById = {};
  nodes.forEach(n => { nodeById[n.id] = n; });

  const byLevel = {};
  nodes.forEach(n => {
    const lv = levelMap[n.id];
    if (!byLevel[lv]) byLevel[lv] = [];
    byLevel[lv].push(n);
  });

  // Sort levels cleanly and order each column by parent average Y + branch priority (barycenter ordering)
  Object.keys(byLevel).map(Number).sort((a, b) => a - b).forEach(lv => {
    const grp = byLevel[lv];
    if (lv > 0) {
      grp.sort((a, b) => {
        const score = (node) => {
          const ps = parents[node.id] || [];
          if (!ps.length) return Number(node.y || 0);
          let sum = 0;
          ps.forEach(pe => {
            const pNode = nodeById[pe.source];
            const cond = (pe.condition || '').toLowerCase();
            const branchBias = (cond === 'true' || cond === 'route_1') ? -40 : (cond === 'route_2' ? 0 : (cond === 'false' || cond === 'default') ? 40 : 0);
            sum += (pNode ? Number(pNode.y || 0) : 0) + branchBias;
          });
          return sum / ps.length;
        };
        return score(a) - score(b);
      });
    }
    const startY = grp.length === 1 ? 160 : 60;
    grp.forEach((n, idx) => {
      n.x = snapCoord(40 + lv * 300);
      n.y = snapCoord(startY + idx * 160);
    });
  });

  markWfDirty();
  fitCanvasToView();
  wfToast('📐 ক্যানভাস ও তার অটো-অ্যালাইন + ফিট সম্পন্ন হয়েছে।', 'info');
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
  const canUndo = wfState.undoStack.length > 0;
  const canRedo = wfState.redoStack.length > 0;

  bar.innerHTML = `
    <div class="wf-tb-left">
      <button type="button" class="wf-tb-btn wf-btn-mini ${wfState.leftCollapsed ? 'active' : ''}" onclick="toggleStudioPane('left')" title="বাম প্যানেল লুকান/দেখান">◧</button>
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
      <button type="button" class="wf-tb-btn wf-btn-mini" ${canUndo ? '' : 'disabled style="opacity:0.4;"'} onclick="undoWorkflowChange()" title="Undo (Ctrl+Z)">↩️</button>
      <button type="button" class="wf-tb-btn wf-btn-mini" ${canRedo ? '' : 'disabled style="opacity:0.4;"'} onclick="redoWorkflowChange()" title="Redo (Ctrl+Y)">↪️</button>
      <div class="wf-zoom-group">
        <button type="button" class="wf-tb-btn wf-btn-mini" onclick="setCanvasZoom(-0.1)" title="Zoom Out">-</button>
        <button type="button" class="wf-tb-btn wf-btn-mini" onclick="setCanvasZoom(0)" title="Reset 100%">${zoomPct}%</button>
        <button type="button" class="wf-tb-btn wf-btn-mini" onclick="setCanvasZoom(0.1)" title="Zoom In">+</button>
        <button type="button" class="wf-tb-btn wf-btn-mini" onclick="fitCanvasToView()" title="Fit Workflow to View (F)">⛶</button>
      </div>
      <button type="button" class="wf-tb-btn" onclick="autoLayoutWorkflow()" title="অটো-অ্যালাইন ও ফিট">📐</button>
      <button type="button" class="wf-tb-btn ${wfState.fullscreenCanvas ? 'active' : ''}" onclick="toggleFullscreenCanvas()" title="ক্যানভাস বড়/ফুলস্ক্রিন করুন">🖥️</button>
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
      <button type="button" class="wf-tb-btn wf-btn-mini ${wfState.rightCollapsed ? 'active' : ''}" onclick="toggleStudioPane('right')" title="ডান ইন্সপেক্টর লুকান/দেখান">◨</button>
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
    case 'mcp_tool':
      return `🔌 MCP: ${c.tool_name || 'select tool'}${c.server_id ? ' @ ' + c.server_id : ''}`;
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
    maxX = Math.max(maxX, (Number(n.x) || 0) + 360);
    maxY = Math.max(maxY, (Number(n.y) || 0) + 260);
  });
  wfState.stageWidth = maxX;
  wfState.stageHeight = maxY;
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
            ${!isTrig ? `<button type="button" class="wf-node-mini-btn wf-node-run-mini" onclick="runNodeQuickTestFromCard(event, '${wfEsc(node.id)}')" title="এক-ক্লিক সিঙ্গেল নোড টেস্ট">🧪</button>` : ''}
            ${!isTrig ? `<button type="button" class="wf-node-mini-btn" onclick="toggleNodeDisabled(event, '${wfEsc(node.id)}')" title="${isDisabled ? 'সক্রিয় করুন' : 'মিউট/বাইপাস করুন'}">${isDisabled ? '▶️' : '⏸️'}</button>` : ''}
            <button type="button" class="wf-node-mini-btn" onclick="duplicateNodeById(event, '${wfEsc(node.id)}')" title="নোড ডুপ্লিকেট (Ctrl+D)">❐</button>
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
  renderCanvasHud();
  renderCanvasMinimap();
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
    const condTxt = cond ? cond.replace('route_', 'R').toUpperCase() : '';

    return `
      <g class="wf-edge-group">
        <path class="wf-edge-hit" d="${d}" fill="none" stroke="transparent" stroke-width="16"></path>
        <path class="wf-edge-path ${isFlowActive ? 'wf-edge-animated' : ''}" d="${d}" fill="none" stroke="${color}" stroke-width="2.4" marker-end="${marker}"></path>
        <g class="wf-edge-controls" transform="translate(${mx}, ${my})">
          ${condTxt ? `
            <rect x="-24" y="-24" width="48" height="15" rx="7" fill="#0f172a" stroke="${color}" stroke-width="1.2"></rect>
            <text x="0" y="-13" text-anchor="middle" fill="${color}" font-size="8.5" font-weight="800" font-family="Fira Code, monospace">${wfEsc(condTxt)}</text>
          ` : ''}
          <g class="wf-edge-plus-btn" onclick="openQuickPickerForEdge(event, '${wfEsc(edge.id)}')" title="মাঝে নতুন নোড যোগ করুন (+)">
            <circle cx="-11" cy="0" r="10" fill="#0f172a" stroke="#10b981" stroke-width="1.5"></circle>
            <text x="-11" y="4" text-anchor="middle" fill="#34d399" font-size="13" font-weight="800">+</text>
          </g>
          <g class="wf-edge-del-btn" onclick="removeEdgeById('${wfEsc(edge.id)}', event)" title="সংযোগ মুছে ফেলুন">
            <circle cx="11" cy="0" r="10" fill="#0f172a" stroke="#f43f5e" stroke-width="1.4"></circle>
            <text x="11" y="3.5" text-anchor="middle" fill="#fda4af" font-size="10.5" font-weight="800">✕</text>
          </g>
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
    const cond = (wfState.connectingFrom.condition || '').toLowerCase();
    if (srcNode.type === 'condition') {
      sy = Number(srcNode.y || 0) + (cond === 'false' ? h * 0.72 : h * 0.32);
    } else if (srcNode.type === 'switch_router') {
      sy = Number(srcNode.y || 0) + (cond === 'route_1' ? h * 0.24 : cond === 'route_2' ? h * 0.52 : h * 0.80);
    }
    const tx = wfState.mouseCanvasX || (sx + 80);
    const ty = wfState.mouseCanvasY || sy;
    tempWire = `<path d="M ${sx} ${sy} L ${tx} ${ty}" stroke="#38bdf8" stroke-width="2" stroke-dasharray="5,5" fill="none"></path>`;
  }

  svg.setAttribute('width', stage.offsetWidth || 1400);
  svg.setAttribute('height', stage.offsetHeight || 600);
  svg.innerHTML = defs + paths + tempWire;
}

function renderCanvasHud() {
  const hud = document.getElementById('wf-canvas-hud');
  if (!hud) return;
  const wf = wfState.activeWorkflow;
  const nCnt = wf ? (wf.nodes || []).length : 0;
  const eCnt = wf ? (wf.edges || []).length : 0;
  const zoomPct = Math.round((wfState.zoom || 1) * 100);
  hud.innerHTML = `
    <span class="wf-hud-stat">${nCnt} Nodes • ${eCnt} Edges</span>
    <button type="button" class="wf-hud-btn" onclick="setCanvasZoom(-0.1)" title="Zoom Out">-</button>
    <button type="button" class="wf-hud-btn" onclick="setCanvasZoom(0)" title="100% Zoom">${zoomPct}%</button>
    <button type="button" class="wf-hud-btn" onclick="setCanvasZoom(0.1)" title="Zoom In">+</button>
    <button type="button" class="wf-hud-btn" onclick="fitCanvasToView()" title="Fit Workflow (F)">⛶ Fit</button>
    <button type="button" class="wf-hud-btn ${wfState.snapGrid ? 'active' : ''}" onclick="toggleGridSnap()" title="20px Grid Snap">${wfState.snapGrid ? '🧲 Snap' : 'Free'}</button>
    <button type="button" class="wf-hud-btn" onclick="autoLayoutWorkflow()" title="অটো-অ্যালাইন ও ফিট">📐</button>
  `;
}

function renderCanvasMinimap() {
  const mm = document.getElementById('wf-canvas-minimap');
  const vp = document.getElementById('wf-canvas-viewport');
  const wf = wfState.activeWorkflow;
  if (!mm || !vp || !wf || !(wf.nodes || []).length) {
    if (mm) mm.innerHTML = '';
    return;
  }

  const mw = 156, mh = 92;
  const stW = Math.max(wfState.stageWidth || 1200, 1200);
  const stH = Math.max(wfState.stageHeight || 540, 540);
  const scale = Math.min(mw / stW, mh / stH);
  const zoom = wfState.zoom || 1;

  const rects = (wf.nodes || []).map(n => {
    const meta = wfNodeMeta(n.type);
    const rx = Math.round(Number(n.x || 0) * scale);
    const ry = Math.round(Number(n.y || 0) * scale);
    const rw = Math.max(10, Math.round(230 * scale));
    const rh = Math.max(6, Math.round(92 * scale));
    const isSel = wfState.selectedNodeId === n.id;
    return `<rect x="${rx}" y="${ry}" width="${rw}" height="${rh}" rx="2" fill="${meta.color || '#38bdf8'}" fill-opacity="${isSel ? '1' : '0.68'}" stroke="${isSel ? '#ffffff' : 'none'}" stroke-width="1"></rect>`;
  }).join('');

  const vx = Math.round((vp.scrollLeft / zoom) * scale);
  const vy = Math.round((vp.scrollTop / zoom) * scale);
  const vw = Math.min(mw, Math.round((vp.clientWidth / zoom) * scale));
  const vh = Math.min(mh, Math.round((vp.clientHeight / zoom) * scale));

  mm.innerHTML = `
    <svg width="${mw}" height="${mh}" viewBox="0 0 ${mw} ${mh}" onclick="jumpCanvasFromMinimap(event, ${scale}, ${mw}, ${mh})">
      ${rects}
      <rect x="${vx}" y="${vy}" width="${vw}" height="${vh}" fill="rgba(56,189,248,0.12)" stroke="#38bdf8" stroke-width="1.3"></rect>
    </svg>
  `;
}

function jumpCanvasFromMinimap(event, scale) {
  event.stopPropagation();
  const vp = document.getElementById('wf-canvas-viewport');
  const svg = event.currentTarget;
  if (!vp || !svg) return;
  const rect = svg.getBoundingClientRect();
  const zoom = wfState.zoom || 1;
  const targetCanvasX = (event.clientX - rect.left) / scale;
  const targetCanvasY = (event.clientY - rect.top) / scale;
  vp.scrollLeft = Math.max(0, targetCanvasX * zoom - vp.clientWidth / 2);
  vp.scrollTop = Math.max(0, targetCanvasY * zoom - vp.clientHeight / 2);
  renderCanvasMinimap();
}

// Floating Quick Node Picker (Canvas Double-Click / Edge Mid-Insert)
function onCanvasDoubleClick(event) {
  if (event.target.closest('.wf-node-card') || event.target.closest('.wf-edge-controls')) return;
  const stage = document.getElementById('wf-canvas-stage');
  if (!stage || !wfState.activeWorkflow) return;
  const rect = stage.getBoundingClientRect();
  const zoom = wfState.zoom || 1;
  const cx = snapCoord((event.clientX - rect.left) / zoom - 110);
  const cy = snapCoord((event.clientY - rect.top) / zoom - 40);
  openQuickPicker({ mode: 'canvas', canvasX: cx, canvasY: cy, clientX: event.clientX, clientY: event.clientY });
}

function openQuickPickerForEdge(event, edgeId) {
  if (event) event.stopPropagation();
  openQuickPicker({ mode: 'edge', edgeId, clientX: event ? event.clientX : 400, clientY: event ? event.clientY : 300 });
}

function openQuickPicker(opts) {
  const picker = document.getElementById('wf-quick-picker');
  const wrap = picker ? picker.parentElement : null;
  if (!picker || !wrap) return;
  wfState.quickPicker = opts;
  const wrapRect = wrap.getBoundingClientRect();
  const left = Math.max(12, Math.min(wrapRect.width - 270, (opts.clientX || wrapRect.left + 140) - wrapRect.left - 120));
  const top = Math.max(12, Math.min(wrapRect.height - 290, (opts.clientY || wrapRect.top + 100) - wrapRect.top - 20));
  picker.style.left = `${left}px`;
  picker.style.top = `${top}px`;
  picker.style.display = 'flex';
  const titleTxt = opts.mode === 'edge' ? '➕ তারের মাঝে নোড যোগ করুন' : '⚡ ক্যানভাসে দ্রুত নোড যোগ করুন';
  picker.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; gap:6px;">
      <strong style="font-size:0.78rem; color:#38bdf8;">${titleTxt}</strong>
      <button type="button" class="wf-node-del-btn" onclick="closeQuickPicker()">&times;</button>
    </div>
    <input type="text" id="wf-qp-search" class="text-input" style="padding:5px 8px; font-size:0.76rem;" placeholder="🔍 সার্চ (python, switch, db, telegram...)" oninput="renderQuickPickerList(this.value)">
    <div id="wf-qp-list" class="wf-qp-list"></div>
  `;
  renderQuickPickerList('');
  setTimeout(() => document.getElementById('wf-qp-search')?.focus(), 20);
}

function renderQuickPickerList(q = '') {
  const listEl = document.getElementById('wf-qp-list');
  if (!listEl) return;
  const low = String(q || '').trim().toLowerCase();
  const items = (wfState.nodeCatalog || []).filter(c => {
    if (wfState.quickPicker?.mode === 'edge' && (c.type || '').startsWith('trigger_')) return false;
    if (!low) return true;
    return `${c.type} ${c.label_bn || ''} ${c.label_en || ''}`.toLowerCase().includes(low);
  });
  listEl.innerHTML = items.map(c => `
    <button type="button" class="wf-qp-item" onclick="pickQuickPickerNode('${wfEsc(c.type)}')">
      <span>${wfEsc(c.icon)}</span>
      <span style="flex:1; text-align:left;">${wfEsc(c.label_bn || c.label_en)}</span>
      <span style="font-size:0.68rem; color:var(--text-muted);">${wfEsc(c.category)}</span>
    </button>
  `).join('') || '<div class="wf-empty-hint">মিল পাওয়া যায়নি।</div>';
}

function pickQuickPickerNode(nodeType) {
  const opts = wfState.quickPicker;
  const wf = wfState.activeWorkflow;
  closeQuickPicker();
  if (!wf || !opts) return;

  if (opts.mode === 'edge' && opts.edgeId) {
    const oldEdgeIdx = (wf.edges || []).findIndex(e => e.id === opts.edgeId);
    if (oldEdgeIdx === -1) return;
    pushUndoSnapshot();
    const oldEdge = wf.edges[oldEdgeIdx];
    const srcNode = (wf.nodes || []).find(n => n.id === oldEdge.source);
    const tgtNode = (wf.nodes || []).find(n => n.id === oldEdge.target);
    const midX = srcNode && tgtNode ? snapCoord((Number(srcNode.x || 0) + Number(tgtNode.x || 0)) / 2) : 340;
    const midY = srcNode && tgtNode ? snapCoord((Number(srcNode.y || 0) + Number(tgtNode.y || 0)) / 2) : 160;

    // Create node without taking duplicate undo or auto-wiring anchor
    const meta = wfNodeMeta(nodeType);
    const newId = _nextNodeId(wf.nodes);
    const newNode = {
      id: newId,
      type: nodeType,
      title: meta.label_bn || meta.label_en || nodeType,
      x: midX,
      y: midY,
      disabled: false,
      config: wfClone(meta.default_config || {})
    };
    wf.nodes.push(newNode);
    // Shift downstream target slightly right if cramped cleanly
    if (tgtNode && Math.abs((tgtNode.x || 0) - midX) < 250) {
      tgtNode.x = snapCoord(midX + 280);
    }
    // Split oldEdge cleanly into source->newNode and newNode->target
    const condOut = nodeType === 'condition' ? 'true' : (nodeType === 'switch_router' ? 'route_1' : '');
    wf.edges.splice(oldEdgeIdx, 1,
      { id: `e_${Date.now().toString(36)}_1`, source: oldEdge.source, target: newId, condition: oldEdge.condition || '' },
      { id: `e_${Date.now().toString(36)}_2`, source: newId, target: oldEdge.target, condition: condOut }
    );
    wfState.selectedNodeId = newId;
    markWfDirty();
    renderWorkflowToolbar();
    renderWorkflowCanvas();
    renderNodeInspector();
    switchWfInspectorTab('node');
    wfToast(`➕ তারের মাঝে "${newNode.title}" যুক্ত হয়েছে!`, 'success');
    return;
  }

  addNodeToCanvas(nodeType, opts.canvasX, opts.canvasY, false);
}

function closeQuickPicker() {
  wfState.quickPicker = null;
  const picker = document.getElementById('wf-quick-picker');
  if (picker) picker.style.display = 'none';
}

async function runNodeQuickTestFromCard(event, nodeId) {
  if (event) event.stopPropagation();
  wfState.selectedNodeId = nodeId;
  renderWorkflowCanvas();
  renderNodeInspector();
  switchWfInspectorTab('node');
  await testSelectedNode();
}

// Canvas Viewport Pan, Wheel Zoom, Node Dragging & Port Wiring
function onViewportMouseDown(event) {
  if (
    event.button !== 0 && event.button !== 1
  ) return;
  if (
    event.target.closest('.wf-node-card') ||
    event.target.closest('.wf-edge-controls') ||
    event.target.closest('.wf-canvas-hud') ||
    event.target.closest('.wf-canvas-minimap') ||
    event.target.closest('.wf-quick-picker')
  ) {
    return;
  }
  const vp = document.getElementById('wf-canvas-viewport');
  if (!vp) return;
  wfState.panState = {
    startX: event.clientX,
    startY: event.clientY,
    scrollLeft: vp.scrollLeft,
    scrollTop: vp.scrollTop,
    moved: false
  };
  vp.classList.add('wf-panning');
}

function onCanvasWheel(event) {
  if (!(event.ctrlKey || event.metaKey)) return;
  event.preventDefault();
  const delta = event.deltaY < 0 ? 0.08 : -0.08;
  setCanvasZoom(delta);
}

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
  wfState.dragMoved = false;
  wfState.dragSnapshotTaken = false;
  wfState.dragOffsetX = (event.clientX - stageRect.left) / zoom - Number(node.x || 0);
  wfState.dragOffsetY = (event.clientY - stageRect.top) / zoom - Number(node.y || 0);
}

document.addEventListener('mousemove', (event) => {
  if (wfState.panState) {
    const vp = document.getElementById('wf-canvas-viewport');
    if (vp) {
      const dx = event.clientX - wfState.panState.startX;
      const dy = event.clientY - wfState.panState.startY;
      if (Math.abs(dx) > 3 || Math.abs(dy) > 3) wfState.panState.moved = true;
      vp.scrollLeft = wfState.panState.scrollLeft - dx;
      vp.scrollTop = wfState.panState.scrollTop - dy;
      renderCanvasMinimap();
    }
    return;
  }

  const stage = document.getElementById('wf-canvas-stage');
  if (!stage) return;
  const zoom = wfState.zoom || 1.0;

  if (wfState.draggingNodeId && wfState.activeWorkflow) {
    const node = (wfState.activeWorkflow.nodes || []).find(n => n.id === wfState.draggingNodeId);
    if (!node) return;
    if (!wfState.dragSnapshotTaken) {
      pushUndoSnapshot();
      wfState.dragSnapshotTaken = true;
    }
    const nx = snapCoord((event.clientX - stage.getBoundingClientRect().left) / zoom - wfState.dragOffsetX);
    const ny = snapCoord((event.clientY - stage.getBoundingClientRect().top) / zoom - wfState.dragOffsetY);
    if (nx !== node.x || ny !== node.y) {
      wfState.dragMoved = true;
      node.x = nx;
      node.y = ny;

      const card = document.getElementById(`wf-card-${node.id}`);
      if (card) {
        card.style.left = `${nx}px`;
        card.style.top = `${ny}px`;
      }
      markWfDirty();
      drawWorkflowEdges();
      renderCanvasMinimap();
    }
  } else if (wfState.connectingFrom) {
    const stageRect = stage.getBoundingClientRect();
    wfState.mouseCanvasX = (event.clientX - stageRect.left) / zoom;
    wfState.mouseCanvasY = (event.clientY - stageRect.top) / zoom;
    drawWorkflowEdges();
  }
});

document.addEventListener('mouseup', () => {
  if (wfState.panState) {
    const vp = document.getElementById('wf-canvas-viewport');
    if (vp) vp.classList.remove('wf-panning');
    wfState.justPanned = !!wfState.panState.moved;
    wfState.panState = null;
    if (wfState.justPanned) setTimeout(() => { wfState.justPanned = false; }, 60);
  }
  if (wfState.draggingNodeId) {
    wfState.draggingNodeId = null;
    wfState.dragMoved = false;
    wfState.dragSnapshotTaken = false;
    renderWorkflowToolbar();
  }
});

document.addEventListener('keydown', (e) => {
  const viewWf = document.getElementById('view-workflows');
  if (!viewWf || !viewWf.classList.contains('active')) return;
  if (wfState.subTab !== 'studio') return;

  if (e.key === 'Escape') {
    if (wfState.quickPicker) { closeQuickPicker(); return; }
    if (wfState.connectingFrom) { wfState.connectingFrom = null; renderWorkflowCanvas(); return; }
    if (wfState.fullscreenCanvas) { toggleFullscreenCanvas(false); return; }
  }

  const tag = (document.activeElement?.tagName || '').toLowerCase();
  const isTyping = ['input', 'textarea', 'select'].includes(tag);

  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
    e.preventDefault();
    saveActiveWorkflow();
    return;
  }

  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    e.preventDefault();
    runActiveWorkflowNow();
    return;
  }

  if (isTyping) return;

  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') {
    e.preventDefault();
    if (e.shiftKey) redoWorkflowChange();
    else undoWorkflowChange();
    return;
  }

  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'y') {
    e.preventDefault();
    redoWorkflowChange();
    return;
  }

  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'd') {
    e.preventDefault();
    if (wfState.selectedNodeId) duplicateNodeById(null, wfState.selectedNodeId);
    return;
  }

  if (e.key.toLowerCase() === 'f' && !e.ctrlKey && !e.metaKey) {
    e.preventDefault();
    fitCanvasToView();
    return;
  }

  if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key) && wfState.selectedNodeId && wfState.activeWorkflow) {
    e.preventDefault();
    const node = (wfState.activeWorkflow.nodes || []).find(n => n.id === wfState.selectedNodeId);
    if (!node) return;
    pushUndoSnapshot();
    const step = e.shiftKey ? 5 : 20;
    if (e.key === 'ArrowLeft') node.x = Math.max(12, Number(node.x || 0) - step);
    if (e.key === 'ArrowRight') node.x = Number(node.x || 0) + step;
    if (e.key === 'ArrowUp') node.y = Math.max(12, Number(node.y || 0) - step);
    if (e.key === 'ArrowDown') node.y = Number(node.y || 0) + step;
    markWfDirty();
    renderWorkflowCanvas();
    return;
  }

  if ((e.key === 'Delete' || e.key === 'Backspace') && wfState.selectedNodeId) {
    deleteNodeById(null, wfState.selectedNodeId);
  }
});

function onNodeCardClick(event, nodeId) {
  event.stopPropagation();
  closeQuickPicker();
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
  renderCanvasMinimap();
  switchWfInspectorTab('node');
}

function onOutputPortClick(event, nodeId, condition = '') {
  event.stopPropagation();
  closeQuickPicker();
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
  if (wfState.justPanned) return;
  closeQuickPicker();
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
    pushUndoSnapshot();
    wf.edges.push({
      id: `e_${Date.now().toString(36)}_${Math.floor(Math.random() * 100)}`,
      source: sourceId,
      target: targetId,
      condition: condition || ''
    });
    markWfDirty();
    wfToast(`🔗 সংযোগ তৈরি হয়েছে (${sourceId} → ${targetId})`, 'success');
  }
  renderWorkflowToolbar();
  renderWorkflowCanvas();
  renderNodeInspector();
}

function removeEdgeById(edgeId, event = null) {
  if (event) event.stopPropagation();
  const wf = wfState.activeWorkflow;
  if (!wf) return;
  pushUndoSnapshot();
  wf.edges = (wf.edges || []).filter(e => e.id !== edgeId);
  markWfDirty();
  renderWorkflowToolbar();
  renderWorkflowCanvas();
  renderNodeInspector();
}

function deleteNodeById(event, nodeId) {
  if (event) event.stopPropagation();
  const wf = wfState.activeWorkflow;
  if (!wf) return;
  pushUndoSnapshot();
  wf.nodes = (wf.nodes || []).filter(n => n.id !== nodeId);
  wf.edges = (wf.edges || []).filter(e => e.source !== nodeId && e.target !== nodeId);
  if (wfState.selectedNodeId === nodeId) {
    wfState.selectedNodeId = wf.nodes[0] ? wf.nodes[0].id : null;
  }
  markWfDirty();
  renderWorkflowToolbar();
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
        <label><input type="checkbox" ${c.enable_tools !== false ? 'checked' : ''} onchange="updateNodeCfg('enable_tools', this.checked)"> 🛠️ Built-in Tools</label>
        <label title="প্রয়োজন হলে MCP Hub-এ নিবন্ধিত এক্সটার্নাল MCP টুল ব্যবহার করবে"><input type="checkbox" ${c.use_mcp !== false ? 'checked' : ''} onchange="updateNodeCfg('use_mcp', this.checked)"> 🔌 Use MCP if Needed</label>
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
    const toolOpts = (wfState.tools || []).map(t => {
      const tag = t.source === 'mcp' ? '[MCP] ' : '';
      return `<option value="${wfEsc(t.name)}" ${(c.tool_name || 'system_info') === t.name ? 'selected' : ''}>${tag}${wfEsc(t.name)}</option>`;
    }).join('');
    fieldsHtml = `
      <div class="wf-field-group">
        <label>টুল নির্বাচন (Built-in + MCP Tools)</label>
        <select class="text-input" onchange="updateNodeCfg('tool_name', this.value)">${toolOpts}</select>
      </div>
      <div class="wf-field-group">
        <label>আর্গুমেন্ট JSON</label>
        <textarea id="wf-cfg-args" class="text-input wf-code-textarea" rows="3"
                  onfocus="wfState.lastFocusedFieldId='wf-cfg-args'"
                  onchange="updateNodeCfg('args_json', this.value)">${wfEsc(typeof c.args_json === 'string' ? c.args_json : JSON.stringify(c.args_json || {}, null, 2))}</textarea>
      </div>
    `;
  } else if (node.type === 'mcp_tool') {
    const servers = wfState.mcpServers || [];
    const activeServers = servers.filter(s => s.is_enabled !== false);
    const selectedSid = c.server_id || '';
    const srvOpts = [
      `<option value="" ${!selectedSid ? 'selected' : ''}>⚡ Auto (যেকোনো সক্রিয় MCP সার্ভার)</option>`,
      ...servers.map(s => `<option value="${wfEsc(s.id)}" ${selectedSid === s.id ? 'selected' : ''}>🔌 ${wfEsc(s.name)} (${wfEsc(s.transport)} • ${(s.tools_cache || []).length} tools)</option>`)
    ].join('');

    const mcpToolsList = [];
    activeServers.forEach(s => {
      if (selectedSid && s.id !== selectedSid) return;
      (s.tools_cache || []).forEach(t => {
        mcpToolsList.push({ ...t, serverName: s.name, serverId: s.id });
      });
    });
    const curTool = c.tool_name || (mcpToolsList[0] ? mcpToolsList[0].name : '');
    const matchedSchema = mcpToolsList.find(t => t.name === curTool);
    const toolSelectOpts = mcpToolsList.map(t =>
      `<option value="${wfEsc(t.name)}" ${curTool === t.name ? 'selected' : ''}>[${wfEsc(t.serverName)}] ${wfEsc(t.name)}</option>`
    );
    if (curTool && !matchedSchema) {
      toolSelectOpts.unshift(`<option value="${wfEsc(curTool)}" selected>${wfEsc(curTool)} (Custom / Cached)</option>`);
    }
    const schemaProps = matchedSchema?.inputSchema?.properties ? Object.keys(matchedSchema.inputSchema.properties) : [];

    fieldsHtml = `
      <div style="display:flex; justify-content:space-between; align-items:center; gap:6px; margin-bottom:6px; flex-wrap:wrap;">
        <span style="font-size:0.74rem; color:#a5b4fc; font-weight:700;">🔌 Active MCP Servers: ${activeServers.length}</span>
        <div style="display:flex; gap:5px;">
          <button type="button" class="wf-chip-btn" onclick="refreshWorkflowMcpServer('${wfEsc(selectedSid || (activeServers[0]?.id || ''))}')" title="MCP টুল লিস্ট রিফ্রেশ">🔄 Ping/Refresh</button>
          <button type="button" class="wf-chip-btn" onclick="switchTab('mcp')">⚙️ MCP Hub</button>
        </div>
      </div>
      <div class="wf-field-group">
        <label>টার্গেট MCP সার্ভার</label>
        <select class="text-input" onchange="updateNodeCfg('server_id', this.value); renderNodeInspector();">${srvOpts}</select>
      </div>
      <div class="wf-field-group">
        <label>আবিষ্কৃত MCP টুল (Discovered Tool)</label>
        <select class="text-input" onchange="updateNodeCfg('tool_name', this.value); renderNodeInspector();">${toolSelectOpts.join('') || '<option value="">কোনো MCP টুল নেই</option>'}</select>
      </div>
      <div class="wf-field-group">
        <label>কাস্টম Tool Name (ঐচ্ছিক ওভাররাইড)</label>
        <input type="text" class="text-input" value="${wfEsc(c.tool_name || '')}" placeholder="e.g. fetch_article_markdown" onchange="updateNodeCfg('tool_name', this.value)">
      </div>
      ${matchedSchema ? `
        <div style="font-size:0.72rem; color:var(--text-muted); padding:6px 8px; border-radius:6px; background:rgba(99,102,241,0.08); border:1px solid rgba(99,102,241,0.22);">
          <div>${wfEsc(matchedSchema.description || '')}</div>
          ${schemaProps.length ? `<div style="margin-top:3px;">Params: <code>${wfEsc(schemaProps.join(', '))}</code> <button type="button" class="wf-chip-btn" style="margin-left:6px;" onclick="applyMcpSampleArgs()">📋 Sample JSON</button></div>` : ''}
        </div>
      ` : ''}
      <div class="wf-field-group">
        <label>MCP টুল আর্গুমেন্ট (JSON)</label>
        <textarea id="wf-cfg-mcpargs" class="text-input wf-code-textarea" rows="3"
                  onfocus="wfState.lastFocusedFieldId='wf-cfg-mcpargs'"
                  onchange="updateNodeCfg('args_json', this.value)">${wfEsc(typeof c.args_json === 'string' ? c.args_json : JSON.stringify(c.args_json || {}, null, 2))}</textarea>
        ${varsHtml}
      </div>
      <label style="font-size:0.76rem; cursor:pointer;"><input type="checkbox" ${c.fallback_on_error ? 'checked' : ''} onchange="updateNodeCfg('fallback_on_error', this.checked)"> MCP ত্রুটি হলেও ওয়ার্কফ্লো চালু রাখুন</label>
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
    if (tg.polling_active) parts.push('<span style="color:#34d399; font-weight:700;">📡 Two-Way Chat: LIVE</span>');
    parts.push(`Sent: <strong style="color:#10b981;">${tg.sent_count || 0}</strong> • Failed: <strong style="color:#f43f5e;">${tg.failed_count || 0}</strong> • Chats: <strong>${tg.total_chats || 0}</strong>`);
    if (tg.last_verified_at) parts.push(`Verified: ${wfEsc(tg.last_verified_at)}`);
    if (tg.last_tested_at) parts.push(`Tested: ${wfEsc(tg.last_tested_at)}`);
    if (tg.last_error || tg.poll_error) parts.push(`<span style="color:#fda4af;">ত্রুটি: ${wfEsc(tg.last_error || tg.poll_error)}</span>`);
    metaEl.innerHTML = parts.length ? parts.join(' &nbsp;|&nbsp; ') : 'নিচের ফর্মে @BotFather টোকেন ও Chat ID দিয়ে কানেক্ট করুন।';
  }

  // 4. Populate Form Inputs safely
  const tokenInput = document.getElementById('wf-tg-token-input');
  const tokenHint = document.getElementById('wf-tg-token-hint');
  const chatInput = document.getElementById('wf-tg-chatid-input');
  const enChk = document.getElementById('wf-tg-enabled-chk');
  const interChk = document.getElementById('wf-tg-interactive-chk');
  const autoRepChk = document.getElementById('wf-tg-autoreport-chk');
  const allowedInput = document.getElementById('wf-tg-allowed-chats');

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
  if (allowedInput && document.activeElement !== allowedInput && !allowedInput.value && tg.allowed_chat_ids) {
    allowedInput.value = tg.allowed_chat_ids;
  }
  if (enChk) {
    enChk.checked = tg.has_token ? !!tg.is_enabled : true;
  }
  if (interChk) {
    interChk.checked = tg.interactive_chat_enabled !== false;
  }
  if (autoRepChk) {
    autoRepChk.checked = tg.auto_send_reports !== false;
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
  const interactive_chat_enabled = !!document.getElementById('wf-tg-interactive-chk')?.checked;
  const auto_send_reports = !!document.getElementById('wf-tg-autoreport-chk')?.checked;
  const allowed_chat_ids = document.getElementById('wf-tg-allowed-chats')?.value?.trim() || '';

  const btn = document.getElementById('btn-wf-tg-connect');
  if (btn) { btn.disabled = true; btn.textContent = '⏳ যাচাই ও কানেক্ট হচ্ছে...'; }

  try {
    const res = await wfFetch('/api/workflows/telegram/connect', {
      method: 'POST',
      body: JSON.stringify({
        bot_token,
        chat_id,
        is_enabled,
        verify_live,
        interactive_chat_enabled,
        auto_send_reports,
        allowed_chat_ids
      })
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

function renderTelegramLatestStrip(digest = null) {
  const el = document.getElementById('wf-tg-latest-chat-text');
  if (!el) return;
  const chats = wfState.telegramChats || [];
  if (chats.length > 0) {
    const c = chats[0];
    const firstReplyLine = String(c.reply_message || '').split('\n').slice(0, 2).join(' — ');
    el.innerHTML = `<strong>[${wfEsc((c.intent || c.direction || 'CHAT').toUpperCase())}]</strong> “${wfEsc((c.user_message || '').slice(0, 70))}” &nbsp;➔&nbsp; <span style="color:#34d399;">${wfEsc(firstReplyLine.slice(0, 140))}</span> <span style="color:var(--text-muted); font-size:0.72rem;">(${wfEsc(c.created_at)})</span>`;
  } else if (digest && digest.summary_line) {
    el.innerHTML = `📊 ${wfEsc(digest.summary_line)} — Telegram বটে <code>ping 192.168.9.2</code> বা <code>/status</code> লিখে চ্যাট করুন!`;
  }
}

async function refreshWorkflowTelegramChats() {
  const feedEl = document.getElementById('wf-tg-chat-feed');
  try {
    const res = await wfFetch('/api/workflows/telegram/chats?limit=35');
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.detail || 'Chat load failed');
    wfState.telegramChats = data.chats || [];
    if (data.telegram) {
      wfState.telegram = data.telegram;
      renderTelegramStatusUI();
    }
    renderTelegramLatestStrip(data.workflow_digest || null);
    renderTelegramChatFeed();
  } catch (err) {
    if (feedEl) feedEl.innerHTML = `<div style="color:#f43f5e; padding:12px;">${wfEsc(err.message)}</div>`;
  }
}

function renderTelegramChatFeed() {
  const feedEl = document.getElementById('wf-tg-chat-feed');
  if (!feedEl) return;
  const chats = wfState.telegramChats || [];
  if (!chats.length) {
    feedEl.innerHTML = '<div class="wf-empty-hint">এখনও কোনো Telegram চ্যাট বা ওয়ার্কফ্লো রিপোর্ট নেই। উপরের বক্সে যেমন <code>ping 192.168.9.2 server and let me show status</code> লিখে টেস্ট করুন বা টেলিগ্রাম বটে মেসেজ দিন!</div>';
    return;
  }

  feedEl.innerHTML = chats.map(c => {
    const st = String(c.status || 'SUCCESS').toUpperCase();
    const badgeCls = (st === 'SUCCESS' || st === 'SENT' || st === 'CONNECTED') ? 'ok' : (st === 'WARN' ? 'muted' : 'err');
    const intentIcon = {
      ping: '📡 Ping & Status',
      port_scan: '🔍 Port Scan',
      workflow_status: '📊 WORKFLOWS Status',
      workflow_report: '📢 Auto Report',
      workflow_run: '⚡ Workflow Run',
      workflow_create: '🧠 Created Workflow',
      help: 'ℹ️ Help / ID',
      ai_chat: '🤖 AI Reply'
    }[c.intent] || `💬 ${c.intent || 'Chat'}`;

    return `
      <div class="wf-tg-chat-item">
        <div class="wf-tg-chat-head">
          <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
            <span class="wf-tg-intent-pill">${wfEsc(intentIcon)}</span>
            <strong style="font-size:0.8rem; color:var(--text-primary);">${wfEsc(c.sender_name || c.chat_id)}</strong>
            <code style="font-size:0.71rem;">Chat: ${wfEsc(c.chat_id)}</code>
          </div>
          <div style="display:flex; align-items:center; gap:8px;">
            <span style="font-size:0.71rem; color:var(--text-muted);">🕒 ${wfEsc(c.created_at)}${c.latency_ms ? ' • ' + c.latency_ms + 'ms' : ''}</span>
            <span class="wf-tg-log-badge ${badgeCls}">${wfEsc(st)}</span>
          </div>
        </div>
        <div class="wf-tg-chat-user">👤 <strong>Chat Message:</strong> ${wfEsc(c.user_message)}</div>
        <pre class="wf-tg-chat-reply">${wfEsc(c.reply_message)}</pre>
        ${c.workflow_status_summary ? `<div class="wf-tg-chat-wfbar">⚡ WORKFLOWS (Auto): ${wfEsc(c.workflow_status_summary)}</div>` : ''}
      </div>
    `;
  }).join('');
}

async function submitTelegramChatCommand(event) {
  if (event) event.preventDefault();
  const inp = document.getElementById('wf-tg-cmd-input');
  const sendChk = document.getElementById('wf-tg-cmd-send-tg-chk');
  const btn = document.getElementById('btn-wf-tg-cmd-run');
  const message = inp?.value?.trim();
  if (!message) {
    wfToast('কমান্ড বা প্রশ্ন লিখুন (যেমন: ping 192.168.9.2 server and show status)', 'warning');
    return;
  }

  if (btn) { btn.disabled = true; btn.textContent = '⏳ চলছে...'; }
  try {
    const res = await wfFetch('/api/workflows/telegram/chat/command', {
      method: 'POST',
      body: JSON.stringify({
        message,
        send_to_telegram: !!sendChk?.checked
      })
    });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.detail || 'Command failed');
    if (inp) inp.value = '';
    const sentNote = data.delivery ? (data.delivery.ok ? ' + Telegram-এ পাঠানো হয়েছে!' : ` (Telegram error: ${data.delivery.error})`) : '';
    wfToast(`✅ কমান্ড সম্পন্ন (${data.intent})${sentNote}`, 'success');
    await refreshWorkflowTelegramChats();
    await refreshWorkflowTelegramLogs(false);
  } catch (err) {
    wfToast('কমান্ড ব্যর্থ: ' + err.message, 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '⚡ কমান্ড ও স্ট্যাটাস চালান'; }
  }
}

async function sendWorkflowReportToTelegram(workflowId = '') {
  try {
    const res = await wfFetch('/api/workflows/telegram/send-report', {
      method: 'POST',
      body: JSON.stringify({ workflow_id: workflowId || '' })
    });
    const data = await res.json();
    if (data.delivery && data.delivery.ok) {
      wfToast(`📤 WORKFLOWS (Auto) রিপোর্ট Telegram-এ পাঠানো হয়েছে (Msg #${data.delivery.telegram_message_id || 'OK'})!`, 'success');
    } else if (data.delivery && !data.delivery.ok) {
      wfToast(`⚠️ রিপোর্ট ফিডে যোগ হয়েছে, তবে Telegram ডেলিভারি ব্যর্থ: ${data.delivery.error}`, 'warning');
    } else {
      wfToast('📊 WORKFLOWS (Auto) রিপোর্ট Telegram Chat Feed-এ তৈরি হয়েছে (লাইভ সেন্ডের জন্য Bot Token ও Chat ID কানেক্ট করুন)।', 'info');
    }
    await refreshWorkflowTelegramChats();
    await refreshWorkflowTelegramLogs(false);
  } catch (err) {
    wfToast('রিপোর্ট পাঠাতে ব্যর্থ: ' + err.message, 'error');
  }
}

async function clearWorkflowTelegramChats() {
  try {
    const res = await wfFetch('/api/workflows/telegram/chats', { method: 'DELETE' });
    if (res.ok) {
      wfToast('🗑️ Telegram চ্যাট ইতিহাস মুছে ফেলা হয়েছে।', 'info');
      await refreshWorkflowTelegramChats();
    }
  } catch (err) {
    wfToast('চ্যাট মুছতে ব্যর্থ: ' + err.message, 'error');
  }
}

function renderWorkflowMcpStatusPill() {
  const pillText = document.getElementById('wf-mcp-pill-text');
  if (!pillText) return;
  const servers = wfState.mcpServers || [];
  const active = servers.filter(s => s.is_enabled !== false);
  const totalTools = active.reduce((acc, s) => acc + (s.tools_cache ? s.tools_cache.length : 0), 0);
  pillText.textContent = `MCP: ${active.length} Server (${totalTools} Tools)`;
}

async function refreshWorkflowMcpServer(serverId = '') {
  try {
    if (serverId) {
      const res = await wfFetch(`/api/workflows/mcp/ping/${encodeURIComponent(serverId)}`, { method: 'POST' });
      const data = await res.json();
      if (data.mcp_servers) wfState.mcpServers = data.mcp_servers;
      if (data.success) {
        wfToast(`🔌 MCP '${serverId}' রিফ্রেশ হয়েছে (${data.ping?.latency_ms || 0}ms, ${(data.ping?.tools || []).length} tools)!`, 'success');
      } else {
        wfToast('⚠️ MCP Ping সতর্কতা: ' + (data.ping?.message || 'Offline'), 'warning');
      }
    } else {
      const res = await wfFetch('/api/workflows/mcp/servers');
      const data = await res.json();
      if (data.mcp_servers) wfState.mcpServers = data.mcp_servers;
      wfToast('🔄 MCP সার্ভার লিস্ট আপডেট হয়েছে।', 'info');
    }
    renderWorkflowMcpStatusPill();
    if (wfState.selectedNodeId) renderNodeInspector();
  } catch (err) {
    wfToast('MCP রিফ্রেশ ব্যর্থ: ' + err.message, 'error');
  }
}

function applyMcpSampleArgs() {
  const wf = wfState.activeWorkflow;
  const node = wf ? (wf.nodes || []).find(n => n.id === wfState.selectedNodeId) : null;
  if (!node) return;
  const c = node.config || {};
  const servers = (wfState.mcpServers || []).filter(s => s.is_enabled !== false);
  let foundTool = null;
  for (const s of servers) {
    if (c.server_id && s.id !== c.server_id) continue;
    const hit = (s.tools_cache || []).find(t => t.name === c.tool_name);
    if (hit) { foundTool = hit; break; }
  }
  const props = foundTool?.inputSchema?.properties || {};
  const sample = {};
  Object.keys(props).forEach(k => {
    const t = props[k]?.type || 'string';
    sample[k] = t === 'integer' || t === 'number' ? 0 : (t === 'boolean' ? true : (k === 'url' ? 'https://example.com' : '{{prev.output}}'));
  });
  updateNodeCfg('args_json', JSON.stringify(sample, null, 2));
  renderNodeInspector();
  wfToast('📋 MCP টুল স্কিমা অনুযায়ী Sample JSON বসানো হয়েছে।', 'info');
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
window.refreshWorkflowTelegramChats = refreshWorkflowTelegramChats;
window.submitTelegramChatCommand = submitTelegramChatCommand;
window.sendWorkflowReportToTelegram = sendWorkflowReportToTelegram;
window.clearWorkflowTelegramChats = clearWorkflowTelegramChats;
window.undoWorkflowChange = undoWorkflowChange;
window.redoWorkflowChange = redoWorkflowChange;
window.onPaletteSearchInput = onPaletteSearchInput;
window.setPaletteCategory = setPaletteCategory;
window.onPaletteDragStart = onPaletteDragStart;
window.onCanvasDragOver = onCanvasDragOver;
window.onCanvasDrop = onCanvasDrop;
window.toggleGridSnap = toggleGridSnap;
window.toggleStudioPane = toggleStudioPane;
window.toggleFullscreenCanvas = toggleFullscreenCanvas;
window.fitCanvasToView = fitCanvasToView;
window.renderCanvasMinimap = renderCanvasMinimap;
window.jumpCanvasFromMinimap = jumpCanvasFromMinimap;
window.onCanvasDoubleClick = onCanvasDoubleClick;
window.openQuickPickerForEdge = openQuickPickerForEdge;
window.renderQuickPickerList = renderQuickPickerList;
window.pickQuickPickerNode = pickQuickPickerNode;
window.closeQuickPicker = closeQuickPicker;
window.runNodeQuickTestFromCard = runNodeQuickTestFromCard;
window.onViewportMouseDown = onViewportMouseDown;
window.onCanvasWheel = onCanvasWheel;
window.refreshWorkflowMcpServer = refreshWorkflowMcpServer;
window.applyMcpSampleArgs = applyMcpSampleArgs;
