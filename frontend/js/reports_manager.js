/* ==============================================================================
 * Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
 * Made By Arif (https://arifmahmud.com/)
 * Project: MyAgent | Version: 3.0.0
 * Reports Manager — AI-Powered Enterprise Report Generation UI
 * ============================================================================== */

let _reportsList = [];
let _activeReportId = null;
let _reportTemplates = [];

// ─── Load Templates ───────────────────────────────────────────────────────────
async function loadReportTemplates() {
  try {
    const res = await fetch('/api/reports/templates', {
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {}
    });
    if (res.ok) {
      const data = await res.json();
      _reportTemplates = data.templates || [];
      renderReportTypeSelector();
    }
  } catch (err) {
    console.warn('Report templates load error:', err);
  }
}

function renderReportTypeSelector() {
  const sel = document.getElementById('report-type-select');
  if (!sel || !_reportTemplates.length) return;
  sel.innerHTML = _reportTemplates.map(t =>
    `<option value="${t.id}">${t.icon} ${t.name}</option>`
  ).join('');
}

// ─── Load Reports List ────────────────────────────────────────────────────────
async function loadReportsList() {
  const container = document.getElementById('reports-list-container');
  if (!container) return;
  container.innerHTML = '<div class="loading-spinner-sm"></div>';

  try {
    const res = await fetch('/api/reports/list?limit=50', {
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {}
    });
    if (!res.ok) { container.innerHTML = '<p style="color:var(--text-muted);">লোড ব্যর্থ।</p>'; return; }

    const data = await res.json();
    _reportsList = data.reports || [];

    if (_reportsList.length === 0) {
      container.innerHTML = `
        <div class="empty-state" style="padding:40px; text-align:center;">
          <div style="font-size:3rem; margin-bottom:12px;">📊</div>
          <h4 style="color:var(--text-secondary); margin:0 0 8px;">এখনো কোনো রিপোর্ট তৈরি হয়নি</h4>
          <p style="color:var(--text-muted); font-size:0.85rem;">নিচের ফর্মটি ব্যবহার করে আপনার প্রথম AI রিপোর্ট তৈরি করুন।</p>
        </div>`;
      return;
    }

    const typeIcon = {
      executive_summary: '📊', data_analysis: '📈', kpi_report: '🎯',
      incident_report: '🚨', meeting_minutes: '📝', company_policy: '📋', custom: '✨'
    };

    container.innerHTML = _reportsList.map(r => `
      <div class="report-card" onclick="viewReport('${r.id}')" id="rpt-card-${r.id}">
        <div class="report-card-icon">${typeIcon[r.report_type] || '📄'}</div>
        <div class="report-card-body">
          <div class="report-card-title">${escapeHtml(r.title)}</div>
          <div class="report-card-meta">
            <span class="report-type-badge">${r.report_type.replace(/_/g,' ')}</span>
            <span>${r.word_count || 0} শব্দ</span>
            <span>${formatReportDate(r.created_at)}</span>
            <span>👤 ${escapeHtml(r.created_by)}</span>
          </div>
        </div>
        <div class="report-card-actions" onclick="event.stopPropagation()">
          <button class="btn-icon-sm" title="ডাউনলোড করুন" onclick="downloadReport('${r.id}')">⬇️</button>
          <button class="btn-icon-sm" title="মুছুন" onclick="deleteReport('${r.id}')">🗑️</button>
        </div>
      </div>`
    ).join('');

  } catch (err) {
    container.innerHTML = `<p style="color:var(--text-muted);">লোড ব্যর্থ: ${err.message}</p>`;
  }
}

function formatReportDate(isoStr) {
  if (!isoStr) return '';
  try {
    const d = new Date(isoStr);
    return d.toLocaleDateString('bn-BD', { year:'numeric', month:'short', day:'numeric' }) + ' ' +
           d.toLocaleTimeString('en-US', { hour:'2-digit', minute:'2-digit', hour12: false });
  } catch { return isoStr.substring(0,16); }
}

// ─── Generate Report ──────────────────────────────────────────────────────────
async function generateReport() {
  const type = document.getElementById('report-type-select')?.value;
  const topic = document.getElementById('report-topic-input')?.value?.trim();
  const context = document.getElementById('report-context-input')?.value?.trim();

  if (!topic) {
    showToast('⚠️ রিপোর্টের বিষয় (topic) লিখুন।', 'warning');
    return;
  }

  const btn = document.getElementById('btn-generate-report');
  const statusEl = document.getElementById('report-gen-status');

  if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spin-icon">⟳</span> জেনারেট হচ্ছে...'; }
  if (statusEl) {
    statusEl.style.display = 'block';
    statusEl.innerHTML = `
      <div class="gen-status-card">
        <div class="gen-spinner"></div>
        <div>
          <strong>📊 AI রিপোর্ট তৈরি হচ্ছে...</strong><br>
          <span style="font-size:0.8rem; color:var(--text-muted);">কোম্পানি মেমোরি সার্চ এবং AI বিশ্লেষণ চলছে। এটি ১-২ মিনিট সময় নিতে পারে।</span>
        </div>
      </div>`;
  }

  try {
    const res = await fetch('/api/reports/generate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(typeof getAuthHeaders === 'function' ? getAuthHeaders() : {})
      },
      body: JSON.stringify({ report_type: type, topic, additional_context: context || '' })
    });

    const result = await res.json();

    if (res.ok && result.success) {
      showToast(`✅ রিপোর্ট "${result.title}" সফলভাবে তৈরি হয়েছে!`, 'success');
      if (statusEl) statusEl.style.display = 'none';
      // Clear form
      document.getElementById('report-topic-input').value = '';
      if (document.getElementById('report-context-input')) document.getElementById('report-context-input').value = '';
      // Reload list and view the new report
      await loadReportsList();
      viewReport(result.report_id);
    } else {
      throw new Error(result.detail || 'রিপোর্ট জেনারেশন ব্যর্থ।');
    }
  } catch (err) {
    showToast(`❌ ${err.message}`, 'error');
    if (statusEl) statusEl.innerHTML = `<div class="gen-error">❌ ব্যর্থ: ${escapeHtml(err.message)}</div>`;
  } finally {
    if (btn) { btn.disabled = false; btn.innerHTML = '📊 রিপোর্ট তৈরি করুন'; }
  }
}

// ─── View Report ──────────────────────────────────────────────────────────────
async function viewReport(reportId) {
  _activeReportId = reportId;

  // Highlight selected card
  document.querySelectorAll('.report-card').forEach(c => c.classList.remove('active'));
  const card = document.getElementById(`rpt-card-${reportId}`);
  if (card) card.classList.add('active');

  const viewer = document.getElementById('report-viewer');
  const viewerContent = document.getElementById('report-viewer-content');
  if (!viewer || !viewerContent) return;

  viewer.style.display = 'flex';
  viewerContent.innerHTML = '<div class="loading-spinner-sm" style="margin:40px auto;"></div>';

  try {
    const res = await fetch(`/api/reports/${reportId}`, {
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {}
    });
    if (!res.ok) throw new Error('রিপোর্ট লোড ব্যর্থ।');

    const report = await res.json();

    // Render markdown
    const html = typeof marked !== 'undefined'
      ? marked.parse(report.content)
      : report.content.replace(/\n/g, '<br>');

    viewerContent.innerHTML = `
      <div class="report-view-header">
        <div class="report-view-title">${escapeHtml(report.title)}</div>
        <div class="report-view-actions">
          <button class="btn-secondary btn-sm" onclick="downloadReport('${report.id}')">⬇️ ডাউনলোড</button>
          <button class="btn-secondary btn-sm" onclick="copyReportToClipboard()">📋 কপি</button>
          <button class="btn-icon-sm" onclick="closeReportViewer()" title="বন্ধ করুন">✕</button>
        </div>
      </div>
      <div class="report-markdown-body" id="report-md-body">${html}</div>`;

  } catch (err) {
    viewerContent.innerHTML = `<div style="padding:20px; color:var(--danger);">❌ ${escapeHtml(err.message)}</div>`;
  }
}

function closeReportViewer() {
  const viewer = document.getElementById('report-viewer');
  if (viewer) viewer.style.display = 'none';
  _activeReportId = null;
  document.querySelectorAll('.report-card').forEach(c => c.classList.remove('active'));
}

// ─── Download Report ──────────────────────────────────────────────────────────
async function downloadReport(reportId) {
  try {
    const res = await fetch(`/api/reports/${reportId}/download`, {
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {}
    });
    if (!res.ok) throw new Error('ডাউনলোড ব্যর্থ।');
    const blob = await res.blob();
    const contentDisposition = res.headers.get('content-disposition') || '';
    const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
    const filename = filenameMatch ? filenameMatch[1] : `${reportId}.md`;
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
    showToast('✅ রিপোর্ট ডাউনলোড শুরু হয়েছে!', 'success');
  } catch (err) {
    showToast(`❌ ${err.message}`, 'error');
  }
}

// ─── Delete Report ────────────────────────────────────────────────────────────
async function deleteReport(reportId) {
  if (!confirm('এই রিপোর্টটি স্থায়ীভাবে মুছে ফেলবেন?')) return;
  try {
    const res = await fetch(`/api/reports/${reportId}`, {
      method: 'DELETE',
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {}
    });
    if (!res.ok) throw new Error('মুছে ফেলা ব্যর্থ।');
    showToast('🗑️ রিপোর্ট মুছে ফেলা হয়েছে।', 'success');
    if (_activeReportId === reportId) closeReportViewer();
    await loadReportsList();
  } catch (err) {
    showToast(`❌ ${err.message}`, 'error');
  }
}

// ─── Copy Report to Clipboard ─────────────────────────────────────────────────
async function copyReportToClipboard() {
  const mdBody = document.getElementById('report-md-body');
  if (!mdBody) return;
  try {
    await navigator.clipboard.writeText(mdBody.innerText);
    showToast('📋 রিপোর্ট কপি করা হয়েছে!', 'success');
  } catch {
    showToast('❌ কপি করতে ব্যর্থ।', 'error');
  }
}

// ─── Load full Reports page ───────────────────────────────────────────────────
async function loadReportsPage() {
  if (_reportTemplates.length === 0) await loadReportTemplates();
  await loadReportsList();
}
