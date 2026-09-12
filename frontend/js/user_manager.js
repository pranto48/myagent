/* ==============================================================================
 * Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
 * Made By Arif (https://arifmahmud.com/)
 * Project: MyAgent | Version: 2.0.0
 * ============================================================================== */

// User and Role Management Handler

async function loadUsersList() {
  const tbody = document.getElementById('users-table-body');
  if (!tbody) return;

  try {
    const res = await fetch('/api/users', {
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {}
    });
    if (res.ok) {
      const users = await res.json();
      if (!users || users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:20px; color:var(--text-muted);">কোনো ইউজার পাওয়া যায়নি।</td></tr>';
        return;
      }

      tbody.innerHTML = users.map(u => `
        <tr>
          <td style="font-weight: 600; color: var(--text-primary);">👤 ${escapeHtml(u.username)}</td>
          <td><span class="role-badge role-${u.role.toLowerCase()}">${escapeHtml(u.role)}</span></td>
          <td><span class="status-dot-inline"></span> ${escapeHtml(u.status)}</td>
          <td style="color: var(--text-muted); font-size: 0.75rem;">${u.created_at}</td>
          <td>
            ${u.username === 'admin' 
              ? '<span style="font-size:0.75rem; color:var(--text-muted);">সিস্টেম অ্যাডমিন</span>' 
              : `<button class="btn-sm-danger" onclick="deleteCompanyUser('${u.id}', '${escapeHtml(u.username)}')">মুছে ফেলুন</button>`
            }
          </td>
        </tr>
      `).join('');
    }
  } catch (err) {
    console.warn('Error loading users:', err);
  }
}

function openAddUserModal() {
  document.getElementById('add-user-modal').classList.add('open');
}

function closeAddUserModal() {
  document.getElementById('add-user-modal').classList.remove('open');
  document.getElementById('new-user-username').value = '';
  document.getElementById('new-user-password').value = '';
}

async function submitCreateUser(e) {
  if (e) e.preventDefault();
  const username = document.getElementById('new-user-username').value.trim();
  const password = document.getElementById('new-user-password').value.trim();
  const role = document.getElementById('new-user-role').value;

  if (!username || !password) {
    showToast('ইউজারনেম এবং পাসওয়ার্ড পূরণ করুন।', 'error');
    return;
  }

  try {
    const res = await fetch('/api/users', {
      method: 'POST',
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, role })
    });

    if (res.ok) {
      showToast(`ইউজার '${username}' সফলভাবে তৈরি হয়েছে!`, 'success');
      closeAddUserModal();
      loadUsersList();
      if (typeof loadDashboardMetrics === 'function') loadDashboardMetrics();
    } else {
      const err = await res.json();
      showToast(`ব্যর্থ: ${err.detail || 'ইউজার তৈরি করা যায়নি'}`, 'error');
    }
  } catch (err) {
    showToast(`ত্রুটি: ${err.message}`, 'error');
  }
}

async function deleteCompanyUser(userId, username) {
  if (!confirm(`আপনি কি নিশ্চিত যে ইউজার '${username}' মুছে ফেলতে চান?`)) return;

  try {
    const res = await fetch(`/api/users/${userId}`, {
      method: 'DELETE',
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {}
    });

    if (res.ok) {
      showToast(`ইউজার '${username}' মুছে ফেলা হয়েছে।`, 'info');
      loadUsersList();
      if (typeof loadDashboardMetrics === 'function') loadDashboardMetrics();
    } else {
      showToast('ইউজার মুছতে ব্যর্থ হয়েছে।', 'error');
    }
  } catch (err) {
    showToast(`ত্রুটি: ${err.message}`, 'error');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  loadUsersList();
});
