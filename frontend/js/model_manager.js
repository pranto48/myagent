/* ==============================================================================
 * Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
 * Made By Arif (https://arifmahmud.com/)
 * Project: MyAgent | Version: 3.0.0
 * ============================================================================== */

// AI Model Management & Live Server Latency Hub

async function loadModelsOverview() {
  try {
    const res = await fetch('/api/models', {
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {}
    });
    if (res.ok) {
      const data = await res.json();
      const currentLabel = document.getElementById('hub-current-model');
      if (currentLabel) currentLabel.innerText = data.active_model;

      const serverInput = document.getElementById('hub-server-url');
      if (serverInput) serverInput.value = data.base_url;

      const modelSelect = document.getElementById('hub-model-select');
      if (modelSelect && data.available_models) {
        modelSelect.innerHTML = data.available_models.map(m => `
          <option value="${m}" ${m === data.active_model ? 'selected' : ''}>${m}</option>
        `).join('');
      }
    }
  } catch (err) {
    console.warn('Error loading models hub:', err);
  }
}

async function runLiveLatencyTest() {
  const resultBox = document.getElementById('hub-ping-result');
  const btn = document.getElementById('btn-run-ping');
  const customUrl = document.getElementById('hub-server-url').value.trim();

  btn.disabled = true;
  btn.innerText = typeof t === 'function' ? t('models_pinging', 'পিং টেস্ট চলছে...') : 'পিং টেস্ট চলছে...';
  resultBox.style.display = 'block';
  resultBox.className = 'ping-indicator-box loading';
  resultBox.innerHTML = typeof t === 'function' ? t('models_measuring', '⚡ এলএলএম সার্ভারের রেসপন্স টাইম পরিমাপ করা হচ্ছে...') : '⚡ এলএলএম সার্ভারের রেসপন্স টাইম পরিমাপ করা হচ্ছে...';

  try {
    const res = await fetch('/api/models/ping', {
      method: 'POST',
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: customUrl })
    });

    const data = await res.json();
    if (data.success) {
      const speedClass = data.latency_ms < 100 ? 'fast' : (data.latency_ms < 500 ? 'normal' : 'slow');
      resultBox.className = `ping-indicator-box ${speedClass}`;
      const latLabel = typeof t === 'function' ? t('models_latency_label', 'রেসপন্স লেটেন্সি') : 'রেসপন্স লেটেন্সি';
      resultBox.innerHTML = `
        <div style="font-size: 1.1rem; font-weight: 700;">⚡ ${latLabel}: ${data.latency_ms} ms</div>
        <div style="font-size: 0.76rem; opacity: 0.9; margin-top: 4px;">
          HTTP ${data.status_code} • ${(data.models || []).slice(0, 4).join(', ')}
        </div>
      `;
      showToast(`সার্ভার পিং সফল: ${data.latency_ms} ms`, 'success');
      
      // Update topbar dropdown
      if (typeof updateModelDropdown === 'function') {
        updateModelDropdown(data.models, data.models[0] || 'llama3.3');
      }
    } else {
      resultBox.className = 'ping-indicator-box error';
      resultBox.innerHTML = `❌ সংযোগ ব্যর্থ: ${escapeHtml(data.error || 'সার্ভার এক্সেস করা সম্ভব হয়নি')}`;
      showToast('সার্ভার পিং ব্যর্থ হয়েছে!', 'error');
    }
  } catch (err) {
    resultBox.className = 'ping-indicator-box error';
    resultBox.innerHTML = `❌ নেটওয়ার্ক ত্রুটি: ${err.message}`;
  } finally {
    btn.disabled = false;
    btn.innerText = typeof t === 'function' ? t('models_btn_run_ping', 'লাইভ পিং টেস্ট চালান') : 'লাইভ পিং টেস্ট চালান';
  }
}

async function applyActiveModelChange() {
  const model = document.getElementById('hub-model-select').value;
  const temp = parseFloat(document.getElementById('hub-temperature').value) || 0.3;

  try {
    const res = await fetch('/api/models/active', {
      method: 'POST',
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: model, temperature: temp })
    });

    if (res.ok) {
      showToast(`সক্রিয় মডেল পরিবর্তিত হয়েছে: ${model}`, 'success');
      const sideModel = document.getElementById('sidebar-model-name');
      if (sideModel) sideModel.innerText = model;
      loadModelsOverview();
    }
  } catch (err) {
    showToast(`মডেল পরিবর্তনে ত্রুটি: ${err.message}`, 'error');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  loadModelsOverview();
});
