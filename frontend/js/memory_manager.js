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
    listElem.innerHTML = `<tr><td colspan="5" style="text-align:center; color:var(--text-muted); padding:30px;">কোনো ফাইল পাওয়া যায়নি।</td></tr>`;
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
        <td>${doc.total_chunks || 1} চাঙ্কস</td>
        <td>${formatBytes(doc.size_bytes || 0)}</td>
        <td style="color:var(--text-muted); font-size:0.8rem;">${doc.uploaded_at || 'সম্প্রতি'}</td>
        <td style="text-align:right;">
          <button class="btn-sm-action" onclick="inspectDocumentChunks('${doc.id}', '${escapeHtml(doc.filename)}')">
            চাঙ্কস
          </button>
          <button class="btn-sm-action" style="color:var(--rose-red); border-color:rgba(244,63,94,0.3);" onclick="deleteDocument('${doc.id}', '${escapeHtml(doc.filename)}')">
            🗑️ ডিলিট
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

    if (countBadge) countBadge.innerText = `${total}টি চাঙ্ক`;

    if (chunks.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:30px; color:var(--text-muted);">কোনো মেমোরি চাঙ্ক পাওয়া যায়নি।</td></tr>`;
      return;
    }

    tbody.innerHTML = chunks.map(c => `
      <tr>
        <td style="font-family:monospace; font-size:0.75rem; color:var(--cyan-glow);">${escapeHtml(c.id)}</td>
        <td style="font-weight:600; font-size:0.85rem; color:white;">${escapeHtml(c.source)}</td>
        <td><span class="badge-tag">পৃষ্ঠা ${c.page || 1}</span></td>
        <td style="font-size:0.82rem; color:var(--text-muted); max-width:420px;">
          <div style="max-height:60px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
            ${escapeHtml(c.content)}
          </div>
        </td>
        <td style="text-align:right; white-space:nowrap;">
          <button class="btn-sm-action" style="color:var(--cyan-glow); border-color:rgba(6,182,212,0.4);" onclick="openEditChunkModal('${c.id}')" title="ভুল তথ্য সংশোধন / এডিট">
            ✏️ এডিট
          </button>
          <button class="btn-sm-action" style="color:var(--rose-red); border-color:rgba(244,63,94,0.3);" onclick="deleteChunk('${c.id}')" title="চাঙ্ক মুছে ফেলুন">
            🗑️ ডিলিট
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

  title.innerText = `চাঙ্ক আইডি: ${chunkId}`;
  textarea.value = 'ডাটা লোড হচ্ছে...';
  modal.style.display = 'flex';

  try {
    const res = await fetch(`/api/memory/chunks/${chunkId}`, {
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {}
    });
    if (!res.ok) throw new Error('চাঙ্ক তথ্য লোড করা যায়নি');

    const chunk = await res.json();
    textarea.value = chunk.content || '';
    if (sourceDisplay) {
      sourceDisplay.innerText = `উৎস: ${chunk.source} (পৃষ্ঠা: ${chunk.page || 1})`;
    }
  } catch (err) {
    textarea.value = `ত্রুটি: ${err.message}`;
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

  title.innerText = `ভেক্টর চাঙ্কস: ${filename}`;
  body.innerHTML = '<div style="text-align:center; padding:30px; color:var(--cyan-glow);">চাঙ্কস লোড হচ্ছে...</div>';
  modal.style.display = 'flex';

  try {
    const res = await fetch(`/api/documents/${docId}/chunks`, {
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {}
    });
    const data = await res.json();
    const chunks = data.chunks || [];

    if (chunks.length === 0) {
      body.innerHTML = '<div style="text-align:center; padding:30px; color:var(--text-muted);">কোনো সংরক্ষিত চাঙ্ক পাওয়া যায়নি।</div>';
    } else {
      body.innerHTML = chunks.map((c, idx) => `
        <div class="chunk-card">
          <div class="chunk-header">
            <span>চাঙ্ক #${idx + 1} (${escapeHtml(c.chunk_id)})</span>
            <div>
              <button class="btn-sm-action" style="color:var(--cyan-glow);" onclick="closeChunkModal(); openEditChunkModal('${c.chunk_id}')">✏️ এডিট</button>
              <button class="btn-sm-action" style="color:var(--rose-red);" onclick="deleteChunk('${c.chunk_id}')">🗑️ ডিলিট</button>
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

document.addEventListener('DOMContentLoaded', () => {
  loadDocumentList();
  loadMemoryStats();
  loadChunksList();
});
