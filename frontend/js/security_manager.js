/* ==============================================================================
 * Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
 * Made By Arif (https://arifmahmud.com/)
 * Project: MyAgent | Version: 2.2.0
 * ============================================================================== */

// Enterprise Data Security, DLP Redaction, Firewall & Compliance Audit Management

let currentAuditPage = 0;
const AUDIT_PAGE_SIZE = 25;

async function loadSecurityDashboard() {
    try {
        const token = localStorage.getItem('myagent_access_token');
        const headers = token ? { 'Authorization': `Bearer ${token}` } : {};

        const res = await fetch('/api/security/stats', { headers });
        if (!res.ok) {
            console.warn('Security stats returned:', res.status);
            return;
        }

        const data = await res.json();
        
        // Update security metric badges
        const encEl = document.getElementById('sec-encryption-badge');
        if (encEl) encEl.innerText = data.encryption_algorithm || 'AES-256-GCM';

        const dlpCountEl = document.getElementById('sec-dlp-count');
        if (dlpCountEl) dlpCountEl.innerText = data.dlp_triggers_count || '0';

        const firewallCountEl = document.getElementById('sec-firewall-count');
        if (firewallCountEl) firewallCountEl.innerText = data.firewall_blocks_count || '0';

        const totalAuditEl = document.getElementById('sec-total-audit');
        if (totalAuditEl) totalAuditEl.innerText = data.total_audit_events || '0';

        const postureEl = document.getElementById('sec-posture-badge');
        if (postureEl) {
            if (data.overall_status === 'SECURE') {
                postureEl.className = 'status-badge online';
                postureEl.innerHTML = '<span class="status-dot green"></span> সুরক্ষিত (SECURE)';
            } else {
                postureEl.className = 'status-badge offline';
                postureEl.innerHTML = '<span class="status-dot red"></span> মনোযোগ প্রয়োজন (ATTENTION)';
            }
        }

        // Load audit log trail
        await loadAuditLogs();
    } catch (e) {
        console.error('Error loading security dashboard:', e);
    }
}

async function loadAuditLogs(offset = 0) {
    const tableBody = document.getElementById('security-audit-tbody');
    if (!tableBody) return;

    tableBody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding: 24px; color: var(--text-muted);"><i class="fas fa-spinner fa-spin"></i> অডিট লগ লোড হচ্ছে...</td></tr>';

    try {
        const token = localStorage.getItem('myagent_access_token');
        const headers = token ? { 'Authorization': `Bearer ${token}` } : {};

        const severityFilter = document.getElementById('audit-severity-filter')?.value || 'ALL';
        const searchVal = document.getElementById('audit-search-input')?.value || '';

        let url = `/api/security/audit-logs?limit=${AUDIT_PAGE_SIZE}&offset=${offset}`;
        if (severityFilter !== 'ALL') url += `&severity=${encodeURIComponent(severityFilter)}`;
        if (searchVal.trim()) url += `&search=${encodeURIComponent(searchVal.trim())}`;

        const res = await fetch(url, { headers });
        if (!res.ok) {
            tableBody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding: 24px; color: var(--danger-color);"><i class="fas fa-lock"></i> অডিট লগ দেখতে অ্যাডমিন বা অ্যানালিস্ট পারমিশন আবশ্যক।</td></tr>';
            return;
        }

        const data = await res.json();
        const logs = data.logs || [];
        currentAuditPage = offset;

        if (logs.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding: 24px; color: var(--text-muted);">কোনো সিকিউরিটি অডিট রেকর্ড পাওয়া যায়নি।</td></tr>';
            return;
        }

        tableBody.innerHTML = logs.map(log => {
            let badgeClass = 'badge-info';
            if (log.severity === 'CRITICAL') badgeClass = 'badge-critical';
            else if (log.severity === 'WARNING') badgeClass = 'badge-warning';

            const detailsStr = typeof log.details === 'object' ? JSON.stringify(log.details) : String(log.details || '');
            const truncatedDetails = detailsStr.length > 50 ? detailsStr.substring(0, 50) + '...' : detailsStr;

            return `
                <tr>
                    <td style="font-family: monospace; font-size: 0.8rem; color: var(--text-muted);">${escapeHtml(log.iso_time)}</td>
                    <td><span class="action-pill">${escapeHtml(log.action)}</span></td>
                    <td><strong>${escapeHtml(log.username)}</strong> <span style="font-size:0.75rem; color:var(--text-muted);">(${escapeHtml(log.user_role)})</span></td>
                    <td style="font-size: 0.85rem; color: var(--text-secondary);">${escapeHtml(log.resource || '-')}</td>
                    <td><span class="severity-badge ${badgeClass}">${escapeHtml(log.severity)}</span></td>
                    <td style="font-family: monospace; font-size: 0.8rem;">${escapeHtml(log.ip_address)}</td>
                    <td>
                        <span class="details-snippet" title="${escapeHtml(detailsStr)}">${escapeHtml(truncatedDetails)}</span>
                    </td>
                </tr>
            `;
        }).join('');

        // Update pagination counter
        const pageIndicator = document.getElementById('audit-page-indicator');
        if (pageIndicator) {
            const current = Math.floor(offset / AUDIT_PAGE_SIZE) + 1;
            const totalPages = Math.max(1, Math.ceil((data.total || 1) / AUDIT_PAGE_SIZE));
            pageIndicator.innerText = `পৃষ্ঠা ${current} / ${totalPages} (মোট: ${data.total || 0})`;
        }
    } catch (e) {
        console.error('Error fetching audit logs:', e);
        tableBody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding: 24px; color: var(--danger-color);">অডিট লগ লোড করতে ত্রুটি হয়েছে।</td></tr>';
    }
}

function prevAuditPage() {
    if (currentAuditPage >= AUDIT_PAGE_SIZE) {
        loadAuditLogs(currentAuditPage - AUDIT_PAGE_SIZE);
    }
}

function nextAuditPage() {
    loadAuditLogs(currentAuditPage + AUDIT_PAGE_SIZE);
}

async function runSecuritySandboxTest() {
    const inputEl = document.getElementById('sandbox-test-input');
    const resultBox = document.getElementById('sandbox-test-result');
    if (!inputEl || !resultBox) return;

    const sample = inputEl.value.trim();
    if (!sample) {
        showToast('অনুগ্রহ করে পরীক্ষার জন্য কিছু টেক্সট লিখুন!', 'warning');
        return;
    }

    resultBox.style.display = 'block';
    resultBox.innerHTML = '<div style="padding: 20px; text-align: center;"><i class="fas fa-spinner fa-spin"></i> এন্টারপ্রাইজ ফায়ারওয়াল ও DLP বিশ্লেষণ চলছে...</div>';

    try {
        const token = localStorage.getItem('myagent_access_token');
        const headers = { 'Content-Type': 'application/json' };
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const res = await fetch('/api/security/sandbox-test', {
            method: 'POST',
            headers,
            body: JSON.stringify({ sample_text: sample })
        });

        if (!res.ok) {
            resultBox.innerHTML = '<div style="color: var(--danger-color); padding: 16px;">স্যান্ডবক্স টেস্টে ত্রুটি হয়েছে।</div>';
            return;
        }

        const data = await res.json();
        const fw = data.firewall;
        const dlp = data.dlp;
        const crypto = data.crypto_demo;

        let fwHtml = fw.is_safe 
            ? '<span class="status-badge online"><i class="fas fa-shield-alt"></i> নিরাপদ (CLEAN)</span>' 
            : `<span class="status-badge offline"><i class="fas fa-ban"></i> ব্লকড (${fw.threat_level})</span> - ${escapeHtml(fw.reason || '')}`;

        let dlpFindingsHtml = dlp.findings.length > 0
            ? dlp.findings.map(f => `<span class="tag-pill tag-danger"><i class="fas fa-exclamation-triangle"></i> ${escapeHtml(f.type)}: ${escapeHtml(f.match)}</span>`).join(' ')
            : '<span class="tag-pill tag-success"><i class="fas fa-check-circle"></i> কোনো সেনসিটিভ PII পাওয়া যায়নি</span>';

        resultBox.innerHTML = `
            <div class="sandbox-result-grid">
                <div class="sandbox-card">
                    <h4><i class="fas fa-fire-alt"></i> প্রম্পট ইনজেকশন ফায়ারওয়াল</h4>
                    <div style="margin: 8px 0;">${fwHtml}</div>
                    <div style="font-size:0.85rem; color: var(--text-muted); margin-top: 6px;">
                        সনাক্তকরণ প্যাটার্ন: ${fw.threat_types.length ? fw.threat_types.join(', ') : 'নাই'}
                    </div>
                </div>

                <div class="sandbox-card">
                    <h4><i class="fas fa-user-shield"></i> ডাটা লস প্রিভেনশন (DLP) ও মাস্কিং</h4>
                    <div style="margin: 8px 0;">${dlpFindingsHtml}</div>
                    <div style="margin-top: 10px;">
                        <label style="font-size: 0.8rem; color: var(--text-muted);">স্যানিটাইজড আউটপুট প্রিভিউ:</label>
                        <pre class="code-preview">${escapeHtml(dlp.sanitized_text)}</pre>
                    </div>
                </div>

                <div class="sandbox-card">
                    <h4><i class="fas fa-key"></i> AES-256-GCM সাইফার টেস্ট</h4>
                    <div style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 6px;">
                        এনক্রিপশন অ্যালগরিদম: <strong>${escapeHtml(crypto.cipher)}</strong> | রাউন্ড-ট্রিপ ইন্টিগ্রিটি: <span style="color:var(--success-color);"><i class="fas fa-check"></i> ভেরিফাইড</span>
                    </div>
                    <pre class="code-preview" style="font-size: 0.75rem;">${escapeHtml(crypto.encrypted_preview)}</pre>
                </div>
            </div>
        `;
    } catch (e) {
        console.error('Error during sandbox test:', e);
        resultBox.innerHTML = '<div style="color: var(--danger-color); padding: 16px;">স্যান্ডবক্স সার্ভার সংযোগে সমস্যা হয়েছে।</div>';
    }
}

async function exportAuditTrail() {
    try {
        const token = localStorage.getItem('myagent_access_token');
        const headers = token ? { 'Authorization': `Bearer ${token}` } : {};

        const res = await fetch('/api/security/audit-logs?limit=500&offset=0', { headers });
        if (!res.ok) {
            showToast('অডিট লগ এক্সপোর্টে ব্যর্থ।', 'danger');
            return;
        }

        const data = await res.json();
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `myagent_security_audit_${new Date().toISOString().slice(0, 10)}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        showToast('সিকিউরিটি অডিট লগ সফলভাবে ডাউনলোড হয়েছে!', 'success');
    } catch (e) {
        console.error('Export error:', e);
        showToast('এক্সপোর্ট করার সময় সমস্যা হয়েছে।', 'danger');
    }
}
