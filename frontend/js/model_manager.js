/* ==============================================================================
 * Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
 * Made By Arif (https://arifmahmud.com/)
 * Project: MyAgent | Version: 3.2.0
 * AI Model Management & Live Server Latency Hub (with OpenRouter Multi-Provider)
 * ============================================================================== */

let currentOpenRouterModels = [];

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

      // Update provider pill buttons
      const isOR = data.active_provider === 'openrouter' || (data.active_model && data.active_model.includes('/'));
      const btnDef = document.getElementById('btn-provider-default');
      const btnOR = document.getElementById('btn-provider-openrouter');
      if (btnDef) btnDef.classList.toggle('active', !isOR);
      if (btnOR) btnOR.classList.toggle('active', isOR);

      const modelSelect = document.getElementById('hub-model-select');
      let models = (data.available_models && data.available_models.length > 2)
        ? data.available_models
        : (typeof ALL_OXIONAI_MODELS !== 'undefined' ? ALL_OXIONAI_MODELS : []);
      if (data.active_model && !models.includes(data.active_model)) {
        models = [data.active_model, ...models];
      }
      if (modelSelect) {
        modelSelect.innerHTML = models.map(m => `
          <option value="${m}" ${m === data.active_model ? 'selected' : ''}>${m}</option>
        `).join('');
      }

      // Automatically sync available models to topbar dropdown
      if (typeof updateModelDropdown === 'function') {
        updateModelDropdown(models, data.active_model);
      }

      // Load OpenRouter Status
      loadOpenRouterStatus(data.openrouter);
    }
  } catch (err) {
    console.warn('Error loading models hub:', err);
  }
}

async function loadOpenRouterStatus(preloaded = null) {
  try {
    let orData = preloaded;
    if (!orData) {
      const res = await fetch('/api/models/openrouter/status', {
        headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {}
      });
      if (res.ok) {
        orData = await res.json();
      }
    }

    if (!orData) return;

    // 1. Status badge
    const badge = document.getElementById('openrouter-status-badge');
    const tierBadge = document.getElementById('openrouter-tier-badge');
    const usageSub = document.getElementById('openrouter-usage-sub');
    const keyInput = document.getElementById('openrouter-key-input');

    if (orData.configured) {
      if (badge) {
        badge.className = 'status-pill status-online';
        badge.innerText = 'CONNECTED';
      }
      if (tierBadge) {
        const ver = orData.verification || {};
        tierBadge.innerText = ver.is_free_tier ? 'Free Tier Account' : 'Active Paid Account';
        tierBadge.style.color = '#22c55e';
      }
      if (usageSub) {
        const ver = orData.verification || {};
        const limitText = ver.limit ? `$${ver.limit}` : 'Pay-as-you-go';
        const usageText = ver.usage !== undefined ? `$${Number(ver.usage).toFixed(3)} used` : '';
        usageSub.innerText = `${limitText} • ${usageText}`;
      }
      if (keyInput && !keyInput.value && orData.key_masked) {
        keyInput.placeholder = orData.key_masked;
      }
    } else {
      if (badge) {
        badge.className = 'status-pill status-ready';
        badge.innerText = 'NOT CONFIGURED';
      }
      if (tierBadge) {
        tierBadge.innerText = 'API Key Required';
        tierBadge.style.color = '#f59e0b';
      }
    }

    // 2. Render Featured Models
    const models = orData.featured_models || [];
    currentOpenRouterModels = models;
    renderOpenRouterModelsGrid(models, orData.active_model);
  } catch (err) {
    console.error('Error loading OpenRouter status:', err);
  }
}

function renderOpenRouterModelsGrid(models, activeModel) {
  const container = document.getElementById('openrouter-models-grid');
  if (!container) return;

  container.innerHTML = models.map(m => {
    const isActive = m.id === activeModel;
    const badgeClass = m.category === 'Free' ? 'badge-free' : (m.category === 'Reasoning' ? 'badge-reasoning' : '');

    return `
      <div class="openrouter-model-card ${isActive ? 'active-model' : ''}" onclick="selectOpenRouterModel('${escapeHtml(m.id)}')">
        <div>
          <div class="openrouter-card-header">
            <h5 class="openrouter-model-title">${escapeHtml(m.name)}</h5>
            <span class="openrouter-badge ${badgeClass}">${escapeHtml(m.badge || m.category)}</span>
          </div>
          <p class="openrouter-model-desc">${escapeHtml(m.description)}</p>
        </div>
        <div class="openrouter-model-footer">
          <span>${escapeHtml(m.id)}</span>
          <span style="color:#38bdf8;">${isActive ? '✓ ACTIVE' : '⚡ 1-Click Use'}</span>
        </div>
      </div>
    `;
  }).join('');
}

async function selectOpenRouterModel(modelId) {
  try {
    const res = await fetch('/api/models/openrouter/config', {
      method: 'POST',
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: modelId, set_as_active: true, provider: 'openrouter' })
    });
    const data = await res.json();
    if (data.success) {
      showToast(`সক্রিয় মডেল OpenRouter: ${modelId}-এ পরিবর্তিত হয়েছে`, 'success');
      loadModelsOverview();

      // Update sidebar model label
      const sideModel = document.getElementById('sidebar-model-name');
      if (sideModel) sideModel.innerText = modelId;

      // Update topbar select
      const topSelect = document.getElementById('topbar-model-select');
      if (topSelect) {
        let opt = Array.from(topSelect.options).find(o => o.value === modelId);
        if (!opt) {
          opt = new Option(modelId, modelId, true, true);
          topSelect.add(opt);
        }
        topSelect.value = modelId;
      }
    } else {
      showToast(data.message || 'মডেল পরিবর্তন ব্যর্থ হয়েছে', 'error');
    }
  } catch (err) {
    showToast(`ত্রুটি: ${err.message}`, 'error');
  }
}

async function saveOpenRouterKey() {
  const keyInput = document.getElementById('openrouter-key-input');
  if (!keyInput) return;
  const key = keyInput.value.trim();
  if (!key) {
    showToast('অনুগ্রহ করে ওপেনরাউটার API Key প্রদান করুন', 'error');
    return;
  }

  try {
    const res = await fetch('/api/models/openrouter/config', {
      method: 'POST',
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key: key, provider: 'openrouter' })
    });
    const data = await res.json();
    if (data.success) {
      showToast('OpenRouter API Key সফলভাবে সেভ হয়েছে!', 'success');
      keyInput.value = '';
      loadModelsOverview();
    } else {
      showToast('API Key সংরক্ষণ ব্যর্থ হয়েছে', 'error');
    }
  } catch (err) {
    showToast(`ত্রুটি: ${err.message}`, 'error');
  }
}

async function verifyOpenRouterKey(showAlert = false) {
  const badge = document.getElementById('openrouter-status-badge');
  if (badge) badge.innerText = 'VERIFYING...';

  try {
    const res = await fetch('/api/models/openrouter/status', {
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {}
    });
    const data = await res.json();
    if (data.configured && data.verification?.valid) {
      if (showAlert) showToast(`OpenRouter সংযোগ সফল! (${data.verification.label || 'Active'})`, 'success');
    } else {
      if (showAlert) showToast(`সংযোগ ব্যর্থ: ${data.verification?.message || 'Invalid key'}`, 'error');
    }
    loadOpenRouterStatus(data);
  } catch (err) {
    if (showAlert) showToast(`নেটওয়ার্ক ত্রুটি: ${err.message}`, 'error');
  }
}

async function switchActiveProvider(provider) {
  try {
    const res = await fetch('/api/models/openrouter/config', {
      method: 'POST',
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider: provider })
    });
    const data = await res.json();
    if (data.success) {
      showToast(`প্রোভাইডার পরিবর্তিত হয়েছে: ${provider === 'openrouter' ? 'OpenRouter Cloud' : 'Default / Local'}`, 'success');
      loadModelsOverview();
    }
  } catch (err) {
    showToast(`ত্রুটি: ${err.message}`, 'error');
  }
}

function toggleOpenRouterKeyVisibility() {
  const input = document.getElementById('openrouter-key-input');
  if (input) {
    input.type = input.type === 'password' ? 'text' : 'password';
  }
}

async function runOpenRouterTestPrompt() {
  const modelSelect = document.getElementById('openrouter-test-model-select');
  const promptInput = document.getElementById('openrouter-test-prompt-input');
  const outputBox = document.getElementById('openrouter-test-output');
  if (!modelSelect || !promptInput || !outputBox) return;

  const model = modelSelect.value;
  const prompt = promptInput.value.trim();

  outputBox.style.display = 'block';
  outputBox.innerHTML = '<span style="color:#94a3b8;">⚡ টেস্ট প্রম্পট পাঠানো হচ্ছে OpenRouter-এ...</span>';

  try {
    const res = await fetch('/api/models/openrouter/test', {
      method: 'POST',
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: model, prompt: prompt })
    });
    const data = await res.json();
    if (data.success) {
      outputBox.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
          <strong style="color:#22c55e;">✓ সফল (${data.latency_ms} ms)</strong>
          <span style="font-size:0.75rem; color:#94a3b8; font-family:'Fira Code',monospace;">${data.model_tested}</span>
        </div>
        <div style="font-size:0.85rem; color:#f1e7d0; white-space:pre-wrap;">${escapeHtml(data.reply || '')}</div>
      `;
      showToast(`OpenRouter রেসপন্স সফল (${data.latency_ms} ms)`, 'success');
    } else {
      outputBox.innerHTML = `<span style="color:#f43f5e;">❌ ত্রুটি: ${escapeHtml(data.error || 'Test failed')}</span>`;
      showToast('OpenRouter টেস্ট ব্যর্থ হয়েছে!', 'error');
    }
  } catch (err) {
    outputBox.innerHTML = `<span style="color:#f43f5e;">❌ নেটওয়ার্ক ত্রুটি: ${escapeHtml(err.message)}</span>`;
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

// Window exports
window.loadModelsOverview = loadModelsOverview;
window.runLiveLatencyTest = runLiveLatencyTest;
window.applyActiveModelChange = applyActiveModelChange;
window.loadOpenRouterStatus = loadOpenRouterStatus;
window.saveOpenRouterKey = saveOpenRouterKey;
window.verifyOpenRouterKey = verifyOpenRouterKey;
window.switchActiveProvider = switchActiveProvider;
window.selectOpenRouterModel = selectOpenRouterModel;
window.toggleOpenRouterKeyVisibility = toggleOpenRouterKeyVisibility;
window.runOpenRouterTestPrompt = runOpenRouterTestPrompt;

document.addEventListener('DOMContentLoaded', () => {
  loadModelsOverview();
});
