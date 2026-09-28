/* ==============================================================================
 * Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
 * Made By Arif (https://arifmahmud.com/)
 * Project: MyAgent | Version: 3.1.0
 * Hermes Agent Operational Suite Manager
 * (FILES, MODELS, LOGS, CRON, SKILLS, PLUGINS, MCP, CHANNELS, WEBHOOKS, PAIRING, PROFILES)
 * ============================================================================== */

// Global Hermes State
let hermesLogsAutoScroll = true;
let hermesPairingTimer = null;
let hermesActiveFilter = 'ALL';
let hermesFsCurrentPath = '/opt/data';
let hermesSessionsData = null;
let hermesCurrentSessionFilter = 'chats';
let hermesCurrentSessionSource = 'any';
let hermesCurrentSessionView = 'overview';

// ------------------------------------------------------------------------------
// Helper: Authenticated fetch wrapper
// ------------------------------------------------------------------------------
async function hermesFetch(url, options = {}) {
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
async function loadHermesSessions() {
  const badgeCount = document.getElementById('hermes-sessions-badge-count');
  const kpiTotal = document.getElementById('hermes-kpi-total-sess');
  const kpiActive = document.getElementById('hermes-kpi-active-sess');
  const kpiArchived = document.getElementById('hermes-kpi-archived-sess');
  const kpiMessages = document.getElementById('hermes-kpi-messages-sess');
  const kpiSources = document.getElementById('hermes-kpi-sources-sess');
  const platformsContainer = document.getElementById('hermes-connected-platforms-list');
  const recentSessionsContainer = document.getElementById('hermes-recent-sessions-list');

  if (platformsContainer) platformsContainer.innerHTML = '<div style="color:var(--text-muted); font-size:0.85rem; padding:10px;">লোড হচ্ছে...</div>';
  if (recentSessionsContainer) recentSessionsContainer.innerHTML = '<div style="color:var(--text-muted); font-size:0.85rem; padding:10px;">লোড হচ্ছে...</div>';

  try {
    const res = await hermesFetch('/api/sessions/overview');
    const data = await res.json();
    if (!data.success) throw new Error('Failed to load sessions');
    hermesSessionsData = data;

    if (badgeCount) badgeCount.innerText = data.active_in_store || data.total || 0;
    if (kpiTotal) kpiTotal.innerText = data.total || 0;
    if (kpiActive) kpiActive.innerText = data.active_in_store || 0;
    if (kpiArchived) kpiArchived.innerText = data.archived || 0;
    if (kpiMessages) kpiMessages.innerText = data.messages || 0;
    if (kpiSources) kpiSources.innerText = data.sources || 1;

    renderHermesPlatforms(data.connected_platforms || []);
    renderHermesRecentSessions();
  } catch (err) {
    console.error('Error loading hermes sessions:', err);
    if (platformsContainer) platformsContainer.innerHTML = '<div style="color:var(--rose-glow); font-size:0.85rem;">প্ল্যাটফর্ম লোড ব্যর্থ হয়েছে।</div>';
    if (recentSessionsContainer) recentSessionsContainer.innerHTML = '<div style="color:var(--rose-glow); font-size:0.85rem;">সেশন লোড ব্যর্থ হয়েছে।</div>';
  }
}

function renderHermesPlatforms(platforms) {
  const container = document.getElementById('hermes-connected-platforms-list');
  if (!container) return;
  if (!platforms || platforms.length === 0) {
    container.innerHTML = '<div style="color:var(--text-muted); font-size:0.85rem;">কোনো সক্রিয় প্ল্যাটফর্ম পাওয়া যায়নি।</div>';
    return;
  }
  container.innerHTML = platforms.map(p => `
    <div class="hermes-platform-row">
      <div class="hermes-plat-left">
        <span class="hermes-plat-icon">📶</span>
        <div>
          <div class="hermes-plat-title">${escapeHtml(p.name)}</div>
          <div class="hermes-plat-sub">Last update: ${escapeHtml(p.last_update)}</div>
        </div>
      </div>
      <div class="hermes-status-pill">${escapeHtml(p.status || 'Connected')}</div>
    </div>
  `).join('');
}

function renderHermesRecentSessions() {
  const container = document.getElementById('hermes-recent-sessions-list');
  if (!container || !hermesSessionsData) return;

  let list = hermesSessionsData.recent_sessions || [];

  // Filter by Type
  if (hermesCurrentSessionFilter === 'automation') {
    list = list.filter(s => s.is_archived || s.source === 'automation');
  } else if (hermesCurrentSessionFilter === 'chats') {
    list = list.filter(s => !s.is_archived);
  }

  // Filter by Source
  if (hermesCurrentSessionSource !== 'any') {
    list = list.filter(s => s.source === hermesCurrentSessionSource);
  }

  if (list.length === 0) {
    container.innerHTML = '<div style="color:var(--text-muted); font-size:0.85rem; padding:12px; text-align:center;">কোনো সেশন পাওয়া যায়নি।</div>';
    return;
  }

  container.innerHTML = list.map(s => `
    <div class="hermes-session-card" onclick="openSessionDirectly('${escapeHtml(s.id)}')">
      <div>
        <div class="hermes-sess-title">${escapeHtml(s.title || 'Untitled Session')}</div>
        <div class="hermes-sess-meta">${escapeHtml(s.model)} · ${s.msg_count} msgs · ${escapeHtml(s.updated_at || 'just now')}</div>
        <div class="hermes-sess-snippet">${escapeHtml(s.snippet || '')}</div>
      </div>
      <div style="display:flex; align-items:center; gap:8px;">
        <button type="button" class="hermes-tui-badge" onclick="event.stopPropagation(); openSessionDirectly('${escapeHtml(s.id)}')">
          💾 TUI
        </button>
        <button type="button" class="hermes-action-icon-btn danger" onclick="event.stopPropagation(); deleteHermesSession('${escapeHtml(s.id)}')">
          🗑️
        </button>
      </div>
    </div>
  `).join('');
}

function setHermesSessionFilter(type, btn) {
  hermesCurrentSessionFilter = type;
  const parent = document.getElementById('hermes-sess-type-group');
  if (parent) {
    parent.querySelectorAll('.hermes-filter-btn').forEach(b => b.classList.remove('active'));
  }
  if (btn) btn.classList.add('active');
  renderHermesRecentSessions();
}

function filterHermesSessionsBySource(src) {
  hermesCurrentSessionSource = src;
  renderHermesRecentSessions();
}

function setHermesSessionView(view, btn) {
  hermesCurrentSessionView = view;
  const parent = document.getElementById('hermes-sess-view-group');
  if (parent) {
    parent.querySelectorAll('.hermes-filter-btn').forEach(b => b.classList.remove('active'));
  }
  if (btn) btn.classList.add('active');
  renderHermesRecentSessions();
}

function openSessionDirectly(sessionId) {
  if (typeof switchSession === 'function') {
    switchSession(sessionId);
  }
  if (typeof switchTab === 'function') {
    switchTab('chat');
  }
}

async function deleteHermesSession(sessionId) {
  if (!confirm('এই সেশনটি সম্পূর্ণ মুছে ফেলতে চান?')) return;
  try {
    const res = await hermesFetch(`/api/sessions/${sessionId}`, { method: 'DELETE' });
    const data = await res.json();
    if (data.success) {
      if (typeof showToast === 'function') showToast('সেশন মুছে ফেলা হয়েছে', 'info');
      loadHermesSessions();
      if (typeof loadSessionList === 'function') loadSessionList();
    }
  } catch (err) {
    alert('Failed to delete session');
  }
}

function openPruneSessionsModal() {
  const m = document.getElementById('hermes-prune-sessions-modal');
  if (m) m.style.display = 'flex';
}
function closePruneSessionsModal() {
  const m = document.getElementById('hermes-prune-sessions-modal');
  if (m) m.style.display = 'none';
}
async function executePruneSessions(e) {
  e.preventDefault();
  const days = parseInt(document.getElementById('prune-sess-days').value) || 30;
  const emptyOnly = document.getElementById('prune-sess-empty-only').checked;

  try {
    const res = await hermesFetch('/api/sessions/prune', {
      method: 'POST',
      body: JSON.stringify({ days, empty_only: emptyOnly })
    });
    const data = await res.json();
    if (data.success) {
      closePruneSessionsModal();
      loadHermesSessions();
      if (typeof loadSessionList === 'function') loadSessionList();
      if (typeof showToast === 'function') showToast(`সফলভাবে ${data.pruned_count}টি সেশন প্রুন করা হয়েছে`, 'success');
    }
  } catch (err) {
    alert('Failed to prune sessions');
  }
}

function openImportSessionsModal() {
  const m = document.getElementById('hermes-import-sessions-modal');
  if (m) m.style.display = 'flex';
}
function closeImportSessionsModal() {
  const m = document.getElementById('hermes-import-sessions-modal');
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
    const res = await hermesFetch('/api/sessions/import', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.success) {
      closeImportSessionsModal();
      loadHermesSessions();
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
async function loadHermesFilesExplorer(targetPath) {
  if (targetPath) hermesFsCurrentPath = targetPath;
  const path = hermesFsCurrentPath || '/opt/data';

  const badge = document.getElementById('hermes-fs-header-badge');
  const pathDisplay = document.getElementById('hermes-fs-current-path');
  const dropPath = document.getElementById('hermes-fs-drop-path');
  const upBtn = document.getElementById('hermes-fs-up-btn');
  const tableBody = document.getElementById('hermes-fs-table-body');

  if (badge) badge.innerText = path;
  if (pathDisplay) pathDisplay.innerText = path;
  if (dropPath) dropPath.innerText = path;

  if (tableBody) {
    tableBody.innerHTML = `<tr><td colspan="4" class="text-center py-4" style="color:var(--text-muted);">${typeof t === 'function' ? t('hermes_loading') : 'লোড হচ্ছে...'}</td></tr>`;
  }

  try {
    const res = await hermesFetch(`/api/hermes/fs/list?path=${encodeURIComponent(path)}`);
    const data = await res.json();
    if (!data.success) throw new Error(data.message || 'Failed to list directory');

    if (upBtn) {
      upBtn.style.display = data.parent_path ? 'inline-flex' : 'none';
      upBtn.setAttribute('data-parent-path', data.parent_path || '');
    }

    if (!data.items || data.items.length === 0) {
      tableBody.innerHTML = `<tr><td colspan="4" class="text-center py-4" style="color:var(--text-muted);">${typeof t === 'function' ? t('hermes_files_empty') : 'কোনো ফাইল বা ফোল্ডার পাওয়া যায়নি।'}</td></tr>`;
      return;
    }

    tableBody.innerHTML = data.items.map(item => `
      <tr class="hermes-row">
        <td>
          <div class="hermes-row-name" onclick="${item.is_dir ? `loadHermesFilesExplorer('${escapeHtml(item.virtual_path)}')` : `downloadOrPreviewFsFile('${escapeHtml(item.virtual_path)}')`}">
            <span class="${item.is_dir ? 'hermes-folder-icon' : 'hermes-file-icon'}">${item.is_dir ? '📁' : '📄'}</span>
            <span>${escapeHtml(item.name)}</span>
          </div>
        </td>
        <td style="font-family:'Fira Code', monospace; color:var(--text-muted); font-size:0.8rem;">${escapeHtml(item.size)}</td>
        <td style="color:var(--text-secondary); font-size:0.8rem;">${escapeHtml(item.modified)}</td>
        <td style="text-align:right;">
          ${item.is_dir ? `
            <button type="button" class="hermes-action-icon-btn" title="Open Folder" onclick="loadHermesFilesExplorer('${escapeHtml(item.virtual_path)}')">📁</button>
          ` : `
            <button type="button" class="hermes-action-icon-btn" title="Download File" onclick="downloadOrPreviewFsFile('${escapeHtml(item.virtual_path)}')">⬇️</button>
          `}
          <button type="button" class="hermes-action-icon-btn danger" title="Delete" onclick="deleteHermesFsItem('${escapeHtml(path)}', '${escapeHtml(item.name)}', ${item.is_dir})">🗑️</button>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    console.error('Error loading filesystem:', err);
    if (tableBody) {
      tableBody.innerHTML = `<tr><td colspan="4" class="text-center py-4" style="color:var(--rose-glow);">${typeof t === 'function' ? t('hermes_error_load') : 'ফাইলসিস্টেম লোড করতে ব্যর্থ হয়েছে।'}</td></tr>`;
    }
  }
}

function navigateHermesFsUp() {
  const upBtn = document.getElementById('hermes-fs-up-btn');
  const parentPath = upBtn ? upBtn.getAttribute('data-parent-path') : null;
  if (parentPath) {
    loadHermesFilesExplorer(parentPath);
  }
}

function triggerHermesFsUpload() {
  const input = document.getElementById('hermes-fs-file-input');
  if (input) input.click();
}

async function handleHermesFsFileSelected(e) {
  const files = e.target.files;
  if (!files || files.length === 0) return;
  await uploadFilesToFs(files);
  e.target.value = '';
}

function handleHermesFsDragOver(e) {
  e.preventDefault();
  const dropzone = document.getElementById('hermes-fs-dropzone');
  if (dropzone) dropzone.classList.add('drag-active');
}

function handleHermesFsDragLeave(e) {
  e.preventDefault();
  const dropzone = document.getElementById('hermes-fs-dropzone');
  if (dropzone) dropzone.classList.remove('drag-active');
}

async function handleHermesFsDrop(e) {
  e.preventDefault();
  const dropzone = document.getElementById('hermes-fs-dropzone');
  if (dropzone) dropzone.classList.remove('drag-active');

  const files = e.dataTransfer.files;
  if (files && files.length > 0) {
    await uploadFilesToFs(files);
  }
}

async function uploadFilesToFs(files) {
  const path = hermesFsCurrentPath || '/opt/data';
  const token = localStorage.getItem('myagent_token');

  for (let i = 0; i < files.length; i++) {
    const file = files[i];
    const formData = new FormData();
    formData.append('file', file);
    formData.append('path', path);

    try {
      const headers = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const res = await fetch('/api/hermes/fs/upload', {
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
  loadHermesFilesExplorer();
}

function openHermesCreateFsItemModal() {
  const modal = document.getElementById('hermes-create-fs-modal');
  const pathInput = document.getElementById('hermes-create-fs-path');
  const nameInput = document.getElementById('hermes-create-fs-name');
  if (pathInput) pathInput.value = hermesFsCurrentPath || '/opt/data';
  if (nameInput) nameInput.value = '';
  if (modal) modal.style.display = 'flex';
}

function closeHermesCreateFsItemModal() {
  const modal = document.getElementById('hermes-create-fs-modal');
  if (modal) modal.style.display = 'none';
}

async function executeHermesCreateFsItem(e) {
  e.preventDefault();
  const path = document.getElementById('hermes-create-fs-path').value.trim();
  const type = document.getElementById('hermes-create-fs-type').value;
  const name = document.getElementById('hermes-create-fs-name').value.trim();

  if (!name) return;

  try {
    const res = await hermesFetch('/api/hermes/fs/create', {
      method: 'POST',
      body: JSON.stringify({
        path,
        name,
        is_directory: type === 'folder'
      })
    });
    const data = await res.json();
    if (data.success) {
      closeHermesCreateFsItemModal();
      loadHermesFilesExplorer();
      if (typeof showToast === 'function') showToast(`${name} তৈরি করা হয়েছে`, 'success');
    } else {
      alert(data.message || 'Failed to create item');
    }
  } catch (err) {
    alert('Create request failed');
  }
}

async function deleteHermesFsItem(path, name, isDir) {
  const msg = isDir ? `আপনি কি ফোল্ডার '${name}' এবং এর ভেতরের সবকিছু মুছে ফেলতে চান?` : `আপনি কি '${name}' মুছে ফেলতে চান?`;
  if (!confirm(msg)) return;

  try {
    const res = await hermesFetch('/api/hermes/fs/delete', {
      method: 'DELETE',
      body: JSON.stringify({ path, name })
    });
    const data = await res.json();
    if (data.success) {
      loadHermesFilesExplorer();
      if (typeof showToast === 'function') showToast(`${name} মুছে ফেলা হয়েছে`, 'info');
    }
  } catch (err) {
    alert('Delete request failed');
  }
}

function downloadOrPreviewFsFile(virtualPath) {
  const url = `/api/hermes/fs/download?path=${encodeURIComponent(virtualPath)}`;
  window.open(url, '_blank');
}

// ==============================================================================
// 1. FILES MODULE (Vector Ingested Overview)
// ==============================================================================
async function loadHermesFiles() {
  const container = document.getElementById('hermes-files-table-body');
  const countBadge = document.getElementById('hermes-files-total-badge');
  const chunksBadge = document.getElementById('hermes-files-chunks-badge');
  if (!container) return;

  container.innerHTML = `<tr><td colspan="6" class="text-center py-4" style="color:var(--text-muted);">${typeof t === 'function' ? t('hermes_loading') : 'লোড হচ্ছে...'}</td></tr>`;

  try {
    const res = await hermesFetch('/api/hermes/files/overview');
    const data = await res.json();
    if (!data.success) throw new Error(data.message || 'Failed to fetch files');

    if (countBadge) countBadge.innerText = data.total_files || 0;
    if (chunksBadge) chunksBadge.innerText = data.total_chunks || 0;

    if (!data.files || data.files.length === 0) {
      container.innerHTML = `<tr><td colspan="6" class="text-center py-4" style="color:var(--text-muted);">${typeof t === 'function' ? t('hermes_files_empty') : 'কোনো ফাইল আপলোড করা হয়নি।'}</td></tr>`;
      return;
    }

    container.innerHTML = data.files.map(f => `
      <tr class="hermes-row">
        <td style="font-weight:600; color:var(--text-primary); display:flex; align-items:center; gap:8px;">
          <span>📁</span>
          <span>${escapeHtml(f.filename)}</span>
        </td>
        <td><span class="hermes-tag">${escapeHtml(f.file_type.toUpperCase())}</span></td>
        <td style="font-family:'Fira Code', monospace; color:var(--cyan-glow);">${f.chunk_count} ${typeof t === 'function' ? t('hermes_chunks') : 'চাঙ্কস'}</td>
        <td style="color:var(--text-secondary); font-size:0.8rem;">${escapeHtml(f.category)}</td>
        <td style="color:var(--text-muted); font-size:0.8rem;">${f.created_at}</td>
        <td style="text-align:right;">
          <button class="btn-sm-cyber" onclick="previewHermesFile('${escapeHtml(f.id)}', '${escapeHtml(f.filename)}')">👁️ ${typeof t === 'function' ? t('hermes_btn_preview') : 'প্রিভিউ'}</button>
          <button class="btn-sm-cyber danger" onclick="deleteHermesFile('${escapeHtml(f.id)}')">🗑️</button>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    console.error('Error loading hermes files:', err);
    container.innerHTML = `<tr><td colspan="6" class="text-center py-4" style="color:var(--rose-glow);">${typeof t === 'function' ? t('hermes_error_load') : 'ফাইল লোড করতে সমস্যা হয়েছে।'}</td></tr>`;
  }
}

async function previewHermesFile(docId, filename) {
  try {
    const res = await hermesFetch(`/api/documents/${docId}/chunks`);
    const data = await res.json();
    const modal = document.getElementById('hermes-preview-modal');
    const title = document.getElementById('hermes-preview-title');
    const body = document.getElementById('hermes-preview-body');
    if (title) title.innerText = filename;
    if (body) {
      if (data.chunks && data.chunks.length > 0) {
        body.innerHTML = data.chunks.map((c, i) => `
          <div class="hermes-chunk-card">
            <div class="chunk-badge">${typeof t === 'function' ? t('hermes_chunk_num') : 'চাঙ্ক'} #${i + 1}</div>
            <pre class="chunk-text">${escapeHtml(c.text || c.content || '')}</pre>
          </div>
        `).join('');
      } else {
        body.innerHTML = `<div style="padding:20px; text-align:center; color:var(--text-muted);">${typeof t === 'function' ? t('hermes_no_chunks') : 'কোনো সংরক্ষিত চাঙ্ক পাওয়া যায়নি।'}</div>`;
      }
    }
    if (modal) modal.style.display = 'flex';
  } catch (err) {
    alert(typeof t === 'function' ? t('hermes_preview_err') : 'প্রিভিউ লোড করা সম্ভব হয়নি');
  }
}

async function deleteHermesFile(docId) {
  const confirmMsg = typeof t === 'function' ? t('hermes_confirm_delete_file') : 'আপনি কি নিশ্চিত যে এই ফাইলটি মুছে ফেলতে চান?';
  if (!confirm(confirmMsg)) return;
  try {
    const res = await hermesFetch(`/api/documents/${docId}`, { method: 'DELETE' });
    const data = await res.json();
    if (data.success) {
      loadHermesFiles();
      if (typeof showToast === 'function') showToast(typeof t === 'function' ? t('hermes_file_deleted') : 'ফাইলটি সফলভাবে মুছে ফেলা হয়েছে', 'success');
    }
  } catch (err) {
    alert('Failed to delete file');
  }
}

function closeHermesPreviewModal() {
  const modal = document.getElementById('hermes-preview-modal');
  if (modal) modal.style.display = 'none';
}

// ==============================================================================
// 2. LOGS MODULE
// ==============================================================================
async function loadHermesLogs() {
  const container = document.getElementById('hermes-logs-console');
  if (!container) return;

  try {
    const searchVal = document.getElementById('hermes-logs-search') ? document.getElementById('hermes-logs-search').value : '';
    let url = `/api/hermes/logs?limit=150&level=${encodeURIComponent(hermesActiveFilter)}`;
    if (searchVal) url += `&search=${encodeURIComponent(searchVal)}`;

    const res = await hermesFetch(url);
    const data = await res.json();
    if (!data.success) return;

    if (!data.logs || data.logs.length === 0) {
      container.innerHTML = `<div class="hermes-log-line muted">> ${typeof t === 'function' ? t('hermes_no_logs') : 'কোনো লগ রেকর্ড পাওয়া যায়নি।'}</div>`;
      return;
    }

    container.innerHTML = data.logs.reverse().map(l => {
      let levelClass = 'info';
      if (l.level === 'SUCCESS') levelClass = 'success';
      else if (l.level === 'AI_AGENT') levelClass = 'agent';
      else if (l.level === 'WARN') levelClass = 'warn';
      else if (l.level === 'ERROR') levelClass = 'error';

      return `
        <div class="hermes-log-entry ${levelClass}">
          <span class="log-ts">[${l.timestamp}]</span>
          <span class="log-badge ${levelClass}">${l.level}</span>
          <span class="log-mod">[${escapeHtml(l.module)}]</span>
          <span class="log-msg">${escapeHtml(l.message)}</span>
        </div>
      `;
    }).join('');

    if (hermesLogsAutoScroll) {
      container.scrollTop = container.scrollHeight;
    }
  } catch (err) {
    console.error('Error loading hermes logs:', err);
  }
}

function setHermesLogFilter(lvl) {
  hermesActiveFilter = lvl;
  document.querySelectorAll('.hermes-filter-btn').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-level') === lvl);
  });
  loadHermesLogs();
}

function toggleHermesLogAutoScroll() {
  hermesLogsAutoScroll = !hermesLogsAutoScroll;
  const btn = document.getElementById('btn-hermes-autoscroll');
  if (btn) {
    btn.classList.toggle('active', hermesLogsAutoScroll);
    btn.innerText = hermesLogsAutoScroll ? '⚡ Auto-Scroll ON' : '⏸ Auto-Scroll OFF';
  }
}

async function clearHermesLogs() {
  const confirmMsg = typeof t === 'function' ? t('hermes_confirm_clear_logs') : 'আপনি কি সমস্ত লগ পরিষ্কার করতে চান?';
  if (!confirm(confirmMsg)) return;
  try {
    const res = await hermesFetch('/api/hermes/logs/clear', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      loadHermesLogs();
      if (typeof showToast === 'function') showToast(typeof t === 'function' ? t('hermes_logs_cleared') : 'লগ পরিষ্কার করা হয়েছে', 'success');
    }
  } catch (err) {
    alert('Failed to clear logs');
  }
}

function downloadHermesLogs() {
  const consoleEl = document.getElementById('hermes-logs-console');
  if (!consoleEl) return;
  const text = consoleEl.innerText;
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `myagent_hermes_logs_${Date.now()}.txt`;
  a.click();
}

// ==============================================================================
// 3. CRON MODULE
// ==============================================================================
async function loadHermesCron() {
  const jobsList = document.getElementById('hermes-cron-jobs-list');
  const historyList = document.getElementById('hermes-cron-history-list');
  if (!jobsList) return;

  try {
    const res = await hermesFetch('/api/hermes/cron');
    const data = await res.json();
    if (!data.success) return;

    // Render Jobs
    jobsList.innerHTML = data.jobs.map(j => `
      <div class="hermes-card cron-card ${j.is_enabled ? 'active-job' : 'disabled-job'}">
        <div class="cron-card-header">
          <div style="display:flex; align-items:center; gap:10px;">
            <div class="cron-icon">⏱️</div>
            <div>
              <div class="cron-name">${escapeHtml(j.name)}</div>
              <div class="cron-expr"><code>${escapeHtml(j.expression)}</code> • <span style="color:var(--text-muted);">${escapeHtml(j.next_run || '')}</span></div>
            </div>
          </div>
          <div class="cron-actions">
            <button class="btn-sm-action-cyber" onclick="triggerHermesCron('${j.id}')" title="Run Now">⚡ ${typeof t === 'function' ? t('hermes_run_now') : 'রান নাও'}</button>
            <label class="hermes-switch">
              <input type="checkbox" ${j.is_enabled ? 'checked' : ''} onchange="toggleHermesCron('${j.id}')">
              <span class="slider round"></span>
            </label>
            <button class="btn-sm-action-cyber danger" onclick="deleteHermesCron('${j.id}')">🗑️</button>
          </div>
        </div>
        <div class="cron-card-footer">
          <span>${typeof t === 'function' ? t('hermes_last_status') : 'সর্বশেষ স্ট্যাটাস'}: <span class="badge-${j.last_status === 'SUCCESS' ? 'online' : 'idle'}">${j.last_status}</span></span>
          <span style="color:var(--text-muted); font-size:0.75rem;">${typeof t === 'function' ? t('hermes_last_run') : 'সর্বশেষ রান'}: ${j.last_run || 'N/A'}</span>
        </div>
      </div>
    `).join('');

    // Render History
    if (historyList) {
      if (!data.history || data.history.length === 0) {
        historyList.innerHTML = `<div style="text-align:center; padding:16px; color:var(--text-muted);">${typeof t === 'function' ? t('hermes_cron_no_hist') : 'কোনো পূর্ববর্তী এক্সিকিউশন ইতিহাস নেই।'}</div>`;
      } else {
        historyList.innerHTML = data.history.map(h => `
          <div class="hermes-history-item">
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
    console.error('Error loading hermes cron:', err);
  }
}

async function triggerHermesCron(jobId) {
  try {
    const res = await hermesFetch(`/api/hermes/cron/${jobId}/run`, { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      if (typeof showToast === 'function') {
        showToast(typeof t === 'function' ? t('hermes_cron_triggered') : `জব সফলভাবে এক্সিকিউট হয়েছে (${data.duration_ms}ms)`, 'success');
      }
      loadHermesCron();
    }
  } catch (err) {
    alert('Failed to trigger cron job');
  }
}

async function toggleHermesCron(jobId) {
  try {
    await hermesFetch(`/api/hermes/cron/${jobId}/toggle`, { method: 'PUT' });
    loadHermesCron();
  } catch (err) {
    console.error(err);
  }
}

async function deleteHermesCron(jobId) {
  if (!confirm(typeof t === 'function' ? t('hermes_confirm_delete_cron') : 'এই ক্রন জবটি মুছে ফেলতে চান?')) return;
  try {
    await hermesFetch(`/api/hermes/cron/${jobId}`, { method: 'DELETE' });
    loadHermesCron();
  } catch (err) {
    alert('Failed to delete cron');
  }
}

function openNewCronModal() {
  const modal = document.getElementById('hermes-new-cron-modal');
  if (modal) modal.style.display = 'flex';
}

function closeNewCronModal() {
  const modal = document.getElementById('hermes-new-cron-modal');
  if (modal) modal.style.display = 'none';
}

async function saveNewHermesCron(e) {
  e.preventDefault();
  const name = document.getElementById('cron-input-name').value.trim();
  const expression = document.getElementById('cron-input-expr').value.trim();
  const task_type = document.getElementById('cron-input-type').value;

  try {
    const res = await hermesFetch('/api/hermes/cron', {
      method: 'POST',
      body: JSON.stringify({ name, expression, task_type, payload: {} })
    });
    const data = await res.json();
    if (data.success) {
      closeNewCronModal();
      loadHermesCron();
      if (typeof showToast === 'function') showToast(typeof t === 'function' ? t('hermes_cron_saved') : 'নতুন ক্রন জব যুক্ত হয়েছে', 'success');
    }
  } catch (err) {
    alert('Failed to save cron');
  }
}

// ==============================================================================
// ==============================================================================
// 4. SKILLS MODULE (Matching Hermes Agent Skills Hub Screenshot)
// ==============================================================================
let hermesSkillsState = {
  allSkills: [],
  categories: {},
  filters: { all: 53, toolsets: 29, browse_hub: 0 },
  activeFilter: 'all',
  activeCategory: 'all',
  searchQuery: ''
};

async function loadHermesSkills() {
  const listPane = document.getElementById('hermes-skills-list-pane');
  if (!listPane) return;

  listPane.innerHTML = `<div style="padding:28px; text-align:center; color:#64748b;">${typeof t === 'function' ? t('hermes_loading') : 'লোড হচ্ছে...'}</div>`;

  try {
    let url = `/api/hermes/skills?filter_type=${encodeURIComponent(hermesSkillsState.activeFilter)}`;
    if (hermesSkillsState.activeCategory && hermesSkillsState.activeCategory !== 'all') {
      url += `&category=${encodeURIComponent(hermesSkillsState.activeCategory)}`;
    }
    if (hermesSkillsState.searchQuery) {
      url += `&search=${encodeURIComponent(hermesSkillsState.searchQuery)}`;
    }

    const res = await hermesFetch(url);
    const data = await res.json();
    if (!data.success) throw new Error(data.message || 'Failed to fetch skills');

    hermesSkillsState.allSkills = data.skills || [];
    if (data.categories) hermesSkillsState.categories = data.categories;
    if (data.filters) hermesSkillsState.filters = data.filters;

    // 1. Update Subtitle
    const subTitle = document.getElementById('hermes-skills-enabled-subtitle');
    if (subTitle) {
      subTitle.innerText = `${data.enabled_skills || 0}/${data.total_skills || 0} enabled`;
    }

    // 2. Update Filter counts
    const countAll = document.getElementById('hermes-filter-count-all');
    if (countAll) countAll.innerText = `(${data.filters?.all ?? 53})`;
    const countToolsets = document.getElementById('hermes-filter-count-toolsets');
    if (countToolsets) countToolsets.innerText = `(${data.filters?.toolsets ?? 29})`;

    // 3. Render Categories sidebar
    renderHermesSkillsCategories(hermesSkillsState.categories);

    // 4. Update Active Header
    const activeIcon = document.getElementById('hermes-active-cat-icon');
    const activeTitle = document.getElementById('hermes-active-cat-title');
    const paneCount = document.getElementById('hermes-skills-pane-count');
    if (activeTitle) {
      activeTitle.innerText = hermesSkillsState.activeCategory === 'all' 
        ? (hermesSkillsState.activeFilter === 'toolsets' ? 'TOOLSETS' : (hermesSkillsState.activeFilter === 'browse_hub' ? 'BROWSE HUB' : 'ALL'))
        : hermesSkillsState.activeCategory.toUpperCase();
    }
    if (activeIcon) {
      activeIcon.innerText = hermesSkillsState.activeFilter === 'toolsets' ? '🔧' : '⬡';
    }
    if (paneCount) {
      paneCount.innerText = `${hermesSkillsState.allSkills.length} skills`;
    }

    // 5. Render Skills Rows
    renderHermesSkillsRows(hermesSkillsState.allSkills);
  } catch (err) {
    console.error('Error loading hermes skills:', err);
    listPane.innerHTML = `<div style="padding:28px; text-align:center; color:#f43f5e;">${typeof t === 'function' ? t('hermes_error_load') : 'স্কিল লোড করতে সমস্যা হয়েছে।'}</div>`;
  }
}

function renderHermesSkillsCategories(catMap) {
  const catList = document.getElementById('hermes-skills-cat-list');
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
    const isActive = hermesSkillsState.activeCategory.toLowerCase() === cat.toLowerCase();
    return `
      <button type="button" class="hermes-cat-row-btn ${isActive ? 'active' : ''}" onclick="setHermesSkillCategory('${escapeHtml(cat)}', this)">
        <span>${escapeHtml(cat)}</span>
        <span class="cat-count">${count}</span>
      </button>
    `;
  }).join('');
}

function renderHermesSkillsRows(skills) {
  const listPane = document.getElementById('hermes-skills-list-pane');
  if (!listPane) return;

  if (!skills || skills.length === 0) {
    listPane.innerHTML = `<div style="padding:40px; text-align:center; color:#64748b;">কোনো স্কিল পাওয়া যায়নি।</div>`;
    return;
  }

  listPane.innerHTML = skills.map(s => {
    const isEnabled = s.is_enabled === 1 || s.is_enabled === true;
    return `
      <div class="hermes-skill-entry-row" id="skill-row-${s.id}">
        <div class="hermes-skill-tile-box ${isEnabled ? '' : 'disabled'}" onclick="toggleHermesSkillTile('${s.id}')" title="${isEnabled ? 'Disable skill' : 'Enable skill'}">
          <div class="tile-inner"></div>
        </div>
        <div class="hermes-skill-entry-body" onclick="openSkillDetailModal('${s.id}')" style="cursor:pointer;">
          <div class="hermes-skill-entry-name">
            <span>${escapeHtml(s.name)}</span>
            ${s.is_toolset ? '<span style="font-size:0.68rem; padding:1px 5px; border-radius:3px; background:rgba(56,189,248,0.12); color:#38bdf8; font-weight:500;">TOOLSET</span>' : ''}
          </div>
          <div class="hermes-skill-entry-desc">${escapeHtml(s.description)}</div>
        </div>
        <button type="button" class="hermes-skill-edit-btn" onclick="editHermesSkill('${s.id}')" title="Edit skill">
          ✏️
        </button>
        ${!s.is_system ? `<button type="button" class="hermes-action-icon-btn danger" onclick="deleteHermesSkill('${s.id}')" title="Delete">🗑️</button>` : ''}
      </div>
    `;
  }).join('');
}

function setHermesSkillFilter(filterType, btnEl) {
  hermesSkillsState.activeFilter = filterType;
  hermesSkillsState.activeCategory = 'all';

  document.querySelectorAll('.hermes-skill-filter-item').forEach(b => b.classList.remove('active'));
  if (btnEl) btnEl.classList.add('active');
  document.querySelectorAll('.hermes-cat-row-btn').forEach(b => b.classList.remove('active'));

  loadHermesSkills();
}

function setHermesSkillCategory(catName, btnEl) {
  hermesSkillsState.activeCategory = catName;
  hermesSkillsState.activeFilter = 'all';

  document.querySelectorAll('.hermes-skill-filter-item').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.hermes-cat-row-btn').forEach(b => b.classList.remove('active'));
  if (btnEl) btnEl.classList.add('active');

  loadHermesSkills();
}

function handleHermesSkillsSearch(query) {
  hermesSkillsState.searchQuery = query.trim();
  loadHermesSkills();
}

async function toggleHermesSkillTile(skillId) {
  try {
    const res = await hermesFetch(`/api/hermes/skills/${skillId}/toggle`, { method: 'PUT' });
    const data = await res.json();
    if (data.success) {
      loadHermesSkills();
    }
  } catch (err) {
    console.error(err);
  }
}

function openHermesLearnSkillModal() {
  const modal = document.getElementById('hermes-learn-skill-modal');
  if (modal) modal.style.display = 'flex';
}

function closeHermesLearnSkillModal() {
  const modal = document.getElementById('hermes-learn-skill-modal');
  if (modal) modal.style.display = 'none';
}

async function executeHermesLearnSkill(e) {
  e.preventDefault();
  const source_url = document.getElementById('hermes-learn-url').value.trim();
  const name = document.getElementById('hermes-learn-name').value.trim();
  const description = document.getElementById('hermes-learn-desc').value.trim();
  const category = document.getElementById('hermes-learn-cat').value;

  try {
    const res = await hermesFetch('/api/hermes/skills/learn', {
      method: 'POST',
      body: JSON.stringify({ source_url, name, description, category })
    });
    const data = await res.json();
    if (data.success) {
      closeHermesLearnSkillModal();
      loadHermesSkills();
      if (typeof showToast === 'function') showToast(`নতুন স্কিল '${data.name}' সংযুক্ত হয়েছে`, 'success');
    } else {
      alert(data.message || 'Failed to learn skill');
    }
  } catch (err) {
    alert('Learn skill request failed');
  }
}

function openNewSkillModal() {
  const modal = document.getElementById('hermes-new-skill-modal');
  if (modal) modal.style.display = 'flex';
}

function closeNewSkillModal() {
  const modal = document.getElementById('hermes-new-skill-modal');
  if (modal) modal.style.display = 'none';
}

async function saveNewHermesSkill(e) {
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
    const res = await hermesFetch('/api/hermes/skills', {
      method: 'POST',
      body: JSON.stringify({ name, description, icon, category, instructions, triggers, is_toolset })
    });
    const data = await res.json();
    if (data.success) {
      closeNewSkillModal();
      loadHermesSkills();
      if (typeof showToast === 'function') showToast(typeof t === 'function' ? t('hermes_skill_saved') : 'নতুন স্কিল যুক্ত হয়েছে', 'success');
    }
  } catch (err) {
    alert('Failed to save skill');
  }
}

async function deleteHermesSkill(skillId) {
  if (!confirm(typeof t === 'function' ? t('hermes_confirm_delete_skill') : 'এই স্কিলটি মুছে ফেলতে চান?')) return;
  try {
    await hermesFetch(`/api/hermes/skills/${skillId}`, { method: 'DELETE' });
    loadHermesSkills();
  } catch (err) {
    alert('Failed to delete skill');
  }
}

function openSkillDetailModal(skillId) {
  const skill = hermesSkillsState.allSkills.find(s => s.id === skillId);
  if (!skill) return;
  alert(`Skill: ${skill.name}\nCategory: ${skill.category}\nToolset: ${skill.is_toolset ? 'Yes' : 'No'}\n\n${skill.description}\n\nInstructions:\n${skill.instructions || 'Standard operation instructions.'}`);
}

function editHermesSkill(skillId) {
  openSkillDetailModal(skillId);
}

function openSkillAssistantPrompt() {
  if (typeof switchTab === 'function') {
    switchTab('chat');
    const input = document.getElementById('chat-input');
    if (input) {
      input.value = "Tell me about available Hermes Agent skills and how I can utilize them for autonomous automation.";
      input.focus();
    }
  }
}

// ==============================================================================
// 5. PLUGINS MODULE
// ==============================================================================
async function loadHermesPlugins() {
  const grid = document.getElementById('hermes-plugins-grid');
  if (!grid) return;

  try {
    const res = await hermesFetch('/api/hermes/plugins');
    const data = await res.json();
    if (!data.success) return;

    grid.innerHTML = data.plugins.map(p => `
      <div class="hermes-card plugin-card">
        <div class="plugin-header">
          <div class="plugin-icon">${p.icon || '🧩'}</div>
          <div style="flex:1;">
            <div class="plugin-name">${escapeHtml(p.name)}</div>
            <div class="plugin-ver">v${escapeHtml(p.version)} • <span class="badge-${p.is_enabled ? 'online' : 'idle'}">${p.status}</span></div>
          </div>
          <label class="hermes-switch">
            <input type="checkbox" ${p.is_enabled ? 'checked' : ''} onchange="toggleHermesPlugin('${p.id}')">
            <span class="slider round"></span>
          </label>
        </div>
        <p class="plugin-desc">${escapeHtml(p.description)}</p>
        <div class="plugin-footer">
          <span style="font-size:0.75rem; color:var(--text-muted);">${typeof t === 'function' ? t('hermes_category') : 'ক্যাটাগরি'}: ${escapeHtml(p.category)}</span>
          <button class="btn-sm-action-cyber" onclick="testHermesPlugin('${p.id}')">🔬 ${typeof t === 'function' ? t('hermes_btn_test') : 'টেস্ট'}</button>
        </div>
      </div>
    `).join('');
  } catch (err) {
    console.error('Error loading plugins:', err);
  }
}

async function toggleHermesPlugin(pluginId) {
  try {
    await hermesFetch(`/api/hermes/plugins/${pluginId}/toggle`, { method: 'PUT' });
    loadHermesPlugins();
  } catch (err) {
    console.error(err);
  }
}

async function testHermesPlugin(pluginId) {
  try {
    const res = await hermesFetch(`/api/hermes/plugins/${pluginId}/test`, { method: 'POST' });
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
async function loadHermesChannels() {
  const grid = document.getElementById('hermes-channels-grid');
  if (!grid) return;

  try {
    const res = await hermesFetch('/api/hermes/channels');
    const data = await res.json();
    if (!data.success) return;

    grid.innerHTML = data.channels.map(c => `
      <div class="hermes-card channel-card">
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
          <button class="btn-sm-action-cyber" onclick="openChannelConfigModal('${c.id}', '${escapeHtml(c.name)}', '${escapeHtml(c.token || '')}', '${escapeHtml(c.webhook_url || '')}', '${escapeHtml(c.chat_id || '')}', ${c.is_enabled})">⚙️ ${typeof t === 'function' ? t('hermes_btn_config') : 'কনফিগার'}</button>
          <button class="btn-sm-action-cyber" onclick="testHermesChannel('${c.id}')">📡 ${typeof t === 'function' ? t('hermes_btn_ping') : 'পিং'}</button>
        </div>
      </div>
    `).join('');
  } catch (err) {
    console.error('Error loading channels:', err);
  }
}

function openChannelConfigModal(id, name, token, url, chatId, isEnabled) {
  const modal = document.getElementById('hermes-channel-config-modal');
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
  const modal = document.getElementById('hermes-channel-config-modal');
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
    const res = await hermesFetch(`/api/hermes/channels/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ token, webhook_url, chat_id, is_enabled })
    });
    const data = await res.json();
    if (data.success) {
      closeChannelConfigModal();
      loadHermesChannels();
      if (typeof showToast === 'function') showToast(typeof t === 'function' ? t('hermes_channel_saved') : 'চ্যানেল কনফিগারেশন সংরক্ষিত হয়েছে', 'success');
    }
  } catch (err) {
    alert('Failed to save channel configuration');
  }
}

async function testHermesChannel(channelId) {
  try {
    const res = await hermesFetch(`/api/hermes/channels/${channelId}/test`, { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      if (typeof showToast === 'function') showToast(data.message, 'success');
      loadHermesChannels();
    }
  } catch (err) {
    alert('Channel ping failed');
  }
}

// ==============================================================================
// 7. WEBHOOKS MODULE
// ==============================================================================
async function loadHermesWebhooks() {
  const tableBody = document.getElementById('hermes-webhooks-table-body');
  const logsList = document.getElementById('hermes-webhook-logs-list');
  if (!tableBody) return;

  try {
    const res = await hermesFetch('/api/hermes/webhooks');
    const data = await res.json();
    if (!data.success) return;

    if (!data.webhooks || data.webhooks.length === 0) {
      tableBody.innerHTML = `<tr><td colspan="6" class="text-center py-4" style="color:var(--text-muted);">${typeof t === 'function' ? t('hermes_webhooks_empty') : 'কোনো সক্রিয় ওয়েবহুক নেই।'}</td></tr>`;
    } else {
      tableBody.innerHTML = data.webhooks.map(w => `
        <tr class="hermes-row">
          <td style="font-weight:600; color:var(--text-primary);">${escapeHtml(w.name)}</td>
          <td><span class="status-pill ${w.webhook_type === 'inbound' ? 'info' : 'agent'}">${w.webhook_type.toUpperCase()}</span></td>
          <td><code style="font-size:0.75rem; color:var(--cyan-glow);">${escapeHtml(w.target_url)}</code></td>
          <td style="font-family:'Fira Code', monospace; font-size:0.75rem;">${escapeHtml(w.secret_token ? w.secret_token.substring(0, 10) + '...' : 'None')}</td>
          <td><span class="hermes-tag">${w.delivery_count} ${typeof t === 'function' ? t('hermes_delivered') : 'ডেলিভারি'}</span></td>
          <td style="text-align:right;">
            <button class="btn-sm-cyber" onclick="testHermesWebhook('${w.id}')">🚀 ${typeof t === 'function' ? t('hermes_btn_test') : 'টেস্ট'}</button>
            <button class="btn-sm-cyber danger" onclick="deleteHermesWebhook('${w.id}')">🗑️</button>
          </td>
        </tr>
      `).join('');
    }

    if (logsList) {
      if (!data.logs || data.logs.length === 0) {
        logsList.innerHTML = `<div style="text-align:center; padding:12px; color:var(--text-muted);">${typeof t === 'function' ? t('hermes_no_webhook_logs') : 'কোনো ওয়েবহুক ইভেন্ট হিস্টোরি নেই।'}</div>`;
      } else {
        logsList.innerHTML = data.logs.map(l => `
          <div class="hermes-history-item">
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

async function testHermesWebhook(hookId) {
  try {
    const res = await hermesFetch(`/api/hermes/webhooks/${hookId}/test`, { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      if (typeof showToast === 'function') showToast(typeof t === 'function' ? t('hermes_webhook_tested') : `ওয়েবহুক সফলভাবে ট্রিগার হয়েছে (${data.duration_ms}ms)`, 'success');
      loadHermesWebhooks();
    }
  } catch (err) {
    alert('Webhook test failed');
  }
}

async function deleteHermesWebhook(hookId) {
  if (!confirm(typeof t === 'function' ? t('hermes_confirm_delete_webhook') : 'ওয়েবহুকটি মুছে ফেলতে চান?')) return;
  try {
    await hermesFetch(`/api/hermes/webhooks/${hookId}`, { method: 'DELETE' });
    loadHermesWebhooks();
  } catch (err) {
    alert('Failed to delete webhook');
  }
}

function openNewWebhookModal() {
  const modal = document.getElementById('hermes-new-webhook-modal');
  if (modal) modal.style.display = 'flex';
}

function closeNewWebhookModal() {
  const modal = document.getElementById('hermes-new-webhook-modal');
  if (modal) modal.style.display = 'none';
}

async function saveNewHermesWebhook(e) {
  e.preventDefault();
  const name = document.getElementById('webhook-input-name').value.trim();
  const webhook_type = document.getElementById('webhook-input-type').value;
  const target_url = document.getElementById('webhook-input-url').value.trim();

  try {
    const res = await hermesFetch('/api/hermes/webhooks', {
      method: 'POST',
      body: JSON.stringify({ name, webhook_type, target_url })
    });
    const data = await res.json();
    if (data.success) {
      closeNewWebhookModal();
      loadHermesWebhooks();
      if (typeof showToast === 'function') showToast(typeof t === 'function' ? t('hermes_webhook_created') : 'নতুন ওয়েবহুক তৈরি হয়েছে', 'success');
    }
  } catch (err) {
    alert('Failed to create webhook');
  }
}

// ==============================================================================
// 8. PAIRING MODULE
// ==============================================================================
async function loadHermesPairing() {
  const tableBody = document.getElementById('hermes-paired-devices-table');
  const codeBox = document.getElementById('hermes-active-pairing-code');
  const countdownBox = document.getElementById('hermes-pairing-countdown');
  if (!tableBody) return;

  try {
    const res = await hermesFetch('/api/hermes/pairing');
    const data = await res.json();
    if (!data.success) return;

    // Active pairing code
    if (data.active_code) {
      if (codeBox) codeBox.innerText = data.active_code.code;
      startPairingCountdown(data.active_code.expires_in_seconds);
    } else {
      if (codeBox) codeBox.innerText = '------';
      if (countdownBox) countdownBox.innerText = typeof t === 'function' ? t('hermes_click_generate_code') : 'কোড তৈরি করতে নিচের বাটনে চাপ দিন';
    }

    // Devices table
    if (!data.devices || data.devices.length === 0) {
      tableBody.innerHTML = `<tr><td colspan="6" class="text-center py-4" style="color:var(--text-muted);">${typeof t === 'function' ? t('hermes_no_paired_devices') : 'কোনো পেয়ার করা ডিভাইস নেই।'}</td></tr>`;
    } else {
      tableBody.innerHTML = data.devices.map(d => `
        <tr class="hermes-row">
          <td style="font-weight:600; color:var(--text-primary); display:flex; align-items:center; gap:8px;">
            <span>💻</span>
            <span>${escapeHtml(d.device_name)}</span>
          </td>
          <td><span class="hermes-tag">${escapeHtml(d.platform)}</span></td>
          <td style="font-family:'Fira Code', monospace; font-size:0.8rem;">${escapeHtml(d.ip_address || '192.168.9.x')}</td>
          <td style="color:var(--text-muted); font-size:0.8rem;">${d.paired_at}</td>
          <td><span class="status-pill success">${d.status}</span></td>
          <td style="text-align:right;">
            <button class="btn-sm-cyber danger" onclick="revokeHermesDevice('${d.device_id}')">❌ ${typeof t === 'function' ? t('hermes_btn_revoke') : 'বাতিল'}</button>
          </td>
        </tr>
      `).join('');
    }
  } catch (err) {
    console.error('Error loading pairing:', err);
  }
}

async function generateHermesPairingCode() {
  try {
    const res = await hermesFetch('/api/hermes/pairing/generate', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      const codeBox = document.getElementById('hermes-active-pairing-code');
      if (codeBox) codeBox.innerText = data.code;
      startPairingCountdown(data.expires_in_seconds);
      if (typeof showToast === 'function') showToast(typeof t === 'function' ? t('hermes_pairing_code_generated') : `নতুন ৬-সংখ্যার পেয়ারিং কোড তৈরি হয়েছে: ${data.code}`, 'success');
    }
  } catch (err) {
    alert('Failed to generate pairing code');
  }
}

function startPairingCountdown(seconds) {
  if (hermesPairingTimer) clearInterval(hermesPairingTimer);
  let left = seconds;
  const box = document.getElementById('hermes-pairing-countdown');

  function update() {
    if (left <= 0) {
      clearInterval(hermesPairingTimer);
      if (box) box.innerText = typeof t === 'function' ? t('hermes_code_expired') : 'কোডের মেয়াদ শেষ হয়েছে। নতুন কোড তৈরি করুন।';
      const codeBox = document.getElementById('hermes-active-pairing-code');
      if (codeBox) codeBox.innerText = '------';
      return;
    }
    const mins = Math.floor(left / 60);
    const secs = left % 60;
    if (box) box.innerText = `${typeof t === 'function' ? t('hermes_code_valid_for') : 'মেয়াদ আছে'}: ${mins}:${secs < 10 ? '0' : ''}${secs}`;
    left--;
  }

  update();
  hermesPairingTimer = setInterval(update, 1000);
}

async function revokeHermesDevice(deviceId) {
  if (!confirm(typeof t === 'function' ? t('hermes_confirm_revoke') : 'এই ডিভাইসের অ্যাক্সেস বাতিল করতে চান?')) return;
  try {
    await hermesFetch(`/api/hermes/pairing/${deviceId}`, { method: 'DELETE' });
    loadHermesPairing();
    if (typeof showToast === 'function') showToast(typeof t === 'function' ? t('hermes_device_revoked') : 'ডিভাইস অ্যাক্সেস বাতিল করা হয়েছে', 'success');
  } catch (err) {
    alert('Failed to revoke device');
  }
}

// ==============================================================================
// 9. PROFILES MODULE
// ==============================================================================
async function loadHermesProfiles() {
  const grid = document.getElementById('hermes-profiles-grid');
  if (!grid) return;

  try {
    const res = await hermesFetch('/api/hermes/profiles');
    const data = await res.json();
    if (!data.success) return;

    grid.innerHTML = data.profiles.map(p => `
      <div class="hermes-card profile-card ${p.is_active ? 'active-profile' : ''}">
        <div class="profile-header">
          <div class="profile-avatar">${p.avatar || '🤖'}</div>
          <div style="flex:1;">
            <div class="profile-name">${escapeHtml(p.name)}</div>
            <div class="profile-meta">Temp: ${p.temperature} • Model: ${escapeHtml(p.model)}</div>
          </div>
          ${p.is_active 
            ? `<span class="status-pill success">★ ${typeof t === 'function' ? t('hermes_profile_active') : 'সক্রিয় পার্সোনা'}</span>`
            : `<button class="btn-sm-action-cyber" onclick="activateHermesProfile('${p.id}')">⚡ ${typeof t === 'function' ? t('hermes_btn_activate') : 'সক্রিয় করুন'}</button>`
          }
        </div>
        <p class="profile-desc">${escapeHtml(p.description)}</p>
        <div class="profile-prompt-preview">
          <code>${escapeHtml(p.system_prompt.substring(0, 130))}...</code>
        </div>
        <div class="profile-footer">
          <span style="font-size:0.75rem; color:var(--text-muted);">${typeof t === 'function' ? t('hermes_memory_scope') : 'মেমোরি স্কোপ'}: ${escapeHtml(p.memory_scope)}</span>
          ${!p.is_system && !p.is_active ? `<button class="btn-icon-danger" onclick="deleteHermesProfile('${p.id}')">🗑️</button>` : ''}
        </div>
      </div>
    `).join('');
  } catch (err) {
    console.error('Error loading profiles:', err);
  }
}

async function activateHermesProfile(profId) {
  try {
    const res = await hermesFetch(`/api/hermes/profiles/${profId}/activate`, { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      loadHermesProfiles();
      if (typeof showToast === 'function') showToast(typeof t === 'function' ? t('hermes_profile_switched') : `এজেন্ট পার্সোনা পরিবর্তিত হয়েছে: ${data.name}`, 'success');
    }
  } catch (err) {
    alert('Failed to switch profile');
  }
}

async function deleteHermesProfile(profId) {
  if (!confirm(typeof t === 'function' ? t('hermes_confirm_delete_profile') : 'এই পার্সোনা প্রোফাইলটি মুছে ফেলতে চান?')) return;
  try {
    await hermesFetch(`/api/hermes/profiles/${profId}`, { method: 'DELETE' });
    loadHermesProfiles();
  } catch (err) {
    alert('Failed to delete profile');
  }
}

function openNewProfileModal() {
  const modal = document.getElementById('hermes-new-profile-modal');
  if (modal) modal.style.display = 'flex';
}

function closeNewProfileModal() {
  const modal = document.getElementById('hermes-new-profile-modal');
  if (modal) modal.style.display = 'none';
}

async function saveNewHermesProfile(e) {
  e.preventDefault();
  const name = document.getElementById('profile-input-name').value.trim();
  const avatar = document.getElementById('profile-input-avatar').value.trim() || '🤖';
  const description = document.getElementById('profile-input-desc').value.trim();
  const system_prompt = document.getElementById('profile-input-prompt').value.trim();
  const temperature = parseFloat(document.getElementById('profile-input-temp').value) || 0.3;
  const model = document.getElementById('profile-input-model').value;

  try {
    const res = await hermesFetch('/api/hermes/profiles', {
      method: 'POST',
      body: JSON.stringify({ name, avatar, description, system_prompt, temperature, model })
    });
    const data = await res.json();
    if (data.success) {
      closeNewProfileModal();
      loadHermesProfiles();
      if (typeof showToast === 'function') showToast(typeof t === 'function' ? t('hermes_profile_saved') : 'নতুন পার্সোনা তৈরি হয়েছে', 'success');
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
window.loadHermesFiles = loadHermesFiles;
window.previewHermesFile = previewHermesFile;
window.deleteHermesFile = deleteHermesFile;
window.closeHermesPreviewModal = closeHermesPreviewModal;

window.loadHermesLogs = loadHermesLogs;
window.setHermesLogFilter = setHermesLogFilter;
window.toggleHermesLogAutoScroll = toggleHermesLogAutoScroll;
window.clearHermesLogs = clearHermesLogs;
window.downloadHermesLogs = downloadHermesLogs;

window.loadHermesCron = loadHermesCron;
window.triggerHermesCron = triggerHermesCron;
window.toggleHermesCron = toggleHermesCron;
window.deleteHermesCron = deleteHermesCron;
window.openNewCronModal = openNewCronModal;
window.closeNewCronModal = closeNewCronModal;
window.saveNewHermesCron = saveNewHermesCron;

window.loadHermesSkills = loadHermesSkills;
window.setHermesSkillFilter = setHermesSkillFilter;
window.setHermesSkillCategory = setHermesSkillCategory;
window.handleHermesSkillsSearch = handleHermesSkillsSearch;
window.toggleHermesSkillTile = toggleHermesSkillTile;
window.openHermesLearnSkillModal = openHermesLearnSkillModal;
window.closeHermesLearnSkillModal = closeHermesLearnSkillModal;
window.executeHermesLearnSkill = executeHermesLearnSkill;
window.openSkillAssistantPrompt = openSkillAssistantPrompt;
window.openSkillDetailModal = openSkillDetailModal;
window.editHermesSkill = editHermesSkill;
window.deleteHermesSkill = deleteHermesSkill;
window.openNewSkillModal = openNewSkillModal;
window.closeNewSkillModal = closeNewSkillModal;
window.saveNewHermesSkill = saveNewHermesSkill;

window.loadHermesPlugins = loadHermesPlugins;
window.toggleHermesPlugin = toggleHermesPlugin;
window.testHermesPlugin = testHermesPlugin;

window.loadHermesChannels = loadHermesChannels;
window.openChannelConfigModal = openChannelConfigModal;
window.closeChannelConfigModal = closeChannelConfigModal;
window.saveChannelConfig = saveChannelConfig;
window.testHermesChannel = testHermesChannel;

window.loadHermesWebhooks = loadHermesWebhooks;
window.testHermesWebhook = testHermesWebhook;
window.deleteHermesWebhook = deleteHermesWebhook;
window.openNewWebhookModal = openNewWebhookModal;
window.closeNewWebhookModal = closeNewWebhookModal;
window.saveNewHermesWebhook = saveNewHermesWebhook;

window.loadHermesPairing = loadHermesPairing;
window.generateHermesPairingCode = generateHermesPairingCode;
window.revokeHermesDevice = revokeHermesDevice;

window.loadHermesProfiles = loadHermesProfiles;
window.activateHermesProfile = activateHermesProfile;
window.deleteHermesProfile = deleteHermesProfile;
window.openNewProfileModal = openNewProfileModal;
window.closeNewProfileModal = closeNewProfileModal;
window.saveNewHermesProfile = saveNewHermesProfile;

// Hermes Sessions Module
window.loadHermesSessions = loadHermesSessions;
window.openPruneSessionsModal = openPruneSessionsModal;
window.closePruneSessionsModal = closePruneSessionsModal;
window.executePruneSessions = executePruneSessions;
window.openImportSessionsModal = openImportSessionsModal;
window.closeImportSessionsModal = closeImportSessionsModal;
window.handleImportSessionFile = handleImportSessionFile;
window.executeImportSessions = executeImportSessions;
window.setHermesSessionFilter = setHermesSessionFilter;
window.filterHermesSessionsBySource = filterHermesSessionsBySource;
window.setHermesSessionView = setHermesSessionView;
window.openSessionDirectly = openSessionDirectly;
window.deleteHermesSession = deleteHermesSession;

// Hermes Filesystem Explorer (/opt/data)
window.loadHermesFilesExplorer = loadHermesFilesExplorer;
window.navigateHermesFsUp = navigateHermesFsUp;
window.triggerHermesFsUpload = triggerHermesFsUpload;
window.handleHermesFsFileSelected = handleHermesFsFileSelected;
window.handleHermesFsDragOver = handleHermesFsDragOver;
window.handleHermesFsDragLeave = handleHermesFsDragLeave;
window.handleHermesFsDrop = handleHermesFsDrop;
window.openHermesCreateFsItemModal = openHermesCreateFsItemModal;
window.closeHermesCreateFsItemModal = closeHermesCreateFsItemModal;
window.executeHermesCreateFsItem = executeHermesCreateFsItem;
window.deleteHermesFsItem = deleteHermesFsItem;
window.downloadOrPreviewFsFile = downloadOrPreviewFsFile;
