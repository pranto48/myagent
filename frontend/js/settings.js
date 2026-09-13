// Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 2.2.0
// Settings and Remote LLM Connectivity Management

function showToast(message, type = 'info') {
  const shelf = document.getElementById('toast-shelf');
  if (!shelf) return;

  const toast = document.createElement('div');
  toast.className = 'toast';
  if (type === 'error') {
    toast.style.borderColor = 'rgba(244, 63, 94, 0.4)';
    toast.style.color = '#fda4af';
  } else if (type === 'success') {
    toast.style.borderColor = 'rgba(16, 185, 129, 0.4)';
    toast.style.color = '#6ee7b7';
  }
  toast.innerText = message;
  shelf.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.4s ease';
    setTimeout(() => toast.remove(), 400);
  }, 4000);
}

// ==============================================================================
// Theme Switching & Appearance Manager
// ==============================================================================

function initTheme() {
  const savedTheme = localStorage.getItem('myagent_theme') || 'dark';
  applyTheme(savedTheme, false);
}

function applyTheme(theme, notify = true) {
  let effectiveTheme = theme;
  if (theme === 'system') {
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    effectiveTheme = prefersDark ? 'dark' : 'light';
  }

  if (effectiveTheme === 'light') {
    document.documentElement.setAttribute('data-theme', 'light');
    document.body.classList.add('light-theme');
    const toggleIcon = document.getElementById('theme-toggle-icon');
    if (toggleIcon) toggleIcon.innerText = '☀️';
  } else {
    document.documentElement.setAttribute('data-theme', 'dark');
    document.body.classList.remove('light-theme');
    const toggleIcon = document.getElementById('theme-toggle-icon');
    if (toggleIcon) toggleIcon.innerText = '🌙';
  }

  localStorage.setItem('myagent_theme', theme);
  updateThemeCardSelection(theme);

  if (notify && typeof showToast === 'function') {
    if (theme === 'light') {
      showToast('☀️ লাইট মোড (Light Mode) সক্রিয় করা হয়েছে।', 'success');
    } else if (theme === 'dark') {
      showToast('🌙 ডার্ক মোড (Dark Mode) সক্রিয় করা হয়েছে।', 'success');
    } else {
      showToast('💻 সিস্টেম প্রেফারেন্স অনুযায়ী থিম স্বয়ংক্রিয়ভাবে সেট করা হয়েছে।', 'info');
    }
  }
}

function selectTheme(theme) {
  applyTheme(theme, true);
}

function toggleTheme() {
  const current = localStorage.getItem('myagent_theme') || 'dark';
  const next = current === 'light' ? 'dark' : 'light';
  applyTheme(next, true);
}

function updateThemeCardSelection(theme) {
  ['dark', 'light', 'system'].forEach(t => {
    const card = document.getElementById(`theme-card-${t}`);
    if (card) {
      if (t === theme) {
        card.classList.add('selected');
      } else {
        card.classList.remove('selected');
      }
    }
  });
}

function openSettingsModal() {
  if (typeof switchTab === 'function') {
    switchTab('settings');
  }
}

function closeSettingsModal() {
  // No modal to close in full-page mode
}

// Load current configuration
async function loadSettings() {
  try {
    const res = await fetch('/api/settings', {
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {}
    });
    if (res.ok) {
      const data = await res.json();
      const urlInput = document.getElementById('setting-llm-url');
      const modelInput = document.getElementById('setting-llm-model');
      const tempInput = document.getElementById('setting-agent-temp');
      const tempDisplay = document.getElementById('temp-val-display');

      if (urlInput) urlInput.value = data.llm_base_url || '';
      if (modelInput) modelInput.value = data.llm_model || '';
      if (tempInput) tempInput.value = data.agent_temperature || 0.3;
      if (tempDisplay) tempDisplay.innerText = data.agent_temperature !== undefined ? data.agent_temperature : '0.3';
      
      const modelLabel = document.getElementById('sidebar-model-name');
      if (modelLabel) modelLabel.innerText = data.llm_model || 'Unknown';

      // Sync topbar model dropdown
      updateModelDropdown([data.llm_model], data.llm_model);
    }
  } catch (err) {
    console.warn('Error loading settings:', err);
  }
}

const loadSettingsHub = loadSettings;

// Update Model Select Dropdown in Topbar
function updateModelDropdown(models, activeModel) {
  const select = document.getElementById('topbar-model-select');
  if (!select) return;

  const uniqueModels = Array.from(new Set([activeModel, ...(models || [])])).filter(Boolean);
  select.innerHTML = uniqueModels.map(m => `
    <option value="${m}" ${m === activeModel ? 'selected' : ''}>${m}</option>
  `).join('');
}

// Test connectivity to external LLM Server
async function testConnection() {
  const btn = document.getElementById('btn-test-conn');
  const badge = document.getElementById('test-connection-badge');
  btn.disabled = true;
  btn.innerText = 'সংযোগ পরীক্ষা করা হচ্ছে...';
  badge.style.display = 'none';

  try {
    const res = await fetch('/api/settings/test-connection', {
      method: 'POST',
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {}
    });
    const data = await res.json();

    badge.style.display = 'block';
    if (data.success) {
      badge.className = 'test-res-badge success';
      badge.innerHTML = `✅ ${data.message}<br><small>উপলব্ধ মডেল: ${data.models_available.slice(0, 5).join(', ') || 'কাস্টম মডেল সক্রিয়'}</small>`;
      showToast('এলএলএম সার্ভারের সাথে সফলভাবে সংযুক্ত হয়েছে!', 'success');
      
      if (data.models_available && data.models_available.length > 0) {
        updateModelDropdown(data.models_available, data.active_model);
      }
    } else {
      badge.className = 'test-res-badge error';
      badge.innerText = `❌ ${data.message}`;
      showToast('এলএলএম সার্ভারের সাথে সংযোগ ব্যর্থ হয়েছে।', 'error');
    }
  } catch (err) {
    badge.style.display = 'block';
    badge.className = 'test-res-badge error';
    badge.innerText = `❌ নেটওয়ার্ক ত্রুটি: ${err.message}`;
  } finally {
    btn.disabled = false;
    btn.innerText = 'সার্ভার সংযোগ টেস্ট করুন';
  }
}

// Save Settings to Backend
async function saveSettings() {
  const url = document.getElementById('setting-llm-url').value.trim();
  const model = document.getElementById('setting-llm-model').value.trim();
  const key = document.getElementById('setting-llm-key').value.trim();
  const temp = parseFloat(document.getElementById('setting-agent-temp').value);

  if (!url || !model) {
    showToast('অনুগ্রহ করে সার্ভার URL এবং মডেল নাম পূরণ করুন।', 'error');
    return;
  }

  try {
    const res = await fetch('/api/settings', {
      method: 'POST',
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        llm_base_url: url,
        llm_model: model,
        llm_api_key: key || 'not-needed',
        agent_temperature: isNaN(temp) ? 0.3 : temp
      })
    });

    if (res.ok) {
      showToast('সেটিংস সফলভাবে সংরক্ষিত হয়েছে!', 'success');
      const sideModel = document.getElementById('sidebar-model-name');
      if (sideModel) sideModel.innerText = model;
      updateModelDropdown([model], model);
    } else {
      showToast('সেটিংস সেভ করতে ব্যর্থ হয়েছে।', 'error');
    }
  } catch (err) {
    showToast(`ত্রুটি: ${err.message}`, 'error');
  }
}

function resetSettingsDefaults() {
  if (document.getElementById('setting-llm-url')) {
    document.getElementById('setting-llm-url').value = 'http://192.168.20.10:1234/v1';
  }
  if (document.getElementById('setting-llm-model')) {
    document.getElementById('setting-llm-model').value = 'gemma-4-e2b-it-qat';
  }
  if (document.getElementById('setting-llm-key')) {
    document.getElementById('setting-llm-key').value = 'sk-lm-itvN1hr4:n8gt8iapM8Slt3NqjlHk';
  }
  if (document.getElementById('setting-agent-temp')) {
    document.getElementById('setting-agent-temp').value = '0.3';
  }
  if (document.getElementById('temp-val-display')) {
    document.getElementById('temp-val-display').innerText = '0.3';
  }
  showToast('ডিফল্ট LM Studio কনফিগারেশন সেট করা হয়েছে। সেভ করতে "সেটিংস সংরক্ষণ" চাপুন।', 'info');
}

// Auto-initialize Theme immediately and on DOM ready
initTheme();
document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  loadSettings();
});
