/* ==============================================================================
 * Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
 * Made By Arif (https://arifmahmud.com/)
 * Project: MyAgent | Version: 2.0.0
 * ============================================================================== */

// Company Knowledge Base, Big Data & Vector Memory Manager

let activeFilter = 'all';
let allLoadedDocs = [];

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

function renderFilteredDocs() {
  const listEl = document.getElementById('doc-inventory-list');
  if (!listEl) return;

  let filtered = allLoadedDocs;
  if (activeFilter !== 'all') {
    filtered = allLoadedDocs.filter(d => {
      const ext = (d.filename.split('.').pop() || '').toLowerCase();
      if (activeFilter === 'pdf') return ext === 'pdf';
      if (activeFilter === 'excel') return ['xlsx', 'xls', 'csv'].includes(ext);
      if (activeFilter === 'word') return ['docx', 'doc'].includes(ext);
      if (activeFilter === 'photo') return ['png', 'jpg', 'jpeg', 'webp', 'bmp'].includes(ext);
      if (activeFilter === 'text') return ['txt', 'md', 'json', 'log'].includes(ext);
      return true;
    });
  }

  if (filtered.length === 0) {
    listEl.innerHTML = '<div style="text-align: center; color: var(--text-muted); padding: 20px;">এই ক্যাটাগরিতে কোনো ফাইল নেই।</div>';
    return;
  }

  listEl.innerHTML = filtered.map(doc => {
    const ext = (doc.filename.split('.').pop() || '').toLowerCase();
    let icon = '📄';
    if (['xlsx', 'xls', 'csv'].includes(ext)) icon = '📊';
    else if (['docx', 'doc'].includes(ext)) icon = '📝';
    else if (['png', 'jpg', 'jpeg', 'webp'].includes(ext)) icon = '🖼️';

    return `
      <div class="doc-item" id="doc-${doc.doc_id}">
        <div class="doc-info">
          <div class="doc-icon">${icon}</div>
          <div>
            <div class="doc-title">${escapeHtml(doc.filename)}</div>
            <div class="doc-meta">
              ${formatBytes(doc.size_bytes)} • ${doc.chunks_count}টি ভেক্টর চাঙ্ক • ${doc.created_at}
            </div>
          </div>
        </div>
        <div style="display:flex; align-items:center; gap: 8px;">
          <button class="btn-inspect-chunks" onclick="inspectChunks('${doc.doc_id}', '${escapeHtml(doc.filename)}')">
            চাঙ্কস দেখুন
          </button>
          <span class="doc-badge">মেমোরিতে ইনডেক্সড</span>
          <button class="delete-doc-btn" title="মুছে ফেলুন" onclick="deleteDocument('${doc.doc_id}')">
            <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>
    `;
  }).join('');
}

// Fetch and Render Documents
async function loadDocumentList() {
  const listEl = document.getElementById('doc-inventory-list');
  if (!listEl) return;

  try {
    const res = await fetch('/api/documents', {
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {}
    });
    if (res.ok) {
      allLoadedDocs = await res.json();
      renderFilteredDocs();
    }
  } catch (err) {
    listEl.innerHTML = `<div style="color:var(--rose-red); padding:10px;">তালিকা লোড ব্যর্থ: ${err.message}</div>`;
  }
}

// Inspect Document Chunks in Vector Store Modal
async function inspectChunks(docId, filename) {
  const modal = document.getElementById('chunks-modal');
  const title = document.getElementById('chunks-modal-title');
  const meta = document.getElementById('chunks-modal-meta');
  const list = document.getElementById('chunks-viewer-list');

  title.innerText = `চাঙ্কস প্রিভিউ: ${filename}`;
  meta.innerText = 'ChromaDB থেকে ভেক্টর চাঙ্কস লোড হচ্ছে...';
  list.innerHTML = '';
  modal.classList.add('open');

  try {
    const res = await fetch(`/api/documents/${docId}/chunks`, {
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {}
    });
    if (res.ok) {
      const data = await res.json();
      meta.innerText = `মোট ভেক্টর চাঙ্কস: ${data.total_chunks || 0}টি`;
      if (!data.chunks || data.chunks.length === 0) {
        list.innerHTML = '<div style="color:var(--text-muted); padding:20px;">কোনো চাঙ্ক পাওয়া যায়নি।</div>';
        return;
      }

      list.innerHTML = data.chunks.map(c => `
        <div class="chunk-card">
          <div class="chunk-card-meta">
            <span>ID: ${escapeHtml(c.chunk_id)}</span>
            <span>পৃষ্ঠা / সেকশন: ${c.metadata ? (c.metadata.page || 1) : 1}</span>
          </div>
          <div class="chunk-card-body">${escapeHtml(c.content)}</div>
        </div>
      `).join('');
    }
  } catch (err) {
    meta.innerText = `ত্রুটি: ${err.message}`;
  }
}

function closeChunksModal() {
  document.getElementById('chunks-modal').classList.remove('open');
}

// Delete Document from Vector Store and Disk
async function deleteDocument(docId) {
  if (!confirm('আপনি কি নিশ্চিত যে এই ডকুমেন্টটি মেমোরি থেকে সম্পূর্ণ মুছে ফেলতে চান?')) {
    return;
  }

  try {
    const res = await fetch(`/api/documents/${docId}`, {
      method: 'DELETE',
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {}
    });
    if (res.ok) {
      showToast('ডকুমেন্টটি মেমোরি থেকে মুছে ফেলা হয়েছে।', 'info');
      loadDocumentList();
      loadMemoryStats();
      if (typeof loadDashboardMetrics === 'function') loadDashboardMetrics();
    } else {
      showToast('ডকুমেন্ট ডিলিট করতে ব্যর্থ হয়েছে।', 'error');
    }
  } catch (err) {
    showToast(`ত্রুটি: ${err.message}`, 'error');
  }
}

// Direct Semantic Memory Search Sandbox
async function executeMemorySearch() {
  const query = document.getElementById('memory-search-input').value.trim();
  const resultsContainer = document.getElementById('memory-search-results');

  if (!query) {
    showToast('অনুগ্রহ করে সার্চ কোয়েরি লিখুন।', 'info');
    return;
  }

  resultsContainer.innerHTML = '<div style="color:var(--text-muted); padding:10px;">মেমোরিতে সেমান্টিক সার্চ চলছে...</div>';

  try {
    const res = await fetch('/api/memory/search', {
      method: 'POST',
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: query, top_k: 4 })
    });

    if (res.ok) {
      const hits = await res.json();
      if (!hits || hits.length === 0) {
        resultsContainer.innerHTML = '<div style="color:var(--text-muted); padding:10px;">কোনো প্রাসঙ্গিক তথ্য খুঁজে পাওয়া যায়নি।</div>';
        return;
      }

      resultsContainer.innerHTML = hits.map(h => `
        <div class="search-hit-card">
          <div class="hit-meta">
            <span>📄 ${escapeHtml(h.source)} (পৃষ্ঠা ${h.page || 1})</span>
            <span>স্কোর: ${(h.score * 100).toFixed(1)}%</span>
          </div>
          <div>${escapeHtml(h.content)}</div>
        </div>
      `).join('');
    }
  } catch (err) {
    resultsContainer.innerHTML = `<div style="color:var(--rose-red); padding:10px;">সার্চ ত্রুটি: ${err.message}</div>`;
  }
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
    const res = await fetch('/api/memory/note', {
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
});
