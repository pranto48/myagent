// Main Application Logic, Chat Streaming & UI Interactions

let currentSessionId = null;
let conversationHistory = [];
let isGenerating = false;
let useMemory = true;

// Tab Switching
function switchTab(tabName) {
  const chatView = document.getElementById('view-chat');
  const knowledgeView = document.getElementById('view-knowledge');
  const navChatBtn = document.getElementById('nav-chat-btn');
  const navKnowledgeBtn = document.getElementById('nav-knowledge-btn');
  const topbarTitle = document.getElementById('topbar-title-text');
  const topbarDesc = document.getElementById('topbar-desc-text');

  if (tabName === 'chat') {
    chatView.classList.add('active');
    knowledgeView.classList.remove('active');
    navChatBtn.classList.add('active');
    navKnowledgeBtn.classList.remove('active');
    topbarTitle.innerText = 'কোম্পানি ডেটা ইন্টেলিজেন্স এজেন্ট';
    topbarDesc.innerText = 'ওপেনক্ল-স্টাইল পারসিসটেন্ট মেমোরি ও অটোনোমাস কোম্পানি এআই';
  } else {
    chatView.classList.remove('active');
    knowledgeView.classList.add('active');
    navChatBtn.classList.remove('active');
    navKnowledgeBtn.classList.add('active');
    topbarTitle.innerText = 'কোম্পানি নলেজবেস ও মেমোরি ম্যানেজার';
    topbarDesc.innerText = 'কোম্পানির ফাইল ইনডেক্সিং এবং ভেক্টর সার্চ অডিট';
    loadDocumentList();
    loadMemoryStats();
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
    label.innerText = 'কোম্পানি মেমোরি: সক্রিয়';
    btn.style.borderColor = 'rgba(6, 182, 212, 0.4)';
    btn.style.color = 'var(--cyan-glow)';
  } else {
    icon.innerText = '⚡';
    label.innerText = 'মেমোরি: নিষ্ক্রিয় (সরাসরি এলএলএম)';
    btn.style.borderColor = 'rgba(255, 255, 255, 0.15)';
    btn.style.color = 'var(--text-muted)';
  }
}

// Textarea Auto-resize
function autoResizeTextarea(textarea) {
  textarea.style.height = 'auto';
  textarea.style.height = Math.min(textarea.scrollHeight, 160) + 'px';
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

// ==============================================================================
// Persistent Chat Sessions Management
// ==============================================================================
async function loadChatSessions() {
  const listEl = document.getElementById('sessions-list');
  if (!listEl) return;

  try {
    const res = await fetch('/api/sessions', { headers: getAuthHeaders() });
    if (res.ok) {
      const sessions = await res.json();
      if (!sessions || sessions.length === 0) {
        listEl.innerHTML = '<div style="font-size: 0.75rem; color: var(--text-muted); padding: 8px;">কোনো পূর্ববর্তী চ্যাট নেই।</div>';
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
  
  // Highlight active session item
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
      showToast(`সক্রিয় মডেল পরিবর্তন করা হয়েছে: ${newModel}`, 'success');
      const sideModel = document.getElementById('sidebar-model-name');
      if (sideModel) sideModel.innerText = newModel;
    }
  });
}

// ==============================================================================
// Send Message & Stream SSE Response
// ==============================================================================
async function sendMessage() {
  if (isGenerating) return;

  const input = document.getElementById('chat-input');
  const prompt = input.value.trim();
  if (!prompt) return;

  // Ensure session exists
  if (!currentSessionId) {
    await createNewChatSession();
  }

  // Hide empty state hero
  const hero = document.getElementById('empty-hero');
  if (hero) hero.style.display = 'none';

  // 1. Render User Message
  renderMessage('user', prompt);
  conversationHistory.push({ role: 'user', content: prompt });
  input.value = '';
  input.style.height = 'auto';

  // 2. Prepare Assistant Message Placeholder
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

    // Finalize bubble with markdown & citations
    updateAssistantMessage(assistantBubble, assistantContent, false, citations);
    conversationHistory.push({ role: 'assistant', content: assistantContent });
    
    // Refresh sessions list to update title
    loadChatSessions();

  } catch (err) {
    assistantContent += `\n\n❌ **নেটওয়ার্ক বা সার্ভার সমস্যা:** ${err.message}. নিশ্চিত করুন যে ব্যাকএন্ড সার্ভিস এবং আপনার এলএলএম সার্ভার চালু আছে।`;
    updateAssistantMessage(assistantBubble, assistantContent, false);
  } finally {
    isGenerating = false;
    document.getElementById('btn-send-message').disabled = false;
  }
}

// Render Message in DOM
function renderMessage(role, text, isStreaming = false) {
  const feed = document.getElementById('chat-feed');
  const messageEl = document.createElement('div');
  messageEl.className = `chat-message ${role}-message`;

  const avatar = role === 'user' ? '👤' : '🤖';
  const senderTitle = role === 'user' ? 'আপনি' : 'কোম্পানি এআই এজেন্ট';

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

// Update Streaming Message
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

// Lightweight Markdown Renderer
function renderMarkdown(md) {
  if (!md) return '';

  let html = md
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // Code blocks
  html = html.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (match, lang, code) => {
    return `<pre><code class="lang-${lang}">${code.trim()}</code></pre>`;
  });

  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  // Headers
  html = html.replace(/^### (.*$)/gim, '<h4>$1</h4>');
  html = html.replace(/^## (.*$)/gim, '<h3>$1</h3>');
  html = html.replace(/^# (.*$)/gim, '<h2>$1</h2>');

  // Bold & Italic
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');

  // Blockquotes
  html = html.replace(/^\> (.*$)/gim, '<blockquote>$1</blockquote>');

  // Unordered list items
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
