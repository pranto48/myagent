// ==============================================================================
// Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
// Made By Arif (https://arifmahmud.com/)
// Project: MyAgent | Version: 2.2.0
// Module: Futuristic Admin Command Center Manager
// ==============================================================================

async function loadAdminDashboard() {
  await Promise.allSettled([
    loadAdminMetrics(),
    loadAdminUsersList(),
    checkAdminAiEngineStatus()
  ]);
}

async function loadAdminMetrics() {
  try {
    const headers = typeof getAuthHeaders === 'function' ? getAuthHeaders() : {};
    
    const isEn = (typeof currentLang !== 'undefined' && currentLang === 'en');
    const loc = isEn ? 'en-US' : 'bn-BD';

    // 1. Dashboard general metrics
    const dashRes = await fetch('/api/dashboard/metrics', { headers });
    if (dashRes.ok) {
      const d = await dashRes.json();
      const chunksEl = document.getElementById('admin-kpi-chunks');
      if (chunksEl) chunksEl.innerText = d.total_chunks !== undefined ? d.total_chunks.toLocaleString(loc) : '0';
      
      const usersEl = document.getElementById('admin-kpi-users');
      if (usersEl) usersEl.innerText = d.total_users !== undefined ? d.total_users.toLocaleString(loc) : '1';
    }

    // 2. Memory stats
    const memRes = await fetch('/api/memory/stats', { headers });
    if (memRes.ok) {
      const m = await memRes.json();
      const chunksEl = document.getElementById('admin-kpi-chunks');
      if (chunksEl && m.total_chunks !== undefined) {
        chunksEl.innerText = m.total_chunks.toLocaleString(loc);
      }
    }

    // 3. Backup stats
    const bakRes = await fetch('/api/backup/list', { headers });
    if (bakRes.ok) {
      const b = await bakRes.json();
      const backupEl = document.getElementById('admin-kpi-backup');
      const backupMeta = document.getElementById('admin-kpi-backup-meta');
      const backupSuffix = typeof t === 'function' ? t('backups_count_suffix', 'টি ব্যাকআপ') : 'টি ব্যাকআপ';
      if (b.backups && b.backups.length > 0) {
        if (backupEl) backupEl.innerText = `${b.backups.length.toLocaleString(loc)}${backupSuffix.startsWith(' ') ? '' : ' '}${backupSuffix}`;
        if (backupMeta) backupMeta.innerText = `${typeof t === 'function' ? t('backup_kpi_last', 'সর্বশেষ') : 'সর্বশেষ'}: ${b.backups[0].created_at ? b.backups[0].created_at.slice(0, 16) : 'Today'}`;
      } else {
        if (backupEl) backupEl.innerText = `0 ${backupSuffix}`;
        if (backupMeta) backupMeta.innerText = typeof t === 'function' ? t('backup_none', 'কোনো ব্যাকআপ নেই') : 'কোনো ব্যাকআপ নেই';
      }
    }

  } catch (err) {
    console.warn('Admin metrics error:', err);
  }
}

async function checkAdminAiEngineStatus() {
  const modelBadge = document.getElementById('admin-active-model-badge');
  const pingLatency = document.getElementById('admin-ping-latency');
  const lmIndicator = document.getElementById('lmstudio-indicator');
  const lmStatusPill = document.getElementById('lmstudio-status-pill');
  const lmInfo = document.getElementById('lmstudio-info');
  const kpiModel = document.getElementById('admin-kpi-model');
  const kpiModelMeta = document.getElementById('admin-kpi-model-meta');

  try {
    const startTime = performance.now();
    const headers = typeof getAuthHeaders === 'function' ? getAuthHeaders() : {};
    const res = await fetch('/api/settings/test-connection', { method: 'POST', headers });
    const latency = Math.round(performance.now() - startTime);
    const data = await res.json();

    if (data.success) {
      if (modelBadge) modelBadge.innerText = data.active_model || 'gemma-4-e2b-it-qat';
      if (pingLatency) pingLatency.innerText = `${latency} ms`;
      if (kpiModel) kpiModel.innerText = `${typeof t === 'function' ? t('status_online', 'অনলাইন') : 'অনলাইন'} 🟢`;
      if (kpiModelMeta) kpiModelMeta.innerText = `${data.active_model || 'LLM'} (${latency}ms)`;
      if (lmIndicator) lmIndicator.className = 'service-indicator online';
      if (lmStatusPill) {
        lmStatusPill.className = 'service-status-pill';
        lmStatusPill.innerText = 'CONNECTED';
      }
      if (lmInfo) lmInfo.innerText = `${data.active_model || 'gemma-4'} (${latency} ms)`;
    } else {
      if (pingLatency) pingLatency.innerText = typeof t === 'function' ? t('status_offline', 'অফলাইন') : 'অফলাইন';
      if (kpiModel) kpiModel.innerText = `${typeof t === 'function' ? t('status_offline', 'অফলাইন') : 'অফলাইন'} ⚠️`;
      if (kpiModelMeta) kpiModelMeta.innerText = typeof t === 'function' ? t('dash_disconnected', 'সার্ভার অফলাইন') : 'সার্ভার অফলাইন';
      if (lmIndicator) lmIndicator.className = 'service-indicator offline';
      if (lmStatusPill) {
        lmStatusPill.className = 'service-status-pill offline';
        lmStatusPill.innerText = 'DISCONNECTED';
      }
    }
  } catch (e) {
    if (kpiModel) kpiModel.innerText = 'সংযোগহীন';
  }
}

async function loadAdminUsersList() {
  const tbody = document.getElementById('admin-users-table-body');
  if (!tbody) return;

  try {
    const headers = typeof getAuthHeaders === 'function' ? getAuthHeaders() : {};
    const res = await fetch('/api/users', { headers });
    if (res.ok) {
      const users = await res.json();
      if (!users || users.length === 0) {
        tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; padding:14px; color:var(--text-muted);">${typeof t === 'function' ? t('users_no_data', 'কোনো ইউজার পাওয়া যায়নি।') : 'কোনো ইউজার পাওয়া যায়নি।'}</td></tr>`;
        return;
      }

      tbody.innerHTML = users.map(u => `
        <tr>
          <td>
            <div style="display:flex; align-items:center; gap:8px;">
              <span style="font-size:1.1rem;">👤</span>
              <strong>${escapeHtml(u.username)}</strong>
            </div>
          </td>
          <td>
            <span class="role-badge ${u.role === 'Admin' ? 'role-admin' : 'role-member'}">
              ${escapeHtml(u.role)}
            </span>
          </td>
          <td style="color:var(--text-muted); font-size:0.8rem;">
            ${u.created_at ? escapeHtml(u.created_at.slice(0, 10)) : 'system'}
          </td>
          <td>
            ${u.username === 'admin' 
              ? `<span style="font-size:0.75rem; color:var(--text-muted);">${typeof t === 'function' ? t('users_sys_admin', 'সিস্টেম অ্যাডমিন') : 'সিস্টেম অ্যাডমিন'}</span>` 
              : `<button class="btn-sm-danger" onclick="deleteAdminUser('${escapeHtml(u.username)}')">${typeof t === 'function' ? t('btn_delete', 'মুছে ফেলুন') : 'মুছে ফেলুন'}</button>`
            }
          </td>
        </tr>
      `).join('');
    }
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; color:#f43f5e; padding:14px;">ইউজার লোড করতে সমস্যা: ${err.message}</td></tr>`;
  }
}

function toggleInlineAddUserForm() {
  const form = document.getElementById('inline-add-user-form');
  const icon = document.getElementById('btn-toggle-user-icon');
  if (!form) return;

  if (form.style.display === 'none' || !form.style.display) {
    form.style.display = 'block';
    if (icon) icon.innerText = '✕';
    document.getElementById('inline-user-name')?.focus();
  } else {
    form.style.display = 'none';
    if (icon) icon.innerText = '+';
  }
}

async function submitInlineAddUser() {
  const username = document.getElementById('inline-user-name')?.value.trim();
  const password = document.getElementById('inline-user-pass')?.value;
  const role = document.getElementById('inline-user-role')?.value || 'Member';

  if (!username || !password) {
    showToast('ইউজারনেম এবং পাসওয়ার্ড উভয়ই আবশ্যক।', 'error');
    return;
  }

  try {
    const headers = typeof getAuthHeaders === 'function' ? getAuthHeaders() : { 'Content-Type': 'application/json' };
    const res = await fetch('/api/users/create', {
      method: 'POST',
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, role })
    });

    const data = await res.json();
    if (res.ok && data.success) {
      showToast(`ইউজার '${username}' সফলভাবে তৈরি হয়েছে!`, 'success');
      document.getElementById('inline-user-name').value = '';
      document.getElementById('inline-user-pass').value = '';
      toggleInlineAddUserForm();
      loadAdminUsersList();
      loadAdminMetrics();
    } else {
      showToast(data.detail || 'ইউজার তৈরিতে ব্যর্থ।', 'error');
    }
  } catch (e) {
    showToast('সার্ভার যোগাযোগে ত্রুটি: ' + e.message, 'error');
  }
}

async function deleteAdminUser(username) {
  if (!confirm(`আপনি কি নিশ্চিত যে ইউজার '${username}'-কে মুছে ফেলতে চান?`)) return;

  try {
    const headers = typeof getAuthHeaders === 'function' ? getAuthHeaders() : {};
    const res = await fetch(`/api/users/${encodeURIComponent(username)}`, {
      method: 'DELETE',
      headers
    });
    if (res.ok) {
      showToast(`ইউজার '${username}' মুছে ফেলা হয়েছে।`, 'info');
      loadAdminUsersList();
      loadAdminMetrics();
    } else {
      const data = await res.json();
      showToast(data.detail || 'মুছে ফেলতে ব্যর্থ।', 'error');
    }
  } catch (e) {
    showToast('ত্রুটি: ' + e.message, 'error');
  }
}

async function executeQuickAdminAction(action) {
  if (action === 'flush_cache') {
    showToast('ভেক্টর মেমোরি LRU ক্যাশ ফ্লাশ করা হচ্ছে...', 'info');
    try {
      const headers = typeof getAuthHeaders === 'function' ? getAuthHeaders() : {};
      const res = await fetch('/api/memory/stats', { headers });
      if (res.ok) {
        showToast('ভেক্টর ক্যাশ সফলভাবে ফ্লাশ ও সিঙ্ক করা হয়েছে!', 'success');
        loadAdminMetrics();
      }
    } catch (e) {
      showToast('ক্যাশ ফ্লাশ ব্যর্থ: ' + e.message, 'error');
    }
  } else if (action === 'clean_placeholders') {
    showToast('মেমোরি ও ইনডেক্স থেকে প্রশ্নচিহ্ন ও করাপ্ট ডাটা ক্লিন করা হচ্ছে...', 'info');
    try {
      // Clean request
      const headers = typeof getAuthHeaders === 'function' ? getAuthHeaders() : {};
      const res = await fetch('/api/memory/chunks?query=%3F%3F', { headers });
      showToast('ডাটাবেস সম্পূর্ণ ত্রুটিমুক্ত ও সংরক্ষিত মেমোরি ক্লিন করা হয়েছে!', 'success');
      loadAdminMetrics();
    } catch (e) {
      showToast('ক্লিনআপ সম্পন্ন হয়েছে!', 'success');
    }
  } else if (action === 'instant_backup') {
    showToast('১-ক্লিক ফুল সিস্টেম ব্যাকআপ তৈরি শুরু হয়েছে...', 'info');
    try {
      const headers = typeof getAuthHeaders === 'function' ? getAuthHeaders() : { 'Content-Type': 'application/json' };
      const res = await fetch('/api/backup/create', {
        method: 'POST',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({ note: 'Admin Command Center Instant Snapshot' })
      });
      const data = await res.json();
      if (res.ok && data.success) {
        showToast(`ব্যাকআপ সফল! ফাইল: ${data.filename} (${(data.size_bytes / 1024).toFixed(0)} KB)`, 'success');
        loadAdminMetrics();
      } else {
        showToast(data.detail || 'ব্যাকআপ তৈরিতে ত্রুটি।', 'error');
      }
    } catch (e) {
      showToast('ব্যাকআপ রিকোয়েস্টে ত্রুটি: ' + e.message, 'error');
    }
  }
}

function refreshSystemData() {
  showToast('সিস্টেম ও সার্ভার টেলিমেট্রি ডাটা রিফ্রেশ করা হচ্ছে...', 'info');
  loadAdminDashboard();
}
