/* ==============================================================================
 * Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
 * Made By Arif (https://arifmahmud.com/)
 * Project: MyAgent | Version: 2.1.0
 * ============================================================================== */

// Analytics Dashboard Rendering Engine

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

      // 1. Update KPI Card numbers
      document.getElementById('kpi-docs-count').innerText = kpi.total_documents || 0;
      document.getElementById('kpi-chunks-count').innerText = kpi.total_chunks || 0;
      document.getElementById('kpi-sessions-count').innerText = kpi.total_sessions || 0;
      document.getElementById('kpi-users-count').innerText = kpi.total_users || 1;
      document.getElementById('kpi-storage-val').innerText = formatBytes(kpi.total_storage_bytes || 0);

      // 2. Update Live LLM Latency & Ping
      const latencyBadge = document.getElementById('dash-llm-latency-badge');
      if (latencyBadge) {
        if (llm.connected) {
          latencyBadge.className = 'status-pill-green';
          latencyBadge.innerHTML = `🟢 সংযুক্ত • ${llm.latency_ms} ms (${escapeHtml(llm.active_model)})`;
        } else {
          latencyBadge.className = 'status-pill-red';
          latencyBadge.innerHTML = `🔴 সংযোগ বিচ্ছিন্ন • ${escapeHtml(llm.url)}`;
        }
      }

      // 3. Render Distribution Bars
      const distContainer = document.getElementById('dash-distribution-bars');
      if (distContainer) {
        const total = (kpi.total_documents || 1);
        distContainer.innerHTML = `
          <div class="dist-row">
            <span>📄 PDF ডকুমেন্টস (${dist.pdf || 0})</span>
            <div class="progress-bar-wrap"><div class="progress-bar-fill" style="width: ${Math.min(100, ((dist.pdf || 0)/total)*100)}%; background: #6366f1;"></div></div>
          </div>
          <div class="dist-row">
            <span>📊 এক্সেল ও স্প্রেডশিট (${dist.excel || 0})</span>
            <div class="progress-bar-wrap"><div class="progress-bar-fill" style="width: ${Math.min(100, ((dist.excel || 0)/total)*100)}%; background: #10b981;"></div></div>
          </div>
          <div class="dist-row">
            <span>📝 Word ডকুমেন্টস (${dist.word || 0})</span>
            <div class="progress-bar-wrap"><div class="progress-bar-fill" style="width: ${Math.min(100, ((dist.word || 0)/total)*100)}%; background: #06b6d4;"></div></div>
          </div>
          <div class="dist-row">
            <span>🖼️ ফটো ও ইমেজ OCR (${dist.image || 0})</span>
            <div class="progress-bar-wrap"><div class="progress-bar-fill" style="width: ${Math.min(100, ((dist.image || 0)/total)*100)}%; background: #f59e0b;"></div></div>
          </div>
          <div class="dist-row">
            <span>📋 টেক্সট ও কোড ফাইল (${dist.text || 0})</span>
            <div class="progress-bar-wrap"><div class="progress-bar-fill" style="width: ${Math.min(100, ((dist.text || 0)/total)*100)}%; background: #ec4899;"></div></div>
          </div>
        `;
      }
    }
  } catch (err) {
    console.warn('Dashboard stats error:', err);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  loadDashboardMetrics();
});
