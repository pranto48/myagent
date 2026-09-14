/* ==============================================================================
 * Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
 * Made By Arif (https://arifmahmud.com/)
 * Project: MyAgent | Version: 2.3.0
 * ============================================================================== */

// Internationalization (i18n) Engine: English & Bangla (Only 2 Languages)

const I18N_TRANSLATIONS = {
  bn: {
    // Navigation Menu
    nav_chat: "এআই চ্যাট (Chat)",
    nav_admin: "অ্যাডমিন কমান্ড সেন্টার",
    nav_dashboard: "অ্যানালিটিক্স ড্যাশবোর্ড",
    nav_users: "ইউজার ম্যানেজমেন্ট",
    nav_knowledge: "ডেটা ও নলেজবেস",
    nav_models: "এআই মডেল হাব ও পিং",
    nav_mcp: "টুলস ও MCP হাব",
    nav_security: "সিকিউরিটি ও কমপ্লায়েন্স",
    nav_reports: "AI রিপোর্ট জেনারেটর",
    nav_backup: "ব্যাকআপ ও রিস্টোর",
    nav_settings: "সিস্টেম সেটিংস",

    // Server & Agent Status
    status_online: "অনলাইন",
    status_offline: "অফলাইন",
    status_connecting: "সংযোগ হচ্ছে...",

    // Topbar
    topbar_title: "কোম্পানি ডেটা ইন্টেলিজেন্স এজেন্ট",
    topbar_desc: "ওপেনক্ল-স্টাইল পারসিসটেন্ট মেমোরি ও অটোনোমাস কোম্পানি এআই",
    topbar_model_label: "মডেল:",
    chat_search_placeholder: "🔍 খুঁজুন...",
    btn_quick_note: "নোট সেভ",
    tooltip_quick_note: "সরাসরি এজেন্টের মেমোরিতে নতুন তথ্য/নোট সেভ করুন",
    tooltip_theme: "থিম পরিবর্তন করুন (ডার্ক / লাইট)",
    tooltip_export_chat: "চ্যাট এক্সপোর্ট করুন",
    tooltip_lang: "ভাষা পরিবর্তন (বাংলা / English)",

    // Chat Sessions Panel
    sessions_title: "চ্যাট সেশনসমূহ",
    sessions_empty: "কোনো পূর্ববর্তী চ্যাট নেই।",
    sessions_new: "নতুন চ্যাট",
    new_chat_btn_title: "নতুন চ্যাট শুরু করুন",

    // User Footer
    role_admin: "সিস্টেম অ্যাডমিন",
    role_analyst: "ডেটা অ্যানালিস্ট",
    role_viewer: "ভিউয়ার",
    tooltip_logout: "লগআউট",

    // Chat Empty State Hero
    hero_title: "আমি কীভাবে আপনাকে সাহায্য করতে পারি?",
    hero_desc: "কোম্পানির অভ্যন্তরীণ নথি, স্প্রেডশিট, পলিসি বা ফাইল সম্পর্কিত যেকোনো প্রশ্ন করুন।",
    hero_chip_1: "📊 কোম্পানির আর্থিক বিবরণী বিশ্লেষণ",
    hero_chip_2: "📋 অভ্যন্তরীণ নীতি ও ছুটির নিয়মাবলী",
    hero_chip_3: "🖥️ কম্পিউটার ও আইটি ইনভেন্টরি রিপোর্ট",
    hero_chip_4: "📁 সংযুক্ত ফাইল বা ছবি থেকে ডেটা এক্সট্রাক্ট",

    // Chat Input Bar
    chat_placeholder: "আপনার প্রশ্ন বা ডেটা বিশ্লেষণ নির্দেশ লিখুন... (Ctrl+V দিয়ে ছবি বা ফাইল পেস্ট করতে পারেন)",
    btn_send_title: "বার্তা পাঠান (Enter)",
    btn_stop_title: "উত্তর তৈরি থামান (Stop Generating)",
    btn_attach_title: "ফাইল বা ফটো যুক্ত করুন (Excel, PDF, Word, Image)",
    memory_checkbox_label: "কোম্পানি মেমোরিতে সংরক্ষণ করুন",
    memory_toggle_label: "কোম্পানি মেমোরি",

    // Settings View
    settings_title: "সিস্টেম ও সার্ভার সেটিংস",
    settings_lang_title: "🌐 ভাষা পরিবর্তন (Language Selection)",
    lang_bn_title: "বাংলা (Bangla)",
    lang_bn_desc: "বাংলা ইন্টারফেস ও রেসপন্স",
    lang_en_title: "English",
    lang_en_desc: "English interface & responses",
    settings_theme_title: "🎨 ডিসপ্লে ও থিম মোড (Theme Mode)",
    theme_dark_title: "ডার্ক মোড",
    theme_dark_desc: "স্লিক অনিক্স ও নিয়ন গ্লো",
    theme_light_title: "লাইট মোড",
    theme_light_desc: "ক্লিন ও ক্রিস্প কর্পোরেট",
    theme_system_title: "সিস্টেম অটো",
    theme_system_desc: "ওএস প্রেফারেন্স অনুযায়ী",
    settings_llm_url: "বাহ্যিক এলএলএম সার্ভার URL (OpenAI-সামঞ্জস্যপূর্ণ)",
    settings_llm_model: "এলএলএম মডেলের নাম (Model Name)",
    settings_llm_key: "এপিআই কি (ঐচ্ছিক / ক্লাউড সার্ভিসের জন্য)",
    settings_agent_temp: "এজেন্ট টেম্পারেচার (Temperature)",
    btn_test_conn: "সার্ভার টেস্ট",
    btn_save_settings: "সেটিংস সেভ করুন",
    btn_backup_restore: "💾 সম্পূর্ণ ব্যাকআপ ও রিস্টোর",

    // Quick Note Modal
    quick_note_modal_title: "🧠 মেমোরিতে দ্রুত নোট/তথ্য যুক্ত করুন",
    quick_note_title_label: "নোটের শিরোনাম",
    quick_note_title_placeholder: "যেমন: ধানমন্ডি শাখা অফিস সময়সূচি ও রুলস",
    quick_note_category_label: "ক্যাটাগরি / বিভাগ",
    quick_note_content_label: "বিস্তারিত তথ্য / গাইডলাইন",
    quick_note_content_placeholder: "যে তথ্যটি এআই এজেন্টের সারাজীবন মনে রাখা প্রয়োজন...",
    btn_cancel: "বাতিল",
    btn_save_memory: "মেমোরিতে সেভ করুন",

    // Knowledge View
    kb_upload_title: "ফাইল, এক্সেল ও ফটো আপলোড",
    kb_upload_desc: "PDF, Word (.docx), Excel (.xlsx), CSV, Text এবং ফটো/ছবি (.png, .jpg) আপলোড করুন।",
    kb_dropzone_text: "ফাইল বা ছবি এখানে ড্রপ করুন অথবা ব্রাউজ করুন",
    kb_dropzone_sub: "সমর্থিত: PDF, Word, Excel, CSV, ফটো (OCR সহ), Text (সর্বোচ্চ ১০০ MB)",
    kb_quicknote_title: "সরাসরি মেমোরি নোট যুক্ত করুন",
    kb_quicknote_desc: "কোনো ফাইল ছাড়াই কোম্পানির গুরুত্বপূর্ণ নিয়মাবলী বা ঘোষণা সরাসরি সেভ করুন।",
    kb_library_title: "সংরক্ষিত কোম্পানি ডেটা লাইব্রেরি",
    kb_library_desc: "ইনডেক্স করা সমস্ত ডকুমেন্ট ও ফটো চাঙ্কস অডিট করুন।",
    kb_chunks_title: "🧠 সংরক্ষিত মেমোরি চাঙ্কস এক্সপ্লোরার ও ভুল তথ্য সংশোধন (CRUD)",
    kb_chunks_desc: "ক্রোমাডিবি ও হাইব্রিড সার্চে সংরক্ষিত সমস্ত চাঙ্ক ব্রাউজ করুন এবং ভুল তথ্য সরাসরি এডিট বা ডিলিট করুন।",
    btn_optimize_store: "⚡ মেমোরি অপ্টিমাইজ",
    btn_reindex_docs: "🔄 স্মার্ট রি-ইনডেক্স",
    btn_refresh: "🔄 রিফ্রেশ",

    // Toasts & Notifications
    toast_lang_changed: "🌐 ভাষা পরিবর্তন করা হয়েছে: বাংলা",
    toast_session_created: "নতুন চ্যাট সেশন শুরু হয়েছে।",
    toast_copied: "ক্লিপবোর্ডে কপি করা হয়েছে!",
    toast_saved: "সফলভাবে সংরক্ষিত হয়েছে!"
  },
  en: {
    // Navigation Menu
    nav_chat: "AI Chat",
    nav_admin: "Admin Command Center",
    nav_dashboard: "Analytics Dashboard",
    nav_users: "User Management",
    nav_knowledge: "Data & Knowledge Base",
    nav_models: "AI Model Hub & Ping",
    nav_mcp: "Tools & MCP Hub",
    nav_security: "Security & Compliance",
    nav_reports: "AI Report Generator",
    nav_backup: "Backup & Restore",
    nav_settings: "System Settings",

    // Server & Agent Status
    status_online: "Online",
    status_offline: "Offline",
    status_connecting: "Connecting...",

    // Topbar
    topbar_title: "Company Data Intelligence Agent",
    topbar_desc: "OpenClaw-style persistent memory & autonomous enterprise AI",
    topbar_model_label: "Model:",
    chat_search_placeholder: "🔍 Search messages...",
    btn_quick_note: "Save Note",
    tooltip_quick_note: "Save instant knowledge note to agent memory",
    tooltip_theme: "Toggle Theme (Dark / Light)",
    tooltip_export_chat: "Export Chat Conversation",
    tooltip_lang: "Change Language (Bangla / English)",

    // Chat Sessions Panel
    sessions_title: "Chat Sessions",
    sessions_empty: "No previous chats.",
    sessions_new: "New Chat",
    new_chat_btn_title: "Start a new chat",

    // User Footer
    role_admin: "System Admin",
    role_analyst: "Data Analyst",
    role_viewer: "Viewer",
    tooltip_logout: "Logout",

    // Chat Empty State Hero
    hero_title: "How can I help you today?",
    hero_desc: "Ask any question regarding company documents, spreadsheets, policies, or internal files.",
    hero_chip_1: "📊 Analyze Financial Statements",
    hero_chip_2: "📋 Internal Policies & Leave Rules",
    hero_chip_3: "🖥️ IT & Computer Inventory Report",
    hero_chip_4: "📁 Extract Data from Files & Photos",

    // Chat Input Bar
    chat_placeholder: "Type your question or data analysis instructions... (Ctrl+V to paste photos/files)",
    btn_send_title: "Send Message (Enter)",
    btn_stop_title: "Stop Generating",
    btn_attach_title: "Attach Files or Photos (Excel, PDF, Word, Image)",
    memory_checkbox_label: "Save to company memory",
    memory_toggle_label: "Company Memory",

    // Settings View
    settings_title: "System & Server Settings",
    settings_lang_title: "🌐 Language Selection",
    lang_bn_title: "বাংলা (Bangla)",
    lang_bn_desc: "Bangla interface & responses",
    lang_en_title: "English",
    lang_en_desc: "English interface & responses",
    settings_theme_title: "🎨 Display & Theme Mode",
    theme_dark_title: "Dark Mode",
    theme_dark_desc: "Sleek onyx & neon glow",
    theme_light_title: "Light Mode",
    theme_light_desc: "Clean & crisp corporate",
    theme_system_title: "System Auto",
    theme_system_desc: "Follows OS preference",
    settings_llm_url: "External LLM Server URL (OpenAI-compatible)",
    settings_llm_model: "LLM Model Name",
    settings_llm_key: "API Key (Optional / For cloud services)",
    settings_agent_temp: "Agent Temperature",
    btn_test_conn: "Test Server",
    btn_save_settings: "Save Settings",
    btn_backup_restore: "💾 Full Backup & Restore",

    // Quick Note Modal
    quick_note_modal_title: "🧠 Add Quick Note to Memory",
    quick_note_title_label: "Note Title",
    quick_note_title_placeholder: "e.g., Dhanmondi Branch Office Hours & Policy",
    quick_note_category_label: "Category / Department",
    quick_note_content_label: "Detailed Content / Guidelines",
    quick_note_content_placeholder: "Key company facts the AI Agent should remember permanently...",
    btn_cancel: "Cancel",
    btn_save_memory: "Save to Memory",

    // Knowledge View
    kb_upload_title: "Upload Files, Spreadsheets & Photos",
    kb_upload_desc: "Upload PDF, Word (.docx), Excel (.xlsx), CSV, Text, and Photos/Images (.png, .jpg).",
    kb_dropzone_text: "Drop files or photos here or click to browse",
    kb_dropzone_sub: "Supported: PDF, Word, Excel, CSV, Photos (with OCR), Text (Max 100 MB)",
    kb_quicknote_title: "Add Direct Memory Note",
    kb_quicknote_desc: "Save important company policies or announcements directly without files.",
    kb_library_title: "Saved Company Data Library",
    kb_library_desc: "Inspect and audit all indexed documents and photo chunks.",
    kb_chunks_title: "🧠 Memory Chunks Explorer & Data Correction (CRUD)",
    kb_chunks_desc: "Browse all chunks in ChromaDB and hybrid search; edit wrong data or delete obsolete chunks directly.",
    btn_optimize_store: "⚡ Optimize Memory",
    btn_reindex_docs: "🔄 Smart Re-index",
    btn_refresh: "🔄 Refresh",

    // Toasts & Notifications
    toast_lang_changed: "🌐 Language switched to: English",
    toast_session_created: "New chat session started.",
    toast_copied: "Copied to clipboard!",
    toast_saved: "Saved successfully!"
  }
};

let currentAppLanguage = 'bn';

/**
 * Returns current language ('bn' or 'en').
 */
function getAppLanguage() {
  return currentAppLanguage || 'bn';
}

/**
 * Translates a key according to current active language.
 */
function t(key, fallback = '') {
  const dict = I18N_TRANSLATIONS[currentAppLanguage] || I18N_TRANSLATIONS['bn'];
  return dict[key] !== undefined ? dict[key] : (fallback || key);
}

/**
 * Sets application language, updates DOM, persists to localStorage,
 * updates switcher buttons, and shows toast notification.
 */
function setAppLanguage(lang, notify = true) {
  if (lang !== 'bn' && lang !== 'en') {
    lang = 'bn';
  }

  currentAppLanguage = lang;
  localStorage.setItem('myagent_lang', lang);
  document.documentElement.setAttribute('lang', lang);

  // 1. Update all DOM elements with data-i18n attributes
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    const val = t(key);
    if (val) el.innerText = val;
  });

  // 2. Update all DOM elements with data-i18n-html attributes
  document.querySelectorAll('[data-i18n-html]').forEach(el => {
    const key = el.getAttribute('data-i18n-html');
    const val = t(key);
    if (val) el.innerHTML = val;
  });

  // 3. Update all DOM elements with data-i18n-placeholder
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    const key = el.getAttribute('data-i18n-placeholder');
    const val = t(key);
    if (val) el.placeholder = val;
  });

  // 4. Update all DOM elements with data-i18n-title
  document.querySelectorAll('[data-i18n-title]').forEach(el => {
    const key = el.getAttribute('data-i18n-title');
    const val = t(key);
    if (val) el.title = val;
  });

  // 5. Update language toggle buttons in Topbar and Mobile Navbar
  updateLanguageSwitcherUI(lang);

  // 6. Update Settings View Language Cards
  updateSettingsLangCards(lang);

  // 7. Dispatch custom event for dynamic components
  window.dispatchEvent(new CustomEvent('appLanguageChanged', { detail: { language: lang } }));

  // 8. Display feedback toast
  if (notify && typeof showToast === 'function') {
    showToast(t('toast_lang_changed'), 'success');
  }
}

/**
 * Updates UI state of language switcher buttons across topbar and mobile navbar.
 */
function updateLanguageSwitcherUI(lang) {
  // Topbar Buttons
  const btnBn = document.getElementById('btn-lang-bn');
  const btnEn = document.getElementById('btn-lang-en');
  if (btnBn && btnEn) {
    if (lang === 'bn') {
      btnBn.classList.add('active');
      btnEn.classList.remove('active');
    } else {
      btnEn.classList.add('active');
      btnBn.classList.remove('active');
    }
  }

  // Mobile Navbar Buttons
  const mBtnBn = document.getElementById('mobile-btn-lang-bn');
  const mBtnEn = document.getElementById('mobile-btn-lang-en');
  if (mBtnBn && mBtnEn) {
    if (lang === 'bn') {
      mBtnBn.classList.add('active');
      mBtnEn.classList.remove('active');
    } else {
      mBtnEn.classList.add('active');
      mBtnBn.classList.remove('active');
    }
  }
}

/**
 * Updates selected state of language cards in Settings View.
 */
function updateSettingsLangCards(lang) {
  const cardBn = document.getElementById('lang-card-bn');
  const cardEn = document.getElementById('lang-card-en');
  if (cardBn && cardEn) {
    if (lang === 'bn') {
      cardBn.classList.add('selected');
      cardEn.classList.remove('selected');
    } else {
      cardEn.classList.add('selected');
      cardBn.classList.remove('selected');
    }
  }
}

/**
 * Initializes language on DOM ready.
 */
function initLanguage() {
  const savedLang = localStorage.getItem('myagent_lang') || 'bn';
  setAppLanguage(savedLang, false);
}

// Auto-run on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  initLanguage();
});
