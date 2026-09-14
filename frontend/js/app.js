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
    sendBtn.title = typeof t === 'function' ? t('btn_send_title', 'বার্তা পাঠান (Enter)') : 'বার্তা পাঠান (Enter)';
  }
  attachChatEventListeners();
  showToast(typeof t === 'function' ? t('toast_gen_stopped', 'উত্তর তৈরি বন্ধ করা হয়েছে।') : 'উত্তর তৈরি বন্ধ করা হয়েছে।', 'info');
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
      if (statusText) statusText.innerText = typeof t === 'function' ? t('status_online', 'অনলাইন') : 'অনলাইন';
      if (sideModel && data.llm_model) sideModel.innerText = data.llm_model;
      if (topModelSelect && data.llm_model) topModelSelect.value = data.llm_model;
    }
  } catch (e) {
    const statusText = document.getElementById('agent-online-status');
    if (statusText) statusText.innerText = typeof t === 'function' ? t('status_offline', 'অফলাইন') : 'অফলাইন';
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

  // Preserve user toggle state if already checked
  const prevChecked = document.getElementById('chat-save-memory-checkbox')?.checked || false;

  shelf.style.display = 'flex';
  shelf.style.flexDirection = 'column';

  const countText = typeof t === 'function' 
    ? (getAppLanguage() === 'en' ? `📎 Attached Files (${attachedChatFiles.length})` : `📎 সংযুক্ত ফাইল (${attachedChatFiles.length}টি)`)
    : `📎 সংযুক্ত ফাইল (${attachedChatFiles.length}টি)`;

  const memLabel = typeof t === 'function' ? t('memory_checkbox_label', 'স্থায়ী মেমোরিতে সংরক্ষণ করুন') : 'স্থায়ী মেমোরিতে সংরক্ষণ করুন';
  const memTitle = typeof t === 'function' ? t('save_memory_toggle_title', 'ইউজার/অ্যাডমিন সিদ্ধান্ত: চেক করলে এই ফাইলগুলো স্থায়ীভাবে কোম্পানির ভেক্টর মেমোরিতে সেভ হবে') : 'ইউজার/অ্যাডমিন সিদ্ধান্ত: চেক করলে এই ফাইলগুলো স্থায়ীভাবে কোম্পানির ভেক্টর মেমোরিতে সেভ হবে';
  const removeTitle = typeof t === 'function' ? t('btn_remove', 'মুছে ফেলুন') : 'মুছে ফেলুন';

  const headerHtml = `
    <div class="attachment-shelf-header" style="display: flex; justify-content: space-between; align-items: center; width: 100%; margin-bottom: 8px; padding-bottom: 6px; border-bottom: 1px solid rgba(255,255,255,0.08);">
      <span style="font-size: 0.8rem; font-weight: 600; color: var(--text-primary, #e2e8f0); display: flex; align-items: center; gap: 6px;">
        ${countText}
      </span>
      <label style="display: inline-flex; align-items: center; gap: 6px; font-size: 0.76rem; cursor: pointer; color: #c7d2fe; background: rgba(99, 102, 241, 0.15); padding: 4px 10px; border-radius: 16px; border: 1px solid rgba(99, 102, 241, 0.35); transition: all 0.2s ease;" title="${escapeHtml(memTitle)}">
        <input type="checkbox" id="chat-save-memory-checkbox" ${prevChecked ? 'checked' : ''} style="cursor: pointer; accent-color: #6366f1;">
        <span style="font-weight: 600;">💾 ${escapeHtml(memLabel)}</span>
      </label>
    </div>
  `;

  const chipsHtml = `
    <div class="attachment-chips-row" style="display: flex; flex-wrap: wrap; gap: 8px; width: 100%;">
      ${attachedChatFiles.map(item => {
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
            <button type="button" class="attachment-remove-btn" title="${escapeHtml(removeTitle)}" onclick="removeAttachedFile('${item.id}')">&times;</button>
          </div>
        `;
      }).join('')}
    </div>
  `;

  shelf.innerHTML = headerHtml + chipsHtml;
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
      const isEn = (typeof getAppLanguage === 'function' && getAppLanguage() === 'en');
      showToast(isEn ? `${filesToUpload.length} file(s) attached from clipboard` : `${filesToUpload.length}টি ফাইল ক্লিপবোর্ড থেকে সংযুক্ত করা হয়েছে`, 'info');
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
      text.innerText = useMemory 
        ? (typeof t === 'function' ? t('memory_toggle_label', 'কোম্পানি মেমোরি') : 'কোম্পানি মেমোরি')
        : (typeof t === 'function' ? (getAppLanguage() === 'en' ? 'Memory Off' : 'মেমোরি বন্ধ') : 'মেমোরি বন্ধ');
    }
    showToast(
      useMemory 
        ? (typeof t === 'function' ? t('toast_mem_active', 'কোম্পানি মেমোরি সার্চ সক্রিয়') : 'কোম্পানি মেমোরি সার্চ সক্রিয়')
        : (typeof t === 'function' ? t('toast_mem_disabled', 'মেমোরি সার্চ বন্ধ') : 'মেমোরি সার্চ বন্ধ'),
      'info'
    );
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
  const tabs = ['chat', 'admin', 'dashboard', 'reports', 'users', 'knowledge', 'models', 'mcp', 'security', 'backup', 'settings'];
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

  const tabTitles = {
    chat: { title: 'tab_chat_title', desc: 'tab_chat_desc' },
    admin: { title: 'tab_admin_title', desc: 'tab_admin_desc' },
    dashboard: { title: 'tab_dash_title', desc: 'tab_dash_desc' },
    users: { title: 'tab_users_title', desc: 'tab_users_desc' },
    knowledge: { title: 'tab_kb_title', desc: 'tab_kb_desc' },
    models: { title: 'tab_models_title', desc: 'tab_models_desc' },
    mcp: { title: 'tab_mcp_title', desc: 'tab_mcp_desc' },
    security: { title: 'tab_sec_title', desc: 'tab_sec_desc' },
    backup: { title: 'tab_backup_title', desc: 'tab_backup_desc' },
    reports: { title: 'tab_reports_title', desc: 'tab_reports_desc' },
    settings: { title: 'tab_settings_title', desc: 'tab_settings_desc' }
  };

  if (tabTitles[tabName]) {
    if (topbarTitle) topbarTitle.innerText = typeof t === 'function' ? t(tabTitles[tabName].title) : '';
    if (topbarDesc) topbarDesc.innerText = typeof t === 'function' ? t(tabTitles[tabName].desc) : '';
  }

  if (tabName === 'admin' && typeof loadAdminDashboard === 'function') loadAdminDashboard();
  else if (tabName === 'dashboard') {
    if (typeof loadDashboardFull === 'function') loadDashboardFull();
    else if (typeof loadDashboardMetrics === 'function') loadDashboardMetrics();
  } else if (tabName === 'users' && typeof loadUsersList === 'function') loadUsersList();
  else if (tabName === 'knowledge') {
    if (typeof loadDocumentList === 'function') loadDocumentList();
    if (typeof loadMemoryStats === 'function') loadMemoryStats();
    if (typeof loadChunksList === 'function') loadChunksList();
  } else if (tabName === 'models' && typeof loadModelsOverview === 'function') loadModelsOverview();
  else if (tabName === 'mcp' && typeof loadMcpDashboard === 'function') loadMcpDashboard();
  else if (tabName === 'security' && typeof loadSecurityDashboard === 'function') loadSecurityDashboard();
  else if (tabName === 'backup' && typeof loadBackupDashboard === 'function') loadBackupDashboard();
  else if (tabName === 'reports' && typeof loadReportsPage === 'function') loadReportsPage();
  else if (tabName === 'settings') {
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
  const isEn = typeof getAppLanguage === 'function' && getAppLanguage() === 'en';

  if (useMemory) {
    if (icon) icon.innerText = '🧠';
    if (label) label.innerText = isEn ? 'Memory: Active' : 'মেমোরি: সক্রিয়';
    if (btn) {
      btn.style.borderColor = 'rgba(6, 182, 212, 0.4)';
      btn.style.color = 'var(--cyan-glow)';
    }
  } else {
    if (icon) icon.innerText = '⚡';
    if (label) label.innerText = isEn ? 'Memory: Disabled' : 'মেমোরি: নিষ্ক্রিয়';
    if (btn) {
      btn.style.borderColor = 'rgba(255, 255, 255, 0.15)';
      btn.style.color = 'var(--text-muted)';
    }
  }
}

// Export Chat Conversation as Markdown
function exportChatConversation() {
  if (!conversationHistory || conversationHistory.length === 0) {
    showToast(typeof t === 'function' ? t('toast_no_export', 'এক্সপোর্ট করার মতো কোনো মেসেজ নেই।') : 'এক্সপোর্ট করার মতো কোনো মেসেজ নেই।', 'info');
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
  showToast(typeof t === 'function' ? t('toast_export_ok', 'চ্যাট কথোপকথন সফলভাবে ডাউনলোড হয়েছে!') : 'চ্যাট কথোপকথন সফলভাবে ডাউনলোড হয়েছে!', 'success');
}

// Quick Productivity Action Prompt Handlers
function useProductivityAction(actionType) {
  const input = document.getElementById('chat-input');
  if (!input) return;

  const prompts = {
    en: {
      'data_analysis': 'Please analyze our uploaded dataset (CSV/Excel). Show key statistics, top categories, and business metrics in clean markdown tables.',
      'memory_search': 'Search company memory and knowledge base for our primary policies, internal rules, and operational procedures in detail.',
      'generate_report': 'Generate an executive corporate report based on our internal knowledge base and save it to the reports folder using the generate_data_report tool.',
      'python_sandbox': 'Run complex mathematical calculations or dataset transformations using the Python sandbox: ',
      'security_audit': 'Analyze our current system security posture, firewall alerts, DLP status, and compliance audit trail.'
    },
    bn: {
      'data_analysis': 'অনুগ্রহ করে আমাদের আপলোড করা ডেটাসেট (CSV/Excel) বিশ্লেষণ করো। প্রধান পরিসংখ্যান, শীর্ষ ক্যাটাগরি এবং ব্যবসায়িক ফলাফল টেবিল আকারে দেখাও।',
      'memory_search': 'কোম্পানির মেমোরি ও নলেজবেসে অনুসন্ধান করে আমাদের প্রধান নীতিমালা, নিয়মাবলী এবং কার্যপ্রণালী সম্পর্কিত তথ্য বিস্তারিত জানাও।',
      'generate_report': 'আমাদের সাম্প্রতিক ডেটা ও নলেজবেসের উপর ভিত্তি করে একটি বিশদ এক্সিকিউটিভ report তৈরি করো এবং generate_data_report টুলের সাহায্যে reports ফোল্ডারে সংরক্ষণ করো।',
      'python_sandbox': 'পাইথন স্যান্ডবক্স ব্যবহার করে আমাদের জন্য জটিল গাণিতিক হিসাব বা ডেটা প্রসেসিং সম্পন্ন করো: ',
      'security_audit': 'আমাদের বর্তমান সিস্টেম সিকিউরিটি স্ট্যাটাস, ফায়ারওয়াল অ্যালার্ট এবং ডেটা প্রোটেকশন পরিস্থিতি বিশ্লেষণ করো।'
    }
  };

  const lang = typeof getAppLanguage === 'function' ? getAppLanguage() : 'bn';
  const langPrompts = prompts[lang] || prompts['bn'];
  input.value = langPrompts[actionType] || prompts.bn[actionType] || '';
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

const PROMPT_SUGGESTIONS = {
  en: {
    policy: "Please explain our company internal policies, workplace rules, and leave guidelines in detail.",
    excel: "Please analyze the uploaded Excel spreadsheet and dataset. Show key metrics and trends in structured tables.",
    report: "Generate a comprehensive executive corporate report based on our company knowledge base.",
    ocr: "Extract and thoroughly explain all text and structured information found in the uploaded image/photo."
  },
  bn: {
    policy: "আমাদের কোম্পানির অভ্যন্তরীণ নীতিমালা এবং ছুটির নিয়মগুলো বিস্তারিত জানাও।",
    excel: "আপলোড করা এক্সেল ফাইলের হিসাব, বিক্রয় তথ্য ও প্রধান পরিসংখ্যান বিশ্লেষণ করো।",
    report: "আমাদের সাম্প্রতিক কোম্পানির নলেজবেসের উপর ভিত্তি করে একটি বিশদ এক্সিকিউটিভ রিপোর্ট তৈরি করো।",
    ocr: "আপলোড করা ইমেজ বা ছবির মধ্যে কী কী টেক্সট বা তথ্য রয়েছে বিস্তারিত ব্যাখ্যা করো।"
  }
};

function usePrompt(keyOrText) {
  const input = document.getElementById('chat-input');
  if (!input) return;
  const lang = typeof getAppLanguage === 'function' ? getAppLanguage() : 'bn';
  const localizedText = (PROMPT_SUGGESTIONS[lang] && PROMPT_SUGGESTIONS[lang][keyOrText])
    ? PROMPT_SUGGESTIONS[lang][keyOrText]
    : (PROMPT_SUGGESTIONS.bn[keyOrText] || keyOrText);

  input.value = localizedText;
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
      const isEn = (typeof getAppLanguage === 'function' && getAppLanguage() === 'en');
      if (!sessions || sessions.length === 0) {
        listEl.innerHTML = `<div style="font-size: 0.72rem; color: var(--text-muted); padding: 6px;">${isEn ? 'No previous chats.' : 'কোনো পূর্ববর্তী চ্যাট নেই।'}</div>`;
        if (!currentSessionId) {
          await createNewChatSession();
        }
        return;
      }

      listEl.innerHTML = sessions.map(s => `
        <div class="session-item ${s.id === currentSessionId ? 'active' : ''}" onclick="switchSession('${s.id}')" id="session-item-${s.id}">
          <span class="session-title-text" title="${escapeHtml(s.title)}">💬 ${escapeHtml(s.title)}</span>
          <div class="session-actions">
            <button class="session-del-btn" title="${typeof t === 'function' ? t('btn_delete', 'ডিলিট করুন') : 'ডিলিট করুন'}" onclick="deleteChatSession('${s.id}', event)">&times;</button>
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
  const isEn = (typeof getAppLanguage === 'function' && getAppLanguage() === 'en');
  try {
    const res = await fetch('/api/sessions', {
      method: 'POST',
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: isEn ? 'New Chat' : 'নতুন চ্যাট' })
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
      showToast(typeof t === 'function' ? t('toast_session_created', 'নতুন চ্যাট সেশন শুরু হয়েছে।') : 'নতুন চ্যাট সেশন শুরু হয়েছে।', 'info');
      return currentSessionId;
    }
  } catch (err) {
    showToast((isEn ? 'Session error: ' : 'সেশন তৈরিতে সমস্যা: ') + err.message, 'error');
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
  const isEn = (typeof getAppLanguage === 'function' && getAppLanguage() === 'en');
  if (!confirm(isEn ? 'Are you sure you want to delete this chat session?' : 'আপনি কি এই চ্যাট সেশনটি মুছে ফেলতে চান?')) return;

  try {
    const res = await fetch(`/api/sessions/${sessionId}`, {
      method: 'DELETE',
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {}
    });
    if (res.ok) {
      showToast(isEn ? 'Chat session deleted.' : 'চ্যাট সেশন মুছে ফেলা হয়েছে।', 'info');
      if (currentSessionId === sessionId) {
        currentSessionId = null;
        await createNewChatSession();
      } else {
        await loadChatSessions();
      }
    }
  } catch (err) {
    showToast((isEn ? 'Delete failed: ' : 'ডিলিট ব্যর্থ: ') + err.message, 'error');
  }
}

// Model Switcher from Topbar
function onModelSelectChange(newModel) {
  const isEn = (typeof getAppLanguage === 'function' && getAppLanguage() === 'en');
  fetch('/api/settings', {
    method: 'POST',
    headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : { 'Content-Type': 'application/json' },
    body: JSON.stringify({ llm_model: newModel })
  }).then(res => {
    if (res.ok) {
      showToast((isEn ? 'Active Model: ' : 'সক্রিয় মডেল: ') + newModel, 'success');
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
    prompt = typeof t === 'function' 
      ? t('default_attach_prompt', 'অনুগ্রহ করে সংযুক্ত ফাইলগুলো বিশ্লেষণ করে বিস্তারিত সারসংক্ষেপ ও অন্তর্দৃষ্টি তুলে ধরুন।') 
      : 'অনুগ্রহ করে সংযুক্ত ফাইলগুলো বিশ্লেষণ করে বিস্তারিত সারসংক্ষেপ ও অন্তর্দৃষ্টি তুলে ধরুন।';
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
    const saveToMemoryCheckbox = document.getElementById('chat-save-memory-checkbox');
    const shouldSaveToMemory = saveToMemoryCheckbox ? saveToMemoryCheckbox.checked : false;
    const isEn = typeof getAppLanguage === 'function' && getAppLanguage() === 'en';

    const actionText = shouldSaveToMemory 
      ? (isEn ? 'Uploading and indexing into persistent memory...' : 'আপলোড ও স্থায়ী মেমোরিতে ইনডেক্সিং হচ্ছে...')
      : (isEn ? 'Uploading and preparing for chat analysis...' : 'আপলোড ও চ্যাট বিশ্লেষণের জন্য প্রস্তুত হচ্ছে...');
    showUploadProgress(isEn ? `${attachedChatFiles.length} file(s) ${actionText}` : `${attachedChatFiles.length}টি ফাইল ${actionText}`);
    try {
      const formData = new FormData();
      for (const item of attachedChatFiles) {
        formData.append('files', item.file, item.name);
      }
      formData.append('save_to_memory', shouldSaveToMemory ? 'true' : 'false');

      const uploadHeaders = typeof getAuthHeaders === 'function' ? getAuthHeaders() : {};
      delete uploadHeaders['Content-Type'];

      const uploadRes = await fetch('/api/chat/upload', {
        method: 'POST',
        headers: uploadHeaders,
        body: formData
      });

      if (!uploadRes.ok) {
        const errJson = await uploadRes.json().catch(() => ({}));
        throw new Error(errJson.detail || (isEn ? 'File upload failed' : 'ফাইল আপলোড ব্যর্থ হয়েছে'));
      }

      const uploadData = await uploadRes.json();
      serverAttachedFiles = uploadData.files || [];

      attachedFilesForDisplay = serverAttachedFiles.map(f => ({
        name: f.filename,
        filename: f.filename,
        size: f.size_bytes || f.size || 0,
        extension: f.extension || f.filename.split('.').pop(),
        doc_id: f.doc_id,
        saved_to_memory: f.saved_to_memory === true
      }));

      // Free local object URLs and clear shelf
      attachedChatFiles.forEach(item => {
        if (item.previewUrl) URL.revokeObjectURL(item.previewUrl);
      });
      attachedChatFiles = [];
      renderAttachmentShelf();

      const successToast = shouldSaveToMemory 
        ? (isEn ? `${serverAttachedFiles.length} file(s) successfully attached and saved into permanent memory.` : `${serverAttachedFiles.length}টি ফাইল সফলভাবে যুক্ত ও স্থায়ী মেমোরিতে সংরক্ষিত হয়েছে`)
        : (isEn ? `${serverAttachedFiles.length} file(s) prepared for chat analysis.` : `${serverAttachedFiles.length}টি ফাইল চ্যাট বিশ্লেষণের জন্য প্রস্তুত করা হয়েছে`);
      showToast(successToast, 'success');

    } catch (uploadErr) {
      showToast((isEn ? 'File processing error: ' : 'ফাইল প্রসেসিং ত্রুটি: ') + uploadErr.message, 'error');
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
    sendBtn.title = typeof t === 'function' ? t('btn_stop_title', 'Stop Generating') : 'উত্তর তৈরি থামান (Stop Generating)';
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
        attached_files: serverAttachedFiles,
        language: typeof getAppLanguage === 'function' ? getAppLanguage() : 'bn'
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
              const callingLabel = typeof t === 'function' ? t('calling_tool', 'টুল কল করা হচ্ছে:') : 'টুল কল করা হচ্ছে:';
              assistantContent += `\n\n⚙️ *[${callingLabel} **${data.name}**...]*\n`;
              updateAssistantMessage(assistantBubble, assistantContent, true);
            } else if (data.type === 'tool_result') {
              const resLabel = typeof t === 'function' ? t('tool_result', 'ফলাফল') : 'ফলাফল';
              assistantContent += `\n> 💡 **[${data.name} ${resLabel}]:**\n> \`\`\`\n> ${escapeHtml(data.result).slice(0, 500)}\n> \`\`\`\n\n`;
              updateAssistantMessage(assistantBubble, assistantContent, true);
            } else if (data.type === 'token') {
              assistantContent += data.token;
              updateAssistantMessage(assistantBubble, assistantContent, true);
            } else if (data.type === 'error') {
              const errLabel = typeof t === 'function' ? t('error_prefix', 'ত্রুটি:') : 'ত্রুটি:';
              assistantContent += `\n\n⚠️ **${errLabel}** ${data.error}`;
              updateAssistantMessage(assistantBubble, assistantContent, false);
            }
          } catch (parseErr) {
            console.warn('SSE Parse notice:', parseErr);
          }
        }
      }
    }

    // Finalize assistant message
    const doneFallback = typeof getAppLanguage === 'function' && getAppLanguage() === 'en' ? 'Response completed.' : 'উত্তর প্রক্রিয়া সম্পন্ন হয়েছে।';
    updateAssistantMessage(assistantBubble, assistantContent || doneFallback, false, citations);
    conversationHistory.push({ role: 'assistant', content: assistantContent });
    loadChatSessions();

  } catch (err) {
    const isEn = typeof getAppLanguage === 'function' && getAppLanguage() === 'en';
    if (err.name === 'AbortError') {
      const stopText = typeof t === 'function' ? t('stopped_by_user', 'ব্যবহারকারী কর্তৃক উত্তর তৈরি থামানো হয়েছে') : 'ব্যবহারকারী কর্তৃক উত্তর তৈরি থামানো হয়েছে';
      assistantContent += `\n\n⏹️ *[${stopText}]*`;
      updateAssistantMessage(assistantBubble, assistantContent, false);
    } else {
      const serverErrText = typeof t === 'function' ? t('server_error_prefix', 'সার্ভার সমস্যা:') : 'সার্ভার সমস্যা:';
      const noteText = isEn ? 'Please make sure the backend service is active.' : 'অনুগ্রহ করে নিশ্চিত করুন যে ব্যাকএন্ড সার্ভিসটি সক্রিয় রয়েছে।';
      assistantContent += `\n\n❌ **${serverErrText}** ${err.message}। ${noteText}`;
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
      sendBtn.title = typeof t === 'function' ? t('btn_send_title', 'Send Message (Enter)') : 'বার্তা পাঠান (Enter)';
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
  const senderTitle = role === 'user' 
    ? (typeof t === 'function' ? t('sender_you', 'আপনি') : 'আপনি')
    : (typeof t === 'function' ? t('sender_ai', 'MyAgent AI') : 'MyAgent AI');

  const avatarStyle = role === 'assistant' 
    ? 'background: linear-gradient(135deg, #4285f4, #9b72cb); color: #ffffff; box-shadow: 0 0 12px rgba(155, 114, 203, 0.45);' 
    : '';

  let attachmentHtml = '';
  if (attachedFiles && attachedFiles.length > 0) {
    const savedBadgeText = typeof t === 'function' ? t('file_saved_badge', '✅ মেমোরিতে সংরক্ষিত') : '✅ মেমোরিতে সংরক্ষিত';
    const savedBadgeTitle = typeof t === 'function' ? t('file_saved_title', 'এই ফাইলটি কোম্পানির স্থায়ী মেমোরিতে সংরক্ষিত') : 'এই ফাইলটি কোম্পানির স্থায়ী মেমোরিতে সংরক্ষিত';
    const saveBtnText = typeof t === 'function' ? t('file_save_btn', '💾 মেমোরিতে সেভ করুন') : '💾 মেমোরিতে সেভ করুন';
    const saveBtnTitle = typeof t === 'function' ? t('file_save_title', 'ব্যবহারকারী/অ্যাডমিন সিদ্ধান্ত: ক্লিক করলে এই ফাইলটি স্থায়ী মেমোরিতে সংরক্ষিত হবে') : 'ব্যবহারকারী/অ্যাডমিন সিদ্ধান্ত: ক্লিক করলে এই ফাইলটি স্থায়ী মেমোরিতে সংরক্ষিত হবে';

    attachmentHtml = `
      <div class="user-attached-files-container" style="display: flex; flex-direction: column; gap: 8px; margin-bottom: 8px; width: 100%;">
        ${attachedFiles.map(f => {
          const docId = f.doc_id || '';
          const fname = f.name || f.filename || '';
          const isSaved = f.saved_to_memory === true;
          const curation = f.ai_curation || null;
          const isEn = typeof getAppLanguage === 'function' && getAppLanguage() === 'en';

          if (curation) {
            window._curations = window._curations || {};
            window._curations[docId] = curation;
          }

          let curationHtml = '';
          if (curation && !isSaved) {
            const docType = isEn ? (curation.doc_type_en || curation.doc_type_bn) : (curation.doc_type_bn || curation.doc_type_en);
            const thought = isEn ? (curation.ai_thought_en || curation.ai_thought_bn) : (curation.ai_thought_bn || curation.ai_thought_en);
            const facts = isEn ? (curation.distilled_facts_en || curation.distilled_facts_bn || []) : (curation.distilled_facts_bn || curation.distilled_facts_en || []);
            const noise = isEn ? (curation.noise_filtered_en || curation.noise_filtered_bn) : (curation.noise_filtered_bn || curation.noise_filtered_en);
            
            const recClass = curation.recommended_action === 'SAVE_CURATED_PERMANENT' ? 'rec-save' : (curation.recommended_action === 'TEMPORARY_CHAT_ONLY' ? 'rec-temp' : 'rec-review');
            const recText = isEn 
              ? (curation.recommended_action === 'SAVE_CURATED_PERMANENT' ? 'Recommended: Save to Memory' : (curation.recommended_action === 'TEMPORARY_CHAT_ONLY' ? 'Temporary Analysis' : 'User Review'))
              : (curation.recommended_action === 'SAVE_CURATED_PERMANENT' ? 'প্রস্তাবিত: মেমোরিতে সংরক্ষণ' : (curation.recommended_action === 'TEMPORARY_CHAT_ONLY' ? 'সাময়িক বিশ্লেষণ' : 'পর্যালোচনা প্রয়োজন'));

            curationHtml = `
              <div class="ai-curation-card" id="curation-card-${escapeHtml(docId)}">
                <div class="curation-header">
                  <div class="curation-title">
                    <span class="curation-brain-icon">🧠</span>
                    <span>${typeof t === 'function' ? t('curation_badge', 'AI মেমোরি বিশ্লেষণ') : 'AI মেমোরি বিশ্লেষণ'} • <strong>${escapeHtml(docType)}</strong></span>
                  </div>
                  <span class="curation-rec-badge ${recClass}">${escapeHtml(recText)}</span>
                </div>
                <div class="curation-thought">
                  <em>"${escapeHtml(thought)}"</em>
                </div>
                ${facts.length > 0 ? `
                  <div class="curation-facts">
                    <div class="curation-facts-title">${typeof t === 'function' ? t('curation_facts_heading', 'স্থায়ী কর্পোরেট জ্ঞান ও ফ্যাক্টস') : 'স্থায়ী কর্পোরেট জ্ঞান ও ফ্যাক্টস'}</div>
                    <ul>
                      ${facts.slice(0, 4).map(fc => `<li>${escapeHtml(fc)}</li>`).join('')}
                    </ul>
                  </div>
                ` : ''}
                ${noise ? `
                  <div class="curation-noise-bar">
                    <span>🧹 ${escapeHtml(noise)}</span>
                  </div>
                ` : ''}
                <div class="curation-actions">
                  <button type="button" class="btn-curate-save" onclick="saveCuratedMemory('${escapeHtml(docId)}', '${escapeHtml(fname)}', window._curations['${escapeHtml(docId)}'], this)">
                    ${typeof t === 'function' ? t('curation_btn_curated', '💾 এআই কিউরেটেড মেমোরি সংরক্ষণ (প্রস্তাবিত)') : '💾 এআই কিউরেটেড মেমোরি সংরক্ষণ (প্রস্তাবিত)'}
                  </button>
                  <button type="button" class="btn-curate-raw" onclick="saveAttachedFileToMemory('${escapeHtml(docId)}', '${escapeHtml(fname)}', this)">
                    ${typeof t === 'function' ? t('curation_btn_raw', '📦 সম্পূর্ণ ফাইল মেমোরিতে সেভ') : '📦 সম্পূর্ণ ফাইল মেমোরিতে সেভ'}
                  </button>
                </div>
              </div>
            `;
          }

          return `
            <div class="user-attached-file-wrapper" style="width: 100%;">
              <div class="user-attached-file-chip" data-doc-id="${escapeHtml(docId)}">
                <span>${getFileBadgeIcon(fname)}</span>
                <span>${escapeHtml(fname)}</span>
                <span style="opacity: 0.75; font-size: 0.72rem;">(${formatFileSize(f.size || 0)})</span>
                ${isSaved 
                  ? `<span class="chip-memory-badge saved" title="${escapeHtml(savedBadgeTitle)}">${escapeHtml(savedBadgeText)}</span>`
                  : `<button type="button" class="chip-save-memory-btn" onclick="saveAttachedFileToMemory('${escapeHtml(docId)}', '${escapeHtml(fname)}', this)" title="${escapeHtml(saveBtnTitle)}">${escapeHtml(saveBtnText)}</button>`
                }
              </div>
              ${curationHtml}
            </div>
          `;
        }).join('')}
      </div>
    `;
  }

  messageEl.innerHTML = `
    <div class="chat-avatar" style="${avatarStyle}">${avatar}</div>
    <div class="message-content-wrapper">
      <div class="message-sender-name" data-role="${role}">${senderTitle}</div>
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
      const isEn = typeof getAppLanguage === 'function' && getAppLanguage() === 'en';
      const headerTitle = isEn 
        ? `📑 Memory References & Sources (${validCitations.length})` 
        : `📑 মেমোরি রেফারেন্স ও সোর্স (${validCitations.length}টি)`;
      const pageLabel = typeof t === 'function' ? t('sources_page', 'পৃষ্ঠা') : 'পৃষ্ঠা';
      const matchLabel = typeof t === 'function' ? t('sources_match', 'মিল') : 'মিল';

      sourcesSlot.innerHTML = `
        <div class="sources-container">
          <div class="sources-header">
            <span>${headerTitle}</span>
          </div>
          <div class="sources-list">
            ${validCitations.map(c => `
              <span class="citation-chip" title="${escapeHtml(c.content)}">
                📄 ${escapeHtml(c.source)} (${pageLabel} ${c.page || 1}) • ${(c.score * 100).toFixed(0)}% ${matchLabel}
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

        const copyBtn = typeof t === 'function' ? t('msg_copy_btn', 'কপি') : 'কপি';
        const copyTitle = typeof t === 'function' ? t('msg_copy_title', 'কপি করুন') : 'কপি করুন';
        const saveMemBtn = typeof t === 'function' ? t('msg_save_mem_btn', 'মেমোরিতে সেভ') : 'মেমোরিতে সেভ';
        const saveMemTitle = typeof t === 'function' ? t('msg_save_mem_title', 'এআই-এর উত্তরটি কোম্পানির স্থায়ী মেমোরিতে সেভ করুন') : 'এআই-এর উত্তরটি কোম্পানির স্থায়ী মেমোরিতে সেভ করুন';
        const retryBtn = typeof t === 'function' ? t('msg_retry_btn', 'রিট্রাই') : 'রিট্রাই';
        const retryTitle = typeof t === 'function' ? t('msg_retry_title', 'পুনরায় চেষ্টা করুন') : 'পুনরায় চেষ্টা করুন';
        const likeTitle = typeof t === 'function' ? t('msg_like_title', 'পছন্দ হয়েছে') : 'পছন্দ হয়েছে';
        const dislikeTitle = typeof t === 'function' ? t('msg_dislike_title', 'অপছন্দ হয়েছে') : 'অপছন্দ হয়েছে';

        toolbar.innerHTML = `
          <button class="msg-tool-btn msg-tool-copy" onclick="copyMessageText(this)" title="${escapeHtml(copyTitle)}">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
            <span class="btn-label">${escapeHtml(copyBtn)}</span>
          </button>
          <button class="msg-tool-btn msg-tool-save" onclick="saveMsgToAgentMemory(this)" title="${escapeHtml(saveMemTitle)}">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>
            <span class="btn-label">${escapeHtml(saveMemBtn)}</span>
          </button>
          <button class="msg-tool-btn msg-tool-retry" onclick="retryLastPrompt()" title="${escapeHtml(retryTitle)}">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>
            <span class="btn-label">${escapeHtml(retryBtn)}</span>
          </button>
          <button class="msg-tool-btn msg-tool-like" onclick="toggleMsgLike(this, 'like')" title="${escapeHtml(likeTitle)}">👍</button>
          <button class="msg-tool-btn msg-tool-dislike" onclick="toggleMsgLike(this, 'dislike')" title="${escapeHtml(dislikeTitle)}">👎</button>
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
    const copyCodeLabel = typeof t === 'function' ? t('msg_copy_code', 'Copy Code') : 'Copy Code';
    return `<div class="chatgpt-code-box">
      <div class="code-box-header">
        <span class="code-lang-label">${displayLang}</span>
        <button class="copy-code-btn" type="button" onclick="copyCodeBlock(this, '${codeId}')">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
          ${copyCodeLabel}
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
  const copiedBadge = typeof t === 'function' ? t('copied_badge', '✓ Copied!') : '✓ Copied!';
  const copyFailed = typeof t === 'function' ? t('copy_failed', 'Failed to copy to clipboard') : 'Failed to copy to clipboard';
  navigator.clipboard.writeText(text).then(() => {
    const originalText = btn.innerHTML;
    btn.innerHTML = copiedBadge;
    btn.style.color = '#34d399';
    setTimeout(() => {
      btn.innerHTML = originalText;
      btn.style.color = '';
    }, 2000);
  }).catch(() => {
    showToast(copyFailed, 'error');
  });
}

function copyMessageText(btn) {
  const bubble = btn.closest('.message-bubble');
  if (!bubble) return;
  const textEl = bubble.querySelector('.message-text');
  if (!textEl) return;
  const text = textEl.innerText || textEl.textContent;
  const copiedBadge = typeof t === 'function' ? t('copied_badge', '✓ Copied!') : '✓ Copied!';
  const copyFailed = typeof t === 'function' ? t('copy_failed', 'Failed to copy to clipboard') : 'Failed to copy to clipboard';
  navigator.clipboard.writeText(text).then(() => {
    const originalText = btn.innerHTML;
    btn.innerHTML = copiedBadge;
    btn.style.color = '#34d399';
    setTimeout(() => {
      btn.innerHTML = originalText;
      btn.style.color = '';
    }, 2000);
  }).catch(() => {
    showToast(copyFailed, 'error');
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
    showToast(typeof t === 'function' ? t('toast_feedback_like', 'Thank you for your feedback!') : 'Thank you for your feedback!', 'success');
  } else {
    btn.classList.toggle('active-dislike');
    showToast(typeof t === 'function' ? t('toast_feedback_dislike', 'Feedback recorded. We are improving the model.') : 'Feedback recorded. We are improving the model.', 'info');
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
    showToast(typeof t === 'function' && getAppLanguage() === 'en' ? 'Please provide both title and detailed content.' : 'দয়া করে শিরোনাম ও বিস্তারিত কনটেন্ট লিখুন', 'error');
    return;
  }

  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerText = typeof t === 'function' ? t('saving_text', 'Saving...') : 'সেভ হচ্ছে...';
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
      throw new Error(err.detail || (typeof getAppLanguage === 'function' && getAppLanguage() === 'en' ? 'Failed to save memory' : 'মেমোরি সেভ ব্যর্থ হয়েছে'));
    }

    const data = await res.json();
    showToast(data.message || (typeof getAppLanguage === 'function' && getAppLanguage() === 'en' ? 'Note successfully saved to memory!' : 'নোট সফলভাবে মেমোরিতে সংরক্ষিত হয়েছে!'), 'success');
    titleInput.value = '';
    contentInput.value = '';
    closeQuickMemoryModal();

    if (typeof loadDocumentList === 'function') loadDocumentList();
    if (typeof loadMemoryStats === 'function') loadMemoryStats();
    if (typeof loadChunksList === 'function') loadChunksList();
  } catch (err) {
    showToast(`Error: ${err.message}`, 'error');
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerText = typeof t === 'function' ? t('btn_save_memory', 'Save to Memory') : 'মেমোরিতে সেভ করুন';
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

  const defaultNoteTitle = typeof t === 'function' ? t('chat_note_default', 'Chat Note') : 'Chat Note';
  const firstLine = content.split('\n')[0].replace(/^[#\*\s\-]+/, '').trim().slice(0, 45) || defaultNoteTitle;
  const originalHtml = btn.innerHTML;
  btn.disabled = true;
  btn.innerText = typeof t === 'function' ? t('saving_text', 'Saving...') : 'Saving...';

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
      btn.innerHTML = typeof t === 'function' ? t('saved_badge', '✓ Saved!') : '✓ Saved!';
      btn.style.color = '#34d399';
      const isEn = typeof getAppLanguage === 'function' && getAppLanguage() === 'en';
      showToast(isEn ? `'${firstLine}' successfully saved to company permanent memory!` : `'${firstLine}' সফলভাবে এজেন্টের স্থায়ী মেমোরিতে সেভ হয়েছে!`, 'success');
      setTimeout(() => {
        btn.innerHTML = originalHtml;
        btn.style.color = '';
        btn.disabled = false;
      }, 3000);
    } else {
      throw new Error(typeof getAppLanguage === 'function' && getAppLanguage() === 'en' ? 'Failed to save on server' : 'সার্ভারে সেভ করা যায়নি');
    }
  } catch (err) {
    btn.innerHTML = originalHtml;
    btn.disabled = false;
    showToast(typeof getAppLanguage === 'function' && getAppLanguage() === 'en' ? 'Failed to save to memory' : 'মেমোরিতে সেভ ব্যর্থ হয়েছে', 'error');
  }
}

async function saveAttachedFileToMemory(docId, filename, btnEl) {
  if (!docId || !filename) return;
  const isEn = typeof getAppLanguage === 'function' && getAppLanguage() === 'en';
  if (btnEl) {
    btnEl.disabled = true;
    btnEl.innerText = typeof t === 'function' ? t('saving_text', 'Saving...') : 'সংরক্ষণ হচ্ছে...';
  }
  try {
    const res = await fetch('/api/chat/save-attachment-to-memory', {
      method: 'POST',
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : { 'Content-Type': 'application/json' },
      body: JSON.stringify({ doc_id: docId, filename: filename })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || (isEn ? 'Failed to save to memory' : 'মেমোরিতে সংরক্ষণ ব্যর্থ হয়েছে'));

    const successMsg = isEn 
      ? `'${filename}' successfully saved into permanent company memory!` 
      : (data.message || `'${filename}' সফলভাবে কোম্পানির স্থায়ী মেমোরিতে সংরক্ষণ করা হয়েছে!`);
    showToast(successMsg, 'success');

    if (btnEl) {
      const badge = document.createElement('span');
      badge.className = 'chip-memory-badge saved';
      badge.title = typeof t === 'function' ? t('file_saved_title', 'This file is saved in company persistent memory') : 'কোম্পানির স্থায়ী মেমোরিতে সংরক্ষিত';
      badge.innerText = typeof t === 'function' ? t('file_saved_badge', '✅ Saved in Memory') : '✅ মেমোরিতে সংরক্ষিত';
      btnEl.replaceWith(badge);
    }
  } catch (err) {
    showToast((isEn ? 'Memory save error: ' : 'মেমোরি সংরক্ষণ ত্রুটি: ') + err.message, 'error');
    if (btnEl) {
      btnEl.disabled = false;
      btnEl.innerText = typeof t === 'function' ? t('file_save_btn', '💾 Save to Memory') : '💾 মেমোরিতে সেভ করুন';
    }
  }
}

async function saveCuratedMemory(docId, filename, curation, btnEl) {
  if (!docId || !filename) return;
  const isEn = typeof getAppLanguage === 'function' && getAppLanguage() === 'en';
  const originalText = btnEl ? btnEl.innerText : '';
  if (btnEl) {
    btnEl.disabled = true;
    btnEl.innerText = typeof t === 'function' ? t('saving_text', 'Saving...') : 'সংরক্ষণ হচ্ছে...';
  }

  try {
    const res = await fetch('/api/chat/save-curated-memory', {
      method: 'POST',
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        doc_id: docId,
        filename: filename,
        curation: curation || (window._curations ? window._curations[docId] : null)
      })
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || (isEn ? 'Failed to save curated memory' : 'কিউরেটেড মেমোরি সংরক্ষণ ব্যর্থ হয়েছে'));
    }

    const successMsg = isEn
      ? `'${filename}' AI curated facts saved to permanent memory (${data.chunks_indexed || 1} chunks)!`
      : (data.message || `'${filename}'-এর এআই কিউরেটেড ফ্যাক্টস কোম্পানির স্থায়ী মেমোরিতে সংরক্ষিত হয়েছে!`);
    showToast(successMsg, 'success');

    // Find curation card actions container and replace with saved badge
    const curationCard = btnEl ? btnEl.closest('.ai-curation-card') : null;
    if (curationCard) {
      const actionsDiv = curationCard.querySelector('.curation-actions');
      if (actionsDiv) {
        actionsDiv.innerHTML = `
          <div class="curation-saved-badge">
            ${typeof t === 'function' ? t('curation_saved_success', '✅ এআই কিউরেটেড মেমোরি সংরক্ষিত হয়েছে') : '✅ এআই কিউরেটেড মেমোরি সংরক্ষিত হয়েছে'} (${data.chunks_indexed || 1} chunks)
          </div>
        `;
      }
    }

    // Also update chip badge if present
    const chip = document.querySelector(`.user-attached-file-chip[data-doc-id="${docId}"]`);
    if (chip) {
      const existingBtn = chip.querySelector('.chip-save-memory-btn');
      if (existingBtn) {
        const badge = document.createElement('span');
        badge.className = 'chip-memory-badge saved';
        badge.title = isEn ? 'AI Curated memory saved' : 'এআই কিউরেটেড মেমোরি সংরক্ষিত';
        badge.innerText = isEn ? '✅ Curated Saved' : '✅ কিউরেটেড সংরক্ষিত';
        existingBtn.replaceWith(badge);
      }
    }
  } catch (err) {
    showToast((isEn ? 'Curated save error: ' : 'কিউরেটেড মেমোরি ত্রুটি: ') + err.message, 'error');
    if (btnEl) {
      btnEl.disabled = false;
      btnEl.innerText = originalText;
    }
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

// Listen for Language Switch Events
window.addEventListener('appLanguageChanged', (e) => {
  const lang = e.detail && e.detail.language ? e.detail.language : 'bn';
  if (typeof t === 'function') {
    document.title = t('app_title', document.title);
    const metaDesc = document.querySelector('meta[name="description"]');
    if (metaDesc) {
      metaDesc.setAttribute('content', t('app_description', metaDesc.getAttribute('content')));
    }
    const statusText = document.getElementById('agent-online-status');
    if (statusText) {
      statusText.innerText = isServerHealthy ? t('status_online', 'অনলাইন') : t('status_offline', 'অফলাইন');
    }
    const memToggleText = document.getElementById('memory-toggle-text');
    if (memToggleText) {
      memToggleText.innerText = useMemory 
        ? (lang === 'en' ? 'Memory: Active' : 'মেমোরি: সক্রিয়')
        : (lang === 'en' ? 'Memory: Disabled' : 'মেমোরি: নিষ্ক্রিয়');
    }

    // Update active tab topbar texts
    const activeTabBtn = document.querySelector('.nav-btn.active');
    if (activeTabBtn && activeTabBtn.id) {
      const tabKey = activeTabBtn.id.replace('nav-', '').replace('-btn', '');
      const tabTitles = {
        chat: { title: 'tab_chat_title', desc: 'tab_chat_desc' },
        admin: { title: 'tab_admin_title', desc: 'tab_admin_desc' },
        dashboard: { title: 'tab_dash_title', desc: 'tab_dash_desc' },
        users: { title: 'tab_users_title', desc: 'tab_users_desc' },
        knowledge: { title: 'tab_kb_title', desc: 'tab_kb_desc' },
        models: { title: 'tab_models_title', desc: 'tab_models_desc' },
        mcp: { title: 'tab_mcp_title', desc: 'tab_mcp_desc' },
        security: { title: 'tab_sec_title', desc: 'tab_sec_desc' },
        backup: { title: 'tab_backup_title', desc: 'tab_backup_desc' },
        reports: { title: 'tab_reports_title', desc: 'tab_reports_desc' },
        settings: { title: 'tab_settings_title', desc: 'tab_settings_desc' }
      };
      if (tabTitles[tabKey]) {
        const topbarTitle = document.getElementById('topbar-title-text');
        const topbarDesc = document.getElementById('topbar-desc-text');
        if (topbarTitle) topbarTitle.innerText = t(tabTitles[tabKey].title);
        if (topbarDesc) topbarDesc.innerText = t(tabTitles[tabKey].desc);
      }
    }

    // Update existing user & assistant message headers in chat feed
    document.querySelectorAll('.chat-message.user-message .message-sender-name').forEach(el => {
      el.innerText = t('sender_you', 'You');
    });
    document.querySelectorAll('.chat-message.assistant-message .message-sender-name').forEach(el => {
      el.innerText = t('sender_ai', 'MyAgent AI');
    });

    // Update existing action toolbars
    document.querySelectorAll('.msg-action-toolbar').forEach(tb => {
      const copyBtn = tb.querySelector('.msg-tool-copy');
      if (copyBtn) {
        copyBtn.title = t('msg_copy_title');
        const lbl = copyBtn.querySelector('.btn-label');
        if (lbl) lbl.innerText = t('msg_copy_btn');
      }
      const saveBtn = tb.querySelector('.msg-tool-save');
      if (saveBtn) {
        saveBtn.title = t('msg_save_mem_title');
        const lbl = saveBtn.querySelector('.btn-label');
        if (lbl) lbl.innerText = t('msg_save_mem_btn');
      }
      const retryBtn = tb.querySelector('.msg-tool-retry');
      if (retryBtn) {
        retryBtn.title = t('msg_retry_title');
        const lbl = retryBtn.querySelector('.btn-label');
        if (lbl) lbl.innerText = t('msg_retry_btn');
      }
      const likeBtn = tb.querySelector('.msg-tool-like');
      if (likeBtn) likeBtn.title = t('msg_like_title');
      const dislikeBtn = tb.querySelector('.msg-tool-dislike');
      if (dislikeBtn) dislikeBtn.title = t('msg_dislike_title');
    });

    // Update existing code block copy buttons
    document.querySelectorAll('.copy-code-btn').forEach(btn => {
      if (!btn.innerText.includes('✓')) {
        btn.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg> ${t('msg_copy_code', 'Copy Code')}`;
      }
    });

    // Update existing attached file chips
    document.querySelectorAll('.chip-memory-badge.saved').forEach(badge => {
      badge.innerText = t('file_saved_badge');
      badge.title = t('file_saved_title');
    });
    document.querySelectorAll('.chip-save-memory-btn').forEach(btn => {
      btn.innerText = t('file_save_btn');
      btn.title = t('file_save_title');
    });

    // Update attachment shelf if currently visible
    if (attachedChatFiles && attachedChatFiles.length > 0) {
      renderAttachmentShelf();
    }

    // Re-render the active view so its tables, badges, and statuses update immediately in the chosen language
    const activeViewEl = document.querySelector('.tab-view.active');
    if (activeViewEl) {
      const activeId = activeViewEl.id;
      if (activeId === 'view-admin' && typeof loadAdminDashboard === 'function') loadAdminDashboard();
      else if (activeId === 'view-dashboard' && typeof loadDashboardFull === 'function') loadDashboardFull();
      else if (activeId === 'view-users' && typeof loadUsersList === 'function') loadUsersList();
      else if (activeId === 'view-knowledge') {
        if (typeof loadDocumentList === 'function') loadDocumentList();
        if (typeof loadChunksList === 'function') loadChunksList(typeof currentChunksPage !== 'undefined' ? currentChunksPage : 0);
      } else if (activeId === 'view-models' && typeof loadModelsOverview === 'function') loadModelsOverview();
      else if (activeId === 'view-mcp' && typeof loadMcpDashboard === 'function') loadMcpDashboard();
      else if (activeId === 'view-security' && typeof loadSecurityDashboard === 'function') loadSecurityDashboard();
      else if (activeId === 'view-backup' && typeof loadBackupDashboard === 'function') loadBackupDashboard();
      else if (activeId === 'view-reports' && typeof loadReportsPage === 'function') loadReportsPage();
      else if (activeId === 'view-settings' && typeof loadSettingsHub === 'function') loadSettingsHub();
    }
  }
});

