// Settings and Remote LLM Connectivity Management

const API_BASE = '/api';

// Toast Notification Helper
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

// Modal Toggle
function openSettingsModal() {
  document.getElementById('settings-modal').classList.add('open');
  loadSettings();
}

function closeSettingsModal() {
  document.getElementById('settings-modal').classList.remove('open');
  const badge = document.getElementById('test-connection-badge');
  badge.className = 'test-res-badge';
  badge.style.display = 'none';
}

// Load current configuration
async function loadSettings() {
  try {
    const res = await fetch(`${API_BASE}/settings`);
    if (res.ok) {
      const data = await res.json();
      document.getElementById('setting-llm-url').value = data.llm_base_url || '';
      document.getElementById('setting-llm-model').value = data.llm_model || '';
      document.getElementById('setting-agent-temp').value = data.agent_temperature || 0.3;
      
      // Update sidebar
      const modelLabel = document.getElementById('sidebar-model-name');
      if (modelLabel) modelLabel.innerText = data.llm_model || 'Unknown';
    }
  } catch (err) {
    console.error('Error loading settings:', err);
  }
}

// Test connectivity to external LLM Server
async function testConnection() {
  const btn = document.getElementById('btn-test-conn');
  const badge = document.getElementById('test-connection-badge');
  btn.disabled = true;
  btn.innerText = 'সংযোগ পরীক্ষা করা হচ্ছে...';
  badge.style.display = 'none';

  try {
    const res = await fetch(`${API_BASE}/settings/test-connection`, { method: 'POST' });
    const data = await res.json();

    badge.style.display = 'block';
    if (data.success) {
      badge.className = 'test-res-badge success';
      badge.innerHTML = `✅ ${data.message}<br><small>উপলব্ধ মডেল: ${data.models_available.slice(0, 5).join(', ') || 'কাস্টম মডেল সক্রিয়'}</small>`;
      showToast('এলএলএম সার্ভারের সাথে সফলভাবে সংযুক্ত হয়েছে!', 'success');
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
    const res = await fetch(`${API_BASE}/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        llm_base_url: url,
        llm_model: model,
        llm_api_key: key || 'not-needed',
        agent_temperature: isNaN(temp) ? 0.3 : temp
      })
    });

    if (res.ok) {
      showToast('সেটিংস সফলভাবে সংরক্ষিত হয়েছে!', 'success');
      document.getElementById('sidebar-model-name').innerText = model;
      closeSettingsModal();
    } else {
      showToast('সেটিংস সেভ করতে ব্যর্থ হয়েছে।', 'error');
    }
  } catch (err) {
    showToast(`ত্রুটি: ${err.message}`, 'error');
  }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  loadSettings();
});
