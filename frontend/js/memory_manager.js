// Company Knowledge Base and Vector Memory Manager

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

// Upload and Index Files into Memory
async function uploadFiles(files) {
  const formData = new FormData();
  for (let i = 0; i < files.length; i++) {
    formData.append('files', files[i]);
  }

  showToast(`${files.length}টি ফাইল প্রসেসিং এবং ভেক্টর মেমোরিতে যুক্ত করা হচ্ছে...`, 'info');

  try {
    const res = await fetch(`${API_BASE}/documents/upload`, {
      method: 'POST',
      body: formData
    });

    const data = await res.json();
    if (res.ok && data.success) {
      showToast('ফাইল সফলভাবে মেমোরিতে ইনজেস্ট করা হয়েছে!', 'success');
      loadDocumentList();
      loadMemoryStats();
    } else {
      showToast(`ইনজেস্ট ত্রুটি: ${data.detail || data.message || 'ব্যর্থ'}`, 'error');
    }
  } catch (err) {
    showToast(`আপলোড ত্রুটি: ${err.message}`, 'error');
  } finally {
    document.getElementById('file-input-hidden').value = '';
  }
}

// Fetch and Render Documents in Inventory
async function loadDocumentList() {
  const listEl = document.getElementById('doc-inventory-list');
  if (!listEl) return;

  try {
    const res = await fetch(`${API_BASE}/documents`);
    if (res.ok) {
      const docs = await res.json();
      if (!docs || docs.length === 0) {
        listEl.innerHTML = `
          <div style="text-align: center; color: var(--text-muted); padding: 24px;">
            কোনো ডকুমেন্ট আপলোড করা হয়নি। বামপাশ থেকে কোম্পানির ফাইল ড্রপ করুন।
          </div>`;
        return;
      }

      listEl.innerHTML = docs.map(doc => `
        <div class="doc-item" id="doc-${doc.doc_id}">
          <div class="doc-info">
            <div class="doc-icon">
              <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div>
              <div class="doc-title">${escapeHtml(doc.filename)}</div>
              <div class="doc-meta">
                ${formatBytes(doc.size_bytes)} • ${doc.chunks_count}টি ভেক্টর চাঙ্ক • ${doc.created_at}
              </div>
            </div>
          </div>
          <div style="display:flex; align-items:center; gap: 8px;">
            <span class="doc-badge">মেমোরিতে যুক্ত</span>
            <button class="delete-doc-btn" title="মুছে ফেলুন" onclick="deleteDocument('${doc.doc_id}')">
              <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        </div>
      `).join('');
    }
  } catch (err) {
    listEl.innerHTML = `<div style="color:var(--rose-red); padding:10px;">তালিকা লোড ব্যর্থ: ${err.message}</div>`;
  }
}

// Delete Document from Vector Store and Disk
async function deleteDocument(docId) {
  if (!confirm('আপনি কি নিশ্চিত যে এই ডকুমেন্টটি মেমোরি থেকে সম্পূর্ণ মুছে ফেলতে চান?')) {
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/documents/${docId}`, { method: 'DELETE' });
    if (res.ok) {
      showToast('ডকুমেন্টটি মেমোরি থেকে মুছে ফেলা হয়েছে।', 'info');
      loadDocumentList();
      loadMemoryStats();
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
    const res = await fetch(`${API_BASE}/memory/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: query, top_k: 3 })
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
    const res = await fetch(`${API_BASE}/memory/note`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, content, tags: ['corporate_note', 'policy'] })
    });

    if (res.ok) {
      showToast(`'${title}' সরাসরি এজেন্টের স্থায়ী মেমোরিতে যুক্ত হয়েছে!`, 'success');
      document.getElementById('note-title').value = '';
      document.getElementById('note-content').value = '';
      loadDocumentList();
      loadMemoryStats();
    }
  } catch (err) {
    showToast(`ত্রুটি: ${err.message}`, 'error');
  }
}

// Load Vector Memory Stats
async function loadMemoryStats() {
  try {
    const res = await fetch(`${API_BASE}/memory/stats`);
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
