/* ==============================================================================
 * Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
 * Made By Arif (https://arifmahmud.com/)
 * Project: MyAgent | Version: 2.2.0
 * ============================================================================== */

// Main Application Logic, Mobile Drawer, Chat Streaming & UI Interactions

let currentSessionId = null;
let conversationHistory = [];
let useMemory = true;
let isGenerating = false;
let isStreaming = false;
let attachedChatFiles = [];
let currentChatAbortController = null;

function stopGenerating() {
  if (currentChatAbortController) {
    currentChatAbortController.abort();
    currentChatAbortController = null;
  }
  isGenerating = false;
  isStreaming = false;
  const sendBtn = document.getElementById('btn-send-message');
  if (sendBtn) {
    sendBtn.classList.remove('streaming-active');
    sendBtn.disabled = false;
    sendBtn.innerHTML = SEND_ICON_SVG;
    sendBtn.title = 'বার্তা পাঠান (Enter)';
  }
  attachChatEventListeners();
  showToast('উত্তর তৈরি বন্ধ করা হয়েছে।', 'info');
}

// Original Send Button SVG Icon
const SEND_ICON_SVG = `
  <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" style="pointer-events:none;">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
  </svg>
`;

const SPINNER_SVG = `
  <span class="spinner-inline" style="width:16px; height:16px; margin:0; border-width:2px; pointer-events:none;"></span>
`;

// Initialize on DOM Ready
document.addEventListener('DOMContentLoaded', () => {
  initApp();
});

async function initApp() {
  try {
    if (typeof checkAuthentication === 'function') {
      checkAuthentication();
    }
  } catch (e) {
    console.warn('Auth check notice:', e);
  }

  await loadServerStatus();
  await loadChatSessions();
  attachChatEventListeners();
  setupChatDragDropAndPaste();
}

/**
 * Loads server status, model name and updates status badge.
 */
async function loadServerStatus() {
  try {
    const res = await fetch('/api/status');
    if (res.ok) {
      const data = await res.json();
      const statusDot = document.getElementById('system-status-dot');
      const statusText = document.getElementById('agent-online-status');
      const sideModel = document.getElementById('sidebar-model-name');
      const topModelSelect = document.getElementById('topbar-model-select');

      if (statusDot) statusDot.style.background = '#10b981';
      if (statusText) statusText.innerText = 'অনলাইন';
      if (sideModel && data.llm_model) sideModel.innerText = data.llm_model;
      if (topModelSelect && data.llm_model) topModelSelect.value = data.llm_model;
    }
  } catch (e) {
    console.warn('Server status check notice:', e);
  }
}

/**
 * Ensures event listeners are actively attached to chat controls.
 */
function attachChatEventListeners() {
  const sendBtn = document.getElementById('btn-send-message');
  const chatInput = document.getElementById('chat-input');

  if (sendBtn) {
    sendBtn.onclick = function(e) {
      if (e) e.preventDefault();
      sendMessage();
    };
  }

  if (chatInput) {
    chatInput.onkeydown = function(e) {
      handleTextareaKey(e);
    };
    chatInput.oninput = function() {
      autoResizeTextarea(this);
    };
  }
}

// ==============================================================================
// Gemini / ChatGPT Style Chat File Attachment & Drag-Drop System
// ==============================================================================

function openChatFilePicker() {
  const fileInput = document.getElementById('chat-file-input');
  if (fileInput) {
    fileInput.click();
  }
}

function getFileBadgeIcon(filename) {
  const ext = (filename || '').split('.').pop().toLowerCase();
  if (['xlsx', 'xls', 'csv', 'tsv'].includes(ext)) return '📊';
  if (['png', 'jpg', 'jpeg', 'webp', 'bmp'].includes(ext)) return '📷';
  if (['pdf'].includes(ext)) return '📕';
  if (['docx', 'doc'].includes(ext)) return '📑';
  if (['txt', 'md', 'json', 'yaml', 'yml'].includes(ext)) return '📝';
  return '📎';
}

function getFileTypeClass(filename) {
  const ext = (filename || '').split('.').pop().toLowerCase();
  if (['xlsx', 'xls', 'csv', 'tsv'].includes(ext)) return 'type-excel';
  if (['png', 'jpg', 'jpeg', 'webp', 'bmp'].includes(ext)) return 'type-photo';
  if (['pdf'].includes(ext)) return 'type-pdf';
  if (['docx', 'doc'].includes(ext)) return 'type-word';
  return 'type-file';
}

function formatFileSize(bytes) {
  if (!bytes || bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function handleChatFilesSelected(files) {
  if (!files || files.length === 0) return;
  const newFiles = Array.from(files);

  for (const file of newFiles) {
    if (attachedChatFiles.some(f => f.name === file.name && f.size === file.size)) {
      continue;
    }
    const isImage = file.type.startsWith('image/');
    const previewUrl = isImage ? URL.createObjectURL(file) : null;
    attachedChatFiles.push({
      id: 'att_' + Math.random().toString(36).substring(2, 9),
      file: file,
      name: file.name,
      size: file.size,
      type: file.type,
      previewUrl: previewUrl,
      isImage: isImage
    });
  }

  renderAttachmentShelf();
  const fileInput = document.getElementById('chat-file-input');
  if (fileInput) fileInput.value = '';
}

function removeAttachedFile(fileId) {
  const index = attachedChatFiles.findIndex(f => f.id === fileId);
  if (index !== -1) {
    const item = attachedChatFiles[index];
    if (item.previewUrl) {
      URL.revokeObjectURL(item.previewUrl);
    }
    attachedChatFiles.splice(index, 1);
    renderAttachmentShelf();
  }
}

function renderAttachmentShelf() {
  const shelf = document.getElementById('chat-attachment-shelf');
  if (!shelf) return;

  if (attachedChatFiles.length === 0) {
    shelf.style.display = 'none';
    shelf.innerHTML = '';
    return;
  }

  shelf.style.display = 'flex';
  shelf.innerHTML = attachedChatFiles.map(item => {
    const typeClass = getFileTypeClass(item.name);
    const icon = getFileBadgeIcon(item.name);
    
    let visualEl = '';
    if (item.isImage && item.previewUrl) {
      visualEl = `<img src="${item.previewUrl}" alt="${escapeHtml(item.name)}" class="attachment-thumbnail">`;
    } else {
      visualEl = `<div class="attachment-icon-badge ${typeClass}">${icon}</div>`;
    }

    return `
      <div class="attachment-chip" id="chip-${item.id}">
        ${visualEl}
        <div class="attachment-details">
          <span class="attachment-name" title="${escapeHtml(item.name)}">${escapeHtml(item.name)}</span>
          <span class="attachment-size">${formatFileSize(item.size)}</span>
        </div>
        <button type="button" class="attachment-remove-btn" title="মুছে ফেলুন" onclick="removeAttachedFile('${item.id}')">&times;</button>
      </div>
    `;
  }).join('');
}

function setupChatDragDropAndPaste() {
  const chatArea = document.querySelector('.chat-section') || document.body;
  const overlay = document.getElementById('chat-drag-drop-overlay');

  let dragCounter = 0;

  window.addEventListener('dragenter', (e) => {
    // Only activate drag overlay if dragging files
    if (e.dataTransfer && e.dataTransfer.types && Array.from(e.dataTransfer.types).includes('Files')) {
      e.preventDefault();
      dragCounter++;
      if (overlay) overlay.style.display = 'flex';
    }
  });

  window.addEventListener('dragleave', (e) => {
    dragCounter--;
    if (dragCounter <= 0 && overlay) {
      dragCounter = 0;
      overlay.style.display = 'none';
    }
  });

  window.addEventListener('dragover', (e) => {
    if (e.dataTransfer && e.dataTransfer.types && Array.from(e.dataTransfer.types).includes('Files')) {
      e.preventDefault();
    }
  });

  window.addEventListener('drop', (e) => {
    if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      e.preventDefault();
      dragCounter = 0;
      if (overlay) overlay.style.display = 'none';
      handleChatFilesSelected(e.dataTransfer.files);
    }
  });

  // Paste handler for screenshots or copied images/files
  window.addEventListener('paste', (e) => {
    if (!e.clipboardData || !e.clipboardData.items) return;
    const items = e.clipboardData.items;
    const filesToUpload = [];

    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.kind === 'file') {
        const file = item.getAsFile();
        if (file) {
          let fileName = file.name;
          if (fileName === 'image.png' || !fileName) {
            fileName = `screenshot_${Date.now()}.png`;
          }
          const renamedFile = new File([file], fileName, { type: file.type });
          filesToUpload.push(renamedFile);
        }
      }
    }

    if (filesToUpload.length > 0) {
      handleChatFilesSelected(filesToUpload);
      showToast(`${filesToUpload.length}টি ফাইল ক্লিপবোর্ড থেকে সংযুক্ত করা হয়েছে`, 'info');
    }
  });
}

function toggleMemoryUsage() {
  const chk = document.getElementById('chk-use-memory');
  const text = document.getElementById('memory-toggle-text');
  if (chk) {
    chk.checked = !chk.checked;
    useMemory = chk.checked;
    if (text) {
      text.innerText = useMemory ? 'মেমোরি অন' : 'মেমোরি অফ';
    }
    showToast(useMemory ? 'কোম্পানি মেমোরি সার্চ সক্রিয়' : 'মেমোরি সার্চ বন্ধ', 'info');
  }
}

// Mobile Sidebar Drawer Toggle
function toggleMobileSidebar() {
  const sidebar = document.getElementById('main-sidebar');
  if (sidebar) {
    sidebar.classList.toggle('mobile-open');
  }
}

// Tab Switching across all views (including Full-Page Admin & Settings)
function switchTab(tabName) {
  const tabs = ['chat', 'admin', 'dashboard', 'users', 'knowledge', 'models', 'mcp', 'security', 'backup', 'settings'];
  tabs.forEach(t => {
    const view = document.getElementById(`view-${t}`);
    const btn = document.getElementById(`nav-${t}-btn`);
    if (view) view.classList.remove('active');
    if (btn) btn.classList.remove('active');
  });

  const activeView = document.getElementById(`view-${tabName}`);
  const activeBtn = document.getElementById(`nav-${tabName}-btn`);
  if (activeView) activeView.classList.add('active');
  if (activeBtn) activeBtn.classList.add('active');

  const topbarTitle = document.getElementById('topbar-title-text');
  const topbarDesc = document.getElementById('topbar-desc-text');

  // Close mobile sidebar after tab switch
  const sidebar = document.getElementById('main-sidebar');
  if (sidebar && sidebar.classList.contains('mobile-open')) {
    sidebar.classList.remove('mobile-open');
  }

  if (tabName === 'chat') {
    if (topbarTitle) topbarTitle.innerText = 'কোম্পানি ডেটা ইন্টেলিজেন্স এজেন্ট';
    if (topbarDesc) topbarDesc.innerText = 'ওপেনক্ল-স্টাইল পারসিসটেন্ট মেমোরি ও অটোনোমাস কোম্পানি এআই';
  } else if (tabName === 'admin') {
    if (topbarTitle) topbarTitle.innerText = 'অ্যাডমিন কমান্ড সেন্টার ও সিস্টেম কন্ট্রোল';
    if (topbarDesc) topbarDesc.innerText = 'সার্ভার হার্টবিট, ক্লাউড মেট্রিক্স ও ইনস্ট্যান্ট অ্যাডমিন অ্যাকশন হাব';
    if (typeof loadAdminDashboard === 'function') loadAdminDashboard();
  } else if (tabName === 'dashboard') {
    if (topbarTitle) topbarTitle.innerText = 'অ্যানালিটিক্স ও সিস্টেম মনিটরিং ড্যাশবোর্ড';
    if (topbarDesc) topbarDesc.innerText = 'সার্ভার পারফরম্যান্স, মেমোরি চাঙ্কস এবং স্টোরেজ অ্যানালাইসিস';
    if (typeof loadDashboardMetrics === 'function') loadDashboardMetrics();
  } else if (tabName === 'users') {
    if (topbarTitle) topbarTitle.innerText = 'কোম্পানি ইউজার ও এক্সেস কন্ট্রোল';
    if (topbarDesc) topbarDesc.innerText = 'অভ্যন্তরীণ কর্মকর্তা ও কর্মচারীদের রোল ম্যানেজমেন্ট';
    if (typeof loadUsersList === 'function') loadUsersList();
  } else if (tabName === 'knowledge') {
    if (topbarTitle) topbarTitle.innerText = 'কোম্পানি ডেটা লাইব্রেরি ও মেমোরি ইনজেস্ট';
    if (topbarDesc) topbarDesc.innerText = 'PDF, Word, Excel, CSV ও ফটো/ছবি OCR প্রসেসিং';
    if (typeof loadDocumentList === 'function') loadDocumentList();
    if (typeof loadMemoryStats === 'function') loadMemoryStats();
    if (typeof loadChunksList === 'function') loadChunksList();
  } else if (tabName === 'models') {
    if (topbarTitle) topbarTitle.innerText = 'এআই মডেল হাব ও রিয়েলটাইম পিং টেস্ট';
    if (topbarDesc) topbarDesc.innerText = 'বাহ্যিক এলএলএম সার্ভারের সংযোগ ও রেসপন্স টাইম (ms)';
    if (typeof loadModelsOverview === 'function') loadModelsOverview();
  } else if (tabName === 'mcp') {
    if (topbarTitle) topbarTitle.innerText = 'টুলস ও মডেল কনটেক্সট প্রোটোকল (MCP) হাব';
    if (topbarDesc) topbarDesc.innerText = 'ওপেন-সোর্স টুলস স্যুট ও ডায়নামিক এমসিপি সার্ভার ব্যবস্থাপনা';
    if (typeof loadMcpDashboard === 'function') loadMcpDashboard();
  } else if (tabName === 'security') {
    if (topbarTitle) topbarTitle.innerText = 'এন্টারপ্রাইজ ডাটা সিকিউরিটি ও কমপ্লায়েন্স';
    if (topbarDesc) topbarDesc.innerText = 'AES-256 এনক্রিপশন, PII/DLP রিডাকশন, ফায়ারওয়াল ও অডিট ট্রেইল';
    if (typeof loadSecurityDashboard === 'function') loadSecurityDashboard();
  } else if (tabName === 'backup') {
    if (topbarTitle) topbarTitle.innerText = 'সম্পূর্ণ ডেটা ও সেটিংস ব্যাকআপ এবং রিস্টোর';
    if (topbarDesc) topbarDesc.innerText = 'ডকুমেন্টস, চ্যাট হিস্ট্রি, ভেক্টর মেমোরি ও সেটিংসের সার্বিক সুরক্ষা';
    if (typeof loadBackupDashboard === 'function') loadBackupDashboard();
  } else if (tabName === 'settings') {
    if (topbarTitle) topbarTitle.innerText = 'সিস্টেম সেটিংস ও এআই ইঞ্জিন কনফিগারেশন';
    if (topbarDesc) topbarDesc.innerText = 'থিম সিলেকশন, LM Studio সংযোগ, মডেল প্যারামিটার ও সিকিউরিটি কন্ট্রোল';
    if (typeof loadSettingsHub === 'function') loadSettingsHub();
    else if (typeof loadSettings === 'function') loadSettings();
  }
}

// Memory Toggle
function toggleMemoryUsage() {
  const chk = document.getElementById('chk-use-memory');
  if (chk) chk.checked = !chk.checked;
  useMemory = chk ? chk.checked : true;
  
  const icon = document.getElementById('memory-toggle-icon');
  const label = document.getElementById('memory-toggle-text');
  const btn = document.getElementById('memory-toggle-btn');

  if (useMemory) {
    if (icon) icon.innerText = '🧠';
    if (label) label.innerText = 'মেমোরি: সক্রিয়';
    if (btn) {
      btn.style.borderColor = 'rgba(6, 182, 212, 0.4)';
      btn.style.color = 'var(--cyan-glow)';
    }
  } else {
    if (icon) icon.innerText = '⚡';
    if (label) label.innerText = 'মেমোরি: নিষ্ক্রিয়';
    if (btn) {
      btn.style.borderColor = 'rgba(255, 255, 255, 0.15)';
      btn.style.color = 'var(--text-muted)';
    }
  }
}

// Export Chat Conversation as Markdown
function exportChatConversation() {
  if (!conversationHistory || conversationHistory.length === 0) {
    showToast('এক্সপোর্ট করার মতো কোনো মেসেজ নেই।', 'info');
    return;
  }

  let mdContent = `# MyAgent Chat Export\n`;
  mdContent += `Date: ${new Date().toLocaleString()}\n`;
  mdContent += `Copyright: IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/)\n\n`;
  mdContent += `---\n\n`;

  conversationHistory.forEach(m => {
    const sender = m.role === 'user' ? 'User' : 'MyAgent';
    mdContent += `### ${sender}\n${m.content}\n\n`;
  });

  const blob = new Blob([mdContent], { type: 'text/markdown;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `myagent_chat_${Date.now()}.md`;
  a.click();
  URL.revokeObjectURL(url);
  showToast('চ্যাট কথোপকথন সফলভাবে ডাউনলোড হয়েছে!', 'success');
}

// Quick Productivity Action Prompt Handlers
function useProductivityAction(actionType) {
  const input = document.getElementById('chat-input');
  if (!input) return;

  const prompts = {
    'data_analysis': 'অনুগ্রহ করে আমাদের আপলোড করা ডেটাসেট (CSV/Excel) বিশ্লেষণ করো। প্রধান পরিসংখ্যান, শীর্ষ ক্যাটাগরি এবং ব্যবসায়িক ফলাফল টেবিল আকারে দেখাও।',
    'memory_search': 'কোম্পানির মেমোরি ও নলেজবেসে অনুসন্ধান করে আমাদের প্রধান নীতিমালা, নিয়মাবলী এবং কার্যপ্রণালী সম্পর্কিত তথ্য বিস্তারিত জানাও।',
    'generate_report': 'আমাদের সাম্প্রতিক ডেটা ও নলেজবেসের উপর ভিত্তি করে একটি বিশদ এক্সিকিউটিভ রিপোর্ট তৈরি করো এবং generate_data_report টুলের সাহায্যে reports ফোল্ডারে সংরক্ষণ করো।',
    'python_sandbox': 'পাইথন স্যান্ডবক্স ব্যবহার করে আমাদের জন্য জটিল গাণিতিক হিসাব বা ডেটা প্রসেসিং সম্পন্ন করো: ',
    'security_audit': 'আমাদের বর্তমান সিস্টেম সিকিউরিটি স্ট্যাটাস, ফায়ারওয়াল অ্যালার্ট এবং ডেটা প্রোটেকশন পরিস্থিতি বিশ্লেষণ করো।'
  };

  input.value = prompts[actionType] || '';
  input.focus();
  autoResizeTextarea(input);
}

// Textarea Auto-resize
function autoResizeTextarea(textarea) {
  if (!textarea) return;
  textarea.style.height = 'auto';
  textarea.style.height = Math.min(textarea.scrollHeight, 140) + 'px';
}

function handleTextareaKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

function usePrompt(text) {
  const input = document.getElementById('chat-input');
  if (!input) return;
  input.value = text;
  autoResizeTextarea(input);
  sendMessage();
}

// Persistent Chat Sessions Management
async function loadChatSessions() {
  const listEl = document.getElementById('sessions-list');
  if (!listEl) return;

  try {
    const res = await fetch('/api/sessions', { headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {} });
    if (res.ok) {
      const sessions = await res.json();
      if (!sessions || sessions.length === 0) {
        listEl.innerHTML = '<div style="font-size: 0.72rem; color: var(--text-muted); padding: 6px;">কোনো পূর্ববর্তী চ্যাট নেই।</div>';
        if (!currentSessionId) {
          await createNewChatSession();
        }
        return;
      }

      listEl.innerHTML = sessions.map(s => `
        <div class="session-item ${s.id === currentSessionId ? 'active' : ''}" onclick="switchSession('${s.id}')" id="session-item-${s.id}">
          <span class="session-title-text" title="${escapeHtml(s.title)}">💬 ${escapeHtml(s.title)}</span>
          <div class="session-actions">
            <button class="session-del-btn" title="ডিলিট করুন" onclick="deleteChatSession('${s.id}', event)">&times;</button>
          </div>
        </div>
      `).join('');

      // Auto-select first session if none is currently active
      if (!currentSessionId && sessions.length > 0) {
        await switchSession(sessions[0].id);
      }
    }
  } catch (err) {
    console.warn('Error loading chat sessions:', err);
  }
}

async function createNewChatSession() {
  try {
    const res = await fetch('/api/sessions', {
      method: 'POST',
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: 'নতুন চ্যাট' })
    });
    if (res.ok) {
      const newSession = await res.json();
      currentSessionId = newSession.id;
      conversationHistory = [];
      
      const feed = document.getElementById('chat-feed');
      if (feed) {
        feed.querySelectorAll('.chat-message').forEach(m => m.remove());
        const hero = document.getElementById('empty-hero');
        if (hero) hero.style.display = 'flex';
      }
      
      await loadChatSessions();
      showToast('নতুন চ্যাট সেশন শুরু হয়েছে।', 'info');
      return currentSessionId;
    }
  } catch (err) {
    showToast(`সেশন তৈরিতে সমস্যা: ${err.message}`, 'error');
  }

  if (!currentSessionId) {
    currentSessionId = 'session_' + Date.now();
  }
  return currentSessionId;
}

async function switchSession(sessionId) {
  if (currentSessionId === sessionId && conversationHistory.length > 0) return;
  currentSessionId = sessionId;
  
  document.querySelectorAll('.session-item').forEach(el => el.classList.remove('active'));
  const activeEl = document.getElementById(`session-item-${sessionId}`);
  if (activeEl) activeEl.classList.add('active');

  const feed = document.getElementById('chat-feed');
  if (!feed) return;

  feed.querySelectorAll('.chat-message').forEach(m => m.remove());
  const hero = document.getElementById('empty-hero');

  try {
    const res = await fetch(`/api/sessions/${sessionId}`, {
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {}
    });

    if (res.ok) {
      const data = await res.json();
      conversationHistory = [];

      if (!data.messages || data.messages.length === 0) {
        if (hero) hero.style.display = 'flex';
      } else {
        if (hero) hero.style.display = 'none';
        data.messages.forEach(m => {
          renderMessage(m.role, m.content, false);
          conversationHistory.push({ role: m.role, content: m.content });
        });
      }
    }
  } catch (err) {
    console.warn('Error loading session messages:', err);
  }
}

async function deleteChatSession(sessionId, event) {
  if (event) event.stopPropagation();
  if (!confirm('আপনি কি এই চ্যাট সেশনটি মুছে ফেলতে চান?')) return;

  try {
    const res = await fetch(`/api/sessions/${sessionId}`, {
      method: 'DELETE',
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {}
    });
    if (res.ok) {
      showToast('চ্যাট সেশন মুছে ফেলা হয়েছে।', 'info');
      if (currentSessionId === sessionId) {
        currentSessionId = null;
        await createNewChatSession();
      } else {
        await loadChatSessions();
      }
    }
  } catch (err) {
    showToast(`ডিলিট ব্যর্থ: ${err.message}`, 'error');
  }
}

// Model Switcher from Topbar
function onModelSelectChange(newModel) {
  fetch('/api/settings', {
    method: 'POST',
    headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : { 'Content-Type': 'application/json' },
    body: JSON.stringify({ llm_model: newModel })
  }).then(res => {
    if (res.ok) {
      showToast(`সক্রিয় মডেল: ${newModel}`, 'success');
      const sideModel = document.getElementById('sidebar-model-name');
      if (sideModel) sideModel.innerText = newModel;
    }
  });
}

// Send Message & Stream SSE Response
async function sendMessage() {
  if (isGenerating) return;

  const input = document.getElementById('chat-input');
  if (!input) return;

  let prompt = input.value.trim();
  const hasAttachments = attachedChatFiles && attachedChatFiles.length > 0;

  if (!prompt && !hasAttachments) {
    input.focus();
    return;
  }

  // Default prompt if user only attached files without typing
  if (!prompt && hasAttachments) {
    prompt = 'অনুগ্রহ করে সংযুক্ত ফাইলগুলো বিশ্লেষণ করে বিস্তারিত সারসংক্ষেপ ও অন্তর্দৃষ্টি তুলে ধরুন।';
  }

  const sendBtn = document.getElementById('btn-send-message');

  // Ensure active session exists
  if (!currentSessionId) {
    await createNewChatSession();
  }

  const hero = document.getElementById('empty-hero');
  if (hero) hero.style.display = 'none';

  if (sendBtn) {
    sendBtn.disabled = true;
    sendBtn.innerHTML = SPINNER_SVG;
  }

  let serverAttachedFiles = [];
  let attachedFilesForDisplay = [];

  // Step 1: Upload attached files to backend if any
  if (hasAttachments) {
    showUploadProgress(`${attachedChatFiles.length}টি ফাইল আপলোড ও মেমোরি ইনডেক্সিং হচ্ছে...`);
    try {
      const formData = new FormData();
      for (const item of attachedChatFiles) {
        formData.append('files', item.file, item.name);
      }

      const uploadHeaders = typeof getAuthHeaders === 'function' ? getAuthHeaders() : {};
      delete uploadHeaders['Content-Type'];

      const uploadRes = await fetch('/api/chat/upload', {
        method: 'POST',
        headers: uploadHeaders,
        body: formData
      });

      if (!uploadRes.ok) {
        const errJson = await uploadRes.json().catch(() => ({}));
        throw new Error(errJson.detail || 'ফাইল আপলোড ব্যর্থ হয়েছে');
      }

      const uploadData = await uploadRes.json();
      serverAttachedFiles = uploadData.files || [];

      attachedFilesForDisplay = serverAttachedFiles.map(f => ({
        name: f.filename,
        size: f.size_bytes || f.size || 0,
        extension: f.extension || f.filename.split('.').pop()
      }));

      // Free local object URLs and clear shelf
      attachedChatFiles.forEach(item => {
        if (item.previewUrl) URL.revokeObjectURL(item.previewUrl);
      });
      attachedChatFiles = [];
      renderAttachmentShelf();

      showToast(`${serverAttachedFiles.length}টি ফাইল সফলভাবে যুক্ত ও প্রসেস করা হয়েছে`, 'success');

    } catch (uploadErr) {
      showToast(`ফাইল প্রসেসিং ত্রুটি: ${uploadErr.message}`, 'error');
      if (sendBtn) {
        sendBtn.disabled = false;
        sendBtn.innerHTML = SEND_ICON_SVG;
      }
      return;
    } finally {
      hideUploadProgress();
    }
  }

  // 2. Render user message with attached file chips
  renderMessage('user', prompt, false, attachedFilesForDisplay);
  conversationHistory.push({ role: 'user', content: prompt });
  input.value = '';
  input.style.height = 'auto';

  // 3. Render empty assistant bubble with streaming cursor
  const assistantBubble = renderMessage('assistant', '', true);
  isGenerating = true;
  isStreaming = true;
  currentChatAbortController = new AbortController();

  if (sendBtn) {
    sendBtn.disabled = false;
    sendBtn.classList.add('streaming-active');
    sendBtn.title = 'উত্তর তৈরি থামান (Stop Generating)';
    sendBtn.innerHTML = `
      <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor" style="pointer-events:none;">
        <rect x="5" y="5" width="14" height="14" rx="2"></rect>
      </svg>
    `;
    sendBtn.onclick = function(e) {
      if (e) e.preventDefault();
      stopGenerating();
    };
  }

  let assistantContent = '';
  let citations = [];

  try {
    const headers = typeof getAuthHeaders === 'function' ? getAuthHeaders() : { 'Content-Type': 'application/json' };
    const response = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: headers,
      signal: currentChatAbortController.signal,
      body: JSON.stringify({
        session_id: currentSessionId,
        prompt: prompt,
        history: conversationHistory.slice(-8),
        use_memory: useMemory,
        attached_files: serverAttachedFiles
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const jsonStr = line.slice(6).trim();
          if (!jsonStr) continue;

          try {
            const data = JSON.parse(jsonStr);
            if (data.type === 'sources') {
              citations = data.sources || [];
            } else if (data.type === 'tool_call') {
              assistantContent += `\n\n⚙️ *[টুল কল করা হচ্ছে: **${data.name}**...]*\n`;
              updateAssistantMessage(assistantBubble, assistantContent, true);
            } else if (data.type === 'tool_result') {
              assistantContent += `\n> 💡 **[${data.name} ফলাফল]:**\n> \`\`\`\n> ${escapeHtml(data.result).slice(0, 500)}\n> \`\`\`\n\n`;
              updateAssistantMessage(assistantBubble, assistantContent, true);
            } else if (data.type === 'token') {
              assistantContent += data.token;
              updateAssistantMessage(assistantBubble, assistantContent, true);
            } else if (data.type === 'error') {
              assistantContent += `\n\n⚠️ **ত্রুটি:** ${data.error}`;
              updateAssistantMessage(assistantBubble, assistantContent, false);
            }
          } catch (parseErr) {
            console.warn('SSE Parse notice:', parseErr);
          }
        }
      }
    }

    // Finalize assistant message
    updateAssistantMessage(assistantBubble, assistantContent || 'উত্তর প্রক্রিয়া সম্পন্ন হয়েছে।', false, citations);
    conversationHistory.push({ role: 'assistant', content: assistantContent });
    loadChatSessions();

  } catch (err) {
    if (err.name === 'AbortError') {
      assistantContent += `\n\n⏹️ *[ব্যবহারকারী কর্তৃক উত্তর তৈরি থামানো হয়েছে]*`;
      updateAssistantMessage(assistantBubble, assistantContent, false);
    } else {
      assistantContent += `\n\n❌ **সার্ভার সমস্যা:** ${err.message}। অনুগ্রহ করে নিশ্চিত করুন যে ব্যাকএন্ড সার্ভিসটি সক্রিয় রয়েছে।`;
      updateAssistantMessage(assistantBubble, assistantContent, false);
    }
  } finally {
    isGenerating = false;
    isStreaming = false;
    currentChatAbortController = null;
    if (sendBtn) {
      sendBtn.classList.remove('streaming-active');
      sendBtn.disabled = false;
      sendBtn.innerHTML = SEND_ICON_SVG;
      sendBtn.title = 'বার্তা পাঠান (Enter)';
    }
    attachChatEventListeners();
    input.focus();
  }
}

function renderMessage(role, text, isStreaming = false, attachedFiles = []) {
  const feed = document.getElementById('chat-feed');
  if (!feed) return null;

  const messageEl = document.createElement('div');
  messageEl.className = `chat-message ${role}-message`;

  const avatar = role === 'user' ? '👤' : '✨';
  const senderTitle = role === 'user' ? 'আপনি' : 'MyAgent AI';
  const avatarStyle = role === 'assistant' 
    ? 'background: linear-gradient(135deg, #4285f4, #9b72cb); color: #ffffff; box-shadow: 0 0 12px rgba(155, 114, 203, 0.45);' 
    : '';

  let attachmentHtml = '';
  if (attachedFiles && attachedFiles.length > 0) {
    attachmentHtml = `
      <div class="user-attached-files-container" style="display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px;">
        ${attachedFiles.map(f => `
          <div class="user-attached-file-chip">
            <span>${getFileBadgeIcon(f.name || f.filename)}</span>
            <span>${escapeHtml(f.name || f.filename)}</span>
            <span style="opacity: 0.8; font-size: 0.72rem;">(${formatFileSize(f.size || 0)})</span>
          </div>
        `).join('')}
      </div>
    `;
  }

  messageEl.innerHTML = `
    <div class="chat-avatar" style="${avatarStyle}">${avatar}</div>
    <div class="message-content-wrapper">
      <div class="message-sender-name">${senderTitle}</div>
      <div class="message-bubble">
        ${attachmentHtml}
        <div class="message-text">${renderMarkdown(text)}</div>
        ${isStreaming ? '<span class="streaming-cursor"></span>' : ''}
        <div class="sources-slot"></div>
      </div>
    </div>
  `;

  feed.appendChild(messageEl);
  feed.scrollTop = feed.scrollHeight;
  return messageEl;
}

function updateAssistantMessage(messageEl, content, isStreaming, citations = []) {
  if (!messageEl) return;

  const textContainer = messageEl.querySelector('.message-text');
  const cursor = messageEl.querySelector('.streaming-cursor');
  const sourcesSlot = messageEl.querySelector('.sources-slot');

  if (textContainer) {
    textContainer.innerHTML = renderMarkdown(content);
  }

  if (!isStreaming && cursor) {
    cursor.remove();
  }

  if (!isStreaming && citations && citations.length > 0 && sourcesSlot) {
    const validCitations = citations.filter(c => {
      const src = String(c.source || '').trim();
      const cnt = String(c.content || '').trim();
      const score = Number(c.score || 0);
      return !src.includes('????') && !cnt.includes('????') && score >= 0.55;
    });

    if (validCitations.length > 0) {
      sourcesSlot.innerHTML = `
        <div class="sources-container">
          <div class="sources-header">
            <span>📑 মেমোরি রেফারেন্স ও সোর্স (${validCitations.length}টি)</span>
          </div>
          <div class="sources-list">
            ${validCitations.map(c => `
              <span class="citation-chip" title="${escapeHtml(c.content)}">
                📄 ${escapeHtml(c.source)} (পৃষ্ঠা ${c.page || 1}) • ${(c.score * 100).toFixed(0)}% মিল
              </span>
            `).join('')}
          </div>
        </div>
      `;
    } else {
      sourcesSlot.innerHTML = '';
    }
  } else if (!isStreaming && sourcesSlot) {
    sourcesSlot.innerHTML = '';
  }

  // Add ChatGPT-style action toolbar upon stream completion
  if (!isStreaming) {
    let toolbar = messageEl.querySelector('.msg-action-toolbar');
    if (!toolbar) {
      const bubble = messageEl.querySelector('.message-bubble');
      if (bubble) {
        toolbar = document.createElement('div');
        toolbar.className = 'msg-action-toolbar';
        toolbar.innerHTML = `
          <button class="msg-tool-btn" onclick="copyMessageText(this)" title="কপি করুন">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
            কপি
          </button>
          <button class="msg-tool-btn" onclick="saveMsgToAgentMemory(this)" title="এআই-এর উত্তরটি কোম্পানির স্থায়ী মেমোরিতে সেভ করুন">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>
            মেমোরিতে সেভ
          </button>
          <button class="msg-tool-btn" onclick="retryLastPrompt()" title="পুনরায় চেষ্টা করুন">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>
            রিট্রাই
          </button>
          <button class="msg-tool-btn" onclick="toggleMsgLike(this, 'like')" title="পছন্দ হয়েছে">👍</button>
          <button class="msg-tool-btn" onclick="toggleMsgLike(this, 'dislike')" title="অপছন্দ হয়েছে">👎</button>
        `;
        bubble.appendChild(toolbar);
      }
    }
  }

  const feed = document.getElementById('chat-feed');
  if (feed) feed.scrollTop = feed.scrollHeight;
}

function renderMarkdown(md) {
  if (!md) return '';

  let html = md
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // Markdown Tables (| Header | Header |\n|---|---|\n| Cell | Cell |)
  html = html.replace(/((?:\|[^\n]+\|\r?\n)+)/g, (tableMatch) => {
    const lines = tableMatch.trim().split('\n').map(l => l.trim()).filter(l => l);
    if (lines.length < 2) return tableMatch;
    if (!lines[1].match(/^\|?\s*[-:]+\s*\|[-:|\s]*$/)) return tableMatch;

    const parseRow = (line) => {
      let cells = line.split('|').map(c => c.trim());
      if (line.startsWith('|')) cells.shift();
      if (line.endsWith('|')) cells.pop();
      return cells;
    };

    const headers = parseRow(lines[0]);
    let tableHtml = '<div class="table-responsive"><table class="markdown-table"><thead><tr>';
    headers.forEach(h => {
      tableHtml += `<th>${h}</th>`;
    });
    tableHtml += '</tr></thead><tbody>';

    for (let i = 2; i < lines.length; i++) {
      const row = parseRow(lines[i]);
      tableHtml += '<tr>';
      row.forEach(cell => {
        tableHtml += `<td>${cell}</td>`;
      });
      tableHtml += '</tr>';
    }
    tableHtml += '</tbody></table></div>';
    return tableHtml;
  });

  // ChatGPT-style Code blocks with header and Copy Code button
  html = html.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (match, lang, code) => {
    const codeId = 'code_' + Math.random().toString(36).substring(2, 9);
    const displayLang = lang ? lang.toLowerCase() : 'code';
    return `<div class="chatgpt-code-box">
      <div class="code-box-header">
        <span class="code-lang-label">${displayLang}</span>
        <button class="copy-code-btn" type="button" onclick="copyCodeBlock(this, '${codeId}')">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
          কপি কোড
        </button>
      </div>
      <pre class="code-box-content" id="${codeId}"><code class="lang-${displayLang}">${code.trim()}</code></pre>
    </div>`;
  });

  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  html = html.replace(/^### (.*$)/gim, '<h4>$1</h4>');
  html = html.replace(/^## (.*$)/gim, '<h3>$1</h3>');
  html = html.replace(/^# (.*$)/gim, '<h2>$1</h2>');
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
  html = html.replace(/^\> (.*$)/gim, '<blockquote>$1</blockquote>');
  html = html.replace(/^\s*-\s+(.*$)/gim, '<li>$1</li>');
  html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');

  const paragraphs = html.split(/\n\n+/);
  return paragraphs.map(p => {
    if (p.startsWith('<div class="chatgpt-code-box"') || p.startsWith('<div class="table-responsive"') || p.startsWith('<pre>') || p.startsWith('<h2>') || p.startsWith('<h3>') || p.startsWith('<h4>') || p.startsWith('<ul>') || p.startsWith('<blockquote>')) {
      return p;
    }
    return `<p>${p.replace(/\n/g, '<br>')}</p>`;
  }).join('');
}


function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// Clipboard & Action Helpers for ChatGPT / Gemini Chat
function copyCodeBlock(btn, codeId) {
  const codeEl = document.getElementById(codeId);
  if (!codeEl) return;
  const text = codeEl.innerText || codeEl.textContent;
  navigator.clipboard.writeText(text).then(() => {
    const originalText = btn.innerHTML;
    btn.innerHTML = '✓ কপি হয়েছে!';
    btn.style.color = '#34d399';
    setTimeout(() => {
      btn.innerHTML = originalText;
      btn.style.color = '';
    }, 2000);
  }).catch(() => {
    showToast('ক্লিপবোর্ডে কপি করা যায়নি', 'error');
  });
}

function copyMessageText(btn) {
  const bubble = btn.closest('.message-bubble');
  if (!bubble) return;
  const textEl = bubble.querySelector('.message-text');
  if (!textEl) return;
  const text = textEl.innerText || textEl.textContent;
  navigator.clipboard.writeText(text).then(() => {
    const originalText = btn.innerHTML;
    btn.innerHTML = '✓ কপি হয়েছে!';
    btn.style.color = '#34d399';
    setTimeout(() => {
      btn.innerHTML = originalText;
      btn.style.color = '';
    }, 2000);
  }).catch(() => {
    showToast('ক্লিপবোর্ডে কপি করা যায়নি', 'error');
  });
}

function retryLastPrompt() {
  if (!conversationHistory || conversationHistory.length === 0) return;
  const lastUserMsg = [...conversationHistory].reverse().find(m => m.role === 'user');
  if (lastUserMsg) {
    const input = document.getElementById('chat-input');
    if (input) {
      input.value = lastUserMsg.content;
      autoResizeTextarea(input);
      sendMessage();
    }
  }
}

function toggleMsgLike(btn, type) {
  if (type === 'like') {
    btn.classList.toggle('active-like');
    showToast('ফিডব্যাকের জন্য ধন্যবাদ!', 'success');
  } else {
    btn.classList.toggle('active-dislike');
    showToast('ফিডব্যাক গ্রহণ করা হয়েছে। আমরা মডেল উন্নত করছি।', 'info');
  }
}

// ==============================================================================
// Instant Note / Agent Memory Saver & Chat Search Enhancements
// ==============================================================================

function openQuickMemoryModal() {
  const modal = document.getElementById('quick-memory-modal');
  if (modal) {
    modal.style.display = 'flex';
    const titleInput = document.getElementById('quick-note-title');
    if (titleInput) {
      titleInput.focus();
    }
  }
}

function closeQuickMemoryModal() {
  const modal = document.getElementById('quick-memory-modal');
  if (modal) modal.style.display = 'none';
}

async function submitQuickNote(event) {
  if (event) event.preventDefault();
  const titleInput = document.getElementById('quick-note-title');
  const catInput = document.getElementById('quick-note-category');
  const contentInput = document.getElementById('quick-note-content');
  const submitBtn = document.getElementById('btn-submit-quick-note');

  if (!titleInput || !contentInput) return;
  const title = titleInput.value.trim();
  const content = contentInput.value.trim();
  const category = catInput ? catInput.value : 'notes';

  if (!title || !content) {
    showToast('দয়া করে শিরোনাম ও বিস্তারিত কনটেন্ট লিখুন', 'error');
    return;
  }

  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerText = 'সেভ হচ্ছে...';
  }

  try {
    const res = await fetch('/api/documents/quick-note', {
      method: 'POST',
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: title,
        content: content,
        category: category,
        security_level: 'INTERNAL'
      })
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'মেমোরি সেভ ব্যর্থ হয়েছে');
    }

    const data = await res.json();
    showToast(data.message || 'নোট সফলভাবে মেমোরিতে সংরক্ষিত হয়েছে!', 'success');
    titleInput.value = '';
    contentInput.value = '';
    closeQuickMemoryModal();

    if (typeof loadDocumentList === 'function') loadDocumentList();
    if (typeof loadMemoryStats === 'function') loadMemoryStats();
    if (typeof loadChunksList === 'function') loadChunksList();
  } catch (err) {
    showToast(`ত্রুটি: ${err.message}`, 'error');
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerText = 'মেমোরিতে সেভ করুন';
    }
  }
}

async function saveMsgToAgentMemory(btn) {
  const bubble = btn.closest('.message-bubble');
  if (!bubble) return;
  const textEl = bubble.querySelector('.message-text');
  if (!textEl) return;
  const content = (textEl.innerText || textEl.textContent).trim();
  if (!content) return;

  const firstLine = content.split('\n')[0].replace(/^[#\*\s\-]+/, '').trim().slice(0, 45) || 'চ্যাট নোট';
  const originalHtml = btn.innerHTML;
  btn.disabled = true;
  btn.innerText = 'সেভ হচ্ছে...';

  try {
    const res = await fetch('/api/documents/quick-note', {
      method: 'POST',
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: firstLine,
        content: content,
        category: 'saved_replies',
        security_level: 'INTERNAL'
      })
    });

    if (res.ok) {
      btn.innerHTML = '✓ সেভ হয়েছে!';
      btn.style.color = '#34d399';
      showToast(`'${firstLine}' সফলভাবে এজেন্টের স্থায়ী মেমোরিতে সেভ হয়েছে!`, 'success');
      setTimeout(() => {
        btn.innerHTML = originalHtml;
        btn.style.color = '';
        btn.disabled = false;
      }, 3000);
    } else {
      throw new Error('সার্ভারে সেভ করা যায়নি');
    }
  } catch (err) {
    btn.innerHTML = originalHtml;
    btn.disabled = false;
    showToast('মেমোরিতে সেভ ব্যর্থ হয়েছে', 'error');
  }
}

// Real-time Upload & Indexing Progress Bar Helpers
function showUploadProgress(text) {
  const pill = document.getElementById('upload-progress-pill');
  const label = document.getElementById('upload-progress-text');
  if (pill) {
    pill.style.display = 'inline-flex';
    if (label && text) label.innerText = text;
  }
}

function hideUploadProgress() {
  const pill = document.getElementById('upload-progress-pill');
  if (pill) pill.style.display = 'none';
}

// Chat Message Search & In-conversation Filter
function filterChatMessages(query) {
  const feed = document.getElementById('chat-feed');
  if (!feed) return;
  const messages = feed.querySelectorAll('.chat-message');
  const cleanQ = (query || '').trim().toLowerCase();

  if (!cleanQ) {
    messages.forEach(m => {
      m.style.display = '';
      m.style.opacity = '1';
    });
    return;
  }

  messages.forEach(m => {
    const txt = (m.innerText || '').toLowerCase();
    if (txt.includes(cleanQ)) {
      m.style.display = '';
      m.style.opacity = '1';
    } else {
      m.style.display = 'none';
    }
  });
}

