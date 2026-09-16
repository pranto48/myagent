// ==============================================================================
// Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
// Made By Arif (https://arifmahmud.com/)
// Project: MyAgent | Version: 3.0.0
// ==============================================================================

let selectedRestoreFilename = null;

function getBackupAuthToken() {
  return localStorage.getItem("myagent_access_token") || getBackupAuthToken() || "";
}

/**
 * Initializes and loads the backup dashboard data.
 */
async function loadBackupDashboard() {
  const token = getBackupAuthToken();
  if (!token) return;

  try {
    const res = await fetch("/api/backup/list", {
      headers: { "Authorization": `Bearer ${token}` }
    });

    if (res.status === 401) {
      if (typeof handleAuthExpiry === "function") handleAuthExpiry();
      return;
    }

    const data = await res.json();
    renderBackupMetrics(data);
    renderBackupsTable(data.backups || []);
  } catch (err) {
    console.error("Failed to load backups list:", err);
    showToast("error", "ব্যাকআপ তালিকা লোড করতে ব্যর্থ হয়েছে।");
  }
}

/**
 * Renders high-level backup metrics and KPIs.
 */
function renderBackupMetrics(data) {
  const countEl = document.getElementById("backup-kpi-count");
  const sizeEl = document.getElementById("backup-kpi-size");
  const lastEl = document.getElementById("backup-kpi-last");
  const statusEl = document.getElementById("backup-kpi-status");

  if (countEl) countEl.innerText = data.total_backups || 0;
  if (sizeEl) sizeEl.innerText = data.total_size_formatted || "0 B";

  if (lastEl) {
    if (data.backups && data.backups.length > 0) {
      const isEn = (typeof currentLang !== 'undefined' && currentLang === 'en');
      const lastDate = new Date(data.backups[0].created_at || data.backups[0].modified_at);
      lastEl.innerText = lastDate.toLocaleDateString(isEn ? "en-US" : "bn-BD", {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit"
      });
    } else {
      lastEl.innerText = typeof t === 'function' ? t('backup_none', 'কোনো ব্যাকআপ নেই') : 'কোনো ব্যাকআপ নেই';
    }
  }

  if (statusEl) {
    if (data.total_backups > 0) {
      statusEl.innerHTML = `<span class="status-dot green"></span> ${typeof t === 'function' ? t('backup_status_protected', 'সুরক্ষিত (Protected)') : 'সুরক্ষিত (Protected)'}`;
      statusEl.className = "status-badge online";
    } else {
      statusEl.innerHTML = `<span class="status-dot orange"></span> ${typeof t === 'function' ? t('backup_status_needed', 'ব্যাকআপ আবশ্যক') : 'ব্যাকআপ আবশ্যক'}`;
      statusEl.className = "status-badge warning";
    }
  }
}

/**
 * Renders the table of server-stored backups.
 */
function renderBackupsTable(backups) {
  const tbody = document.getElementById("backups-table-tbody");
  if (!tbody) return;

  if (!backups || backups.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="6" style="text-align:center; padding:30px; color:var(--text-muted);">
          <div style="font-size:1.8rem; margin-bottom:8px;">📦</div>
          ${typeof t === 'function' ? t('backup_empty_state', 'সার্ভারে এখনও কোনো ব্যাকআপ ফাইল তৈরি করা হয়নি। উপরের "নতুন ব্যাকআপ তৈরি করুন" বাটনে ক্লিক করুন।') : 'সার্ভারে এখনও কোনো ব্যাকআপ ফাইল তৈরি করা হয়নি।'}
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = backups.map(b => {
    const isEn = (typeof currentLang !== 'undefined' && currentLang === 'en');
    const d = new Date(b.created_at || b.modified_at);
    const dateStr = d.toLocaleString(isEn ? "en-US" : "bn-BD", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    });

    const modules = b.modules || {};
    const tags = [];
    if (modules.documents) tags.push('<span class="chip-sm blue">' + (typeof t === 'function' ? t('backup_mod_docs', 'ডকুমেন্টস') : 'ডকুমেন্টস') + '</span>');
    if (modules.chats) tags.push('<span class="chip-sm purple">' + (typeof t === 'function' ? t('backup_mod_chats', 'চ্যাট') : 'চ্যাট') + '</span>');
    if (modules.vector_db) tags.push('<span class="chip-sm cyan">' + (typeof t === 'function' ? t('backup_mod_vector', 'ভেক্টর') : 'ভেক্টর') + '</span>');
    if (modules.settings) tags.push('<span class="chip-sm green">' + (typeof t === 'function' ? t('backup_mod_settings', 'সেটিংস') : 'সেটিংস') + '</span>');

    const modulesHtml = tags.length > 0 ? tags.join(" ") : '<span class="chip-sm">Full</span>';

    return `
      <tr>
        <td>
          <div style="font-weight:600; font-family:monospace; color:var(--text-primary); font-size:0.85rem;">
            ${escapeHtml(b.filename)}
          </div>
          <div style="font-size:0.75rem; color:var(--text-muted); margin-top:3px;">
            ${escapeHtml(b.note || "Snapshot")} • By: <code>${escapeHtml(b.created_by || "admin")}</code>
          </div>
        </td>
        <td><span class="badge-pill">${escapeHtml(b.size_formatted)}</span></td>
        <td style="font-size:0.8rem; color:var(--text-secondary);">${dateStr}</td>
        <td>${modulesHtml}</td>
        <td><span class="badge-ver">v${escapeHtml(b.version || "2.2.0")}</span></td>
        <td style="text-align:right; white-space:nowrap;">
          <div style="display:inline-flex; gap:6px;">
            <button class="btn-table-action download" title="${typeof t === 'function' ? t('reports_btn_download', 'ডাউনলোড করুন') : 'ডাউনলোড করুন'}" onclick="downloadBackup('${escapeHtml(b.filename)}')">
              📥
            </button>
            <button class="btn-table-action restore" title="${typeof t === 'function' ? t('backup_btn_restore', 'রিস্টোর করুন') : 'রিস্টোর করুন'}" onclick="openRestoreModal('${escapeHtml(b.filename)}')">
              🔄
            </button>
            <button class="btn-table-action delete" title="${typeof t === 'function' ? t('btn_delete', 'মুছে ফেলুন') : 'মুছে ফেলুন'}" onclick="deleteBackup('${escapeHtml(b.filename)}')">
              🗑️
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join("");
}

/**
 * Triggers full backup creation with chosen modules.
 */
async function createFullBackup() {
  const token = getBackupAuthToken();
  if (!token) return;

  const btn = document.getElementById("btn-create-backup");
  const noteInput = document.getElementById("backup-note-input");
  const note = noteInput ? noteInput.value.trim() : "";

  const includeDocs = document.getElementById("chk-backup-docs") ? document.getElementById("chk-backup-docs").checked : true;
  const includeChats = document.getElementById("chk-backup-chats") ? document.getElementById("chk-backup-chats").checked : true;
  const includeVector = document.getElementById("chk-backup-vector") ? document.getElementById("chk-backup-vector").checked : true;
  const includeSettings = document.getElementById("chk-backup-settings") ? document.getElementById("chk-backup-settings").checked : true;
  const includeAudit = document.getElementById("chk-backup-audit") ? document.getElementById("chk-backup-audit").checked : true;

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner-inline"></span> ব্যাকআপ তৈরি হচ্ছে...`;
  }

  try {
    const res = await fetch("/api/backup/create", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({
        note: note || "ম্যানুয়াল সম্পূর্ণ ব্যাকআপ",
        include_documents: includeDocs,
        include_chats: includeChats,
        include_vector_db: includeVector,
        include_settings: includeSettings,
        include_security_audit: includeAudit
      })
    });

    const data = await res.json();
    if (res.ok && data.success) {
      showToast("success", `সম্পূর্ণ ব্যাকআপ তৈরি সম্পন্ন হয়েছে (${data.backup.size_formatted})!`);
      if (noteInput) noteInput.value = "";
      await loadBackupDashboard();
    } else {
      showToast("error", data.detail || "ব্যাকআপ তৈরি ব্যর্থ হয়েছে।");
    }
  } catch (err) {
    console.error("Backup creation error:", err);
    showToast("error", "সার্ভারের সাথে সংযোগ ব্যর্থ হয়েছে।");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `📦 এখনই ব্যাকআপ তৈরি করুন`;
    }
  }
}

/**
 * Downloads a backup file directly from the server.
 */
async function downloadBackup(filename) {
  const token = getBackupAuthToken();
  if (!token) return;

  showToast("info", `${filename} ডাউনলোড শুরু হচ্ছে...`);

  try {
    const res = await fetch(`/api/backup/download/${encodeURIComponent(filename)}`, {
      headers: { "Authorization": `Bearer ${token}` }
    });

    if (!res.ok) {
      showToast("error", "ফাইল ডাউনলোড করা যায়নি।");
      return;
    }

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    a.remove();
    showToast("success", "ডাউনলোড সফলভাবে সম্পন্ন হয়েছে।");
  } catch (err) {
    console.error("Download error:", err);
    showToast("error", "ডাউনলোড ত্রুটি হয়েছে।");
  }
}

/**
 * Permanently deletes a backup file.
 */
async function deleteBackup(filename) {
  const token = getBackupAuthToken();
  if (!token) return;

  if (!confirm(`আপনি কি নিশ্চিত যে ব্যাকআপ ফাইল "${filename}" স্থায়ীভাবে মুছে ফেলতে চান?`)) {
    return;
  }

  try {
    const res = await fetch(`/api/backup/${encodeURIComponent(filename)}`, {
      method: "DELETE",
      headers: { "Authorization": `Bearer ${token}` }
    });

    const data = await res.json();
    if (res.ok && data.success) {
      showToast("success", "ব্যাকআপ ফাইলটি মুছে ফেলা হয়েছে।");
      await loadBackupDashboard();
    } else {
      showToast("error", data.detail || "ফাইল মুছতে ব্যর্থ হয়েছে।");
    }
  } catch (err) {
    console.error("Delete error:", err);
    showToast("error", "মুছে ফেলার সময় ত্রুটি হয়েছে।");
  }
}

/**
 * Opens the restore confirmation modal with target backup information.
 */
async function openRestoreModal(filename) {
  selectedRestoreFilename = filename;
  const modal = document.getElementById("restore-modal");
  const targetLabel = document.getElementById("restore-target-name");
  const metaBox = document.getElementById("restore-target-meta");

  if (targetLabel) targetLabel.innerText = filename;
  if (metaBox) metaBox.innerHTML = `তথ্য বিশ্লেষণ করা হচ্ছে...`;

  if (modal) modal.classList.add("active");

  // Inspect the backup file
  const token = getBackupAuthToken();
  if (token) {
    try {
      const res = await fetch(`/api/backup/inspect?filename=${encodeURIComponent(filename)}`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (res.ok) {
        const info = await res.json();
        const m = info.manifest || {};
        if (metaBox) {
          metaBox.innerHTML = `
            <div style="background:var(--bg-main); padding:10px; border-radius:var(--radius-sm); font-size:0.8rem; border:1px solid var(--border-subtle);">
              <div><strong>তৈরির সময়:</strong> ${m.created_at ? new Date(m.created_at).toLocaleString('bn-BD') : 'N/A'}</div>
              <div><strong>সৃষ্টিকর্তা:</strong> <code>${escapeHtml(m.created_by || 'admin')}</code> • <strong>ভার্সন:</strong> v${escapeHtml(m.version || '2.2.0')}</div>
              <div style="margin-top:4px;"><strong>অন্তর্ভুক্ত ফাইল:</strong> ${info.total_files} টি ফাইল (${info.has_documents ? 'ডকুমেন্টস, ' : ''}${info.has_databases ? 'ডাটাবেস, ' : ''}${info.has_chroma ? 'ভেক্টর স্টোর, ' : ''}${info.has_settings ? 'সেটিংস' : ''})</div>
            </div>
          `;
        }
      }
    } catch (e) {
      console.warn("Could not inspect backup:", e);
      if (metaBox) metaBox.innerHTML = `ফাইল: <code>${escapeHtml(filename)}</code>`;
    }
  }
}

/**
 * Closes the restore modal.
 */
function closeRestoreModal() {
  selectedRestoreFilename = null;
  const modal = document.getElementById("restore-modal");
  if (modal) modal.classList.remove("active");
}

/**
 * Executes system restoration from the selected backup file.
 */
async function executeRestore() {
  if (!selectedRestoreFilename) return;
  const token = getBackupAuthToken();
  if (!token) return;

  const btn = document.getElementById("btn-confirm-restore");
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner-inline"></span> রিস্টোর হচ্ছে...`;
  }

  try {
    const res = await fetch("/api/backup/restore", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({
        filename: selectedRestoreFilename,
        create_safety_snapshot: true
      })
    });

    const data = await res.json();
    if (res.ok && data.success) {
      closeRestoreModal();
      showToast("success", "সিস্টেম সফলভাবে রিস্টোর করা হয়েছে! (" + data.duration_seconds + "s)");
      await loadBackupDashboard();
      // Reload chat sessions and settings if available
      if (typeof loadSessionsList === "function") loadSessionsList();
      if (typeof loadSettings === "function") loadSettings();
    } else {
      showToast("error", data.detail || "রিস্টোর প্রক্রিয়া ব্যর্থ হয়েছে।");
    }
  } catch (err) {
    console.error("Restore error:", err);
    showToast("error", "রিস্টোর করার সময় সার্ভার ত্রুটি হয়েছে।");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `⚠️ নিশ্চিত রিস্টোর করুন`;
    }
  }
}

/**
 * Handles client-side .zip file upload and triggers instant restore.
 */
async function handleBackupUpload(event) {
  const file = event.target.files ? event.target.files[0] : null;
  if (!file) return;

  if (!file.name.endsWith(".zip")) {
    showToast("error", "শুধুমাত্র .zip ফরম্যাটের ব্যাকআপ ফাইল আপলোড করতে পারেন।");
    event.target.value = "";
    return;
  }

  if (!confirm(`আপনি কি "${file.name}" ব্যাকআপ ফাইলটি আপলোড করে পুরো সিস্টেমটি রিস্টোর করতে চান? এটি পূর্বের ডাটা আপডেট করবে।`)) {
    event.target.value = "";
    return;
  }

  const token = getBackupAuthToken();
  if (!token) return;

  const dropzoneText = document.getElementById("backup-upload-label");
  if (dropzoneText) dropzoneText.innerText = `আপলোড ও রিস্টোর প্রক্রিয়া চলছে (${file.name})...`;

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/backup/upload-restore", {
      method: "POST",
      headers: { "Authorization": `Bearer ${token}` },
      body: formData
    });

    const data = await res.json();
    if (res.ok && data.success) {
      showToast("success", `সফলভাবে "${file.name}" থেকে রিস্টোর সম্পন্ন হয়েছে!`);
      await loadBackupDashboard();
      if (typeof loadSessionsList === "function") loadSessionsList();
      if (typeof loadSettings === "function") loadSettings();
    } else {
      showToast("error", data.detail || "আপলোড ও রিস্টোর ব্যর্থ হয়েছে।");
    }
  } catch (err) {
    console.error("Upload restore error:", err);
    showToast("error", "আপলোড প্রক্রিয়ায় ত্রুটি ঘটেছে।");
  } finally {
    event.target.value = "";
    if (dropzoneText) dropzoneText.innerText = `এখানে ব্যাকআপ (.zip) ফাইল ড্র্যাগ করুন অথবা ক্লিক করে নির্বাচন করুন`;
  }
}

// Helper escape function
function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
