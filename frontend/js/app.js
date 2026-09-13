/* ==============================================================================
 * Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
 * Made By Arif (https://arifmahmud.com/)
 * Project: MyAgent | Version: 2.2.0
 * ============================================================================== */

// Main Application Logic, Mobile Drawer, Chat Streaming & UI Interactions

let currentSessionId = null;
let conversationHistory = [];
let useMemory = true;
let isStreaming = false;

// Initialize on DOM Ready
document.addEventListener('DOMContentLoaded', () => {
  initApp();
});

async function initApp() {
  checkAuthStatus();
  await loadServerStatus();
  await loadSessionHistory();
  if (typeof initDashboard === 'function') initDashboard();
}

// Mobile Sidebar Drawer Toggle
function toggleMobileSidebar() {
  const sidebar = document.getElementById('main-sidebar');
  if (sidebar) {
    sidebar.classList.toggle('mobile-open');
  }
}

// Tab Switching across all 7 views
function switchTab(tabName) {
  const tabs = ['chat', 'dashboard', 'users', 'knowledge', 'models', 'mcp', 'security'];
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
    topbarTitle.innerText = 'কোম্পানি ডেটা ইন্টেলিজেন্স এজেন্ট';
    topbarDesc.innerText = 'ওপেনক্ল-স্টাইল পারসিসটেন্ট মেমোরি ও অটোনোমাস কোম্পানি এআই';
  } else if (tabName === 'dashboard') {
    topbarTitle.innerText = 'অ্যানালিটিক্স ও সিস্টেম মনিটরিং ড্যাশবোর্ড';
    topbarDesc.innerText = 'সার্ভার পারফরম্যান্স, মেমোরি চাঙ্কস এবং স্টোরেজ অ্যানালাইসিস';
    if (typeof loadDashboardMetrics === 'function') loadDashboardMetrics();
  } else if (tabName === 'users') {
    topbarTitle.innerText = 'কোম্পানি ইউজার ও এক্সেস কন্ট্রোল';
    topbarDesc.innerText = 'অভ্যন্তরীণ কর্মকর্তা ও কর্মচারীদের রোল ম্যানেজমেন্ট';
    if (typeof loadUsersList === 'function') loadUsersList();
  } else if (tabName === 'knowledge') {
    topbarTitle.innerText = 'কোম্পানি ডেটা লাইব্রেরি ও মেমোরি ইনজেস্ট';
    topbarDesc.innerText = 'PDF, Word, Excel, CSV ও ফটো/ছবি OCR প্রসেসিং';
    if (typeof loadDocumentList === 'function') loadDocumentList();
    if (typeof loadMemoryStats === 'function') loadMemoryStats();
    if (typeof loadChunksList === 'function') loadChunksList();
  } else if (tabName === 'models') {
    topbarTitle.innerText = 'এআই মডেল হাব ও রিয়েলটাইম পিং টেস্ট';
    topbarDesc.innerText = 'বাহ্যিক এলএলএম সার্ভারের সংযোগ ও রেসপন্স টাইম (ms)';
    if (typeof loadModelsOverview === 'function') loadModelsOverview();
  } else if (tabName === 'mcp') {
    topbarTitle.innerText = 'টুলস ও মডেল কনটেক্সট প্রোটোকল (MCP) হাব';
    topbarDesc.innerText = 'ওপেন-সোর্স টুলস স্যুট ও ডায়নামিক এমসিপি সার্ভার ব্যবস্থাপনা';
    if (typeof loadMcpDashboard === 'function') loadMcpDashboard();
  } else if (tabName === 'security') {
    topbarTitle.innerText = 'এন্টারপ্রাইজ ডাটা সিকিউরিটি ও কমপ্লায়েন্স';
    topbarDesc.innerText = 'AES-256 এনক্রিপশন, PII/DLP রিডাকশন, ফায়ারওয়াল ও অডিট ট্রেইল';
    if (typeof loadSecurityDashboard === 'function') loadSecurityDashboard();
  }
}

// Memory Toggle
function toggleMemoryUsage() {
  const chk = document.getElementById('chk-use-memory');
  chk.checked = !chk.checked;
  useMemory = chk.checked;
  
  const icon = document.getElementById('memory-toggle-icon');
  const label = document.getElementById('memory-toggle-text');
  const btn = document.getElementById('memory-toggle-btn');

  if (useMemory) {
    icon.innerText = '🧠';
    label.innerText = 'মেমোরি: সক্রিয়';
    btn.style.borderColor = 'rgba(6, 182, 212, 0.4)';
    btn.style.color = 'var(--cyan-glow)';
  } else {
    icon.innerText = '⚡';
    label.innerText = 'মেমোরি: নিষ্ক্রিয়';
    btn.style.borderColor = 'rgba(255, 255, 255, 0.15)';
    btn.style.color = 'var(--text-muted)';
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
  input.value = text;
  autoResizeTextarea(input);
  sendMessage();
}

// Persistent Chat Sessions Management
async function loadChatSessions() {
  const listEl = document.getElementById('sessions-list');
  if (!listEl) return;

  try {
    const res = await fetch('/api/sessions', { headers: getAuthHeaders() });
    if (res.ok) {
      const sessions = await res.json();
      if (!sessions || sessions.length === 0) {
        listEl.innerHTML = '<div style="font-size: 0.72rem; color: var(--text-muted); padding: 6px;">কোনো পূর্ববর্তী চ্যাট নেই।</div>';
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
    }
  } catch (err) {
    console.warn('Error loading chat sessions:', err);
  }
}

async function createNewChatSession() {
  try {
    const res = await fetch('/api/sessions', {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ title: 'নতুন চ্যাট' })
    });
    if (res.ok) {
      const newSession = await res.json();
      currentSessionId = newSession.id;
      conversationHistory = [];
      
      const feed = document.getElementById('chat-feed');
      feed.innerHTML = '';
      
      const hero = document.getElementById('empty-hero');
      if (hero) {
        hero.style.display = 'flex';
        feed.appendChild(hero);
      }
      
      loadChatSessions();
      showToast('নতুন চ্যাট সেশন শুরু হয়েছে।', 'info');
    }
  } catch (err) {
    showToast(`সেশন তৈরিতে সমস্যা: ${err.message}`, 'error');
  }
}

async function switchSession(sessionId) {
  if (currentSessionId === sessionId) return;
  currentSessionId = sessionId;
  
  document.querySelectorAll('.session-item').forEach(el => el.classList.remove('active'));
  const activeEl = document.getElementById(`session-item-${sessionId}`);
  if (activeEl) activeEl.classList.add('active');

  const feed = document.getElementById('chat-feed');
  feed.innerHTML = '<div style="text-align:center; padding:30px; color:var(--text-muted);">মেসেজ লোড হচ্ছে...</div>';

  try {
    const res = await fetch(`/api/sessions/${sessionId}`, { headers: getAuthHeaders() });
    if (res.ok) {
      const data = await res.json();
      feed.innerHTML = '';
      conversationHistory = [];

      if (!data.messages || data.messages.length === 0) {
        const hero = document.getElementById('empty-hero');
        if (hero) {
          hero.style.display = 'flex';
          feed.appendChild(hero);
        }
        return;
      }

      for (const m of data.messages) {
        conversationHistory.push({ role: m.role, content: m.content });
        const bubble = renderMessage(m.role, m.content, false);
        if (m.role === 'assistant' && m.sources && m.sources.length > 0) {
          updateAssistantMessage(bubble, m.content, false, m.sources);
        }
      }
    }
  } catch (err) {
    feed.innerHTML = `<div style="color:var(--rose-red); padding:20px;">লোড ব্যর্থ: ${err.message}</div>`;
  }
}

async function deleteChatSession(sessionId, event) {
  if (event) event.stopPropagation();
  if (!confirm('আপনি কি এই চ্যাট সেশনটি মুছে ফেলতে চান?')) return;

  try {
    const res = await fetch(`/api/sessions/${sessionId}`, {
      method: 'DELETE',
      headers: getAuthHeaders()
    });
    if (res.ok) {
      showToast('চ্যাট সেশন মুছে ফেলা হয়েছে।', 'info');
      if (currentSessionId === sessionId) {
        currentSessionId = null;
        createNewChatSession();
      } else {
        loadChatSessions();
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
    headers: getAuthHeaders(),
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
  const prompt = input.value.trim();
  if (!prompt) return;

  if (!currentSessionId) {
    await createNewChatSession();
  }

  const hero = document.getElementById('empty-hero');
  if (hero) hero.style.display = 'none';

  renderMessage('user', prompt);
  conversationHistory.push({ role: 'user', content: prompt });
  input.value = '';
  input.style.height = 'auto';

  const assistantBubble = renderMessage('assistant', '', true);
  isGenerating = true;
  document.getElementById('btn-send-message').disabled = true;

  let assistantContent = '';
  let citations = [];

  try {
    const response = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        session_id: currentSessionId,
        prompt: prompt,
        history: conversationHistory.slice(-8),
        use_memory: useMemory
      })
    });

    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

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
              assistantContent += `\n> 💡 **[${data.name} রেজাল্ট]:**\n> \`\`\`\n> ${escapeHtml(data.result).slice(0, 500)}\n> \`\`\`\n\n`;
              updateAssistantMessage(assistantBubble, assistantContent, true);
            } else if (data.type === 'token') {
              assistantContent += data.token;
              updateAssistantMessage(assistantBubble, assistantContent, true);
            } else if (data.type === 'error') {
              assistantContent += `\n\n⚠️ **ত্রুটি:** ${data.error}`;
              updateAssistantMessage(assistantBubble, assistantContent, false);
            }
          } catch (parseErr) {
            console.warn('SSE Parse error:', parseErr);
          }
        }
      }
    }

    updateAssistantMessage(assistantBubble, assistantContent, false, citations);
    conversationHistory.push({ role: 'assistant', content: assistantContent });
    loadChatSessions();

  } catch (err) {
    assistantContent += `\n\n❌ **সার্ভার সমস্যা:** ${err.message}. নিশ্চিত করুন যে ব্যাকএন্ড সার্ভিস চালু আছে।`;
    updateAssistantMessage(assistantBubble, assistantContent, false);
  } finally {
    isGenerating = false;
    document.getElementById('btn-send-message').disabled = false;
  }
}

function renderMessage(role, text, isStreaming = false) {
  const feed = document.getElementById('chat-feed');
  const messageEl = document.createElement('div');
  messageEl.className = `chat-message ${role}-message`;

  const avatar = role === 'user' ? '👤' : '🤖';
  const senderTitle = role === 'user' ? 'আপনি' : 'MyAgent AI';

  messageEl.innerHTML = `
    <div class="chat-avatar">${avatar}</div>
    <div class="message-content-wrapper">
      <div class="message-sender-name">${senderTitle}</div>
      <div class="message-bubble">
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
    sourcesSlot.innerHTML = `
      <div class="sources-container">
        <div class="sources-header">
          <span>📑 মেমোরি রেফারেন্স ও সোর্স (${citations.length}টি)</span>
        </div>
        <div class="sources-list">
          ${citations.map(c => `
            <span class="citation-chip" title="${escapeHtml(c.content)}">
              📄 ${escapeHtml(c.source)} (পৃষ্ঠা ${c.page || 1}) • ${(c.score * 100).toFixed(0)}% মিল
            </span>
          `).join('')}
        </div>
      </div>
    `;
  }

  const feed = document.getElementById('chat-feed');
  feed.scrollTop = feed.scrollHeight;
}

function renderMarkdown(md) {
  if (!md) return '';

  let html = md
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  html = html.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (match, lang, code) => {
    return `<pre><code class="lang-${lang}">${code.trim()}</code></pre>`;
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
    if (p.startsWith('<pre>') || p.startsWith('<h2>') || p.startsWith('<h3>') || p.startsWith('<h4>') || p.startsWith('<ul>') || p.startsWith('<blockquote>')) {
      return p;
    }
    return `<p>${p.replace(/\n/g, '<br>')}</p>`;
  }).join('');
}

document.addEventListener('DOMContentLoaded', () => {
  loadChatSessions();
});
