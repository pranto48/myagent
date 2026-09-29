/* ==============================================================================
 * Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
 * Made By Arif (https://arifmahmud.com/)
 * Project: MyAgent | Version: 3.1.0
 * Ops Agent Operational Suite Manager
 * (FILES, MODELS, LOGS, CRON, SKILLS, PLUGINS, MCP, CHANNELS, WEBHOOKS, PAIRING, PROFILES)
 * ============================================================================== */

// Global Ops State
let opsLogsAutoScroll = true;
let opsPairingTimer = null;
let opsActiveFilter = 'ALL';
let opsFsCurrentPath = '/opt/data';
let opsSessionsData = null;
let opsCurrentSessionFilter = 'chats';
let opsCurrentSessionSource = 'any';
let opsCurrentSessionView = 'overview';

// ------------------------------------------------------------------------------
// Helper: Authenticated fetch wrapper
// ------------------------------------------------------------------------------
async function opsFetch(url, options = {}) {
  const token = localStorage.getItem('myagent_token');
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {})
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return fetch(url, { ...options, headers });
}

// ==============================================================================
// 0. SESSIONS MODULE (Matching Screenshot 1)
// ==============================================================================
async function loadOpsSessions() {
  const badgeCount = document.getElementById('ops-sessions-badge-count');
  const kpiTotal = document.getElementById('ops-kpi-total-sess');
  const kpiActive = document.getElementById('ops-kpi-active-sess');
  const kpiArchived = document.getElementById('ops-kpi-archived-sess');
  const kpiMessages = document.getElementById('ops-kpi-messages-sess');
  const kpiSources = document.getElementById('ops-kpi-sources-sess');
  const platformsContainer = document.getElementById('ops-connected-platforms-list');
  const recentSessionsContainer = document.getElementById('ops-recent-sessions-list');

  if (platformsContainer) platformsContainer.innerHTML = '<div style="color:var(--text-muted); font-size:0.85rem; padding:10px;">লোড হচ্ছে...</div>';
  if (recentSessionsContainer) recentSessionsContainer.innerHTML = '<div style="color:var(--text-muted); font-size:0.85rem; padding:10px;">লোড হচ্ছে...</div>';

  try {
    const res = await opsFetch('/api/sessions/overview');
    const data = await res.json();
    if (!data.success) throw new Error('Failed to load sessions');
    opsSessionsData = data;

    if (badgeCount) badgeCount.innerText = data.active_in_store || data.total || 0;
    if (kpiTotal) kpiTotal.innerText = data.total || 0;
    if (kpiActive) kpiActive.innerText = data.active_in_store || 0;
    if (kpiArchived) kpiArchived.innerText = data.archived || 0;
    if (kpiMessages) kpiMessages.innerText = data.messages || 0;
    if (kpiSources) kpiSources.innerText = data.sources || 1;

    renderOpsPlatforms(data.connected_platforms || []);
    renderOpsRecentSessions();
  } catch (err) {
    console.error('Error loading ops sessions:', err);
    if (platformsContainer) platformsContainer.innerHTML = '<div style="color:var(--rose-glow); font-size:0.85rem;">প্ল্যাটফর্ম লোড ব্যর্থ হয়েছে।</div>';
    if (recentSessionsContainer) recentSessionsContainer.innerHTML = '<div style="color:var(--rose-glow); font-size:0.85rem;">সেশন লোড ব্যর্থ হয়েছে।</div>';
  }
}

function renderOpsPlatforms(platforms) {
  const container = document.getElementById('ops-connected-platforms-list');
  if (!container) return;
  if (!platforms || platforms.length === 0) {
    container.innerHTML = '<div style="color:var(--text-muted); font-size:0.85rem;">কোনো সক্রিয় প্ল্যাটফর্ম পাওয়া যায়নি।</div>';
    return;
  }
  container.innerHTML = platforms.map(p => `
    <div class="ops-platform-row">
      <div class="ops-plat-left">
        <span class="ops-plat-icon">📶</span>
        <div>
          <div class="ops-plat-title">${escapeHtml(p.name)}</div>
          <div class="ops-plat-sub">Last update: ${escapeHtml(p.last_update)}</div>
        </div>
      </div>
      <div class="ops-status-pill">${escapeHtml(p.status || 'Connected')}</div>
    </div>
  `).join('');
}

function renderOpsRecentSessions() {
  const container = document.getElementById('ops-recent-sessions-list');
  if (!container || !opsSessionsData) return;

  let list = opsSessionsData.recent_sessions || [];

  // Filter by Type
  if (opsCurrentSessionFilter === 'automation') {
    list = list.filter(s => s.is_archived || s.source === 'automation');
  } else if (opsCurrentSessionFilter === 'chats') {
    list = list.filter(s => !s.is_archived);
  }

  // Filter by Source
  if (opsCurrentSessionSource !== 'any') {
    list = list.filter(s => s.source === opsCurrentSessionSource);
  }

  if (list.length === 0) {
    container.innerHTML = '<div style="color:var(--text-muted); font-size:0.85rem; padding:12px; text-align:center;">কোনো সেশন পাওয়া যায়নি।</div>';
    return;
  }

  container.innerHTML = list.map(s => `
    <div class="ops-session-card" onclick="openSessionDirectly('${escapeHtml(s.id)}')">
      <div>
        <div class="ops-sess-title">${escapeHtml(s.title || 'Untitled Session')}</div>
        <div class="ops-sess-meta">${escapeHtml(s.model)} · ${s.msg_count} msgs · ${escapeHtml(s.updated_at || 'just now')}</div>
        <div class="ops-sess-snippet">${escapeHtml(s.snippet || '')}</div>
      </div>
      <div style="display:flex; align-items:center; gap:8px;">
        <button type="button" class="ops-tui-badge" onclick="event.stopPropagation(); openSessionDirectly('${escapeHtml(s.id)}')">
          💾 TUI
        </button>
        <button type="button" class="ops-action-icon-btn danger" onclick="event.stopPropagation(); deleteOpsSession('${escapeHtml(s.id)}')">
          🗑️
        </button>
      </div>
    </div>
  `).join('');
}

function setOpsSessionFilter(type, btn) {
  opsCurrentSessionFilter = type;
  const parent = document.getElementById('ops-sess-type-group');
  if (parent) {
    parent.querySelectorAll('.ops-filter-btn').forEach(b => b.classList.remove('active'));
  }
  if (btn) btn.classList.add('active');
  renderOpsRecentSessions();
}

function filterOpsSessionsBySource(src) {
  opsCurrentSessionSource = src;
  renderOpsRecentSessions();
}

function setOpsSessionView(view, btn) {
  opsCurrentSessionView = view;
  const parent = document.getElementById('ops-sess-view-group');
  if (parent) {
    parent.querySelectorAll('.ops-filter-btn').forEach(b => b.classList.remove('active'));
  }
  if (btn) btn.classList.add('active');
  renderOpsRecentSessions();
}

function openSessionDirectly(sessionId) {
  if (typeof switchSession === 'function') {
    switchSession(sessionId);
  }
  if (typeof switchTab === 'function') {
    switchTab('chat');
  }
}

async function deleteOpsSession(sessionId) {
  if (!confirm('এই সেশনটি সম্পূর্ণ মুছে ফেলতে চান?')) return;
  try {
    const res = await opsFetch(`/api/sessions/${sessionId}`, { method: 'DELETE' });
    const data = await res.json();
    if (data.success) {
      if (typeof showToast === 'function') showToast('সেশন মুছে ফেলা হয়েছে', 'info');
      loadOpsSessions();
      if (typeof loadSessionList === 'function') loadSessionList();
    }
  } catch (err) {
    alert('Failed to delete session');
  }
}

function openPruneSessionsModal() {
  const m = document.getElementById('ops-prune-sessions-modal');
  if (m) m.style.display = 'flex';
}
function closePruneSessionsModal() {
  const m = document.getElementById('ops-prune-sessions-modal');
  if (m) m.style.display = 'none';
}
async function executePruneSessions(e) {
  e.preventDefault();
  const days = parseInt(document.getElementById('prune-sess-days').value) || 30;
  const emptyOnly = document.getElementById('prune-sess-empty-only').checked;

  try {
    const res = await opsFetch('/api/sessions/prune', {
      method: 'POST',
      body: JSON.stringify({ days, empty_only: emptyOnly })
    });
    const data = await res.json();
    if (data.success) {
      closePruneSessionsModal();
      loadOpsSessions();
      if (typeof loadSessionList === 'function') loadSessionList();
      if (typeof showToast === 'function') showToast(`সফলভাবে ${data.pruned_count}টি সেশন প্রুন করা হয়েছে`, 'success');
    }
  } catch (err) {
    alert('Failed to prune sessions');
  }
}

function openImportSessionsModal() {
  const m = document.getElementById('ops-import-sessions-modal');
  if (m) m.style.display = 'flex';
}
function closeImportSessionsModal() {
  const m = document.getElementById('ops-import-sessions-modal');
  if (m) m.style.display = 'none';
}
function handleImportSessionFile(e) {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = function(evt) {
    const txtArea = document.getElementById('import-sessions-json');
    if (txtArea) txtArea.value = evt.target.result;
  };
  reader.readAsText(file);
}
async function executeImportSessions(e) {
  e.preventDefault();
  const raw = document.getElementById('import-sessions-json').value.trim();
  if (!raw) return;
  try {
    const payload = JSON.parse(raw);
    const res = await opsFetch('/api/sessions/import', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.success) {
      closeImportSessionsModal();
      loadOpsSessions();
      if (typeof loadSessionList === 'function') loadSessionList();
      if (typeof showToast === 'function') showToast(`সফলভাবে ${data.imported_count}টি সেশন ইমপোর্ট হয়েছে`, 'success');
    }
  } catch (err) {
    alert('Invalid JSON format or import error');
  }
}

// ==============================================================================
// 1. FILESYSTEM EXPLORER (Matching Screenshot 2: Files /opt/data)
// ==============================================================================
async function loadOpsFilesExplorer(targetPath) {
  if (targetPath) opsFsCurrentPath = targetPath;
  const path = opsFsCurrentPath || '/opt/data';

  const badge = document.getElementById('ops-fs-header-badge');
  const pathDisplay = document.getElementById('ops-fs-current-path');
  const dropPath = document.getElementById('ops-fs-drop-path');
  const upBtn = document.getElementById('ops-fs-up-btn');
  const tableBody = document.getElementById('ops-fs-table-body');

  if (badge) badge.innerText = path;
  if (pathDisplay) pathDisplay.innerText = path;
  if (dropPath) dropPath.innerText = path;

  if (tableBody) {
    tableBody.innerHTML = `<tr><td colspan="4" class="text-center py-4" style="color:var(--text-muted);">${typeof t === 'function' ? t('ops_loading') : 'লোড হচ্ছে...'}</td></tr>`;
  }

  try {
    const res = await opsFetch(`/api/ops/fs/list?path=${encodeURIComponent(path)}`);
    const data = await res.json();
    if (!data.success) throw new Error(data.message || 'Failed to list directory');

    if (upBtn) {
      upBtn.style.display = data.parent_path ? 'inline-flex' : 'none';
      upBtn.setAttribute('data-parent-path', data.parent_path || '');
    }

    if (!data.items || data.items.length === 0) {
      tableBody.innerHTML = `<tr><td colspan="4" class="text-center py-4" style="color:var(--text-muted);">${typeof t === 'function' ? t('ops_files_empty') : 'কোনো ফাইল বা ফোল্ডার পাওয়া যায়নি।'}</td></tr>`;
      return;
    }

    tableBody.innerHTML = data.items.map(item => `
      <tr class="ops-row">
        <td>
          <div class="ops-row-name" onclick="${item.is_dir ? `loadOpsFilesExplorer('${escapeHtml(item.virtual_path)}')` : `downloadOrPreviewFsFile('${escapeHtml(item.virtual_path)}')`}">
            <span class="${item.is_dir ? 'ops-folder-icon' : 'ops-file-icon'}">${item.is_dir ? '📁' : '📄'}</span>
            <span>${escapeHtml(item.name)}</span>
          </div>
        </td>
        <td style="font-family:'Fira Code', monospace; color:var(--text-muted); font-size:0.8rem;">${escapeHtml(item.size)}</td>
        <td style="color:var(--text-secondary); font-size:0.8rem;">${escapeHtml(item.modified)}</td>
        <td style="text-align:right;">
          ${item.is_dir ? `
            <button type="button" class="ops-action-icon-btn" title="Open Folder" onclick="loadOpsFilesExplorer('${escapeHtml(item.virtual_path)}')">📁</button>
          ` : `
            <button type="button" class="ops-action-icon-btn" title="Download File" onclick="downloadOrPreviewFsFile('${escapeHtml(item.virtual_path)}')">⬇️</button>
          `}
          <button type="button" class="ops-action-icon-btn danger" title="Delete" onclick="deleteOpsFsItem('${escapeHtml(path)}', '${escapeHtml(item.name)}', ${item.is_dir})">🗑️</button>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    console.error('Error loading filesystem:', err);
    if (tableBody) {
      tableBody.innerHTML = `<tr><td colspan="4" class="text-center py-4" style="color:var(--rose-glow);">${typeof t === 'function' ? t('ops_error_load') : 'ফাইলসিস্টেম লোড করতে ব্যর্থ হয়েছে।'}</td></tr>`;
    }
  }
}

function navigateOpsFsUp() {
  const upBtn = document.getElementById('ops-fs-up-btn');
  const parentPath = upBtn ? upBtn.getAttribute('data-parent-path') : null;
  if (parentPath) {
    loadOpsFilesExplorer(parentPath);
  }
}

function triggerOpsFsUpload() {
  const input = document.getElementById('ops-fs-file-input');
  if (input) input.click();
}

async function handleOpsFsFileSelected(e) {
  const files = e.target.files;
  if (!files || files.length === 0) return;
  await uploadFilesToFs(files);
  e.target.value = '';
}

function handleOpsFsDragOver(e) {
  e.preventDefault();
  const dropzone = document.getElementById('ops-fs-dropzone');
  if (dropzone) dropzone.classList.add('drag-active');
}

function handleOpsFsDragLeave(e) {
  e.preventDefault();
  const dropzone = document.getElementById('ops-fs-dropzone');
  if (dropzone) dropzone.classList.remove('drag-active');
}

async function handleOpsFsDrop(e) {
  e.preventDefault();
  const dropzone = document.getElementById('ops-fs-dropzone');
  if (dropzone) dropzone.classList.remove('drag-active');

  const files = e.dataTransfer.files;
  if (files && files.length > 0) {
    await uploadFilesToFs(files);
  }
}

async function uploadFilesToFs(files) {
  const path = opsFsCurrentPath || '/opt/data';
  const token = localStorage.getItem('myagent_token');

  for (let i = 0; i < files.length; i++) {
    const file = files[i];
    const formData = new FormData();
    formData.append('file', file);
    formData.append('path', path);

    try {
      const headers = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const res = await fetch('/api/ops/fs/upload', {
        method: 'POST',
        headers,
        body: formData
      });
      const data = await res.json();
      if (data.success) {
        if (typeof showToast === 'function') showToast(`${file.name} আপলোড সম্পন্ন`, 'success');
      }
    } catch (err) {
      console.error('File upload failed:', err);
      alert(`Upload failed for ${file.name}`);
    }
  }
  loadOpsFilesExplorer();
}

function openOpsCreateFsItemModal() {
  const modal = document.getElementById('ops-create-fs-modal');
  const pathInput = document.getElementById('ops-create-fs-path');
  const nameInput = document.getElementById('ops-create-fs-name');
  if (pathInput) pathInput.value = opsFsCurrentPath || '/opt/data';
  if (nameInput) nameInput.value = '';
  if (modal) modal.style.display = 'flex';
}

function closeOpsCreateFsItemModal() {
  const modal = document.getElementById('ops-create-fs-modal');
  if (modal) modal.style.display = 'none';
}

async function executeOpsCreateFsItem(e) {
  e.preventDefault();
  const path = document.getElementById('ops-create-fs-path').value.trim();
  const type = document.getElementById('ops-create-fs-type').value;
  const name = document.getElementById('ops-create-fs-name').value.trim();

  if (!name) return;

  try {
    const res = await opsFetch('/api/ops/fs/create', {
      method: 'POST',
      body: JSON.stringify({
        path,
        name,
        is_directory: type === 'folder'
      })
    });
    const data = await res.json();
    if (data.success) {
      closeOpsCreateFsItemModal();
      loadOpsFilesExplorer();
      if (typeof showToast === 'function') showToast(`${name} তৈরি করা হয়েছে`, 'success');
    } else {
      alert(data.message || 'Failed to create item');
    }
  } catch (err) {
    alert('Create request failed');
  }
}

async function deleteOpsFsItem(path, name, isDir) {
  const msg = isDir ? `আপনি কি ফোল্ডার '${name}' এবং এর ভেতরের সবকিছু মুছে ফেলতে চান?` : `আপনি কি '${name}' মুছে ফেলতে চান?`;
  if (!confirm(msg)) return;

  try {
    const res = await opsFetch('/api/ops/fs/delete', {
      method: 'DELETE',
      body: JSON.stringify({ path, name })
    });
    const data = await res.json();
    if (data.success) {
      loadOpsFilesExplorer();
      if (typeof showToast === 'function') showToast(`${name} মুছে ফেলা হয়েছে`, 'info');
    }
  } catch (err) {
    alert('Delete request failed');
  }
}

function downloadOrPreviewFsFile(virtualPath) {
  const url = `/api/ops/fs/download?path=${encodeURIComponent(virtualPath)}`;
  window.open(url, '_blank');
}

// ==============================================================================
// 1. FILES MODULE (Vector Ingested Overview)
// ==============================================================================
async function loadOpsFiles() {
  const container = document.getElementById('ops-files-table-body');
  const countBadge = document.getElementById('ops-files-total-badge');
  const chunksBadge = document.getElementById('ops-files-chunks-badge');
  if (!container) return;

  container.innerHTML = `<tr><td colspan="6" class="text-center py-4" style="color:var(--text-muted);">${typeof t === 'function' ? t('ops_loading') : 'লোড হচ্ছে...'}</td></tr>`;

  try {
    const res = await opsFetch('/api/ops/files/overview');
    const data = await res.json();
    if (!data.success) throw new Error(data.message || 'Failed to fetch files');

    if (countBadge) countBadge.innerText = data.total_files || 0;
    if (chunksBadge) chunksBadge.innerText = data.total_chunks || 0;

    if (!data.files || data.files.length === 0) {
      container.innerHTML = `<tr><td colspan="6" class="text-center py-4" style="color:var(--text-muted);">${typeof t === 'function' ? t('ops_files_empty') : 'কোনো ফাইল আপলোড করা হয়নি।'}</td></tr>`;
      return;
    }

    container.innerHTML = data.files.map(f => `
      <tr class="ops-row">
        <td style="font-weight:600; color:var(--text-primary); display:flex; align-items:center; gap:8px;">
          <span>📁</span>
          <span>${escapeHtml(f.filename)}</span>
        </td>
        <td><span class="ops-tag">${escapeHtml(f.file_type.toUpperCase())}</span></td>
        <td style="font-family:'Fira Code', monospace; color:var(--cyan-glow);">${f.chunk_count} ${typeof t === 'function' ? t('ops_chunks') : 'চাঙ্কস'}</td>
        <td style="color:var(--text-secondary); font-size:0.8rem;">${escapeHtml(f.category)}</td>
        <td style="color:var(--text-muted); font-size:0.8rem;">${f.created_at}</td>
        <td style="text-align:right;">
          <button class="btn-sm-cyber" onclick="previewOpsFile('${escapeHtml(f.id)}', '${escapeHtml(f.filename)}')">👁️ ${typeof t === 'function' ? t('ops_btn_preview') : 'প্রিভিউ'}</button>
          <button class="btn-sm-cyber danger" onclick="deleteOpsFile('${escapeHtml(f.id)}')">🗑️</button>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    console.error('Error loading ops files:', err);
    container.innerHTML = `<tr><td colspan="6" class="text-center py-4" style="color:var(--rose-glow);">${typeof t === 'function' ? t('ops_error_load') : 'ফাইল লোড করতে সমস্যা হয়েছে।'}</td></tr>`;
  }
}

async function previewOpsFile(docId, filename) {
  try {
    const res = await opsFetch(`/api/documents/${docId}/chunks`);
    const data = await res.json();
    const modal = document.getElementById('ops-preview-modal');
    const title = document.getElementById('ops-preview-title');
    const body = document.getElementById('ops-preview-body');
    if (title) title.innerText = filename;
    if (body) {
      if (data.chunks && data.chunks.length > 0) {
        body.innerHTML = data.chunks.map((c, i) => `
          <div class="ops-chunk-card">
            <div class="chunk-badge">${typeof t === 'function' ? t('ops_chunk_num') : 'চাঙ্ক'} #${i + 1}</div>
            <pre class="chunk-text">${escapeHtml(c.text || c.content || '')}</pre>
          </div>
        `).join('');
      } else {
        body.innerHTML = `<div style="padding:20px; text-align:center; color:var(--text-muted);">${typeof t === 'function' ? t('ops_no_chunks') : 'কোনো সংরক্ষিত চাঙ্ক পাওয়া যায়নি।'}</div>`;
      }
    }
    if (modal) modal.style.display = 'flex';
  } catch (err) {
    alert(typeof t === 'function' ? t('ops_preview_err') : 'প্রিভিউ লোড করা সম্ভব হয়নি');
  }
}

async function deleteOpsFile(docId) {
  const confirmMsg = typeof t === 'function' ? t('ops_confirm_delete_file') : 'আপনি কি নিশ্চিত যে এই ফাইলটি মুছে ফেলতে চান?';
  if (!confirm(confirmMsg)) return;
  try {
    const res = await opsFetch(`/api/documents/${docId}`, { method: 'DELETE' });
    const data = await res.json();
    if (data.success) {
      loadOpsFiles();
      if (typeof showToast === 'function') showToast(typeof t === 'function' ? t('ops_file_deleted') : 'ফাইলটি সফলভাবে মুছে ফেলা হয়েছে', 'success');
    }
  } catch (err) {
    alert('Failed to delete file');
  }
}

function closeOpsPreviewModal() {
  const modal = document.getElementById('ops-preview-modal');
  if (modal) modal.style.display = 'none';
}

// ==============================================================================
// 2. LOGS MODULE
// ==============================================================================
async function loadOpsLogs() {
  const container = document.getElementById('ops-logs-console');
  if (!container) return;

  try {
    const searchVal = document.getElementById('ops-logs-search') ? document.getElementById('ops-logs-search').value : '';
    let url = `/api/ops/logs?limit=150&level=${encodeURIComponent(opsActiveFilter)}`;
    if (searchVal) url += `&search=${encodeURIComponent(searchVal)}`;

    const res = await opsFetch(url);
    const data = await res.json();
    if (!data.success) return;

    if (!data.logs || data.logs.length === 0) {
      container.innerHTML = `<div class="ops-log-line muted">> ${typeof t === 'function' ? t('ops_no_logs') : 'কোনো লগ রেকর্ড পাওয়া যায়নি।'}</div>`;
      return;
    }

    container.innerHTML = data.logs.reverse().map(l => {
      let levelClass = 'info';
      if (l.level === 'SUCCESS') levelClass = 'success';
      else if (l.level === 'AI_AGENT') levelClass = 'agent';
      else if (l.level === 'WARN') levelClass = 'warn';
      else if (l.level === 'ERROR') levelClass = 'error';

      return `
        <div class="ops-log-entry ${levelClass}">
          <span class="log-ts">[${l.timestamp}]</span>
          <span class="log-badge ${levelClass}">${l.level}</span>
          <span class="log-mod">[${escapeHtml(l.module)}]</span>
          <span class="log-msg">${escapeHtml(l.message)}</span>
        </div>
      `;
    }).join('');

    if (opsLogsAutoScroll) {
      container.scrollTop = container.scrollHeight;
    }
  } catch (err) {
    console.error('Error loading ops logs:', err);
  }
}

function setOpsLogFilter(lvl) {
  opsActiveFilter = lvl;
  document.querySelectorAll('.ops-filter-btn').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-level') === lvl);
  });
  loadOpsLogs();
}

function toggleOpsLogAutoScroll() {
  opsLogsAutoScroll = !opsLogsAutoScroll;
  const btn = document.getElementById('btn-ops-autoscroll');
  if (btn) {
    btn.classList.toggle('active', opsLogsAutoScroll);
    btn.innerText = opsLogsAutoScroll ? '⚡ Auto-Scroll ON' : '⏸ Auto-Scroll OFF';
  }
}

async function clearOpsLogs() {
  const confirmMsg = typeof t === 'function' ? t('ops_confirm_clear_logs') : 'আপনি কি সমস্ত লগ পরিষ্কার করতে চান?';
  if (!confirm(confirmMsg)) return;
  try {
    const res = await opsFetch('/api/ops/logs/clear', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      loadOpsLogs();
      if (typeof showToast === 'function') showToast(typeof t === 'function' ? t('ops_logs_cleared') : 'লগ পরিষ্কার করা হয়েছে', 'success');
    }
  } catch (err) {
    alert('Failed to clear logs');
  }
}

function downloadOpsLogs() {
  const consoleEl = document.getElementById('ops-logs-console');
  if (!consoleEl) return;
  const text = consoleEl.innerText;
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `myagent_ops_logs_${Date.now()}.txt`;
  a.click();
}

// ==============================================================================
// 3. CRON MODULE
// ==============================================================================
async function loadOpsCron() {
  const jobsList = document.getElementById('ops-cron-jobs-list');
  const historyList = document.getElementById('ops-cron-history-list');
  if (!jobsList) return;

  try {
    const res = await opsFetch('/api/ops/cron');
    const data = await res.json();
    if (!data.success) return;

    // Render Jobs
    jobsList.innerHTML = data.jobs.map(j => `
      <div class="ops-card cron-card ${j.is_enabled ? 'active-job' : 'disabled-job'}">
        <div class="cron-card-header">
          <div style="display:flex; align-items:center; gap:10px;">
            <div class="cron-icon">⏱️</div>
            <div>
              <div class="cron-name">${escapeHtml(j.name)}</div>
              <div class="cron-expr"><code>${escapeHtml(j.expression)}</code> • <span style="color:var(--text-muted);">${escapeHtml(j.next_run || '')}</span></div>
            </div>
          </div>
          <div class="cron-actions">
            <button class="btn-sm-action-cyber" onclick="triggerOpsCron('${j.id}')" title="Run Now">⚡ ${typeof t === 'function' ? t('ops_run_now') : 'রান নাও'}</button>
            <label class="ops-switch">
              <input type="checkbox" ${j.is_enabled ? 'checked' : ''} onchange="toggleOpsCron('${j.id}')">
              <span class="slider round"></span>
            </label>
            <button class="btn-sm-action-cyber danger" onclick="deleteOpsCron('${j.id}')">🗑️</button>
          </div>
        </div>
        <div class="cron-card-footer">
          <span>${typeof t === 'function' ? t('ops_last_status') : 'সর্বশেষ স্ট্যাটাস'}: <span class="badge-${j.last_status === 'SUCCESS' ? 'online' : 'idle'}">${j.last_status}</span></span>
          <span style="color:var(--text-muted); font-size:0.75rem;">${typeof t === 'function' ? t('ops_last_run') : 'সর্বশেষ রান'}: ${j.last_run || 'N/A'}</span>
        </div>
      </div>
    `).join('');

    // Render History
    if (historyList) {
      if (!data.history || data.history.length === 0) {
        historyList.innerHTML = `<div style="text-align:center; padding:16px; color:var(--text-muted);">${typeof t === 'function' ? t('ops_cron_no_hist') : 'কোনো পূর্ববর্তী এক্সিকিউশন ইতিহাস নেই।'}</div>`;
      } else {
        historyList.innerHTML = data.history.map(h => `
          <div class="ops-history-item">
            <div style="display:flex; justify-content:space-between;">
              <span style="font-weight:600; color:var(--text-primary);">${escapeHtml(h.job_name)}</span>
              <span class="status-pill ${h.status === 'SUCCESS' ? 'success' : 'failed'}">${h.status} (${h.duration_ms}ms)</span>
            </div>
            <div style="font-size:0.75rem; color:var(--text-secondary); margin-top:4px;">${escapeHtml(h.output || '')}</div>
            <div style="font-size:0.7rem; color:var(--text-muted); margin-top:2px;">${h.run_at}</div>
          </div>
        `).join('');
      }
    }
  } catch (err) {
    console.error('Error loading ops cron:', err);
  }
}

async function triggerOpsCron(jobId) {
  try {
    const res = await opsFetch(`/api/ops/cron/${jobId}/run`, { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      if (typeof showToast === 'function') {
        showToast(typeof t === 'function' ? t('ops_cron_triggered') : `জব সফলভাবে এক্সিকিউট হয়েছে (${data.duration_ms}ms)`, 'success');
      }
      loadOpsCron();
    }
  } catch (err) {
    alert('Failed to trigger cron job');
  }
}

async function toggleOpsCron(jobId) {
  try {
    await opsFetch(`/api/ops/cron/${jobId}/toggle`, { method: 'PUT' });
    loadOpsCron();
  } catch (err) {
    console.error(err);
  }
}

async function deleteOpsCron(jobId) {
  if (!confirm(typeof t === 'function' ? t('ops_confirm_delete_cron') : 'এই ক্রন জবটি মুছে ফেলতে চান?')) return;
  try {
    await opsFetch(`/api/ops/cron/${jobId}`, { method: 'DELETE' });
    loadOpsCron();
  } catch (err) {
    alert('Failed to delete cron');
  }
}

function openNewCronModal() {
  const modal = document.getElementById('ops-new-cron-modal');
  if (modal) modal.style.display = 'flex';
}

function closeNewCronModal() {
  const modal = document.getElementById('ops-new-cron-modal');
  if (modal) modal.style.display = 'none';
}

async function saveNewOpsCron(e) {
  e.preventDefault();
  const name = document.getElementById('cron-input-name').value.trim();
  const expression = document.getElementById('cron-input-expr').value.trim();
  const task_type = document.getElementById('cron-input-type').value;

  try {
    const res = await opsFetch('/api/ops/cron', {
      method: 'POST',
      body: JSON.stringify({ name, expression, task_type, payload: {} })
    });
    const data = await res.json();
    if (data.success) {
      closeNewCronModal();
      loadOpsCron();
      if (typeof showToast === 'function') showToast(typeof t === 'function' ? t('ops_cron_saved') : 'নতুন ক্রন জব যুক্ত হয়েছে', 'success');
    }
  } catch (err) {
    alert('Failed to save cron');
  }
}

// ==============================================================================
// ==============================================================================
// 4. SKILLS MODULE (Matching Ops Agent Skills Hub Screenshot)
// ==============================================================================
let opsSkillsState = {
  allSkills: [],
  categories: {},
  filters: { all: 53, toolsets: 29, browse_hub: 0 },
  activeFilter: 'all',
  activeCategory: 'all',
  searchQuery: ''
};

async function loadOpsSkills() {
  const listPane = document.getElementById('ops-skills-list-pane');
  if (!listPane) return;

  listPane.innerHTML = `<div style="padding:28px; text-align:center; color:#64748b;">${typeof t === 'function' ? t('ops_loading') : 'লোড হচ্ছে...'}</div>`;

  try {
    let url = `/api/ops/skills?filter_type=${encodeURIComponent(opsSkillsState.activeFilter)}`;
    if (opsSkillsState.activeCategory && opsSkillsState.activeCategory !== 'all') {
      url += `&category=${encodeURIComponent(opsSkillsState.activeCategory)}`;
    }
    if (opsSkillsState.searchQuery) {
      url += `&search=${encodeURIComponent(opsSkillsState.searchQuery)}`;
    }

    const res = await opsFetch(url);
    const data = await res.json();
    if (!data.success) throw new Error(data.message || 'Failed to fetch skills');

    opsSkillsState.allSkills = data.skills || [];
    if (data.categories) opsSkillsState.categories = data.categories;
    if (data.filters) opsSkillsState.filters = data.filters;

    // 1. Update Subtitle
    const subTitle = document.getElementById('ops-skills-enabled-subtitle');
    if (subTitle) {
      subTitle.innerText = `${data.enabled_skills || 0}/${data.total_skills || 0} enabled`;
    }

    // 2. Update Filter counts
    const countAll = document.getElementById('ops-filter-count-all');
    if (countAll) countAll.innerText = `(${data.filters?.all ?? 53})`;
    const countToolsets = document.getElementById('ops-filter-count-toolsets');
    if (countToolsets) countToolsets.innerText = `(${data.filters?.toolsets ?? 29})`;

    // 3. Render Categories sidebar
    renderOpsSkillsCategories(opsSkillsState.categories);

    // 4. Update Active Header
    const activeIcon = document.getElementById('ops-active-cat-icon');
    const activeTitle = document.getElementById('ops-active-cat-title');
    const paneCount = document.getElementById('ops-skills-pane-count');
    if (activeTitle) {
      activeTitle.innerText = opsSkillsState.activeCategory === 'all' 
        ? (opsSkillsState.activeFilter === 'toolsets' ? 'TOOLSETS' : (opsSkillsState.activeFilter === 'browse_hub' ? 'BROWSE HUB' : 'ALL'))
        : opsSkillsState.activeCategory.toUpperCase();
    }
    if (activeIcon) {
      activeIcon.innerText = opsSkillsState.activeFilter === 'toolsets' ? '🔧' : '⬡';
    }
    if (paneCount) {
      paneCount.innerText = `${opsSkillsState.allSkills.length} skills`;
    }

    // 5. Render Skills Rows
    renderOpsSkillsRows(opsSkillsState.allSkills);
  } catch (err) {
    console.error('Error loading ops skills:', err);
    listPane.innerHTML = `<div style="padding:28px; text-align:center; color:#f43f5e;">${typeof t === 'function' ? t('ops_error_load') : 'স্কিল লোড করতে সমস্যা হয়েছে।'}</div>`;
  }
}

function renderOpsSkillsCategories(catMap) {
  const catList = document.getElementById('ops-skills-cat-list');
  if (!catList) return;

  const categoriesOrder = [
    "Autonomous AI Agents",
    "Creative",
    "Email",
    "Media",
    "Note Taking",
    "Productivity",
    "Research",
    "Social Media",
    "Software Development",
    "Web"
  ];

  catList.innerHTML = categoriesOrder.map(cat => {
    const count = catMap[cat] ?? 0;
    const isActive = opsSkillsState.activeCategory.toLowerCase() === cat.toLowerCase();
    return `
      <button type="button" class="ops-cat-row-btn ${isActive ? 'active' : ''}" onclick="setOpsSkillCategory('${escapeHtml(cat)}', this)">
        <span>${escapeHtml(cat)}</span>
        <span class="cat-count">${count}</span>
      </button>
    `;
  }).join('');
}

function renderOpsSkillsRows(skills) {
  const listPane = document.getElementById('ops-skills-list-pane');
  if (!listPane) return;

  if (!skills || skills.length === 0) {
    listPane.innerHTML = `<div style="padding:40px; text-align:center; color:#64748b;">কোনো স্কিল পাওয়া যায়নি।</div>`;
    return;
  }

  listPane.innerHTML = skills.map(s => {
    const isEnabled = s.is_enabled === 1 || s.is_enabled === true;
    return `
      <div class="ops-skill-entry-row" id="skill-row-${s.id}">
        <div class="ops-skill-tile-box ${isEnabled ? '' : 'disabled'}" onclick="toggleOpsSkillTile('${s.id}')" title="${isEnabled ? 'Disable skill' : 'Enable skill'}">
          <div class="tile-inner"></div>
        </div>
        <div class="ops-skill-entry-body" onclick="openSkillDetailModal('${s.id}')" style="cursor:pointer;">
          <div class="ops-skill-entry-name">
            <span>${escapeHtml(s.name)}</span>
            ${s.is_toolset ? '<span style="font-size:0.68rem; padding:1px 5px; border-radius:3px; background:rgba(56,189,248,0.12); color:#38bdf8; font-weight:500;">TOOLSET</span>' : ''}
          </div>
          <div class="ops-skill-entry-desc">${escapeHtml(s.description)}</div>
        </div>
        <button type="button" class="ops-skill-edit-btn" onclick="editOpsSkill('${s.id}')" title="Edit skill">
          ✏️
        </button>
        ${!s.is_system ? `<button type="button" class="ops-action-icon-btn danger" onclick="deleteOpsSkill('${s.id}')" title="Delete">🗑️</button>` : ''}
      </div>
    `;
  }).join('');
}

function setOpsSkillFilter(filterType, btnEl) {
  opsSkillsState.activeFilter = filterType;
  opsSkillsState.activeCategory = 'all';

  document.querySelectorAll('.ops-skill-filter-item').forEach(b => b.classList.remove('active'));
  if (btnEl) btnEl.classList.add('active');
  document.querySelectorAll('.ops-cat-row-btn').forEach(b => b.classList.remove('active'));

  loadOpsSkills();
}

function setOpsSkillCategory(catName, btnEl) {
  opsSkillsState.activeCategory = catName;
  opsSkillsState.activeFilter = 'all';

  document.querySelectorAll('.ops-skill-filter-item').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.ops-cat-row-btn').forEach(b => b.classList.remove('active'));
  if (btnEl) btnEl.classList.add('active');

  loadOpsSkills();
}

function handleOpsSkillsSearch(query) {
  opsSkillsState.searchQuery = query.trim();
  loadOpsSkills();
}

async function toggleOpsSkillTile(skillId) {
  try {
    const res = await opsFetch(`/api/ops/skills/${skillId}/toggle`, { method: 'PUT' });
    const data = await res.json();
    if (data.success) {
      loadOpsSkills();
    }
  } catch (err) {
    console.error(err);
  }
}

function openOpsLearnSkillModal() {
  const modal = document.getElementById('ops-learn-skill-modal');
  if (modal) modal.style.display = 'flex';
}

function closeOpsLearnSkillModal() {
  const modal = document.getElementById('ops-learn-skill-modal');
  if (modal) modal.style.display = 'none';
}

async function executeOpsLearnSkill(e) {
  e.preventDefault();
  const source_url = document.getElementById('ops-learn-url').value.trim();
  const name = document.getElementById('ops-learn-name').value.trim();
  const description = document.getElementById('ops-learn-desc').value.trim();
  const category = document.getElementById('ops-learn-cat').value;

  try {
    const res = await opsFetch('/api/ops/skills/learn', {
      method: 'POST',
      body: JSON.stringify({ source_url, name, description, category })
    });
    const data = await res.json();
    if (data.success) {
      closeOpsLearnSkillModal();
      loadOpsSkills();
      if (typeof showToast === 'function') showToast(`নতুন স্কিল '${data.name}' সংযুক্ত হয়েছে`, 'success');
    } else {
      alert(data.message || 'Failed to learn skill');
    }
  } catch (err) {
    alert('Learn skill request failed');
  }
}

function openNewSkillModal() {
  const modal = document.getElementById('ops-new-skill-modal');
  if (modal) modal.style.display = 'flex';
}

function closeNewSkillModal() {
  const modal = document.getElementById('ops-new-skill-modal');
  if (modal) modal.style.display = 'none';
}

async function saveNewOpsSkill(e) {
  e.preventDefault();
  const name = document.getElementById('skill-input-name').value.trim();
  const description = document.getElementById('skill-input-desc').value.trim();
  const icon = document.getElementById('skill-input-icon').value.trim() || '📦';
  const category = document.getElementById('skill-input-cat').value;
  const is_toolset = document.getElementById('skill-input-is-toolset') ? document.getElementById('skill-input-is-toolset').checked : false;
  const instructions = document.getElementById('skill-input-inst').value.trim();
  const triggersRaw = document.getElementById('skill-input-triggers').value.trim();
  const triggers = triggersRaw ? triggersRaw.split(',').map(s => s.trim()) : [];

  try {
    const res = await opsFetch('/api/ops/skills', {
      method: 'POST',
      body: JSON.stringify({ name, description, icon, category, instructions, triggers, is_toolset })
    });
    const data = await res.json();
    if (data.success) {
      closeNewSkillModal();
      loadOpsSkills();
      if (typeof showToast === 'function') showToast(typeof t === 'function' ? t('ops_skill_saved') : 'নতুন স্কিল যুক্ত হয়েছে', 'success');
    }
  } catch (err) {
    alert('Failed to save skill');
  }
}

async function deleteOpsSkill(skillId) {
  if (!confirm(typeof t === 'function' ? t('ops_confirm_delete_skill') : 'এই স্কিলটি মুছে ফেলতে চান?')) return;
  try {
    await opsFetch(`/api/ops/skills/${skillId}`, { method: 'DELETE' });
    loadOpsSkills();
  } catch (err) {
    alert('Failed to delete skill');
  }
}

function openSkillDetailModal(skillId) {
  const skill = opsSkillsState.allSkills.find(s => s.id === skillId);
  if (!skill) return;
  alert(`Skill: ${skill.name}\nCategory: ${skill.category}\nToolset: ${skill.is_toolset ? 'Yes' : 'No'}\n\n${skill.description}\n\nInstructions:\n${skill.instructions || 'Standard operation instructions.'}`);
}

function editOpsSkill(skillId) {
  openSkillDetailModal(skillId);
}

function openSkillAssistantPrompt() {
  if (typeof switchTab === 'function') {
    switchTab('chat');
    const input = document.getElementById('chat-input');
    if (input) {
      input.value = "Tell me about available Ops Agent skills and how I can utilize them for autonomous automation.";
      input.focus();
    }
  }
}

// ==============================================================================
// 5. PLUGINS MODULE
// ==============================================================================
async function loadOpsPlugins() {
  const grid = document.getElementById('ops-plugins-grid');
  if (!grid) return;

  try {
    const res = await opsFetch('/api/ops/plugins');
    const data = await res.json();
    if (!data.success) return;

    grid.innerHTML = data.plugins.map(p => `
      <div class="ops-card plugin-card">
        <div class="plugin-header">
          <div class="plugin-icon">${p.icon || '🧩'}</div>
          <div style="flex:1;">
            <div class="plugin-name">${escapeHtml(p.name)}</div>
            <div class="plugin-ver">v${escapeHtml(p.version)} • <span class="badge-${p.is_enabled ? 'online' : 'idle'}">${p.status}</span></div>
          </div>
          <label class="ops-switch">
            <input type="checkbox" ${p.is_enabled ? 'checked' : ''} onchange="toggleOpsPlugin('${p.id}')">
            <span class="slider round"></span>
          </label>
        </div>
        <p class="plugin-desc">${escapeHtml(p.description)}</p>
        <div class="plugin-footer">
          <span style="font-size:0.75rem; color:var(--text-muted);">${typeof t === 'function' ? t('ops_category') : 'ক্যাটাগরি'}: ${escapeHtml(p.category)}</span>
          <button class="btn-sm-action-cyber" onclick="testOpsPlugin('${p.id}')">🔬 ${typeof t === 'function' ? t('ops_btn_test') : 'টেস্ট'}</button>
        </div>
      </div>
    `).join('');
  } catch (err) {
    console.error('Error loading plugins:', err);
  }
}

async function toggleOpsPlugin(pluginId) {
  try {
    await opsFetch(`/api/ops/plugins/${pluginId}/toggle`, { method: 'PUT' });
    loadOpsPlugins();
  } catch (err) {
    console.error(err);
  }
}

async function testOpsPlugin(pluginId) {
  try {
    const res = await opsFetch(`/api/ops/plugins/${pluginId}/test`, { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      alert(`✅ ${data.name} (v${data.version})\n- Status: ${data.status}\n- Latency: ${data.ping_ms}ms\n- Runtime: ${data.runtime_environment}`);
    }
  } catch (err) {
    alert('Plugin test failed');
  }
}

// ==============================================================================
// 6. CHANNELS MODULE
// ==============================================================================
async function loadOpsChannels() {
  const grid = document.getElementById('ops-channels-grid');
  if (!grid) return;

  try {
    const res = await opsFetch('/api/ops/channels');
    const data = await res.json();
    if (!data.success) return;

    grid.innerHTML = data.channels.map(c => `
      <div class="ops-card channel-card">
        <div class="channel-header">
          <div class="channel-icon">${c.icon || '📡'}</div>
          <div style="flex:1;">
            <div class="channel-name">${escapeHtml(c.name)}</div>
            <div class="channel-platform">${escapeHtml(c.platform.toUpperCase())}</div>
          </div>
          <span class="status-pill ${c.status === 'Connected' ? 'success' : 'warn'}">${c.status}</span>
        </div>
        <div class="channel-body">
          <div class="channel-meta-item">
            <span class="meta-label">Endpoint / Webhook:</span>
            <code class="meta-val">${escapeHtml(c.webhook_url || 'Not configured')}</code>
          </div>
          <div class="channel-meta-item">
            <span class="meta-label">Chat/Channel ID:</span>
            <code class="meta-val">${escapeHtml(c.chat_id || 'Default')}</code>
          </div>
        </div>
        <div class="channel-footer">
          <button class="btn-sm-action-cyber" onclick="openChannelConfigModal('${c.id}', '${escapeHtml(c.name)}', '${escapeHtml(c.token || '')}', '${escapeHtml(c.webhook_url || '')}', '${escapeHtml(c.chat_id || '')}', ${c.is_enabled})">⚙️ ${typeof t === 'function' ? t('ops_btn_config') : 'কনফিগার'}</button>
          <button class="btn-sm-action-cyber" onclick="testOpsChannel('${c.id}')">📡 ${typeof t === 'function' ? t('ops_btn_ping') : 'পিং'}</button>
        </div>
      </div>
    `).join('');
  } catch (err) {
    console.error('Error loading channels:', err);
  }
}

function openChannelConfigModal(id, name, token, url, chatId, isEnabled) {
  const modal = document.getElementById('ops-channel-config-modal');
  if (!modal) return;
  document.getElementById('channel-config-id').value = id;
  document.getElementById('channel-config-name').innerText = name;
  document.getElementById('channel-config-token').value = token;
  document.getElementById('channel-config-url').value = url;
  document.getElementById('channel-config-chatid').value = chatId;
  document.getElementById('channel-config-enabled').checked = Boolean(isEnabled);
  modal.style.display = 'flex';
}

function closeChannelConfigModal() {
  const modal = document.getElementById('ops-channel-config-modal');
  if (modal) modal.style.display = 'none';
}

async function saveChannelConfig(e) {
  e.preventDefault();
  const id = document.getElementById('channel-config-id').value;
  const token = document.getElementById('channel-config-token').value.trim();
  const webhook_url = document.getElementById('channel-config-url').value.trim();
  const chat_id = document.getElementById('channel-config-chatid').value.trim();
  const is_enabled = document.getElementById('channel-config-enabled').checked;

  try {
    const res = await opsFetch(`/api/ops/channels/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ token, webhook_url, chat_id, is_enabled })
    });
    const data = await res.json();
    if (data.success) {
      closeChannelConfigModal();
      loadOpsChannels();
      if (typeof showToast === 'function') showToast(typeof t === 'function' ? t('ops_channel_saved') : 'চ্যানেল কনফিগারেশন সংরক্ষিত হয়েছে', 'success');
    }
  } catch (err) {
    alert('Failed to save channel configuration');
  }
}

async function testOpsChannel(channelId) {
  try {
    const res = await opsFetch(`/api/ops/channels/${channelId}/test`, { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      if (typeof showToast === 'function') showToast(data.message, 'success');
      loadOpsChannels();
    }
  } catch (err) {
    alert('Channel ping failed');
  }
}

// ==============================================================================
// 7. WEBHOOKS MODULE
// ==============================================================================
async function loadOpsWebhooks() {
  const tableBody = document.getElementById('ops-webhooks-table-body');
  const logsList = document.getElementById('ops-webhook-logs-list');
  if (!tableBody) return;

  try {
    const res = await opsFetch('/api/ops/webhooks');
    const data = await res.json();
    if (!data.success) return;

    if (!data.webhooks || data.webhooks.length === 0) {
      tableBody.innerHTML = `<tr><td colspan="6" class="text-center py-4" style="color:var(--text-muted);">${typeof t === 'function' ? t('ops_webhooks_empty') : 'কোনো সক্রিয় ওয়েবহুক নেই।'}</td></tr>`;
    } else {
      tableBody.innerHTML = data.webhooks.map(w => `
        <tr class="ops-row">
          <td style="font-weight:600; color:var(--text-primary);">${escapeHtml(w.name)}</td>
          <td><span class="status-pill ${w.webhook_type === 'inbound' ? 'info' : 'agent'}">${w.webhook_type.toUpperCase()}</span></td>
          <td><code style="font-size:0.75rem; color:var(--cyan-glow);">${escapeHtml(w.target_url)}</code></td>
          <td style="font-family:'Fira Code', monospace; font-size:0.75rem;">${escapeHtml(w.secret_token ? w.secret_token.substring(0, 10) + '...' : 'None')}</td>
          <td><span class="ops-tag">${w.delivery_count} ${typeof t === 'function' ? t('ops_delivered') : 'ডেলিভারি'}</span></td>
          <td style="text-align:right;">
            <button class="btn-sm-cyber" onclick="testOpsWebhook('${w.id}')">🚀 ${typeof t === 'function' ? t('ops_btn_test') : 'টেস্ট'}</button>
            <button class="btn-sm-cyber danger" onclick="deleteOpsWebhook('${w.id}')">🗑️</button>
          </td>
        </tr>
      `).join('');
    }

    if (logsList) {
      if (!data.logs || data.logs.length === 0) {
        logsList.innerHTML = `<div style="text-align:center; padding:12px; color:var(--text-muted);">${typeof t === 'function' ? t('ops_no_webhook_logs') : 'কোনো ওয়েবহুক ইভেন্ট হিস্টোরি নেই।'}</div>`;
      } else {
        logsList.innerHTML = data.logs.map(l => `
          <div class="ops-history-item">
            <div style="display:flex; justify-content:space-between;">
              <span style="font-weight:600; color:var(--text-primary);">${escapeHtml(l.event_type)}</span>
              <span class="status-pill success">${l.status_code} (${l.duration_ms}ms)</span>
            </div>
            <div style="font-size:0.7rem; color:var(--text-muted); margin-top:2px;">${l.timestamp}</div>
          </div>
        `).join('');
      }
    }
  } catch (err) {
    console.error('Error loading webhooks:', err);
  }
}

async function testOpsWebhook(hookId) {
  try {
    const res = await opsFetch(`/api/ops/webhooks/${hookId}/test`, { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      if (typeof showToast === 'function') showToast(typeof t === 'function' ? t('ops_webhook_tested') : `ওয়েবহুক সফলভাবে ট্রিগার হয়েছে (${data.duration_ms}ms)`, 'success');
      loadOpsWebhooks();
    }
  } catch (err) {
    alert('Webhook test failed');
  }
}

async function deleteOpsWebhook(hookId) {
  if (!confirm(typeof t === 'function' ? t('ops_confirm_delete_webhook') : 'ওয়েবহুকটি মুছে ফেলতে চান?')) return;
  try {
    await opsFetch(`/api/ops/webhooks/${hookId}`, { method: 'DELETE' });
    loadOpsWebhooks();
  } catch (err) {
    alert('Failed to delete webhook');
  }
}

function openNewWebhookModal() {
  const modal = document.getElementById('ops-new-webhook-modal');
  if (modal) modal.style.display = 'flex';
}

function closeNewWebhookModal() {
  const modal = document.getElementById('ops-new-webhook-modal');
  if (modal) modal.style.display = 'none';
}

async function saveNewOpsWebhook(e) {
  e.preventDefault();
  const name = document.getElementById('webhook-input-name').value.trim();
  const webhook_type = document.getElementById('webhook-input-type').value;
  const target_url = document.getElementById('webhook-input-url').value.trim();

  try {
    const res = await opsFetch('/api/ops/webhooks', {
      method: 'POST',
      body: JSON.stringify({ name, webhook_type, target_url })
    });
    const data = await res.json();
    if (data.success) {
      closeNewWebhookModal();
      loadOpsWebhooks();
      if (typeof showToast === 'function') showToast(typeof t === 'function' ? t('ops_webhook_created') : 'নতুন ওয়েবহুক তৈরি হয়েছে', 'success');
    }
  } catch (err) {
    alert('Failed to create webhook');
  }
}

// ==============================================================================
// 8. PAIRING MODULE
// ==============================================================================
async function loadOpsPairing() {
  const tableBody = document.getElementById('ops-paired-devices-table');
  const codeBox = document.getElementById('ops-active-pairing-code');
  const countdownBox = document.getElementById('ops-pairing-countdown');
  if (!tableBody) return;

  try {
    const res = await opsFetch('/api/ops/pairing');
    const data = await res.json();
    if (!data.success) return;

    // Active pairing code
    if (data.active_code) {
      if (codeBox) codeBox.innerText = data.active_code.code;
      startPairingCountdown(data.active_code.expires_in_seconds);
    } else {
      if (codeBox) codeBox.innerText = '------';
      if (countdownBox) countdownBox.innerText = typeof t === 'function' ? t('ops_click_generate_code') : 'কোড তৈরি করতে নিচের বাটনে চাপ দিন';
    }

    // Devices table
    if (!data.devices || data.devices.length === 0) {
      tableBody.innerHTML = `<tr><td colspan="6" class="text-center py-4" style="color:var(--text-muted);">${typeof t === 'function' ? t('ops_no_paired_devices') : 'কোনো পেয়ার করা ডিভাইস নেই।'}</td></tr>`;
    } else {
      tableBody.innerHTML = data.devices.map(d => `
        <tr class="ops-row">
          <td style="font-weight:600; color:var(--text-primary); display:flex; align-items:center; gap:8px;">
            <span>💻</span>
            <span>${escapeHtml(d.device_name)}</span>
          </td>
          <td><span class="ops-tag">${escapeHtml(d.platform)}</span></td>
          <td style="font-family:'Fira Code', monospace; font-size:0.8rem;">${escapeHtml(d.ip_address || '192.168.9.x')}</td>
          <td style="color:var(--text-muted); font-size:0.8rem;">${d.paired_at}</td>
          <td><span class="status-pill success">${d.status}</span></td>
          <td style="text-align:right;">
            <button class="btn-sm-cyber danger" onclick="revokeOpsDevice('${d.device_id}')">❌ ${typeof t === 'function' ? t('ops_btn_revoke') : 'বাতিল'}</button>
          </td>
        </tr>
      `).join('');
    }
  } catch (err) {
    console.error('Error loading pairing:', err);
  }
}

async function generateOpsPairingCode() {
  try {
    const res = await opsFetch('/api/ops/pairing/generate', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      const codeBox = document.getElementById('ops-active-pairing-code');
      if (codeBox) codeBox.innerText = data.code;
      startPairingCountdown(data.expires_in_seconds);
      if (typeof showToast === 'function') showToast(typeof t === 'function' ? t('ops_pairing_code_generated') : `নতুন ৬-সংখ্যার পেয়ারিং কোড তৈরি হয়েছে: ${data.code}`, 'success');
    }
  } catch (err) {
    alert('Failed to generate pairing code');
  }
}

function startPairingCountdown(seconds) {
  if (opsPairingTimer) clearInterval(opsPairingTimer);
  let left = seconds;
  const box = document.getElementById('ops-pairing-countdown');

  function update() {
    if (left <= 0) {
      clearInterval(opsPairingTimer);
      if (box) box.innerText = typeof t === 'function' ? t('ops_code_expired') : 'কোডের মেয়াদ শেষ হয়েছে। নতুন কোড তৈরি করুন।';
      const codeBox = document.getElementById('ops-active-pairing-code');
      if (codeBox) codeBox.innerText = '------';
      return;
    }
    const mins = Math.floor(left / 60);
    const secs = left % 60;
    if (box) box.innerText = `${typeof t === 'function' ? t('ops_code_valid_for') : 'মেয়াদ আছে'}: ${mins}:${secs < 10 ? '0' : ''}${secs}`;
    left--;
  }

  update();
  opsPairingTimer = setInterval(update, 1000);
}

async function revokeOpsDevice(deviceId) {
  if (!confirm(typeof t === 'function' ? t('ops_confirm_revoke') : 'এই ডিভাইসের অ্যাক্সেস বাতিল করতে চান?')) return;
  try {
    await opsFetch(`/api/ops/pairing/${deviceId}`, { method: 'DELETE' });
    loadOpsPairing();
    if (typeof showToast === 'function') showToast(typeof t === 'function' ? t('ops_device_revoked') : 'ডিভাইস অ্যাক্সেস বাতিল করা হয়েছে', 'success');
  } catch (err) {
    alert('Failed to revoke device');
  }
}

// ==============================================================================
// 9. PROFILES MODULE
// ==============================================================================
async function loadOpsProfiles() {
  const grid = document.getElementById('ops-profiles-grid');
  if (!grid) return;

  try {
    const res = await opsFetch('/api/ops/profiles');
    const data = await res.json();
    if (!data.success) return;

    grid.innerHTML = data.profiles.map(p => `
      <div class="ops-card profile-card ${p.is_active ? 'active-profile' : ''}">
        <div class="profile-header">
          <div class="profile-avatar">${p.avatar || '🤖'}</div>
          <div style="flex:1;">
            <div class="profile-name">${escapeHtml(p.name)}</div>
            <div class="profile-meta">Temp: ${p.temperature} • Model: ${escapeHtml(p.model)}</div>
          </div>
          ${p.is_active 
            ? `<span class="status-pill success">★ ${typeof t === 'function' ? t('ops_profile_active') : 'সক্রিয় পার্সোনা'}</span>`
            : `<button class="btn-sm-action-cyber" onclick="activateOpsProfile('${p.id}')">⚡ ${typeof t === 'function' ? t('ops_btn_activate') : 'সক্রিয় করুন'}</button>`
          }
        </div>
        <p class="profile-desc">${escapeHtml(p.description)}</p>
        <div class="profile-prompt-preview">
          <code>${escapeHtml(p.system_prompt.substring(0, 130))}...</code>
        </div>
        <div class="profile-footer">
          <span style="font-size:0.75rem; color:var(--text-muted);">${typeof t === 'function' ? t('ops_memory_scope') : 'মেমোরি স্কোপ'}: ${escapeHtml(p.memory_scope)}</span>
          ${!p.is_system && !p.is_active ? `<button class="btn-icon-danger" onclick="deleteOpsProfile('${p.id}')">🗑️</button>` : ''}
        </div>
      </div>
    `).join('');
  } catch (err) {
    console.error('Error loading profiles:', err);
  }
}

async function activateOpsProfile(profId) {
  try {
    const res = await opsFetch(`/api/ops/profiles/${profId}/activate`, { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      loadOpsProfiles();
      if (typeof showToast === 'function') showToast(typeof t === 'function' ? t('ops_profile_switched') : `এজেন্ট পার্সোনা পরিবর্তিত হয়েছে: ${data.name}`, 'success');
    }
  } catch (err) {
    alert('Failed to switch profile');
  }
}

async function deleteOpsProfile(profId) {
  if (!confirm(typeof t === 'function' ? t('ops_confirm_delete_profile') : 'এই পার্সোনা প্রোফাইলটি মুছে ফেলতে চান?')) return;
  try {
    await opsFetch(`/api/ops/profiles/${profId}`, { method: 'DELETE' });
    loadOpsProfiles();
  } catch (err) {
    alert('Failed to delete profile');
  }
}

function openNewProfileModal() {
  const modal = document.getElementById('ops-new-profile-modal');
  if (modal) modal.style.display = 'flex';
}

function closeNewProfileModal() {
  const modal = document.getElementById('ops-new-profile-modal');
  if (modal) modal.style.display = 'none';
}

async function saveNewOpsProfile(e) {
  e.preventDefault();
  const name = document.getElementById('profile-input-name').value.trim();
  const avatar = document.getElementById('profile-input-avatar').value.trim() || '🤖';
  const description = document.getElementById('profile-input-desc').value.trim();
  const system_prompt = document.getElementById('profile-input-prompt').value.trim();
  const temperature = parseFloat(document.getElementById('profile-input-temp').value) || 0.3;
  const model = document.getElementById('profile-input-model').value;

  try {
    const res = await opsFetch('/api/ops/profiles', {
      method: 'POST',
      body: JSON.stringify({ name, avatar, description, system_prompt, temperature, model })
    });
    const data = await res.json();
    if (data.success) {
      closeNewProfileModal();
      loadOpsProfiles();
      if (typeof showToast === 'function') showToast(typeof t === 'function' ? t('ops_profile_saved') : 'নতুন পার্সোনা তৈরি হয়েছে', 'success');
    }
  } catch (err) {
    alert('Failed to save profile');
  }
}

// ------------------------------------------------------------------------------
// Utility helper: HTML escape
// ------------------------------------------------------------------------------
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// Attach functions to global window for template event handlers
window.loadOpsFiles = loadOpsFiles;
window.previewOpsFile = previewOpsFile;
window.deleteOpsFile = deleteOpsFile;
window.closeOpsPreviewModal = closeOpsPreviewModal;

window.loadOpsLogs = loadOpsLogs;
window.setOpsLogFilter = setOpsLogFilter;
window.toggleOpsLogAutoScroll = toggleOpsLogAutoScroll;
window.clearOpsLogs = clearOpsLogs;
window.downloadOpsLogs = downloadOpsLogs;

window.loadOpsCron = loadOpsCron;
window.triggerOpsCron = triggerOpsCron;
window.toggleOpsCron = toggleOpsCron;
window.deleteOpsCron = deleteOpsCron;
window.openNewCronModal = openNewCronModal;
window.closeNewCronModal = closeNewCronModal;
window.saveNewOpsCron = saveNewOpsCron;

window.loadOpsSkills = loadOpsSkills;
window.setOpsSkillFilter = setOpsSkillFilter;
window.setOpsSkillCategory = setOpsSkillCategory;
window.handleOpsSkillsSearch = handleOpsSkillsSearch;
window.toggleOpsSkillTile = toggleOpsSkillTile;
window.openOpsLearnSkillModal = openOpsLearnSkillModal;
window.closeOpsLearnSkillModal = closeOpsLearnSkillModal;
window.executeOpsLearnSkill = executeOpsLearnSkill;
window.openSkillAssistantPrompt = openSkillAssistantPrompt;
window.openSkillDetailModal = openSkillDetailModal;
window.editOpsSkill = editOpsSkill;
window.deleteOpsSkill = deleteOpsSkill;
window.openNewSkillModal = openNewSkillModal;
window.closeNewSkillModal = closeNewSkillModal;
window.saveNewOpsSkill = saveNewOpsSkill;

window.loadOpsPlugins = loadOpsPlugins;
window.toggleOpsPlugin = toggleOpsPlugin;
window.testOpsPlugin = testOpsPlugin;

window.loadOpsChannels = loadOpsChannels;
window.openChannelConfigModal = openChannelConfigModal;
window.closeChannelConfigModal = closeChannelConfigModal;
window.saveChannelConfig = saveChannelConfig;
window.testOpsChannel = testOpsChannel;

window.loadOpsWebhooks = loadOpsWebhooks;
window.testOpsWebhook = testOpsWebhook;
window.deleteOpsWebhook = deleteOpsWebhook;
window.openNewWebhookModal = openNewWebhookModal;
window.closeNewWebhookModal = closeNewWebhookModal;
window.saveNewOpsWebhook = saveNewOpsWebhook;

window.loadOpsPairing = loadOpsPairing;
window.generateOpsPairingCode = generateOpsPairingCode;
window.revokeOpsDevice = revokeOpsDevice;

window.loadOpsProfiles = loadOpsProfiles;
window.activateOpsProfile = activateOpsProfile;
window.deleteOpsProfile = deleteOpsProfile;
window.openNewProfileModal = openNewProfileModal;
window.closeNewProfileModal = closeNewProfileModal;
window.saveNewOpsProfile = saveNewOpsProfile;

// Ops Sessions Module
window.loadOpsSessions = loadOpsSessions;
window.openPruneSessionsModal = openPruneSessionsModal;
window.closePruneSessionsModal = closePruneSessionsModal;
window.executePruneSessions = executePruneSessions;
window.openImportSessionsModal = openImportSessionsModal;
window.closeImportSessionsModal = closeImportSessionsModal;
window.handleImportSessionFile = handleImportSessionFile;
window.executeImportSessions = executeImportSessions;
window.setOpsSessionFilter = setOpsSessionFilter;
window.filterOpsSessionsBySource = filterOpsSessionsBySource;
window.setOpsSessionView = setOpsSessionView;
window.openSessionDirectly = openSessionDirectly;
window.deleteOpsSession = deleteOpsSession;

// Ops Filesystem Explorer (/opt/data)
window.loadOpsFilesExplorer = loadOpsFilesExplorer;
window.navigateOpsFsUp = navigateOpsFsUp;
window.triggerOpsFsUpload = triggerOpsFsUpload;
window.handleOpsFsFileSelected = handleOpsFsFileSelected;
window.handleOpsFsDragOver = handleOpsFsDragOver;
window.handleOpsFsDragLeave = handleOpsFsDragLeave;
window.handleOpsFsDrop = handleOpsFsDrop;
window.openOpsCreateFsItemModal = openOpsCreateFsItemModal;
window.closeOpsCreateFsItemModal = closeOpsCreateFsItemModal;
window.executeOpsCreateFsItem = executeOpsCreateFsItem;
window.deleteOpsFsItem = deleteOpsFsItem;
window.downloadOrPreviewFsFile = downloadOrPreviewFsFile;
