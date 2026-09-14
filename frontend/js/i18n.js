/* ==============================================================================
 * Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
 * Made By Arif (https://arifmahmud.com/)
 * Project: MyAgent | Version: 3.0.0
 * ============================================================================== */

// Internationalization (i18n) Engine: Strictly English & Bangla (Only 2 Languages)

const I18N_TRANSLATIONS = {
  bn: {
    // Brand & App
    app_title: "MyAgent v3.0.0 - এন্টারপ্রাইজ কোম্পানি এআই এজেন্ট ও অ্যানালিটিক্স",
    app_description: "ডকারাইজড কোম্পানি এআই এজেন্ট, পারসিসটেন্ট মেমোরি, অ্যাডমিন ড্যাশবোর্ড ও বিগ ডাটা অ্যানালিটিক্স",

    // Login Overlay
    login_title: "MyAgent Enterprise",
    login_desc: "কোম্পানির সংবেদনশীল ডেটা ও এআই এজেন্ট ব্যবস্থাপনায় অ্যাডমিন লগইন আবশ্যক",
    login_user_label: "অ্যাডমিন ইউজারনেম (Username)",
    login_user_placeholder: "admin",
    login_pass_label: "পাসওয়ার্ড (Password)",
    login_pass_placeholder: "••••••••",
    login_btn: "লগইন করুন",
    login_host_info: "হোস্ট: <code>192.168.9.9:3399</code> • সুরক্ষিত অভ্যন্তরীণ নেটওয়ার্ক",

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
    btn_export: "এক্সপোর্ট",
    btn_new_chat: "নতুন চ্যাট",
    btn_ingest: "ইনজেস্ট",

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
    hero_badge: "MyAgent Enterprise AI",
    hero_hello: "হ্যালো,",
    hero_sub_sparkle: "আজ আমি আপনাকে কীভাবে সাহায্য করতে পারি?",
    hero_desc: "কোম্পানির নিজস্ব সিকিউর ডাটাবেস ও অন-প্রিমিসেস এআই মডেলে পরিচালিত আপনার স্মার্ট কর্পোরেট সহকারী।",
    hero_chip_1: "📊 কোম্পানির আর্থিক বিবরণী বিশ্লেষণ",
    hero_chip_2: "📋 অভ্যন্তরীণ নীতি ও ছুটির নিয়মাবলী",
    hero_chip_3: "🖥️ কম্পিউটার ও আইটি ইনভেন্টরি রিপোর্ট",
    hero_chip_4: "📁 সংযুক্ত ফাইল বা ছবি থেকে ডেটা এক্সট্রাক্ট",
    hero_card_1_title: "কোম্পানি পলিসি ও রুলস",
    hero_card_1_desc: "অভ্যন্তরীণ কর্মপদ্ধতি, ছুটি ও নিয়মাবলী অনুসন্ধান",
    hero_card_2_title: "বিগ ডেটা ও এক্সেল অ্যানালাইসিস",
    hero_card_2_desc: "স্প্রেডশিটের হিসাব, মেট্রিক্স ও ট্রেন্ড টেবিল তৈরি",
    hero_card_3_title: "এক্সিকিউটিভ ডাটা রিপোর্ট",
    hero_card_3_desc: "অটোমেটেড রিপোর্ট জেনারেশন ও পরবর্তী করণীয়",
    hero_card_4_title: "ফটো ও ইমেজ OCR রিডিং",
    hero_card_4_desc: "ছবি থেকে টেক্সট ও ডকুমেন্ট সারসংক্ষেপ নিষ্কাশন",

    // Productivity Quick Action Bar
    quick_bar_label: "⚡ অ্যাকশন:",
    chip_quick_note: "📌 মেমোরিতে নোট সেভ",
    chip_big_data: "📊 বিগ ডেটা",
    chip_policy_search: "🔍 পলিসি সার্চ",
    chip_gen_report: "📑 রিপোর্ট তৈরি",
    chip_py_sandbox: "🐍 পাইথন স্যান্ডবক্স",
    chip_sec_audit: "🛡️ সিকিউরিটি",

    // Chat Input Bar & Attachments
    chat_placeholder: "MyAgent-কে প্রশ্ন করুন, বা ফাইল/এক্সেল/ছবি সংযুক্ত করুন... (Shift+Enter নতুন লাইনের জন্য)",
    btn_send_title: "বার্তা পাঠান (Enter)",
    btn_stop_title: "উত্তর তৈরি থামান (Stop Generating)",
    btn_attach_title: "ফাইল বা ফটো যুক্ত করুন (Excel, PDF, Word, Image)",
    memory_checkbox_label: "কোম্পানি মেমোরিতে সংরক্ষণ করুন",
    memory_toggle_label: "কোম্পানি মেমোরি",
    upload_indexing: "মেমোরি ইনডেক্সিং হচ্ছে...",
    drag_drop_title: "এখানে ফাইল বা ছবি ছেড়ে দিন",
    drag_drop_desc: "Excel (.xlsx, .csv), ছবি/ফটো OCR (.png, .jpg), PDF বা ডকুমেন্টস সরাসরি বিশ্লেষণ হবে",
    chat_privacy_footer: "🔒 MyAgent Enterprise • সুরক্ষিত অন-প্রিমিসেস ডেটাবেস ও নিজস্ব এলএলএম সার্ভারে পরিচালিত",

    // Chat Message Bubbles, Actions & Sources
    sender_you: "আপনি",
    sender_ai: "MyAgent AI",
    file_saved_badge: "✅ মেমোরিতে সংরক্ষিত",
    file_saved_title: "এই ফাইলটি কোম্পানির স্থায়ী মেমোরিতে সংরক্ষিত",
    file_save_btn: "💾 মেমোরিতে সেভ করুন",
    file_save_title: "ব্যবহারকারী/অ্যাডমিন সিদ্ধান্ত: ক্লিক করলে এই ফাইলটি স্থায়ী মেমোরিতে সংরক্ষিত হবে",
    sources_header: "📑 মেমোরি রেফারেন্স ও সোর্স",
    sources_page: "পৃষ্ঠা",
    sources_match: "মিল",
    msg_copy_btn: "কপি",
    msg_copy_title: "কপি করুন",
    msg_save_mem_btn: "মেমোরিতে সেভ",
    msg_save_mem_title: "এআই-এর উত্তরটি কোম্পানির স্থায়ী মেমোরিতে সেভ করুন",
    msg_retry_btn: "রিট্রাই",
    msg_retry_title: "পুনরায় চেষ্টা করুন",
    msg_like_title: "পছন্দ হয়েছে",
    msg_dislike_title: "অপছন্দ হয়েছে",
    copied_badge: "✓ কপি হয়েছে!",
    copy_failed: "ক্লিপবোর্ডে কপি করা যায়নি",
    default_attach_prompt: "অনুগ্রহ করে সংযুক্ত ফাইলগুলো বিশ্লেষণ করে বিস্তারিত সারসংক্ষেপ ও অন্তর্দৃষ্টি তুলে ধরুন।",
    calling_tool: "টুল কল করা হচ্ছে:",
    tool_result: "ফলাফল",
    error_prefix: "ত্রুটি:",
    stopped_by_user: "ব্যবহারকারী কর্তৃক উত্তর তৈরি থামানো হয়েছে",
    server_error_prefix: "সার্ভার সমস্যা:",
    saving_text: "সেভ হচ্ছে...",
    saved_badge: "✓ সেভ হয়েছে!",
    chat_note_default: "চ্যাট নোট",
    msg_copy_code: "কপি কোড",
    btn_remove: "মুছে ফেলুন",
    save_memory_toggle_title: "ইউজার/অ্যাডমিন সিদ্ধান্ত: চেক করলে এই ফাইলগুলো স্থায়ীভাবে কোম্পানির ভেক্টর মেমোরিতে সেভ হবে",
    attached_files_count: "📎 সংযুক্ত ফাইল ({count}টি)",
    tab_chat_title: "কোম্পানি ডেটা ইন্টেলিজেন্স এজেন্ট",
    tab_chat_desc: "ওপেনক্ল-স্টাইল পারসিসটেন্ট মেমোরি ও অটোনোমাস কোম্পানি এআই",
    tab_admin_title: "অ্যাডমিন কমান্ড সেন্টার ও সিস্টেম কন্ট্রোল",
    tab_admin_desc: "সার্ভার হার্টবিট, ক্লাউড মেট্রিক্স ও ইনস্ট্যান্ট অ্যাডমিন অ্যাকশন হাব",
    tab_dash_title: "অ্যানালিটিক্স ও সিস্টেম মনিটরিং ড্যাশবোর্ড",
    tab_dash_desc: "সার্ভার পারফরম্যান্স, মেমোরি চাঙ্কস এবং স্টোরেজ অ্যানালাইসিস",
    tab_users_title: "কোম্পানি ইউজার ও এক্সেস কন্ট্রোল",
    tab_users_desc: "অভ্যন্তরীণ কর্মকর্তা ও কর্মচারীদের রোল ম্যানেজমেন্ট",
    tab_kb_title: "কোম্পানি ডেটা লাইব্রেরি ও মেমোরি ইনজেস্ট",
    tab_kb_desc: "PDF, Word, Excel, CSV ও ফটো/ছবি OCR প্রসেসিং",
    tab_models_title: "এআই মডেল হাব ও রিয়েলটাইম পিং টেস্ট",
    tab_models_desc: "বাহ্যিক এলএলএম সার্ভারের সংযোগ ও রেসপন্স টাইম (ms)",
    tab_mcp_title: "টুলস ও মডেল কনটেক্সট প্রোটোকল (MCP) হাব",
    tab_mcp_desc: "ওপেন-সোর্স টুলস স্যুট ও ডায়নামিক এমসিপি সার্ভার ব্যবস্থাপনা",
    tab_sec_title: "এন্টারপ্রাইজ ডাটা সিকিউরিটি ও কমপ্লায়েন্স",
    tab_sec_desc: "AES-256 এনক্রিপশন, PII/DLP রিডাকশন, ফায়ারওয়াল ও অডিট ট্রেইল",
    tab_backup_title: "সম্পূর্ণ ডেটা ও সেটিংস ব্যাকআপ এবং রিস্টোর",
    tab_backup_desc: "ডকুমেন্টস, চ্যাট হিস্ট্রি, ভেক্টর মেমোরি ও সেটিংসের সার্বিক সুরক্ষা",
    tab_reports_title: "AI রিপোর্ট জেনারেটর — এন্টারপ্রাইজ ইন্টেলিজেন্স রিপোর্টিং",
    tab_reports_desc: "কোম্পানি নলেজবেস থেকে ডেটা রিট্রিভ করে পেশাদার AI রিপোর্ট তৈরি করুন",
    tab_settings_title: "সিস্টেম সেটিংস ও এআই ইঞ্জিন কনফিগারেশন",
    tab_settings_desc: "থিম সিলেকশন, LM Studio সংযোগ, মডেল প্যারামিটার ও সিকিউরিটি কন্ট্রোল",

    // Analytics Dashboard View
    dash_title: "📊 এন্টারপ্রাইজ অ্যানালিটিক্স ড্যাশবোর্ড",
    dash_desc: "রিয়েলটাইম মেমোরি গ্রোথ, স্টোরেজ ব্যবহার এবং সার্ভার কর্মক্ষমতা পর্যবেক্ষণ করুন।",
    dash_kpi_docs: "ইনজেস্টেড ডকুমেন্টস",
    dash_kpi_chunks: "ভেক্টর মেমোরি চাঙ্কস",
    dash_kpi_sessions: "চ্যাট সেশনসমূহ",
    dash_kpi_users: "নিবন্ধিত ইউজার",
    dash_activity_chart: "📅 ৭ দিনের চ্যাট অ্যাক্টিভিটি",
    dash_doc_type: "📁 ডকুমেন্ট টাইপ ডিস্ট্রিবিউশন",
    dash_memory_growth: "🧠 মেমোরি গ্রোথ ট্রেন্ড",
    dash_llm_status: "⚡ LLM সার্ভার স্ট্যাটাস",
    dash_recent_docs: "📂 সাম্প্রতিক ডকুমেন্টস",
    dash_audit_log: "⚡ রিয়েলটাইম অ্যাক্টিভিটি লগ",

    // AI Report Generator View
    reports_title: "📊 AI রিপোর্ট জেনারেটর",
    reports_desc: "কোম্পানির নথি ও তথ্যের ভিত্তিতে তাৎক্ষণিক পেশাদার এক্সিকিউটিভ রিপোর্ট তৈরি করুন।",
    reports_new_title: "✨ নতুন রিপোর্ট তৈরি করুন",
    reports_saved_title: "📋 সংরক্ষিত রিপোর্টসমূহ",

    // User Management View
    users_title: "👥 ইউজার ও রোল ম্যানেজমেন্ট",
    users_desc: "কোম্পানির কর্মকর্তা ও অ্যানালিস্টদের একাউন্ট পারমিশন নিয়ন্ত্রণ করুন।",

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
    kb_title: "ডেটা ও নলেজবেস হাব",
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

    // Models View
    models_title: "⚡ এআই মডেল হাব ও লাইভ লেটেন্সি পিং সিস্টেম",

    // MCP View
    mcp_title: "🔌 টুলস ও মডেল কনটেক্সট প্রোটোকল (MCP) হাব",

    // Security View
    sec_title: "🛡️ এন্টারপ্রাইজ ডাটা সিকিউরিটি ও কমপ্লায়েন্স",

    // Backup View
    backup_title: "💾 ডেটা, চ্যাট ও সেটিংস সম্পূর্ণ ব্যাকআপ এবং রিস্টোর",

    // Admin View
    admin_title: "অ্যাডমিন কমান্ড ও কন্ট্রোল সেন্টার",

    // Toasts & Notifications
    toast_lang_changed: "🌐 ভাষা পরিবর্তন করা হয়েছে: বাংলা",
    toast_session_created: "নতুন চ্যাট সেশন শুরু হয়েছে।",
    toast_copied: "ক্লিপবোর্ডে কপি করা হয়েছে!",
    toast_saved: "সফলভাবে সংরক্ষিত হয়েছে!",
    toast_gen_stopped: "উত্তর তৈরি বন্ধ করা হয়েছে।",
    toast_mem_active: "কোম্পানি মেমোরি সার্চ সক্রিয়",
    toast_mem_disabled: "মেমোরি সার্চ বন্ধ",
    toast_no_export: "এক্সপোর্ট করার মতো কোনো মেসেজ নেই।",
    toast_export_ok: "চ্যাট কথোপকথন সফলভাবে ডাউনলোড হয়েছে!",
    toast_clip_attached: "ফাইল ক্লিপবোর্ড থেকে সংযুক্ত করা হয়েছে",
    toast_login_required: "অনুগ্রহ করে অ্যাডমিন লগইন সম্পন্ন করুন।",
    toast_feedback_like: "ফিডব্যাকের জন্য ধন্যবাদ!",
    toast_feedback_dislike: "ফিডব্যাক গ্রহণ করা হয়েছে। আমরা মডেল উন্নত করছি।"
  },

  en: {
    // Brand & App
    app_title: "MyAgent v3.0.0 - Enterprise Company AI Agent & Analytics",
    app_description: "Dockerized Company AI Agent, Persistent Memory, Admin Dashboard & Big Data Analytics",

    // Login Overlay
    login_title: "MyAgent Enterprise",
    login_desc: "Admin login required to access sensitive company data and AI agent control",
    login_user_label: "Admin Username",
    login_user_placeholder: "admin",
    login_pass_label: "Password",
    login_pass_placeholder: "••••••••",
    login_btn: "Sign In",
    login_host_info: "Host: <code>192.168.9.9:3399</code> • Secure Internal Network",

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
    btn_export: "Export",
    btn_new_chat: "New Chat",
    btn_ingest: "Ingest",

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
    hero_badge: "MyAgent Enterprise AI",
    hero_hello: "Hello,",
    hero_sub_sparkle: "How can I assist you today?",
    hero_desc: "Your smart corporate assistant powered by internal company database and on-premises AI models.",
    hero_chip_1: "📊 Financial Statement Analysis",
    hero_chip_2: "📋 Internal Policies & Leave Rules",
    hero_chip_3: "🖥️ IT & Computer Inventory Report",
    hero_chip_4: "📁 Extract Data from Files & Photos",
    hero_card_1_title: "Company Policies & Rules",
    hero_card_1_desc: "Internal procedures, leave policies, and guidelines",
    hero_card_2_title: "Big Data & Excel Analysis",
    hero_card_2_desc: "Spreadsheet calculation, metrics, and trend tables",
    hero_card_3_title: "Executive Data Report",
    hero_card_3_desc: "Automated report generation and action items",
    hero_card_4_title: "Photo & Image OCR Reading",
    hero_card_4_desc: "Extract text and document summaries from images",

    // Productivity Quick Action Bar
    quick_bar_label: "⚡ Actions:",
    chip_quick_note: "📌 Save Note",
    chip_big_data: "📊 Big Data",
    chip_policy_search: "🔍 Policy Search",
    chip_gen_report: "📑 Generate Report",
    chip_py_sandbox: "🐍 Python Sandbox",
    chip_sec_audit: "🛡️ Security",

    // Chat Input Bar & Attachments
    chat_placeholder: "Ask MyAgent, or attach files/Excel/photos... (Shift+Enter for newline)",
    btn_send_title: "Send Message (Enter)",
    btn_stop_title: "Stop Generating",
    btn_attach_title: "Attach Files or Photos (Excel, PDF, Word, Image)",
    memory_checkbox_label: "Save to company memory",
    memory_toggle_label: "Company Memory",
    upload_indexing: "Indexing into memory...",
    drag_drop_title: "Drop files or photos here",
    drag_drop_desc: "Excel (.xlsx, .csv), Image OCR (.png, .jpg), PDF, or documents analyzed directly",
    chat_privacy_footer: "🔒 MyAgent Enterprise • Secure on-premises database & dedicated LLM server",

    // Chat Message Bubbles, Actions & Sources
    sender_you: "You",
    sender_ai: "MyAgent AI",
    file_saved_badge: "✅ Saved in Memory",
    file_saved_title: "This file is saved in company persistent memory",
    file_save_btn: "💾 Save to Memory",
    file_save_title: "User/Admin Decision: Click to save this file into permanent memory",
    sources_header: "📑 Memory References & Sources",
    sources_page: "Page",
    sources_match: "match",
    msg_copy_btn: "Copy",
    msg_copy_title: "Copy text",
    msg_save_mem_btn: "Save Note",
    msg_save_mem_title: "Save AI response to persistent company memory",
    msg_retry_btn: "Retry",
    msg_retry_title: "Retry generation",
    msg_like_title: "Helpful",
    msg_dislike_title: "Not helpful",
    copied_badge: "✓ Copied!",
    copy_failed: "Failed to copy to clipboard",
    default_attach_prompt: "Please analyze the attached files and provide a comprehensive summary and key actionable insights.",
    calling_tool: "Calling tool:",
    tool_result: "Result",
    error_prefix: "Error:",
    stopped_by_user: "Generation stopped by user",
    server_error_prefix: "Server error:",
    saving_text: "Saving...",
    saved_badge: "✓ Saved!",
    chat_note_default: "Chat Note",
    msg_copy_code: "Copy Code",
    btn_remove: "Remove",
    save_memory_toggle_title: "User/Admin decision: if checked, these files will be permanently saved into company vector memory",
    attached_files_count: "📎 Attached Files ({count})",
    tab_chat_title: "Company Data Intelligence Agent",
    tab_chat_desc: "OpenClaw-style persistent memory & autonomous company AI",
    tab_admin_title: "Admin Command Center & System Control",
    tab_admin_desc: "Server heartbeat, cloud metrics & instant admin actions hub",
    tab_dash_title: "Analytics & System Monitoring Dashboard",
    tab_dash_desc: "Server performance, memory chunks & storage analytics",
    tab_users_title: "Company Users & Access Control",
    tab_users_desc: "Internal staff & employee role management",
    tab_kb_title: "Company Data Library & Memory Ingest",
    tab_kb_desc: "PDF, Word, Excel, CSV & photo/image OCR processing",
    tab_models_title: "AI Model Hub & Realtime Latency Ping",
    tab_models_desc: "External LLM server connection & response time (ms)",
    tab_mcp_title: "Tools & Model Context Protocol (MCP) Hub",
    tab_mcp_desc: "Open-source tools suite & dynamic MCP server management",
    tab_sec_title: "Enterprise Data Security & Compliance",
    tab_sec_desc: "AES-256 encryption, PII/DLP redaction, firewall & audit trail",
    tab_backup_title: "Full Data, Chat & Settings Backup and Restore",
    tab_backup_desc: "Comprehensive protection for documents, chat history & vector memory",
    tab_reports_title: "AI Report Generator — Enterprise Intelligence Reporting",
    tab_reports_desc: "Generate professional AI reports retrieved from company knowledge base",
    tab_settings_title: "System Settings & AI Engine Configuration",
    tab_settings_desc: "Theme selection, LM Studio connection, model parameters & security controls",

    // Analytics Dashboard View
    dash_title: "📊 Enterprise Analytics Dashboard",
    dash_desc: "Monitor real-time memory growth, storage utilization, and server performance.",
    dash_kpi_docs: "Ingested Documents",
    dash_kpi_chunks: "Vector Memory Chunks",
    dash_kpi_sessions: "Chat Sessions",
    dash_kpi_users: "Registered Users",
    dash_activity_chart: "📅 7-Day Chat Activity",
    dash_doc_type: "📁 Document Type Distribution",
    dash_memory_growth: "🧠 Memory Growth Trend",
    dash_llm_status: "⚡ LLM Server Status",
    dash_recent_docs: "📂 Recent Documents",
    dash_audit_log: "⚡ Real-time Activity Log",

    // AI Report Generator View
    reports_title: "📊 AI Report Generator",
    reports_desc: "Generate instant executive corporate reports backed by internal documents.",
    reports_new_title: "✨ Create New Report",
    reports_saved_title: "📋 Saved Reports",

    // User Management View
    users_title: "👥 User & Role Management",
    users_desc: "Manage company personnel and role access permissions.",

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
    kb_title: "Data & Knowledge Base Hub",
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

    // Models View
    models_title: "⚡ AI Model Hub & Live Latency Ping",

    // MCP View
    mcp_title: "🔌 Tools & Model Context Protocol (MCP) Hub",

    // Security View
    sec_title: "🛡️ Enterprise Data Security & Compliance",

    // Backup View
    backup_title: "💾 Full Data, Chat & Settings Backup and Restore",

    // Admin View
    admin_title: "Admin Command & Control Center",

    // Toasts & Notifications
    toast_lang_changed: "🌐 Language switched to: English",
    toast_session_created: "New chat session started.",
    toast_copied: "Copied to clipboard!",
    toast_saved: "Saved successfully!",
    toast_gen_stopped: "Generation stopped.",
    toast_mem_active: "Company memory search enabled",
    toast_mem_disabled: "Memory search disabled",
    toast_no_export: "No messages to export.",
    toast_export_ok: "Chat conversation exported successfully!",
    toast_clip_attached: "Files attached from clipboard",
    toast_login_required: "Please log in to continue.",
    toast_feedback_like: "Thank you for your feedback!",
    toast_feedback_dislike: "Feedback recorded. We are improving the model."
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

  // 5. Update language toggle buttons across Topbar, Mobile Navbar, Login Card
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
 * Updates UI state of language switcher buttons across topbar, mobile navbar, and login overlay.
 */
function updateLanguageSwitcherUI(lang) {
  const switchers = [
    { bn: 'btn-lang-bn', en: 'btn-lang-en' },
    { bn: 'mobile-btn-lang-bn', en: 'mobile-btn-lang-en' },
    { bn: 'login-btn-lang-bn', en: 'login-btn-lang-en' }
  ];

  switchers.forEach(s => {
    const btnBn = document.getElementById(s.bn);
    const btnEn = document.getElementById(s.en);
    if (btnBn && btnEn) {
      if (lang === 'bn') {
        btnBn.classList.add('active');
        btnEn.classList.remove('active');
      } else {
        btnEn.classList.add('active');
        btnBn.classList.remove('active');
      }
    }
  });
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
