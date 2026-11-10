/* ==============================================================================
 * Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
 * Made By Arif (https://arifmahmud.com/)
 * Project: MyAgent | Version: 3.0.0
 * ============================================================================== */

// Model Context Protocol (MCP) and Local Open Source Tools Management

let allMcpServers = [];
let allDiscoveredTools = [];
let myAgentMcpStatus = null;
let activeMcpConfigTab = 'antigravity';
let allProjects = [];
let activeProjectName = 'myagent';
let activeProjectMemories = [];

async function loadMcpDashboard() {
  await Promise.all([
    loadMyAgentMcpServerStatus(),
    loadProjectMemoryVault(),
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
  ['antigravity', 'claude', 'cursor', 'chatgpt', 'openclaw', 'stdio'].forEach(t => {
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

  if (activeMcpConfigTab === 'antigravity') {
    const config = {
      "mcpServers": {
        "myagent_docker": {
          "url": sseUrl
        }
      }
    };
    preview.innerText = JSON.stringify(config, null, 2);
    if (hint) {
      hint.innerHTML = `💡 <strong>Google Antigravity IDE:</strong> সেটিংসে <code>~/.gemini/antigravity/mcp_servers.json</code> ফাইলে অথবা IDE Settings > MCP Servers-এ এই SSE URL কনফিগারেশনটি পেস্ট করুন।`;
    }
  } else if (activeMcpConfigTab === 'claude') {
    const config = {
      "mcpServers": {
        "myagent_docker": {
          "url": sseUrl
        }
      }
    };
    preview.innerText = JSON.stringify(config, null, 2);
    if (hint) {
      hint.innerHTML = `💡 <strong>Claude Desktop:</strong> <code>%APPDATA%\\Claude\\claude_desktop_config.json</code> (Windows) অথবা <code>~/Library/Application Support/Claude/claude_desktop_config.json</code> (macOS) ফাইলে সেভ করুন।`;
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
      hint.innerHTML = `💡 <strong>Cursor IDE:</strong> আপনার প্রজেক্ট রুটে <code>.cursor/mcp.json</code> ফাইলে অথবা Cursor Settings > Features > MCP > Add New MCP Server।`;
    }
  } else if (activeMcpConfigTab === 'chatgpt') {
    const config = {
      "mcpServers": {
        "myagent_docker": {
          "url": sseUrl
        }
      },
      "chatgpt_desktop": {
        "type": "sse",
        "url": sseUrl
      },
      "custom_gpt_action": {
        "openapi_schema_url": `http://${currentHost}/openapi.json`,
        "instructions": "In ChatGPT Custom GPTs > Actions > Import Schema from URL and enter http://192.168.9.9:3399/openapi.json"
      }
    };
    preview.innerText = JSON.stringify(config, null, 2);
    if (hint) {
      hint.innerHTML = `💡 <strong>ChatGPT / OpenAI:</strong> ChatGPT Desktop MCP সাপোর্টে উপরের JSON ব্যবহার করুন, অথবা Custom GPTs Actions-এ <code>http://${currentHost}/openapi.json</code> ইমপোর্ট করে সরাসরি এজেন্টের সকল টুল ব্যবহার করুন।`;
    }
  } else if (activeMcpConfigTab === 'openclaw') {
    const config = {
      "mcpServers": {
        "myagent_docker": {
          "url": sseUrl,
          "disabled": false,
          "autoApprove": [
            "ping_network_diagnostics",
            "query_company_memory",
            "python_runner"
          ]
        }
      }
    };
    preview.innerText = JSON.stringify(config, null, 2);
    if (hint) {
      hint.innerHTML = `💡 <strong>OpenClaw / Cline / Roo Code / LibreChat:</strong> এক্সটেনশন সেটিংসে <code>mcp_settings.json</code> ফাইলে এই কনফিগারেশনটি পেস্ট করুন।`;
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
  } else if (testType === 'get_project') {
    payload = {
      jsonrpc: "2.0",
      id: Date.now(),
      method: "tools/call",
      params: {
        name: "get_project_info",
        arguments: { project_name: activeProjectName || "myagent" }
      }
    };
  } else if (testType === 'save_project_mem') {
    payload = {
      jsonrpc: "2.0",
      id: Date.now(),
      method: "tools/call",
      params: {
        name: "save_project_memory",
        arguments: {
          project_name: activeProjectName || "myagent",
          key: "mcp_quick_test",
          category: "architecture",
          context: "production",
          content: "Sample architectural checkpoint saved via MyAgent MCP Server testing console."
        }
      }
    };
  } else if (testType === 'enhance_prompt') {
    payload = {
      jsonrpc: "2.0",
      id: Date.now(),
      method: "tools/call",
      params: {
        name: "enhance_prompt",
        arguments: {
          prompt: "Build a fast REST API with user login and SQLite database.",
          mode: "architect"
        }
      }
    };
  } else if (testType === 'port_scan') {
    payload = {
      jsonrpc: "2.0",
      id: Date.now(),
      method: "tools/call",
      params: {
        name: "network_port_scan",
        arguments: { target: "192.168.9.9" }
      }
    };
  } else if (testType === 'list_skills') {
    payload = {
      jsonrpc: "2.0",
      id: Date.now(),
      method: "tools/call",
      params: {
        name: "list_available_skills",
        arguments: {}
      }
    };
  } else if (testType === 'prompts/list') {
    payload = {
      jsonrpc: "2.0",
      id: Date.now(),
      method: "prompts/list",
      params: {}
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
    if (testType === 'save_project_mem') {
      loadActiveProjectMemories();
    }
  } catch (err) {
    out.innerText = `MCP টেস্ট ত্রুটি: ${err.message}`;
    showToast(`টেস্ট ত্রুটি: ${err.message}`, 'error');
  }
}

// ==============================================================================
// Per-Project Information & Hierarchical Memory Vault Management
// ==============================================================================

async function loadProjectMemoryVault() {
  try {
    const res = await fetch('/api/mcp/projects', {
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {}
    });
    if (!res.ok) return;
    allProjects = await res.json();

    if (allProjects.length > 0) {
      if (!allProjects.some(p => p.name === activeProjectName)) {
        activeProjectName = allProjects[0].name;
      }
    }

    renderProjectPills();
    const activeProj = allProjects.find(p => p.name === activeProjectName);
    if (activeProj) {
      renderProjectDetails(activeProj);
      await loadActiveProjectMemories();
    }
  } catch (err) {
    console.error('Error loading project memory vault:', err);
  }
}

function renderProjectPills() {
  const container = document.getElementById('project-pills-container');
  if (!container) return;

  container.innerHTML = allProjects.map(p => {
    const isActive = p.name === activeProjectName;
    return `
      <button class="mcp-tab-btn ${isActive ? 'active' : ''}" 
              onclick="selectProject('${escapeHtml(p.name)}')"
              style="display:inline-flex; align-items:center; gap:6px;">
        <span>📁 ${escapeHtml(p.name)}</span>
        <span style="font-size:0.7rem; opacity:0.8; background:rgba(255,255,255,0.1); border-radius:10px; padding:1px 6px;">
          ${p.memories_count || 0}
        </span>
      </button>
    `;
  }).join('');
}

async function selectProject(name) {
  activeProjectName = name;
  renderProjectPills();
  const proj = allProjects.find(p => p.name === name);
  if (proj) {
    renderProjectDetails(proj);
    await loadActiveProjectMemories();
  }
}

function renderProjectDetails(proj) {
  const title = document.getElementById('proj-card-title');
  const desc = document.getElementById('proj-card-desc');
  const status = document.getElementById('proj-card-status');
  const count = document.getElementById('proj-card-count');
  const tech = document.getElementById('proj-card-tech');
  const urls = document.getElementById('proj-card-urls');
  const blueprint = document.getElementById('proj-card-blueprint');

  if (title) title.innerText = proj.display_name || proj.name;
  if (desc) desc.innerText = proj.description || 'কোনো বিবরণ নেই';
  if (status) status.innerText = proj.status || 'active';
  if (count) count.innerText = `${proj.memories_count || 0}টি মেমোরি`;

  if (tech) {
    if (typeof proj.tech_stack === 'object') {
      tech.innerText = Object.entries(proj.tech_stack).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`).join('\n');
    } else {
      tech.innerText = proj.tech_stack || 'N/A';
    }
  }

  if (urls) {
    if (typeof proj.urls === 'object') {
      urls.innerText = Object.entries(proj.urls).map(([k, v]) => `${k}: ${v}`).join('\n');
    } else {
      urls.innerText = proj.urls || 'N/A';
    }
  }

  if (blueprint) {
    blueprint.innerText = proj.architecture_blueprint || 'কোনো আর্কিটেকচার ব্লুপ্রিন্ট সংরক্ষিত নেই।';
  }
}

async function loadActiveProjectMemories() {
  const listContainer = document.getElementById('project-memories-list');
  if (!listContainer || !activeProjectName) return;

  try {
    const res = await fetch(`/api/mcp/projects/${encodeURIComponent(activeProjectName)}/memories`, {
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {}
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    activeProjectMemories = await res.json();
    renderProjectMemoriesList(activeProjectMemories);
  } catch (err) {
    listContainer.innerHTML = `<div style="padding:14px; color:var(--rose-red); text-align:center;">মেমোরি লোড করতে ত্রুটি: ${escapeHtml(err.message)}</div>`;
  }
}

function renderProjectMemoriesList(mems) {
  const listContainer = document.getElementById('project-memories-list');
  if (!listContainer) return;

  if (!mems || mems.length === 0) {
    listContainer.innerHTML = `
      <div style="padding:24px; text-align:center; background:rgba(255,255,255,0.01); border:1px dashed var(--border-subtle); border-radius:8px; color:var(--text-muted); font-size:0.85rem;">
        এই প্রজেক্টে এখনও কোনো মেমোরি সেভ করা হয়নি।
        <div style="margin-top:8px;">
          <button class="btn-sm-action" onclick="openAddProjectMemoryModal()">+ প্রথম মেমোরি সেভ করুন</button>
        </div>
      </div>
    `;
    return;
  }

  listContainer.innerHTML = mems.map(m => {
    const tagsArr = Array.isArray(m.tags) ? m.tags : [];
    return `
      <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-subtle); border-radius:8px; padding:12px 14px; transition:border-color 0.2s ease;">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:8px;">
          <div style="display:flex; align-items:center; gap:8px;">
            <code style="font-weight:700; color:var(--cyan-glow); font-size:0.88rem; background:rgba(6,182,212,0.1); padding:2px 8px; border-radius:4px;">
              ${escapeHtml(m.key)}
            </code>
            <span class="badge-tag" style="background:rgba(168,85,247,0.15); color:var(--purple-neon); font-size:0.72rem;">
              ${escapeHtml(m.category)}
            </span>
            <span class="badge-tag" style="background:rgba(255,255,255,0.05); color:var(--text-muted); font-size:0.72rem;">
              ${escapeHtml(m.context)}
            </span>
          </div>
          <div style="display:flex; align-items:center; gap:8px;">
            <span style="font-size:0.72rem; color:var(--text-muted);">${m.updated_at || ''}</span>
            <button class="btn-sm-action" style="padding:2px 6px; font-size:0.72rem; color:var(--rose-red); border-color:rgba(244,63,94,0.3);" 
                    onclick="deleteProjectMemoryItem('${escapeHtml(m.project_name)}', '${escapeHtml(m.key)}')">
              🗑️
            </button>
          </div>
        </div>

        <div style="margin-top:6px; font-size:0.83rem; color:#f1f5f9; font-weight:600;">
          ${escapeHtml(m.title || m.key)}
        </div>

        <pre style="margin-top:6px; background:rgba(0,0,0,0.4); border-radius:6px; padding:8px 10px; font-family:monospace; font-size:0.78rem; color:#cbd5e1; white-space:pre-wrap; max-height:120px; overflow-y:auto; line-height:1.4;">${escapeHtml(m.content)}</pre>

        ${tagsArr.length > 0 ? `
          <div style="display:flex; gap:4px; flex-wrap:wrap; margin-top:8px;">
            ${tagsArr.map(t => `<span style="font-size:0.7rem; background:rgba(255,255,255,0.04); color:var(--text-muted); padding:1px 6px; border-radius:4px;">#${escapeHtml(t)}</span>`).join('')}
          </div>
        ` : ''}
      </div>
    `;
  }).join('');
}

function filterProjectMemories() {
  const cat = document.getElementById('proj-mem-cat-filter')?.value.toLowerCase();
  const search = document.getElementById('proj-mem-search')?.value.toLowerCase().trim();
  const badge = document.getElementById('proj-mem-filter-badge');

  let filtered = activeProjectMemories;
  if (cat) {
    filtered = filtered.filter(m => (m.category || '').toLowerCase() === cat);
  }
  if (search) {
    filtered = filtered.filter(m => 
      (m.key || '').toLowerCase().includes(search) ||
      (m.title || '').toLowerCase().includes(search) ||
      (m.content || '').toLowerCase().includes(search) ||
      (Array.isArray(m.tags) && m.tags.some(t => t.toLowerCase().includes(search)))
    );
  }

  if (badge) {
    badge.innerText = `${filtered.length}টি মেমোরি`;
  }
  renderProjectMemoriesList(filtered);
}

// Add/Edit Project Modal Handlers
function openAddProjectModal() {
  document.getElementById('add-project-form').reset();
  document.getElementById('add-project-modal-title').innerText = '🏢 নতুন প্রজেক্ট ইনফরমেশন যুক্ত করুন';
  document.getElementById('add-project-modal').style.display = 'flex';
}

function openEditCurrentProjectModal() {
  const proj = allProjects.find(p => p.name === activeProjectName);
  if (!proj) return;

  document.getElementById('add-project-modal-title').innerText = `🏢 প্রজেক্ট এডিট: ${proj.name}`;
  document.getElementById('proj-input-name').value = proj.name;
  document.getElementById('proj-input-name').disabled = true;
  document.getElementById('proj-input-display').value = proj.display_name || '';
  document.getElementById('proj-input-desc').value = proj.description || '';
  document.getElementById('proj-input-tech').value = typeof proj.tech_stack === 'object' ? JSON.stringify(proj.tech_stack) : (proj.tech_stack || '');
  document.getElementById('proj-input-urls').value = typeof proj.urls === 'object' ? JSON.stringify(proj.urls) : (proj.urls || '');
  document.getElementById('proj-input-blueprint').value = proj.architecture_blueprint || '';

  document.getElementById('add-project-modal').style.display = 'flex';
}

function closeAddProjectModal() {
  document.getElementById('proj-input-name').disabled = false;
  document.getElementById('add-project-modal').style.display = 'none';
}

async function submitSaveProjectInfo(e) {
  e.preventDefault();
  const name = document.getElementById('proj-input-name').value.trim();
  const displayName = document.getElementById('proj-input-display').value.trim();
  const desc = document.getElementById('proj-input-desc').value.trim();
  const tech = document.getElementById('proj-input-tech').value.trim();
  const urls = document.getElementById('proj-input-urls').value.trim();
  const blueprint = document.getElementById('proj-input-blueprint').value.trim();

  if (!name || !desc) {
    showToast('প্রজেক্ট নাম ও বিবরণ আবশ্যক!', 'error');
    return;
  }

  try {
    const res = await fetch('/api/mcp/projects', {
      method: 'POST',
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name,
        display_name: displayName || name,
        description: desc,
        tech_stack: tech,
        urls: urls,
        architecture_blueprint: blueprint
      })
    });

    if (res.ok) {
      showToast(`প্রজেক্ট '${name}' সফলভাবে সংরক্ষিত হয়েছে!`, 'success');
      closeAddProjectModal();
      activeProjectName = name;
      await loadProjectMemoryVault();
    } else {
      const err = await res.json();
      showToast(`ত্রুটি: ${err.detail || 'সেভ ব্যর্থ'}`, 'error');
    }
  } catch (err) {
    showToast(`ত্রুটি: ${err.message}`, 'error');
  }
}

// Add/Edit Project Memory Modal Handlers
function openAddProjectMemoryModal() {
  document.getElementById('add-project-memory-form').reset();
  const projInput = document.getElementById('pm-input-project');
  if (projInput) projInput.value = activeProjectName || 'myagent';
  document.getElementById('add-project-memory-modal').style.display = 'flex';
}

function closeAddProjectMemoryModal() {
  document.getElementById('add-project-memory-modal').style.display = 'none';
}

async function submitSaveProjectMemory(e) {
  e.preventDefault();
  const projName = document.getElementById('pm-input-project').value.trim();
  const key = document.getElementById('pm-input-key').value.trim();
  const category = document.getElementById('pm-input-category').value;
  const context = document.getElementById('pm-input-context').value;
  const security = document.getElementById('pm-input-security').value;
  const title = document.getElementById('pm-input-title').value.trim();
  const content = document.getElementById('pm-input-content').value.trim();
  const tagsRaw = document.getElementById('pm-input-tags').value.trim();

  const tags = tagsRaw ? tagsRaw.split(',').map(t => t.trim()).filter(Boolean) : [];

  if (!projName || !key || !content) {
    showToast('প্রজেক্ট, কী এবং কনটেন্ট আবশ্যক!', 'error');
    return;
  }

  try {
    const res = await fetch(`/api/mcp/projects/${encodeURIComponent(projName)}/memories`, {
      method: 'POST',
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        key,
        content,
        title: title || key,
        category,
        context,
        tags,
        security_level: security
      })
    });

    if (res.ok) {
      showToast(`মেমোরি '${key}' সফলভাবে সংরক্ষিত হয়েছে!`, 'success');
      closeAddProjectMemoryModal();
      activeProjectName = projName;
      await loadProjectMemoryVault();
    } else {
      const err = await res.json();
      showToast(`ত্রুটি: ${err.detail || 'সেভ ব্যর্থ'}`, 'error');
    }
  } catch (err) {
    showToast(`ত্রুটি: ${err.message}`, 'error');
  }
}

async function deleteProjectMemoryItem(projName, key) {
  if (!confirm(`আপনি কি নিশ্চিত যে প্রজেক্ট '${projName}' থেকে মেমোরি '${key}' মুছে ফেলতে চান?`)) return;

  try {
    const res = await fetch(`/api/mcp/projects/${encodeURIComponent(projName)}/memories/${encodeURIComponent(key)}`, {
      method: 'DELETE',
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {}
    });
    if (res.ok) {
      showToast(`মেমোরি '${key}' সফলভাবে মুছে ফেলা হয়েছে!`, 'success');
      await loadProjectMemoryVault();
    } else {
      showToast('মুছতে ব্যর্থ হয়েছে।', 'error');
    }
  } catch (err) {
    showToast(`ত্রুটি: ${err.message}`, 'error');
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
