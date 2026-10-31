/* ==============================================================================
 * Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
 * Made By Arif (https://arifmahmud.com/)
 * Project: MyAgent | Version: 3.2.0
 * AI Model Management & Live Server Latency Hub (with OpenRouter Multi-Provider)
 * ============================================================================== */

let currentOpenRouterModels = [];
let openRouterFreeModelsList = [];
let openRouterFeaturedList = [];
let openRouterActiveCategory = 'free';
let openRouterSearchQuery = '';

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

    // 1. Status badge & Account Telemetry
    const badge = document.getElementById('openrouter-status-badge');
    const tierBadge = document.getElementById('openrouter-tier-badge');
    const usageSub = document.getElementById('openrouter-usage-sub');
    const keyInput = document.getElementById('openrouter-key-input');

    const ver = orData.verification || {};
    if (orData.configured && ver.valid) {
      if (badge) {
        badge.className = 'status-pill status-online';
        badge.innerText = 'CONNECTED';
      }
      if (tierBadge) {
        tierBadge.innerText = ver.is_free_tier ? 'Free Tier Account' : 'Active Account';
        tierBadge.style.color = '#22c55e';
      }
      if (usageSub) {
        const limitText = ver.limit ? `$${ver.limit}` : 'Pay-as-you-go';
        const usageText = ver.usage !== undefined ? `$${Number(ver.usage).toFixed(4)} used` : '';
        usageSub.innerText = `${ver.label || 'Default Key'} • ${limitText} • ${usageText}`;
      }
      if (keyInput && !keyInput.value && orData.key_masked) {
        keyInput.placeholder = orData.key_masked;
      }
    } else {
      if (badge) {
        badge.className = 'status-pill status-ready';
        badge.innerText = orData.configured ? 'KEY UNVERIFIED' : 'NOT CONFIGURED';
      }
      if (tierBadge) {
        tierBadge.innerText = orData.configured ? 'Unverified Key' : 'API Key Required';
        tierBadge.style.color = '#f59e0b';
      }
      if (usageSub) {
        usageSub.innerText = orData.configured ? (ver.message || 'Verification needed') : 'কী যুক্ত করে ১০০% ফ্রি মডেল ব্যবহার করুন';
      }
    }

    // 2. Cache models
    openRouterFeaturedList = orData.featured_models || [];
    openRouterFreeModelsList = orData.free_models || [];
    
    // Default to free models if available, otherwise featured
    filterOpenRouterCategory(openRouterActiveCategory, null, orData.active_model);

  } catch (err) {
    console.error('Error loading OpenRouter status:', err);
  }
}

function filterOpenRouterCategory(category, btnEl = null, activeModel = null) {
  openRouterActiveCategory = category;

  // Update tabs active state
  document.querySelectorAll('.or-filter-btn').forEach(b => b.classList.remove('active'));
  if (btnEl) {
    btnEl.classList.add('active');
  } else {
    const tab = document.getElementById(`or-filter-${category}`);
    if (tab) tab.classList.add('active');
  }

  let list = [];
  if (category === 'free') {
    list = openRouterFreeModelsList.length ? openRouterFreeModelsList : openRouterFeaturedList.filter(m => m.category === 'Free' || m.id.includes(':free'));
  } else if (category === 'featured') {
    list = openRouterFeaturedList;
  } else if (category === 'Reasoning') {
    list = [...openRouterFeaturedList, ...openRouterFreeModelsList].filter(m => m.category === 'Reasoning' || m.id.includes('r1') || m.id.includes('reasoning'));
  } else {
    // All
    const map = new Map();
    [...openRouterFreeModelsList, ...openRouterFeaturedList].forEach(m => map.set(m.id, m));
    list = Array.from(map.values());
  }

  // Deduplicate
  const uniqueMap = new Map();
  list.forEach(m => uniqueMap.set(m.id, m));
  currentOpenRouterModels = Array.from(uniqueMap.values());

  // Apply search query if any
  applyOpenRouterSearchAndRender(activeModel);
}

function searchOpenRouterModels(query) {
  openRouterSearchQuery = (query || '').trim().toLowerCase();
  applyOpenRouterSearchAndRender();
}

function applyOpenRouterSearchAndRender(activeModel = null) {
  let filtered = currentOpenRouterModels;
  if (openRouterSearchQuery) {
    filtered = filtered.filter(m => 
      m.id.toLowerCase().includes(openRouterSearchQuery) || 
      (m.name && m.name.toLowerCase().includes(openRouterSearchQuery)) ||
      (m.description && m.description.toLowerCase().includes(openRouterSearchQuery)) ||
      (m.provider && m.provider.toLowerCase().includes(openRouterSearchQuery))
    );
  }

  // Update count label
  const countLabel = document.getElementById('openrouter-models-count-label');
  if (countLabel) {
    countLabel.innerText = `মোট ${filtered.length} টি মডেল প্রদর্শিত হচ্ছে (${openRouterActiveCategory === 'free' ? '১০০% ফ্রি' : openRouterActiveCategory})`;
  }

  renderOpenRouterModelsGrid(filtered, activeModel);
}

function renderOpenRouterModelsGrid(models, activeModel) {
  const container = document.getElementById('openrouter-models-grid');
  if (!container) return;

  if (!models || models.length === 0) {
    container.innerHTML = `
      <div style="grid-column:1/-1; padding:32px; text-align:center; color:#94a3b8; background:rgba(0,0,0,0.2); border-radius:8px;">
        <div style="font-size:1.8rem; margin-bottom:6px;">🔍</div>
        <div>কোনো মডেল পাওয়া যায়নি। অনুগ্রহ করে ফিল্টার পরিবর্তন করুন।</div>
      </div>
    `;
    return;
  }

  const currentAct = activeModel || (document.getElementById('sidebar-model-name')?.innerText || '');

  container.innerHTML = models.map(m => {
    const isActive = m.id === currentAct;
    const isFree = m.category === 'Free' || m.id.includes(':free') || m.pricing === 'free';
    const badgeClass = isFree ? 'badge-free' : (m.category === 'Reasoning' ? 'badge-reasoning' : '');
    const badgeText = isFree ? '100% FREE' : (m.badge || m.category);

    return `
      <div class="openrouter-model-card ${isActive ? 'active-model' : ''}" onclick="selectOpenRouterModel('${escapeHtml(m.id)}')">
        <div>
          <div class="openrouter-card-header">
            <h5 class="openrouter-model-title">${escapeHtml(m.name || m.id)}</h5>
            <span class="openrouter-badge ${badgeClass}">${escapeHtml(badgeText)}</span>
          </div>
          <p class="openrouter-model-desc">${escapeHtml(m.description || 'OpenRouter এআই মডেল।')}</p>
        </div>
        <div class="openrouter-model-footer">
          <span style="font-family:'Fira Code',monospace; font-size:0.75rem; word-break:break-all;">${escapeHtml(m.id)}</span>
          <span style="color:${isActive ? '#10b981' : '#38bdf8'}; font-weight:600; white-space:nowrap; margin-left:6px;">
            ${isActive ? '✓ ACTIVE' : '⚡ 1-Click Use'}
          </span>
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

      // Update test model select
      const testSelect = document.getElementById('openrouter-test-model-select');
      if (testSelect) {
        let topt = Array.from(testSelect.options).find(o => o.value === modelId);
        if (!topt) {
          topt = new Option(modelId, modelId, true, true);
          testSelect.add(topt);
        }
        testSelect.value = modelId;
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
      if (data.key_masked) keyInput.placeholder = data.key_masked;
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
  const keyInput = document.getElementById('openrouter-key-input');
  const inputKey = keyInput ? keyInput.value.trim() : '';

  if (badge) {
    badge.className = 'status-pill status-ready';
    badge.innerText = 'VERIFYING...';
  }

  try {
    const res = await fetch('/api/models/openrouter/verify', {
      method: 'POST',
      headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key: inputKey, save_if_valid: Boolean(inputKey) })
    });
    const data = await res.json();
    const ver = data.verification || {};

    if (ver.valid) {
      if (badge) {
        badge.className = 'status-pill status-online';
        badge.innerText = 'VERIFIED & ACTIVE';
      }
      const tierBadge = document.getElementById('openrouter-tier-badge');
      if (tierBadge) {
        tierBadge.innerText = ver.is_free_tier ? 'Free Tier Account' : 'Active Account';
        tierBadge.style.color = '#22c55e';
      }
      const usageSub = document.getElementById('openrouter-usage-sub');
      if (usageSub) {
        const limitText = ver.limit ? `$${ver.limit}` : 'Pay-as-you-go';
        const usageText = ver.usage !== undefined ? `$${Number(ver.usage).toFixed(4)} used` : '';
        usageSub.innerText = `${ver.label || 'Default Key'} • ${limitText} • ${usageText}`;
      }
      if (keyInput) {
        keyInput.value = '';
        if (data.key_masked) keyInput.placeholder = data.key_masked;
      }
      if (showAlert) {
        showToast(`✓ OpenRouter কী সফলভাবে ভেরিফাই ও সক্রিয় করা হয়েছে! (${ver.label || 'Active'})`, 'success');
      }
      loadModelsOverview();
    } else {
      if (badge) {
        badge.className = 'status-pill';
        badge.style.background = 'rgba(244,63,94,0.15)';
        badge.style.color = '#f43f5e';
        badge.innerText = 'INVALID KEY';
      }
      if (showAlert) {
        showToast(ver.message || 'OpenRouter API Key ভেরিফিকেশন ব্যর্থ হয়েছে', 'error');
      }
    }
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
