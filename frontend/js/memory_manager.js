/* ==============================================================================
 * Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
 * Made By Arif (https://arifmahmud.com/)
 * Project: MyAgent | Version: 2.2.0
 * ============================================================================== */

// Company Knowledge Base, Big Data & Vector Memory Manager
// Full CRUD: View, Search, Edit Wrong Data, Delete Chunks & Documents

let activeFilter = 'all';
let allLoadedDocs = [];
let currentEditingChunkId = null;
let currentChunksPage = 0;
const CHUNKS_PER_PAGE = 25;

function handleDragOver(e) {
  e.preventDefault();
  document.getElementById('file-dropzone').classList.add('dragover');
}

function handleDragLeave(e) {
  e.preventDefault();
  document.getElementById('file-dropzone').classList.remove('dragover');
}

function handleDrop(e) {
  e.preventDefault();
  document.getElementById('file-dropzone').classList.remove('dragover');
  const files = e.dataTransfer.files;
  if (files.length > 0) {
    uploadFiles(files);
  }
}

function handleFileSelected(e) {
  const files = e.target.files;
  if (files.length > 0) {
    uploadFiles(files);
  }
}

// Upload and Index Files into Memory (PDF, Word, Excel, CSV, Photos PNG/JPG, TXT)
async function uploadFiles(files) {
  const formData = new FormData();
  for (let i = 0; i < files.length; i++) {
    formData.append('files', files[i]);
  }

  showToast(`${files.length}টি ফাইল / ফটো মেমোরিতে যুক্ত ও বিশ্লেষণ করা হচ্ছে...`, 'info');

  try {
    const token = typeof getAuthToken === 'function' ? getAuthToken() : null;
    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch('/api/documents/upload', {
      method: 'POST',
      headers: headers,
      body: formData
    });

    const data = await res.json();
    if (res.ok && data.success) {
      showToast('ফাইল সফলভাবে মেমোরিতে ইনজেস্ট করা হয়েছে!', 'success');
      loadDocumentList();
      loadMemoryStats();
      loadChunksList();
      if (typeof loadDashboardMetrics === 'function') loadDashboardMetrics();
    } else {
      showToast(`ইনজেস্ট ত্রুটি: ${data.detail || data.message || 'ব্যর্থ'}`, 'error');
    }
  } catch (err) {
    showToast(`আপলোড ত্রুটি: ${err.message}`, 'error');
  } finally {
    document.getElementById('file-input-hidden').value = '';
  }
}

// Set Filter for Document Inventory
function setDocFilter(type) {
  activeFilter = type;
  document.querySelectorAll('.filter-tab-btn').forEach(b => b.classList.remove('active'));
  const activeBtn = document.getElementById(`filter-btn-${type}`);
  if (activeBtn) activeBtn.classList.add('active');
  renderFilteredDocs();
}

// Fetch Document List from Backend
async function loadDocumentList() {
  const listElem = document.getElementById('document-list-body');
  if (!listElem) return;

  try {
    const res = await fetch('/api/documents', {
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {}
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const docs = await res.json();
    allLoadedDocs = docs;
    renderFilteredDocs();
  } catch (err) {
    listElem.innerHTML = `<tr><td colspan="5" style="text-align:center; color:var(--rose-red);">ডকুমেন্ট লোড করতে ব্যর্থ: ${escapeHtml(err.message)}</td></tr>`;
  }
}

function renderFilteredDocs() {
  const listElem = document.getElementById('document-list-body');
  if (!listElem) return;

  let filtered = allLoadedDocs;
  if (activeFilter !== 'all') {
    filtered = allLoadedDocs.filter(d => {
      const ext = (d.file_type || d.filename.split('.').pop() || '').toLowerCase();
      if (activeFilter === 'pdf') return ext === 'pdf';
      if (activeFilter === 'excel') return ['xlsx', 'xls', 'csv', 'tsv'].includes(ext);
      if (activeFilter === 'word') return ['docx', 'doc'].includes(ext);
      if (activeFilter === 'photo') return ['png', 'jpg', 'jpeg', 'webp', 'bmp'].includes(ext);
      return true;
    });
  }

  if (filtered.length === 0) {
    listElem.innerHTML = `<tr><td colspan="5" style="text-align:center; color:var(--text-muted); padding:30px;">${typeof t === 'function' ? t('kb_no_docs', 'কোনো ফাইল পাওয়া যায়নি।') : 'কোনো ফাইল পাওয়া যায়নি।'}</td></tr>`;
    return;
  }

  listElem.innerHTML = filtered.map(doc => {
    const ext = (doc.file_type || doc.filename.split('.').pop() || '').toUpperCase();
    let badgeColor = 'var(--cyan-glow)';
    if (ext === 'PDF') badgeColor = '#f43f5e';
    else if (['XLSX', 'XLS', 'CSV'].includes(ext)) badgeColor = '#10b981';
    else if (['DOCX', 'DOC'].includes(ext)) badgeColor = '#3b82f6';
    else if (['PNG', 'JPG', 'WEBP'].includes(ext)) badgeColor = '#a855f7';

    return `
      <tr>
        <td style="font-weight: 600; color: white;">
          <div style="display:flex; align-items:center; gap:8px;">
            <span class="file-badge" style="background:${badgeColor}20; color:${badgeColor}; border:1px solid ${badgeColor}40;">${ext}</span>
            <span>${escapeHtml(doc.filename)}</span>
          </div>
        </td>
        <td>${doc.total_chunks || 1} ${typeof t === 'function' ? t('chunks_count_suffix', 'চাঙ্কস') : 'চাঙ্কস'}</td>
        <td>${formatBytes(doc.size_bytes || 0)}</td>
        <td style="color:var(--text-muted); font-size:0.8rem;">${doc.uploaded_at || 'সম্প্রতি'}</td>
        <td style="text-align:right;">
          <button class="btn-sm-action" onclick="inspectDocumentChunks('${doc.id}', '${escapeHtml(doc.filename)}')">
            ${typeof t === 'function' ? t('th_chunks', 'চাঙ্কস') : 'চাঙ্কস'}
          </button>
          <button class="btn-sm-action" style="color:var(--rose-red); border-color:rgba(244,63,94,0.3);" onclick="deleteDocument('${doc.id}', '${escapeHtml(doc.filename)}')">
            🗑️ ${typeof t === 'function' ? t('btn_delete', 'ডিলিট') : 'ডিলিট'}
          </button>
        </td>
      </tr>
    `;
  }).join('');
}

// Delete Entire Document and all its vectors
async function deleteDocument(docId, filename) {
  if (!confirm(`আপনি কি নিশ্চিত যে আপনি '${filename}' এবং এর সমস্ত মেমোরি ভেক্টর মুছে ফেলতে চান?`)) {
    return;
  }

  try {
    const res = await fetch(`/api/documents/${docId}`, {
      method: 'DELETE',
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {}
    });

    if (res.ok) {
      showToast(`'${filename}' সফলভাবে মেমোরি থেকে মুছে ফেলা হয়েছে!`, 'success');
      loadDocumentList();
      loadMemoryStats();
      loadChunksList();
      if (typeof loadDashboardMetrics === 'function') loadDashboardMetrics();
    } else {
      showToast('ডকুমেন্ট মুছতে ব্যর্থ হয়েছে।', 'error');
    }
  } catch (err) {
    showToast(`ত্রুটি: ${err.message}`, 'error');
  }
}

// -----------------------------------------------------------------------------
// CHUNKS EXPLORER: VIEW, SEARCH, EDIT WRONG DATA, DELETE SPECIFIC CHUNK
// -----------------------------------------------------------------------------

async function loadChunksList(page = 0) {
  currentChunksPage = page;
  const tbody = document.getElementById('chunks-table-body');
  const searchInput = document.getElementById('chunk-search-input');
  const countBadge = document.getElementById('chunks-total-count-badge');
  if (!tbody) return;

  const query = searchInput ? searchInput.value.trim() : '';
  const offset = page * CHUNKS_PER_PAGE;

  tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:20px; color:var(--cyan-glow);">সুপার ফাস্ট ইনডেক্স থেকে ডাটা লোড হচ্ছে...</td></tr>`;

  try {
    let url = `/api/memory/chunks?limit=${CHUNKS_PER_PAGE}&offset=${offset}`;
    if (query) url += `&query=${encodeURIComponent(query)}`;

    const res = await fetch(url, {
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {}
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();
    const chunks = data.chunks || [];
    const total = data.total || 0;

    if (countBadge) {
      const isEn = (typeof currentLang !== 'undefined' && currentLang === 'en');
      const suffix = typeof t === 'function' ? t('chunks_count_suffix', 'টি চাঙ্ক') : 'টি চাঙ্ক';
      countBadge.innerText = `${total.toLocaleString(isEn ? 'en-US' : 'bn-BD')}${suffix.startsWith(' ') ? '' : ' '}${suffix}`;
    }

    if (chunks.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:30px; color:var(--text-muted);">${typeof t === 'function' ? t('kb_no_chunks', 'কোনো মেমোরি চাঙ্ক পাওয়া যায়নি।') : 'কোনো মেমোরি চাঙ্ক পাওয়া যায়নি।'}</td></tr>`;
      return;
    }

    tbody.innerHTML = chunks.map(c => `
      <tr>
        <td style="font-family:monospace; font-size:0.75rem; color:var(--cyan-glow);">${escapeHtml(c.id)}</td>
        <td style="font-weight:600; font-size:0.85rem; color:white;">${escapeHtml(c.source)}</td>
        <td><span class="badge-tag">${typeof t === 'function' ? t('th_page', 'পৃষ্ঠা') : 'পৃষ্ঠা'} ${c.page || 1}</span></td>
        <td style="font-size:0.82rem; color:var(--text-muted); max-width:420px;">
          <div style="max-height:60px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
            ${escapeHtml(c.content)}
          </div>
        </td>
        <td style="text-align:right; white-space:nowrap;">
          <button class="btn-sm-action" style="color:var(--cyan-glow); border-color:rgba(6,182,212,0.4);" onclick="openEditChunkModal('${c.id}')" title="${typeof t === 'function' ? t('btn_edit', 'এডিট') : 'এডিট'}">
            ✏️ ${typeof t === 'function' ? t('btn_edit', 'এডিট') : 'এডিট'}
          </button>
          <button class="btn-sm-action" style="color:var(--rose-red); border-color:rgba(244,63,94,0.3);" onclick="deleteChunk('${c.id}')" title="${typeof t === 'function' ? t('btn_delete', 'ডিলিট') : 'ডিলিট'}">
            🗑️ ${typeof t === 'function' ? t('btn_delete', 'ডিলিট') : 'ডিলিট'}
          </button>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:var(--rose-red);">চাঙ্কস লোড ত্রুটি: ${escapeHtml(err.message)}</td></tr>`;
  }
}

// Open Edit Chunk Modal for Correcting Wrong Data
async function openEditChunkModal(chunkId) {
  currentEditingChunkId = chunkId;
  const modal = document.getElementById('edit-chunk-modal');
  const title = document.getElementById('edit-chunk-id-display');
  const textarea = document.getElementById('edit-chunk-textarea');
  const sourceDisplay = document.getElementById('edit-chunk-source-display');

  const isEn = (typeof currentLang !== 'undefined' && currentLang === 'en');
  title.innerText = isEn ? `Chunk ID: ${chunkId}` : `চাঙ্ক আইডি: ${chunkId}`;
  textarea.value = isEn ? 'Loading data...' : 'ডাটা লোড হচ্ছে...';
  modal.style.display = 'flex';

  try {
    const res = await fetch(`/api/memory/chunks/${chunkId}`, {
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {}
    });
    if (!res.ok) throw new Error(isEn ? 'Could not load chunk details' : 'চাঙ্ক তথ্য লোড করা যায়নি');

    const chunk = await res.json();
    textarea.value = chunk.content || '';
    if (sourceDisplay) {
      sourceDisplay.innerText = isEn 
        ? `Source: ${chunk.source} (Page: ${chunk.page || 1})` 
        : `উৎস: ${chunk.source} (পৃষ্ঠা: ${chunk.page || 1})`;
    }
  } catch (err) {
    textarea.value = (isEn ? 'Error: ' : 'ত্রুটি: ') + err.message;
  }
}

function closeEditChunkModal() {
  document.getElementById('edit-chunk-modal').style.display = 'none';
  currentEditingChunkId = null;
}

// Save Edited Chunk with New Vector Embedding
async function saveEditedChunk() {
  if (!currentEditingChunkId) return;

  const textarea = document.getElementById('edit-chunk-textarea');
  const newText = textarea.value.trim();

  if (!newText) {
    showToast('টেক্সট খালি রাখা যাবে না!', 'error');
    return;
  }

  showToast('সংশোধিত তথ্য সংরক্ষণ ও নতুন এমবেডিং তৈরি হচ্ছে...', 'info');

  try {
    const res = await fetch(`/api/memory/chunks/${currentEditingChunkId}`, {
      method: 'PUT',
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: newText })
    });

    const data = await res.json();
    if (res.ok && data.success) {
      showToast('মেমোরি চাঙ্ক সফলভাবে আপডেট করা হয়েছে! এজেন্ট এখন নতুন তথ্য ব্যবহার করবে।', 'success');
      closeEditChunkModal();
      loadChunksList(currentChunksPage);
      loadMemoryStats();
    } else {
      showToast(`সংরক্ষণ ব্যর্থ: ${data.detail || 'ত্রুটি'}`, 'error');
    }
  } catch (err) {
    showToast(`ত্রুটি: ${err.message}`, 'error');
  }
}

// Delete Single Memory Chunk
async function deleteChunk(chunkId) {
  if (!confirm(`আপনি কি নিশ্চিত যে আপনি মেমোরি চাঙ্ক '${chunkId}' মুছে ফেলতে চান?`)) {
    return;
  }

  try {
    const res = await fetch(`/api/memory/chunks/${chunkId}`, {
      method: 'DELETE',
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {}
    });

    if (res.ok) {
      showToast('মেমোরি চাঙ্ক সফলভাবে মুছে ফেলা হয়েছে!', 'success');
      loadChunksList(currentChunksPage);
      loadMemoryStats();
    } else {
      showToast('মুছতে ব্যর্থ হয়েছে।', 'error');
    }
  } catch (err) {
    showToast(`ত্রুটি: ${err.message}`, 'error');
  }
}

// Inspect Chunks of a specific Document
async function inspectDocumentChunks(docId, filename) {
  const modal = document.getElementById('chunk-modal');
  const title = document.getElementById('chunk-modal-title');
  const body = document.getElementById('chunk-modal-body');

  const isEn = (typeof currentLang !== 'undefined' && currentLang === 'en');
  title.innerText = (isEn ? 'Vector Chunks: ' : 'ভেক্টর চাঙ্কস: ') + filename;
  body.innerHTML = `<div style="text-align:center; padding:30px; color:var(--cyan-glow);">${isEn ? 'Loading chunks...' : 'চাঙ্কস লোড হচ্ছে...'}</div>`;
  modal.style.display = 'flex';

  try {
    const res = await fetch(`/api/documents/${docId}/chunks`, {
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {}
    });
    const data = await res.json();
    const chunks = data.chunks || [];

    if (chunks.length === 0) {
      body.innerHTML = `<div style="text-align:center; padding:30px; color:var(--text-muted);">${isEn ? 'No saved chunks found.' : 'কোনো সংরক্ষিত চাঙ্ক পাওয়া যায়নি।'}</div>`;
    } else {
      body.innerHTML = chunks.map((c, idx) => `
        <div class="chunk-card">
          <div class="chunk-header">
            <span>${typeof t === 'function' ? t('th_chunk_id', 'চাঙ্ক') : 'চাঙ্ক'} #${idx + 1} (${escapeHtml(c.chunk_id)})</span>
            <div>
              <button class="btn-sm-action" style="color:var(--cyan-glow);" onclick="closeChunkModal(); openEditChunkModal('${c.chunk_id}')">✏️ ${typeof t === 'function' ? t('btn_edit', 'এডিট') : 'এডিট'}</button>
              <button class="btn-sm-action" style="color:var(--rose-red);" onclick="deleteChunk('${c.chunk_id}')">🗑️ ${typeof t === 'function' ? t('btn_delete', 'ডিলিট') : 'ডিলিট'}</button>
            </div>
          </div>
          <div class="chunk-content">${escapeHtml(c.content)}</div>
        </div>
      `).join('');
    }
  } catch (err) {
    body.innerHTML = `<div style="color:var(--rose-red); padding:20px;">চাঙ্কস লোড করতে ত্রুটি: ${err.message}</div>`;
  }
}

function closeChunkModal() {
  document.getElementById('chunk-modal').style.display = 'none';
}

// Save Direct Corporate Note to Memory
async function saveDirectNote() {
  const title = document.getElementById('note-title').value.trim();
  const content = document.getElementById('note-content').value.trim();

  if (!title || !content) {
    showToast('অনুগ্রহ করে নোটের শিরোনাম এবং বিবরণ পূরণ করুন।', 'error');
    return;
  }

  try {
    const res = await fetch('/api/memory/notes', {
      method: 'POST',
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, content, tags: ['corporate_note', 'policy'] })
    });

    if (res.ok) {
      showToast(`'${title}' সরাসরি এজেন্টের স্থায়ী মেমোরিতে যুক্ত হয়েছে!`, 'success');
      document.getElementById('note-title').value = '';
      document.getElementById('note-content').value = '';
      loadDocumentList();
      loadMemoryStats();
      loadChunksList();
      if (typeof loadDashboardMetrics === 'function') loadDashboardMetrics();
    }
  } catch (err) {
    showToast(`ত্রুটি: ${err.message}`, 'error');
  }
}

// Load Vector Memory Stats
async function loadMemoryStats() {
  try {
    const res = await fetch('/api/memory/stats', {
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {}
    });
    if (res.ok) {
      const stats = await res.json();
      const chunksPill = document.getElementById('sidebar-chunks-count');
      if (chunksPill) {
        chunksPill.innerText = stats.total_chunks || 0;
      }
    }
  } catch (err) {
    console.error('Error loading stats:', err);
  }
}

function formatBytes(bytes, decimals = 1) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

function escapeHtml(text) {
  if (!text) return '';
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Optimize Vector Store & FTS5 Database
async function optimizeMemoryStore() {
  const btn = document.getElementById('btn-optimize-store');
  const origText = btn ? btn.innerHTML : '';
  const isEn = (typeof currentLang !== 'undefined' && currentLang === 'en');
  if (btn) {
    btn.innerHTML = isEn ? '⚡ Optimizing...' : '⚡ অপ্টিমাইজ হচ্ছে...';
    btn.disabled = true;
  }
  showToast(isEn ? 'Vector memory defragmentation and FTS5 optimization in progress...' : 'ভেক্টর মেমোরি ডিফ্র্যাগমেন্টেশন ও FTS5 সার্চ ইনডেক্স অপ্টিমাইজেশন চলছে...', 'info');

  try {
    const res = await fetch('/api/memory/optimize', {
      method: 'POST',
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {}
    });
    const data = await res.json();
    if (res.ok && data.success) {
      const opt = data.optimization || {};
      showToast(isEn ? `Memory optimized! Total chunks: ${opt.total_chunks || 0}, Time: ${opt.elapsed_seconds || 0}s` : `মেমোরি সফলভাবে অপ্টিমাইজ হয়েছে! মোট চাঙ্ক: ${opt.total_chunks || 0}, সময়: ${opt.elapsed_seconds || 0}s`, 'success');
      loadMemoryStats();
      loadChunksList(0);
    } else {
      showToast(isEn ? `Optimization failed: ${data.detail || 'error'}` : `অপ্টিমাইজেশন ব্যর্থ: ${data.detail || 'ত্রুটি'}`, 'error');
    }
  } catch (err) {
    showToast(`Error: ${err.message}`, 'error');
  } finally {
    if (btn) {
      btn.innerHTML = origText;
      btn.disabled = false;
    }
  }
}

// Re-index all uploaded documents using smart table-aware chunker
async function reindexAllDocuments() {
  const isEn = (typeof currentLang !== 'undefined' && currentLang === 'en');
  if (!confirm(isEn ? 'Do you want to re-index all uploaded files using the smart table-aware chunker? This maximizes data quality and retrieval accuracy.' : 'আপনি কি সমস্ত সংরক্ষিত ফাইল পুনরায় স্মার্ট টেবিল-অ্যাওয়ার চাঙ্কিং দিয়ে রি-ইনডেক্স করতে চান? এতে ডাটার কোয়ালিটি ও সার্চ একুরেসি সর্বোচ্চ হবে।')) {
    return;
  }

  const btn = document.getElementById('btn-reindex-docs');
  const origText = btn ? btn.innerHTML : '';
  if (btn) {
    btn.innerHTML = isEn ? '🔄 Reindexing...' : '🔄 রি-ইনডেক্সিং হচ্ছে...';
    btn.disabled = true;
  }
  showToast('সকল ডকুমেন্টের ভেক্টর এমবেডিং ও টেবিল চাঙ্কিং পুনরায় তৈরি হচ্ছে...', 'info');

  try {
    const res = await fetch('/api/documents/reindex', {
      method: 'POST',
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {}
    });
    const data = await res.json();
    if (res.ok && data.success) {
      showToast(data.message || 'স্মার্ট রি-ইনডেক্স সম্পন্ন হয়েছে!', 'success');
      loadDocumentList();
      loadMemoryStats();
      loadChunksList(0);
      if (typeof loadDashboardMetrics === 'function') loadDashboardMetrics();
    } else {
      showToast(`রি-ইনডেক্সিং ব্যর্থ: ${data.detail || 'ত্রুটি'}`, 'error');
    }
  } catch (err) {
    showToast(`ত্রুটি: ${err.message}`, 'error');
  } finally {
    if (btn) {
      btn.innerHTML = origText;
      btn.disabled = false;
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  loadDocumentList();
  loadMemoryStats();
  loadChunksList();
});

// =============================================================================
// 💀 COGNITIVE 200IQ MEMORY PURGE & FACTORY RESET ENGINE
// =============================================================================

async function openPurgeMemoryModal() {
  const modal = document.getElementById('purge-memory-modal');
  if (!modal) return;

  // Reset state
  const confirmInput = document.getElementById('purge-confirm-input');
  if (confirmInput) confirmInput.value = '';
  const execBtn = document.getElementById('btn-execute-purge');
  if (execBtn) execBtn.disabled = true;
  const radios = document.querySelectorAll('input[name="purge-type-radio"]');
  radios.forEach(r => { if (r.value === 'nuclear') r.checked = true; });
  const backupChk = document.getElementById('purge-auto-backup');
  if (backupChk) backupChk.checked = true;

  // Load telemetry
  try {
    const res = await fetch('/api/memory/health', {
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {}
    });
    if (res.ok) {
      const d = await res.json();
      const cv = document.getElementById('purge-stat-chunks-val');
      const dv = document.getElementById('purge-stat-docs-val');
      const sv = document.getElementById('purge-stat-sessions-val');
      if (cv) cv.textContent = (d.total_chunks || 0).toLocaleString();
      if (dv) dv.textContent = (d.total_documents || 0).toLocaleString();
      if (sv) sv.textContent = (d.total_chat_sessions || 0).toLocaleString();
    }
  } catch (e) {
    // Silently ignore telemetry load errors
  }

  modal.style.display = 'flex';
}

function closePurgeMemoryModal() {
  const modal = document.getElementById('purge-memory-modal');
  if (modal) modal.style.display = 'none';
}

function checkPurgeCodeInput() {
  const val = (document.getElementById('purge-confirm-input')?.value || '').trim().toUpperCase();
  const btn = document.getElementById('btn-execute-purge');
  const validCodes = ['DELETE', 'PURGE', 'CONFIRM_DELETE', 'মুছে ফেলুন'];
  if (btn) btn.disabled = !validCodes.includes(val);
}

async function executePurgeMemory() {
  const confirmCode = document.getElementById('purge-confirm-input')?.value.trim() || '';
  const purgeType = document.querySelector('input[name="purge-type-radio"]:checked')?.value || 'nuclear';
  const autoBackup = document.getElementById('purge-auto-backup')?.checked ?? true;
  const execBtn = document.getElementById('btn-execute-purge');
  const isEn = (typeof currentLang !== 'undefined' && currentLang === 'en');

  if (execBtn) {
    execBtn.disabled = true;
    execBtn.innerHTML = isEn ? '⏳ Purging Agent Memory...' : '⏳ এজেন্ট মেমোরি মুছে হচ্ছে...';
  }

  showToast(
    isEn ? '💀 Agent Memory Purge Engine activated. Processing...' : '💀 এজেন্ট মেমোরি পার্জ ইঞ্জিন সক্রিয়। প্রসেসিং চলছে...',
    'info'
  );

  try {
    const res = await fetch('/api/memory/purge', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(typeof getAuthHeaders === 'function' ? getAuthHeaders() : {})
      },
      body: JSON.stringify({
        purge_type: purgeType,
        auto_backup: autoBackup,
        confirmation_code: confirmCode
      })
    });

    const data = await res.json();

    if (res.ok && data.success) {
      closePurgeMemoryModal();

      const vm = data.vector_memory || {};
      const cs = data.chat_sessions || {};
      const chunksGone = vm.chunks_purged || 0;
      const docsGone = vm.documents_purged || 0;
      const sessGone = cs.purged_sessions || 0;
      const backupMade = vm.backup_created || false;

      const summaryMsg = isEn
        ? `✅ Agent memory fully reset! Purged: ${chunksGone} vector chunks, ${docsGone} documents, ${sessGone} chat sessions. DB vacuumed. ${backupMade ? '🛡️ Safety backup created.' : ''}`
        : `✅ এজেন্ট মেমোরি সম্পূর্ণ রিসেট! মুছে গেছে: ${chunksGone}টি ভেক্টর, ${docsGone}টি ডকুমেন্ট, ${sessGone}টি চ্যাট সেশন। ডাটাবেস ভ্যাকুয়াম হয়েছে। ${backupMade ? '🛡️ সেফটি ব্যাকআপ সংরক্ষিত।' : ''}`;

      showToast(summaryMsg, 'success');

      // Refresh all relevant panels
      loadDocumentList();
      loadMemoryStats();
      loadChunksList(0);
      if (typeof loadAdminMetrics === 'function') loadAdminMetrics();
      if (typeof loadDashboardMetrics === 'function') loadDashboardMetrics();
      if (typeof loadSessionList === 'function') loadSessionList();

      // If new session was created, switch to it
      if (cs.new_session_id && typeof loadSessionMessages === 'function') {
        loadSessionMessages(cs.new_session_id);
      }
    } else {
      showToast(
        isEn ? `Purge failed: ${data.detail || 'Server error'}` : `পার্জ ব্যর্থ: ${data.detail || 'সার্ভার ত্রুটি'}`,
        'error'
      );
      if (execBtn) {
        execBtn.disabled = false;
        execBtn.innerHTML = isEn ? '💀 Permanently Reset Memory' : '💀 মেমোরি স্থায়ীভাবে রিসেট করুন';
      }
    }
  } catch (err) {
    showToast(isEn ? `Error: ${err.message}` : `ত্রুটি: ${err.message}`, 'error');
    if (execBtn) {
      execBtn.disabled = false;
      execBtn.innerHTML = isEn ? '💀 Permanently Reset Memory' : '💀 মেমোরি স্থায়ীভাবে রিসেট করুন';
    }
  }
}
