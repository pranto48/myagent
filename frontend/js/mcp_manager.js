/* ==============================================================================
 * Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
 * Made By Arif (https://arifmahmud.com/)
 * Project: MyAgent | Version: 3.0.0
 * ============================================================================== */

// Model Context Protocol (MCP) and Local Open Source Tools Management

let allMcpServers = [];
let allDiscoveredTools = [];
let myAgentMcpStatus = null;
let activeMcpConfigTab = 'claude';

async function loadMcpDashboard() {
  await Promise.all([
    loadMyAgentMcpServerStatus(),
    loadMcpServers(),
    loadAllToolsRegistry()
  ]);
}

// Load MyAgent Built-in MCP Server Status & Configs
async function loadMyAgentMcpServerStatus() {
  try {
    const res = await fetch('/api/mcp/server/status', {
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {}
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    myAgentMcpStatus = await res.json();
    renderMyAgentMcpServerStatus(myAgentMcpStatus);
  } catch (err) {
    console.error('Error loading MyAgent MCP Server status:', err);
  }
}

function renderMyAgentMcpServerStatus(status) {
  if (!status) return;

  const badge = document.getElementById('mcp-server-status-badge');
  const toggleBtn = document.getElementById('mcp-server-toggle-btn');
  const kpiProto = document.getElementById('mcp-kpi-proto');
  const kpiTools = document.getElementById('mcp-kpi-tools');
  const kpiHost = document.getElementById('mcp-kpi-host');
  const sseCode = document.getElementById('mcp-endpoint-sse');
  const rpcCode = document.getElementById('mcp-endpoint-rpc');

  const isEnabled = status.is_enabled;
  if (badge) {
    if (isEnabled) {
      badge.style.background = 'rgba(16,185,129,0.2)';
      badge.style.color = '#6ee7b7';
      badge.style.borderColor = 'rgba(16,185,129,0.4)';
      badge.innerText = '🟢 সক্রিয় (Online)';
    } else {
      badge.style.background = 'rgba(239,68,68,0.2)';
      badge.style.color = '#fca5a5';
      badge.style.borderColor = 'rgba(239,68,68,0.4)';
      badge.innerText = '🔴 নিষ্ক্রিয় (Offline)';
    }
  }

  if (toggleBtn) {
    toggleBtn.innerText = isEnabled ? '⚡ সার্ভার বন্ধ করুন' : '⚡ সার্ভার চালু করুন';
    toggleBtn.style.color = isEnabled ? 'var(--rose-red)' : 'var(--emerald-green)';
    toggleBtn.style.borderColor = isEnabled ? 'rgba(244,63,94,0.4)' : 'rgba(16,185,129,0.4)';
  }

  if (kpiProto) kpiProto.innerText = status.protocol_version || 'MCP 2024-11-05';
  if (kpiTools) kpiTools.innerText = `${status.tools_count || 18}+ টুলস রেডি`;
  if (kpiHost) kpiHost.innerText = status.server_host || window.location.host;

  if (sseCode && status.endpoints?.sse) {
    sseCode.innerText = status.endpoints.sse;
  }
  if (rpcCode && status.endpoints?.rpc) {
    rpcCode.innerText = status.endpoints.rpc;
  }

  // Update configuration code preview
  updateMcpConfigCodePreview();
}

async function toggleMyAgentMcpServer() {
  const current = myAgentMcpStatus?.is_enabled ?? true;
  const target = !current;

  try {
    const res = await fetch('/api/mcp/server/toggle', {
      method: 'POST',
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_enabled: target })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    showToast(target ? 'MyAgent MCP সার্ভার সক্রিয় করা হয়েছে!' : 'MyAgent MCP সার্ভার নিষ্ক্রিয় করা হয়েছে!', 'info');
    await loadMyAgentMcpServerStatus();
  } catch (err) {
    showToast(`টগল ত্রুটি: ${err.message}`, 'error');
  }
}

function switchMcpConfigTab(tabName) {
  activeMcpConfigTab = tabName;
  ['claude', 'cursor', 'antigravity', 'stdio'].forEach(t => {
    const btn = document.getElementById(`mcp-btn-tab-${t}`);
    if (btn) {
      if (t === tabName) btn.classList.add('active');
      else btn.classList.remove('active');
    }
  });
  updateMcpConfigCodePreview();
}

function updateMcpConfigCodePreview() {
  const preview = document.getElementById('mcp-config-code-preview');
  const hint = document.getElementById('mcp-config-path-hint');
  if (!preview) return;

  const currentHost = window.location.host || '192.168.9.9:3399';
  const sseUrl = `http://${currentHost}/api/mcp/server/sse`;
  const rpcUrl = `http://${currentHost}/api/mcp/server/rpc`;

  if (activeMcpConfigTab === 'claude') {
    const config = {
      "mcpServers": {
        "myagent_docker": {
          "url": sseUrl
        }
      }
    };
    preview.innerText = JSON.stringify(config, null, 2);
    if (hint) {
      hint.innerHTML = `💡 <strong>ফাইল লোকেশন:</strong> <code>%APPDATA%\\Claude\\claude_desktop_config.json</code> (Windows) অথবা <code>~/Library/Application Support/Claude/claude_desktop_config.json</code> (macOS)`;
    }
  } else if (activeMcpConfigTab === 'cursor') {
    const config = {
      "mcpServers": {
        "myagent-docker": {
          "url": sseUrl
        }
      }
    };
    preview.innerText = JSON.stringify(config, null, 2);
    if (hint) {
      hint.innerHTML = `💡 <strong>ফাইল লোকেশন:</strong> আপনার প্রজেক্ট রুটে <code>.cursor/mcp.json</code> অথবা Cursor Settings > Features > MCP > Add New MCP Server.`;
    }
  } else if (activeMcpConfigTab === 'antigravity') {
    const config = {
      "mcpServers": {
        "myagent_docker": {
          "url": sseUrl
        }
      }
    };
    preview.innerText = JSON.stringify(config, null, 2);
    if (hint) {
      hint.innerHTML = `💡 <strong>ফাইল লোকেশন:</strong> Google Antigravity IDE Settings / <code>~/.gemini/antigravity/mcp_servers.json</code> (SSE Transport).`;
    }
  } else if (activeMcpConfigTab === 'stdio') {
    const config = {
      "mcpServers": {
        "myagent_bridge": {
          "command": "python",
          "args": [
            "-c",
            `import sys, urllib.request, json; [print(urllib.request.urlopen(urllib.request.Request('${rpcUrl}', data=l.encode('utf-8'), headers={'Content-Type':'application/json'})).read().decode('utf-8'), flush=True) for l in sys.stdin if l.strip()]`
          ]
        }
      }
    };
    preview.innerText = JSON.stringify(config, null, 2);
    if (hint) {
      hint.innerHTML = `💡 <strong>Stdio ব্রিজ:</strong> যেসকল ক্লায়েন্ট শুধুমাত্র Stdio সাব-প্রসেস সাপোর্ট করে, তারা এই কমান্ড দিয়ে সরাসরি MyAgent ডকার অ্যাপের সাথে সংযুক্ত হতে পারবে।`;
    }
  }
}

function copyActiveMcpConfig() {
  const preview = document.getElementById('mcp-config-code-preview');
  if (!preview) return;
  copyToClipboardText(preview.innerText, `${activeMcpConfigTab.toUpperCase()} কনফিগারেশন ক্লিপবোর্ডে কপি করা হয়েছে!`);
}

function copyToClipboardText(text, successMsg) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(() => {
      showToast(successMsg || 'কপি করা হয়েছে!', 'success');
    }).catch(() => {
      fallbackCopy(text, successMsg);
    });
  } else {
    fallbackCopy(text, successMsg);
  }
}

function fallbackCopy(text, successMsg) {
  const ta = document.createElement('textarea');
  ta.value = text;
  document.body.appendChild(ta);
  ta.select();
  document.execCommand('copy');
  document.body.removeChild(ta);
  showToast(successMsg || 'কপি করা হয়েছে!', 'success');
}

async function runMyAgentMcpTest(testType) {
  const out = document.getElementById('myagent-mcp-test-output');
  if (!out) return;

  out.innerText = `[${testType}] রিকোয়েস্ট পাঠানো হচ্ছে...`;

  let payload = {};
  if (testType === 'initialize') {
    payload = {
      jsonrpc: "2.0",
      id: Date.now(),
      method: "initialize",
      params: {
        protocolVersion: "2024-11-05",
        capabilities: {},
        clientInfo: { name: "WebTester", version: "3.1.0" }
      }
    };
  } else if (testType === 'tools/list') {
    payload = {
      jsonrpc: "2.0",
      id: Date.now(),
      method: "tools/list",
      params: {}
    };
  } else if (testType === 'ping_host') {
    payload = {
      jsonrpc: "2.0",
      id: Date.now(),
      method: "tools/call",
      params: {
        name: "ping_network_diagnostics",
        arguments: { target: "192.168.9.1", count: 2 }
      }
    };
  } else if (testType === 'query_memory') {
    payload = {
      jsonrpc: "2.0",
      id: Date.now(),
      method: "tools/call",
      params: {
        name: "query_company_memory",
        arguments: { query: "Company guidelines and policies", top_k: 2 }
      }
    };
  }

  try {
    const res = await fetch('/api/mcp/server/rpc', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    out.innerText = JSON.stringify(data, null, 2);
    showToast('MCP টেস্ট সফল হয়েছে!', 'success');
  } catch (err) {
    out.innerText = `MCP টেস্ট ত্রুটি: ${err.message}`;
    showToast(`টেস্ট ত্রুটি: ${err.message}`, 'error');
  }
}

// Fetch all registered MCP servers
async function loadMcpServers() {
  const container = document.getElementById('mcp-servers-grid');
  if (!container) return;

  try {
    const res = await fetch('/api/mcp/servers', {
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {}
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    allMcpServers = await res.json();
    renderMcpServers(allMcpServers);
  } catch (err) {
    container.innerHTML = `
      <div style="grid-column: 1/-1; padding: 24px; text-align: center; color: var(--rose-red);">
        MCP সার্ভার লোড করতে ত্রুটি: ${escapeHtml(err.message)}
      </div>
    `;
  }
}

// Render MCP Server cards
function renderMcpServers(servers) {
  const container = document.getElementById('mcp-servers-grid');
  if (!container) return;

  if (!servers || servers.length === 0) {
    container.innerHTML = `
      <div style="grid-column: 1/-1; padding: 40px 20px; text-align: center; background: rgba(255,255,255,0.02); border-radius: 12px; border: 1px dashed var(--border-color);">
        <div style="font-size: 2rem; margin-bottom: 8px;">🔌</div>
        <div style="font-weight: 600; color: white; margin-bottom: 4px;">${typeof t === 'function' ? t('mcp_no_servers', 'কোনো MCP সার্ভার নিবন্ধিত নেই') : 'কোনো MCP সার্ভার নিবন্ধিত নেই'}</div>
        <div style="color: var(--text-muted); font-size: 0.85rem; margin-bottom: 16px;">
          ${typeof t === 'function' ? t('mcp_servers_desc', 'নিচের ১-ক্লিক ওপেন সোর্স টেমপ্লেট ব্যবহার করে অথবা নতুন সার্ভার যুক্ত করুন।') : 'নিচের ১-ক্লিক ওপেন সোর্স টেমপ্লেট ব্যবহার করে অথবা নতুন সার্ভার যুক্ত করুন।'}
        </div>
        <button class="btn-primary" onclick="openAddMcpModal()">+ ${typeof t === 'function' ? t('mcp_btn_add_custom', 'নতুন MCP সার্ভার যোগ করুন') : 'নতুন MCP সার্ভার যোগ করুন'}</button>
      </div>
    `;
    return;
  }

  container.innerHTML = servers.map(s => {
    const isConn = s.status === 'connected';
    const isErr = s.status === 'error';
    const statusColor = isConn ? 'var(--emerald-green)' : (isErr ? 'var(--rose-red)' : 'var(--amber-yellow)');
    const statusText = isConn 
      ? (typeof t === 'function' ? t('mcp_status_connected', 'সংযুক্ত (Connected)') : 'সংযুক্ত (Connected)') 
      : (isErr 
        ? (typeof t === 'function' ? t('mcp_status_disconnected', 'সংযোগ বিচ্ছিন্ন') : 'সংযোগ বিচ্ছিন্ন') 
        : (typeof t === 'function' ? t('mcp_status_ready', 'প্রস্তুত (Ready)') : 'প্রস্তুত (Ready)'));
    const pingBadge = s.last_ping_ms >= 0 ? `${s.last_ping_ms} ms` : 'N/A';
    const toolCount = (s.tools_cache || []).length;

    return `
      <div class="mcp-server-card">
        <div class="mcp-card-header">
          <div style="display:flex; align-items:center; gap:10px;">
            <div class="mcp-icon-badge">${s.transport === 'stdio' ? '💻' : '🌐'}</div>
            <div>
              <div class="mcp-server-name">${escapeHtml(s.name)}</div>
              <div class="mcp-server-meta">
                <span class="badge-tag">${escapeHtml(s.transport.toUpperCase())}</span>
                <span class="badge-tag" style="background:rgba(255,255,255,0.06); color:var(--text-muted);">${s.id}</span>
              </div>
            </div>
          </div>
          <div style="text-align:right;">
            <div style="display:inline-flex; align-items:center; gap:6px; font-size:0.75rem; color:${statusColor}; font-weight:600;">
              <span style="width:7px; height:7px; border-radius:50%; background:${statusColor}; display:inline-block;"></span>
              ${statusText}
            </div>
            <div style="font-size:0.72rem; color:var(--text-muted); margin-top:2px;">পিং: <strong>${pingBadge}</strong></div>
          </div>
        </div>

        <div class="mcp-card-body">
          ${s.transport === 'sse' 
            ? `<div class="mcp-code-preview">URL: ${escapeHtml(s.url || 'কোনো URL নেই')}</div>` 
            : `<div class="mcp-code-preview">CMD: ${escapeHtml(s.command)} ${(s.args || []).join(' ')}</div>`
          }
          <div style="display:flex; justify-content:space-between; align-items:center; margin-top:12px; font-size:0.8rem;">
            <span style="color:var(--text-muted);">${typeof t === 'function' ? t('mcp_discovered_tools', 'ডিসকভার্ড টুলস:') : 'ডিসকভার্ড টুলস:'}</span>
            <span style="color:var(--cyan-glow); font-weight:600; cursor:pointer;" onclick="viewMcpTools('${s.id}')">
              🛠️ ${toolCount}${typeof t === 'function' ? t('mcp_view_tools_btn', 'টি টুলস দেখুন') : 'টি টুলস দেখুন'}
            </span>
          </div>
        </div>

        <div class="mcp-card-actions">
          <button class="btn-sm-action" onclick="pingMcpServer('${s.id}')" title="${typeof t === 'function' ? t('mcp_ping_title', 'পিং ও টুলস রিফ্রেশ') : 'পিং ও টুলস রিফ্রেশ'}">
            ⚡ ${typeof t === 'function' ? t('mcp_btn_ping', 'পিং টেস্ট') : 'পিং টেস্ট'}
          </button>
          <button class="btn-sm-action" onclick="viewMcpTools('${s.id}')" title="${typeof t === 'function' ? t('mcp_tools_title', 'টুলস স্কিমা দেখুন') : 'টুলস স্কিমা দেখুন'}">
            🔍 ${typeof t === 'function' ? t('mcp_btn_tools', 'টুলস') : 'টুলস'}
          </button>
          <button class="btn-sm-action" style="color:var(--rose-red); border-color:rgba(244,63,94,0.3);" onclick="deleteMcpServer('${s.id}')" title="${typeof t === 'function' ? t('btn_delete', 'মুছে ফেলুন') : 'মুছে ফেলুন'}">
            🗑️ ${typeof t === 'function' ? t('btn_delete', 'ডিলিট') : 'ডিলিট'}
          </button>
        </div>
      </div>
    `;
  }).join('');
}

// Ping an MCP Server
async function pingMcpServer(serverId) {
  showToast(`MCP সার্ভার '${serverId}' পিং করা হচ্ছে...`, 'info');
  try {
    const res = await fetch(`/api/mcp/servers/${serverId}/ping`, {
      method: 'POST',
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {}
    });
    const data = await res.json();
    if (res.ok && data.success) {
      showToast(`সফল সংযোগ! ল্যাটেন্সি: ${data.latency_ms} ms (${(data.tools || []).length}টি টুলস পাওয়া গেছে)`, 'success');
      loadMcpServers();
      loadAllToolsRegistry();
    } else {
      showToast(`পিং ব্যর্থ: ${data.message || 'ত্রুটি'}`, 'error');
      loadMcpServers();
    }
  } catch (err) {
    showToast(`ত্রুটি: ${err.message}`, 'error');
  }
}

// View Tools of an MCP Server
async function viewMcpTools(serverId) {
  const server = allMcpServers.find(s => s.id === serverId);
  if (!server) return;

  const modal = document.getElementById('mcp-tools-modal');
  const title = document.getElementById('mcp-tools-modal-title');
  const body = document.getElementById('mcp-tools-modal-body');

  const isEn = typeof currentLang !== 'undefined' && currentLang === 'en';
  title.innerText = isEn 
    ? `Tools Explorer: ${server.name} (${(server.tools_cache || []).length} tools)` 
    : `টুলস এক্সপ্লোরার: ${server.name} (${(server.tools_cache || []).length}টি টুল)`;

  if (!server.tools_cache || server.tools_cache.length === 0) {
    body.innerHTML = `
      <div style="padding:30px; text-align:center; color:var(--text-muted);">
        ${typeof t === 'function' ? t('mcp_no_active_tools', 'কোনো সক্রিয় টুল পাওয়া যায়নি।') : 'কোনো সক্রিয় টুল পাওয়া যায়নি।'}
      </div>
    `;
  } else {
    body.innerHTML = server.tools_cache.map(tItem => `
      <div style="background:rgba(255,255,255,0.03); border:1px solid var(--border-color); border-radius:8px; padding:14px; margin-bottom:12px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
          <strong style="color:var(--cyan-glow); font-family:monospace; font-size:0.95rem;">${escapeHtml(tItem.name)}</strong>
          <span class="badge-tag">MCP Tool</span>
        </div>
        <p style="color:var(--text-muted); font-size:0.85rem; margin-bottom:8px;">${escapeHtml(tItem.description || 'No description provided')}</p>
        <details style="font-size:0.75rem;">
          <summary style="cursor:pointer; color:var(--purple-neon);">${typeof t === 'function' ? t('mcp_input_schema', 'ইনপুট স্কিমা (JSON Schema)') : 'ইনপুট স্কিমা (JSON Schema)'}</summary>
          <pre style="background:rgba(0,0,0,0.4); padding:8px; border-radius:6px; overflow-x:auto; margin-top:6px;">${escapeHtml(JSON.stringify(tItem.inputSchema || {}, null, 2))}</pre>
        </details>
      </div>
    `).join('');
  }

  modal.style.display = 'flex';
}

function closeMcpToolsModal() {
  document.getElementById('mcp-tools-modal').style.display = 'none';
}

// Delete an MCP Server
async function deleteMcpServer(serverId) {
  if (!confirm(`আপনি কি নিশ্চিত যে আপনি MCP সার্ভার '${serverId}' মুছে ফেলতে চান?`)) return;

  try {
    const res = await fetch(`/api/mcp/servers/${serverId}`, {
      method: 'DELETE',
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {}
    });
    if (res.ok) {
      showToast('MCP সার্ভার সফলভাবে মুছে ফেলা হয়েছে!', 'success');
      loadMcpServers();
      loadAllToolsRegistry();
    } else {
      showToast('মুছতে ব্যর্থ হয়েছে।', 'error');
    }
  } catch (err) {
    showToast(`ত্রুটি: ${err.message}`, 'error');
  }
}

// Open Add MCP Modal
function openAddMcpModal() {
  document.getElementById('add-mcp-form').reset();
  onMcpTransportChanged();
  document.getElementById('add-mcp-modal').style.display = 'flex';
}

function closeAddMcpModal() {
  document.getElementById('add-mcp-modal').style.display = 'none';
}

function onMcpTransportChanged() {
  const transport = document.getElementById('mcp-transport-select').value;
  const sseGroup = document.getElementById('mcp-sse-group');
  const stdioGroup = document.getElementById('mcp-stdio-group');

  if (transport === 'sse') {
    sseGroup.style.display = 'block';
    stdioGroup.style.display = 'none';
  } else {
    sseGroup.style.display = 'none';
    stdioGroup.style.display = 'block';
  }
}

// Submit New MCP Server
async function submitAddMcpServer(e) {
  e.preventDefault();
  const name = document.getElementById('mcp-name').value.trim();
  const transport = document.getElementById('mcp-transport-select').value;
  const url = document.getElementById('mcp-url').value.trim();
  const command = document.getElementById('mcp-command').value.trim();
  const argsRaw = document.getElementById('mcp-args').value.trim();

  let args = [];
  if (argsRaw) {
    args = argsRaw.split(' ').filter(a => a.trim().length > 0);
  }

  if (!name) {
    showToast('নাম আবশ্যক।', 'error');
    return;
  }

  const payload = {
    name,
    transport,
    url: transport === 'sse' ? url : '',
    command: transport === 'stdio' ? command : '',
    args: transport === 'stdio' ? args : [],
    is_enabled: true
  };

  try {
    const res = await fetch('/api/mcp/servers', {
      method: 'POST',
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      showToast(`'${name}' MCP সার্ভার সফলভাবে নিবন্ধিত হয়েছে!`, 'success');
      closeAddMcpModal();
      loadMcpServers();
      loadAllToolsRegistry();
    } else {
      const err = await res.json();
      showToast(`যোগ করতে ব্যর্থ: ${err.detail || 'ত্রুটি'}`, 'error');
    }
  } catch (err) {
    showToast(`ত্রুটি: ${err.message}`, 'error');
  }
}

// Quick 1-Click MCP Templates
async function addQuickTemplate(templateKey) {
  let payload = null;
  if (templateKey === 'filesystem') {
    payload = {
      name: "Local Data Volume FileSystem",
      transport: "stdio",
      command: "python3",
      args: ["-c", "import sys; print('Ready')"],
      is_enabled: true
    };
  } else if (templateKey === 'sqlite') {
    payload = {
      name: "Corporate SQLite Database",
      transport: "stdio",
      command: "python3",
      args: ["-c", "import sys; print('Ready')"],
      is_enabled: true
    };
  } else if (templateKey === 'web-fetch') {
    payload = {
      name: "Live Web & Article Scraper MCP",
      transport: "sse",
      url: "http://127.0.0.1:8000/api/mcp/mock-sse",
      is_enabled: true
    };
  }

  if (!payload) return;

  try {
    const res = await fetch('/api/mcp/servers', {
      method: 'POST',
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      showToast(`টেমপ্লেট '${payload.name}' সফলভাবে যুক্ত হয়েছে!`, 'success');
      loadMcpServers();
      loadAllToolsRegistry();
    }
  } catch (err) {
    showToast(`ত্রুটি: ${err.message}`, 'error');
  }
}

// Load Combined Tools Registry (Builtin + MCP)
async function loadAllToolsRegistry() {
  const container = document.getElementById('builtin-tools-grid');
  const toolSelect = document.getElementById('sandbox-tool-select');

  try {
    const res = await fetch('/api/mcp/tools', {
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {}
    });
    if (!res.ok) return;

    const data = await res.json();
    allDiscoveredTools = data.tools || [];

    // Populate dropdown
    if (toolSelect) {
      toolSelect.innerHTML = allDiscoveredTools.map(t => `
        <option value="${escapeHtml(t.name)}">${escapeHtml(t.name)} (${t.source === 'builtin' ? 'Builtin' : 'MCP'})</option>
      `).join('');
    }

    // Populate Builtin Tools Grid
    if (container) {
      const builtinTools = allDiscoveredTools.filter(t => t.source === 'builtin');
      container.innerHTML = builtinTools.map(t => `
        <div class="tool-feature-card">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:6px;">
            <div style="font-weight:700; font-family:monospace; color:var(--cyan-glow); font-size:0.92rem;">
              ${escapeHtml(t.name)}
            </div>
            <span class="badge-tag" style="background:rgba(16,185,129,0.15); color:#6ee7b7;">${typeof t === 'function' ? t('status_online', 'সক্রিয়') : 'সক্রিয়'}</span>
          </div>
          <div style="font-size:0.82rem; color:var(--text-muted); line-height:1.5;">
            ${escapeHtml(t.description)}
          </div>
        </div>
      `).join('');
    }
  } catch (err) {
    console.error('Error loading tools registry:', err);
  }
}

// Run Manual Tool Test in Sandbox
async function runToolSandboxTest() {
  const toolName = document.getElementById('sandbox-tool-select').value;
  const argsText = document.getElementById('sandbox-tool-args').value.trim();
  const outputElem = document.getElementById('sandbox-tool-output');

  let args = {};
  if (argsText) {
    try {
      args = JSON.parse(argsText);
    } catch (err) {
      showToast('আর্গুমেন্ট অবশ্যই সঠিক JSON ফরম্যাটে হতে হবে!', 'error');
      return;
    }
  }

  const isEn = typeof currentLang !== 'undefined' && currentLang === 'en';
  outputElem.innerText = isEn ? `Executing tool '${toolName}'...` : `টুল '${toolName}' এক্সিকিউট করা হচ্ছে...`;

  try {
    const res = await fetch('/api/mcp/tools/execute', {
      method: 'POST',
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tool_name: toolName, arguments: args })
    });

    const data = await res.json();
    outputElem.innerText = data.output || JSON.stringify(data, null, 2);
  } catch (err) {
    outputElem.innerText = (isEn ? 'Execution Error: ' : 'এক্সিকিউশন ত্রুটি: ') + err.message;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  loadMcpDashboard();
});
