/* ==============================================================================
 * Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
 * Made By Arif (https://arifmahmud.com/)
 * Project: MyAgent | Version: 3.0.0
 * Analytics Dashboard Engine — Chart.js Integration
 * ============================================================================== */

// Lazy-load Chart.js from CDN
function loadChartJS(callback) {
  if (window.Chart) { callback(); return; }
  const script = document.createElement('script');
  script.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js';
  script.onload = callback;
  script.onerror = () => console.warn('Chart.js CDN load failed — charts disabled.');
  document.head.appendChild(script);
}

// Active chart instances (for destroy/re-render)
const _charts = {};

function destroyChart(key) {
  if (_charts[key]) {
    _charts[key].destroy();
    delete _charts[key];
  }
}

// ─── KPI Stats ──────────────────────────────────────────────────────────────
async function loadDashboardMetrics() {
  const container = document.getElementById('dashboard-metrics-grid');
  if (!container) return;

  try {
    const res = await fetch('/api/dashboard/stats', {
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {}
    });

    if (res.ok) {
      const data = await res.json();
      const kpi = data.kpi || {};
      const dist = data.document_distribution || {};
      const llm = data.llm_status || {};

      // 1. Animate KPI counters
      animateCounter('kpi-docs-count', kpi.total_documents || 0);
      animateCounter('kpi-chunks-count', kpi.total_chunks || 0);
      animateCounter('kpi-sessions-count', kpi.total_sessions || 0);
      animateCounter('kpi-users-count', kpi.total_users || 1);

      const storageEl = document.getElementById('kpi-storage-val');
      if (storageEl) storageEl.innerText = formatBytes(kpi.total_storage_bytes || 0);

      // 2. LLM Latency Badge
      const latencyBadge = document.getElementById('dash-llm-latency-badge');
      if (latencyBadge) {
        if (llm.connected) {
          latencyBadge.className = 'status-pill-green';
          latencyBadge.innerHTML = `🟢 সংযুক্ত &nbsp; <strong>${llm.latency_ms} ms</strong> &nbsp; <code style="font-size:0.75rem;">${escapeHtml(llm.active_model)}</code>`;
        } else {
          latencyBadge.className = 'status-pill-red';
          latencyBadge.innerHTML = `🔴 সংযোগ বিচ্ছিন্ন &nbsp; <code style="font-size:0.75rem;">${escapeHtml(llm.url)}</code>`;
        }
      }

      // 3. Distribution bars (existing + updated)
      const distContainer = document.getElementById('dash-distribution-bars');
      if (distContainer) {
        const total = Math.max(kpi.total_documents || 1, 1);
        const items = [
          { label: '📄 PDF', count: dist.pdf || 0, color: '#6366f1' },
          { label: '📊 Excel/CSV', count: dist.excel || 0, color: '#10b981' },
          { label: '📝 Word', count: dist.word || 0, color: '#06b6d4' },
          { label: '🖼️ Image OCR', count: dist.image || 0, color: '#f59e0b' },
          { label: '📋 Text', count: dist.text || 0, color: '#ec4899' }
        ];
        distContainer.innerHTML = items.map(item => `
          <div class="dist-row">
            <div class="dist-label-row">
              <span>${item.label}</span>
              <span class="dist-count">${item.count}</span>
            </div>
            <div class="progress-bar-wrap">
              <div class="progress-bar-fill" style="width:${Math.min(100, (item.count/total)*100)}%; background:${item.color};"></div>
            </div>
          </div>
        `).join('');
      }
    }
  } catch (err) {
    console.warn('Dashboard stats error:', err);
  }

  // Load charts separately
  loadChartJS(() => loadAnalyticsCharts());
}

// ─── Animate Counter ─────────────────────────────────────────────────────────
function animateCounter(id, targetValue) {
  const el = document.getElementById(id);
  if (!el) return;
  const start = parseInt(el.innerText.replace(/[^\d]/g, '')) || 0;
  const duration = 800;
  const startTime = performance.now();
  function step(now) {
    const progress = Math.min((now - startTime) / duration, 1);
    const ease = 1 - Math.pow(1 - progress, 3); // ease-out cubic
    el.innerText = Math.round(start + (targetValue - start) * ease).toLocaleString('bn-BD');
    if (progress < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

// ─── Analytics Charts ────────────────────────────────────────────────────────
async function loadAnalyticsCharts() {
  if (!window.Chart) return;

  try {
    const res = await fetch('/api/dashboard/analytics', {
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {}
    });
    if (!res.ok) return;
    const data = await res.json();

    const isDark = document.documentElement.getAttribute('data-theme') !== 'light';
    const gridColor = isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,0,0,0.07)';
    const textColor = isDark ? 'rgba(255,255,255,0.65)' : 'rgba(0,0,0,0.65)';
    Chart.defaults.color = textColor;
    Chart.defaults.borderColor = gridColor;

    // ── Chart 1: Chat Activity (7-day bar chart) ──
    const actCtx = document.getElementById('chart-activity');
    if (actCtx && data.chat_activity) {
      destroyChart('activity');
      _charts['activity'] = new Chart(actCtx, {
        type: 'bar',
        data: {
          labels: data.chat_activity.labels,
          datasets: [{
            label: 'চ্যাট সেশন',
            data: data.chat_activity.data,
            backgroundColor: 'rgba(99,102,241,0.7)',
            borderColor: '#6366f1',
            borderWidth: 1,
            borderRadius: 6
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: gridColor } },
            x: { grid: { display: false } }
          }
        }
      });
    }

    // ── Chart 2: Document Distribution (doughnut) ──
    const docCtx = document.getElementById('chart-doctype');
    if (docCtx && data.document_distribution) {
      destroyChart('doctype');
      const dd = data.document_distribution;
      const hasData = dd.data.some(v => v > 0);
      _charts['doctype'] = new Chart(docCtx, {
        type: 'doughnut',
        data: {
          labels: dd.labels,
          datasets: [{
            data: hasData ? dd.data : [1],
            backgroundColor: hasData
              ? ['#6366f1','#10b981','#06b6d4','#f59e0b','#ec4899']
              : ['rgba(255,255,255,0.1)'],
            borderWidth: 2,
            borderColor: isDark ? '#1e1e2e' : '#f8fafc'
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutout: '65%',
          plugins: {
            legend: {
              position: 'bottom',
              labels: { padding: 12, boxWidth: 12, font: { size: 11 } }
            }
          }
        }
      });
    }

    // ── Chart 3: Memory Growth (line chart) ──
    const memCtx = document.getElementById('chart-memory');
    if (memCtx && data.memory_growth) {
      destroyChart('memory');
      _charts['memory'] = new Chart(memCtx, {
        type: 'line',
        data: {
          labels: data.memory_growth.labels,
          datasets: [{
            label: 'মেমোরি চাঙ্কস',
            data: data.memory_growth.data,
            borderColor: '#10b981',
            backgroundColor: 'rgba(16,185,129,0.15)',
            fill: true,
            tension: 0.4,
            pointBackgroundColor: '#10b981',
            pointRadius: 5
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            y: { beginAtZero: true, grid: { color: gridColor } },
            x: { grid: { display: false } }
          }
        }
      });
    }

    // ── Recent Documents Table ──
    const recentDocsEl = document.getElementById('dash-recent-docs');
    if (recentDocsEl && data.recent_documents) {
      recentDocsEl.innerHTML = data.recent_documents.length > 0
        ? data.recent_documents.map(doc => `
            <tr>
              <td style="max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${escapeHtml(doc.name)}">${getFileIcon(doc.name)} ${escapeHtml(doc.name)}</td>
              <td>${doc.size_kb} KB</td>
              <td><code style="font-size:0.72rem;">${doc.modified}</code></td>
            </tr>`
          ).join('')
        : '<tr><td colspan="3" style="text-align:center; color:var(--text-muted);">কোনো ডকুমেন্ট নেই</td></tr>';
    }

  } catch (err) {
    console.warn('Analytics charts error:', err);
  }
}

// ─── Activity Log ────────────────────────────────────────────────────────────
async function loadActivityLog() {
  const container = document.getElementById('dash-activity-log');
  if (!container) return;
  container.innerHTML = '<div class="loading-spinner-sm"></div>';

  try {
    const res = await fetch('/api/dashboard/activity-log?limit=20', {
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {}
    });
    if (!res.ok) { container.innerHTML = '<p style="color:var(--text-muted);">লোড ব্যর্থ।</p>'; return; }

    const data = await res.json();
    const activities = data.activities || [];

    if (activities.length === 0) {
      container.innerHTML = '<p style="color:var(--text-muted); font-size:0.85rem; text-align:center; padding:20px;">কোনো অ্যাক্টিভিটি লগ পাওয়া যায়নি।</p>';
      return;
    }

    const severityClass = { 'CRITICAL': 'severity-critical', 'WARNING': 'severity-warning', 'INFO': 'severity-info' };
    const actionIcon = {
      'CHAT_SESSION': '💬', 'PROMPT_INJECTION_BLOCKED': '🛡️', 'DLP_TRIGGERED': '🔒',
      'LOGIN': '🔑', 'DOCUMENT_UPLOAD': '📁', 'MEMORY_SAVE': '📌', 'REPORT_GENERATE': '📊'
    };

    container.innerHTML = activities.map(act => {
      const icon = actionIcon[act.action] || '⚡';
      const badge = severityClass[act.severity] || 'severity-info';
      const ts = act.timestamp ? act.timestamp.replace('T', ' ').substring(0, 16) : '';
      return `
        <div class="activity-item">
          <span class="activity-icon">${icon}</span>
          <div class="activity-body">
            <div class="activity-action">${escapeHtml(act.action.replace(/_/g,' '))} <span class="activity-badge ${badge}">${act.severity}</span></div>
            <div class="activity-meta">${escapeHtml(act.username)} • ${ts} • ${escapeHtml(act.resource)}</div>
          </div>
        </div>`;
    }).join('');

  } catch (err) {
    container.innerHTML = `<p style="color:var(--text-muted);">লোড ব্যর্থ: ${err.message}</p>`;
  }
}

function getFileIcon(name) {
  const ext = (name || '').split('.').pop().toLowerCase();
  const icons = { pdf: '📄', xlsx: '📊', xls: '📊', csv: '📊', docx: '📝', doc: '📝', png: '🖼️', jpg: '🖼️', jpeg: '🖼️', txt: '📋', md: '📋' };
  return icons[ext] || '📎';
}

// ─── Main load function (called on tab switch) ────────────────────────────────
async function loadDashboardFull() {
  await loadDashboardMetrics();
  await loadActivityLog();
}

document.addEventListener('DOMContentLoaded', () => {
  // Charts load when dashboard tab is opened
});
