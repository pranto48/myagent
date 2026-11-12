/* ==============================================================================
 * Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
 * Made By Arif (https://arifmahmud.com/)
 * Project: MyAgent | Version: 3.4.0
 * Documentation & How-To Guide for Automatic Daily Work Tasks & n8n Workflows
 * ============================================================================== */

let wfDocsState = {
  lang: (typeof getAppLanguage === 'function' ? getAppLanguage() : localStorage.getItem('myagent_lang')) || 'bn',
  search: '',
  nodeCategory: 'all', // 'all' | 'trigger' | 'ai' | 'logic' | 'action' | 'output'
};

const WF_DOC_RECIPES = [
  {
    key: 'fleet_ping',
    icon: '🏥',
    time: '08:30',
    frequency: 'daily',
    saveReport: true,
    saveMemory: false,
    notifyChannels: true,
    name_bn: 'দৈনিক সার্ভার ও নেটওয়ার্ক ফ্লিট অডিট',
    name_en: 'Daily Server Fleet & Network Audit',
    badge_bn: 'প্রতিদিন সকাল ৮:৩০',
    badge_en: 'Daily 08:30 AM',
    desc_bn: 'প্রতিদিন সকালে LAN সার্ভার ও DNS পিং, পোর্ট স্ক্যান এবং Python হেলথ স্কোর বের করে; সমস্যা পেলে Telegram/চ্যাটে সতর্কবার্তা পাঠায়, নাহলে AI Reports-এ সেভ করে।',
    desc_en: 'Pings LAN servers & DNS every morning, runs TCP port scan & Python health scoring; sends urgent alerts if issues arise, else archives executive report.',
    prompt: '192.168.9.1, 192.168.9.5, 192.168.9.9, 8.8.8.8 পিং ও পোর্ট স্ক্যান করে Python দিয়ে হেলথ স্কোর বের করো; কোনো সমস্যা থাকলে সতর্কবার্তা পাঠাও, নাহলে AI Reports-এ সেভ করো।',
    nodesPreview: ['⏰ Trigger 08:30', '🔁 ForEach Ping', '🐍 Python Score', '🧠 AI Agent', '🔀 IF Alert', '📣 Notify / 📄 Report']
  },
  {
    key: 'project_review',
    icon: '📊',
    time: '10:00',
    frequency: 'daily',
    saveReport: true,
    saveMemory: true,
    notifyChannels: false,
    name_bn: 'দৈনিক প্রজেক্ট মেমোরি ও কাজের অগ্রাধিকার',
    name_en: 'Daily Project Memory & Action Plan',
    badge_bn: 'প্রতিদিন সকাল ১০:০০',
    badge_en: 'Daily 10:00 AM',
    desc_bn: 'সংরক্ষিত Project Memory ও SQLite ডাটাবেস রিভিউ করে আজকের করণীয় কাজের তালিকা (Action Items) বানায়, প্রজেক্ট মেমোরিতে আপডেট রাখে ও চ্যাটে ডাইজেস্ট দেয়।',
    desc_en: 'Reviews Project Memory & SQLite DB stats every morning, writes daily action priorities, persists to Project Memory, and delivers to Chat.',
    prompt: 'সংরক্ষিত প্রজেক্ট মেমোরি ও SQLite ডাটাবেস চেক করে আজকের অগ্রাধিকারভিত্তিক কাজের তালিকা (Action Plan) এবং প্রজেক্ট স্ট্যাটাস সারাংশ তৈরি ও মেমোরিতে সংরক্ষণ করো।',
    nodesPreview: ['⏰ Trigger 10:00', '🛠️ SQLite/System', '🧠 AI Agent', '📄 Save Report', '💾 Project Memory', '📣 Chat Digest']
  },
  {
    key: 'security_audit',
    icon: '🛡️',
    time: '03:00',
    frequency: 'daily',
    saveReport: true,
    saveMemory: false,
    notifyChannels: true,
    name_bn: 'রাতের অটো সিকিউরিটি ও DLP কমপ্লায়েন্স অডিট',
    name_en: 'Overnight Security & DLP Compliance Audit',
    badge_bn: 'প্রতিদিন রাত ৩:০০',
    badge_en: 'Daily 03:00 AM',
    desc_bn: 'গভীর রাতে 192.168.9.9 সার্ভারের ওপেন পোর্ট ও DLP/সিকিউরিটি অডিট চালিয়ে ঝুঁকি শনাক্ত করে ও অডিট রিপোর্ট আর্কাইভ করে।',
    desc_en: 'Runs TCP port scan on 192.168.9.9 and DLP security auditor sub-agent overnight, surfacing risks and archiving compliance report.',
    prompt: 'সার্ভার 192.168.9.9 ও লোকাল পোর্ট স্ক্যান এবং সিকিউরিটি DLP অডিট চালিয়ে কোনো warning বা critical ঝুঁকি পাওয়া গেলে সতর্ক করো, নাহলে রিপোর্ট সেভ করো।',
    nodesPreview: ['⏰ Trigger 03:00', '🛠️ Port Scan', '🤖 Security SubAgent', '🧠 Analyst', '📄 Security Report']
  },
  {
    key: 'api_uptime',
    icon: '📡',
    time: '09:00',
    frequency: 'every_6h',
    saveReport: false,
    saveMemory: true,
    notifyChannels: true,
    name_bn: 'প্রতি ৬ ঘণ্টায় API এন্ডপয়েন্ট হেলথ ও JSON চেক',
    name_en: 'Every-6h API Endpoint Uptime & JSON Monitor',
    badge_bn: 'প্রতি ৬ ঘণ্টায়',
    badge_en: 'Every 6 Hours',
    desc_bn: 'আপনার গুরুত্বপূর্ণ ওয়েব/এপিআই URL প্রতি ৬ ঘণ্টায় চেক করে রেসপন্স যাচাই করে এবং প্রজেক্ট মেমোরিতে আপটাইম লগ রাখে।',
    desc_en: 'Polls target web/API endpoints every 6 hours via HTTP Request + Python validation and stores uptime telemetry into memory & notifications.',
    prompt: 'http://192.168.9.9:3399/api/health এ HTTP চেক করে রেসপন্স ও ল্যাটেন্সি যাচাই করো; কোনো ত্রুটি পেলে সাথে সাথে সতর্ক করো ও প্রজেক্ট মেমোরিতে সেভ করো।',
    nodesPreview: ['⏰ Every 6h', '📡 HTTP GET', '🐍 Python Check', '🔀 IF Error', '📣 Alert / 💾 Memory']
  }
];

const WF_DOC_NODES = [
  { type: 'trigger_daily', cat: 'trigger', icon: '⏰', color: '#06b6d4', title_bn: 'Daily Schedule Trigger', title_en: 'Daily Schedule Trigger', desc_bn: 'প্রতিদিন, প্রতি ঘণ্টায়, প্রতি ৬ ঘণ্টায়, সাপ্তাহিক বা প্রতি ১৫ মিনিটে Asia/Dhaka (+06:00) সময় অনুযায়ী ওয়ার্কফ্লো চালু করে।', desc_en: 'Fires workflows automatically on daily, hourly, every 6h, weekly, or 15-min schedules using Asia/Dhaka (+06:00) local time.', cfg_hint: 'daily_time, frequency, timezone' },
  { type: 'trigger_webhook', cat: 'trigger', icon: '🌐', color: '#0ea5e9', title_bn: 'Webhook HTTP Trigger', title_en: 'Webhook HTTP Trigger', desc_bn: 'যেকোনো বাহ্যিক অ্যাপ, স্ক্রিপ্ট বা মনিটরিং টুল থেকে POST রিকোয়েস্ট পাঠালেই {{trigger.payload}} ডেটাসহ পাইপলাইন রান করে।', desc_en: 'Starts the workflow whenever an external app sends an authenticated HTTP POST with JSON payload into {{trigger.payload}}.', cfg_hint: 'POST /api/workflows/webhook/{id}?secret=...' },
  { type: 'ai_agent', cat: 'ai', icon: '🧠', color: '#a855f7', title_bn: 'AI Autonomous Agent', title_en: 'AI Autonomous Agent', desc_bn: 'RAG ও Project Memory পড়ে এবং প্রয়োজন অনুযায়ী মাল্টি-টার্ন টুল কলিং (Ping, SQLite, File, Code Audit) চালিয়ে ফলাফল তৈরি করে। OpenRouter ও অফলাইন ফলব্যাক সমর্থিত।', desc_en: 'Headless autonomous agent with RAG + Project Memory injection, multi-turn tool calling (max_turns), OpenRouter failover & optional offline telemetry digest.', cfg_hint: 'prompt, model, enable_tools, use_memory, fallback_on_error' },
  { type: 'subagent', cat: 'ai', icon: '🤖', color: '#8b5cf6', title_bn: 'Sub-Agent / Multi-Agent Swarm', title_en: 'Sub-Agent / Swarm', desc_bn: 'বিশেষায়িত সাব-এজেন্ট (Net Ping, Security Auditor, DevOps Fleet, Memory Synthesizer, Task Planner) অথবা পূর্ণ Multi-Agent Swarm অর্কেস্ট্রেটর চালায়।', desc_en: 'Runs specialized domain sentinels (Net Ping, Security, DevOps, Memory, Planner) or the full autonomous Swarm pipeline.', cfg_hint: 'agent_id (or swarm), task, model' },
  { type: 'tool_call', cat: 'action', icon: '🛠️', color: '#3b82f6', title_bn: 'Execute Agent Tool', title_en: 'Execute Agent Tool', desc_bn: '৩৭+ বিল্ট-ইন ও MCP টুলের যেকোনোটি সরাসরি চালায় — যেমন system_info, network_port_scan, sqlite_schema_inspector, git_repo_inspector, enhance_prompt ইত্যাদি।', desc_en: 'Directly executes any of 37+ built-in/MCP tools (system_info, network_port_scan, sqlite_schema_inspector, git_repo_inspector, etc.) without LLM token cost.', cfg_hint: 'tool_name, args_json' },
  { type: 'mcp_tool', cat: 'action', icon: '🔌', color: '#6366f1', title_bn: 'MCP Tool Call (Hub)', title_en: 'MCP Tool Call (External Hub)', desc_bn: 'MCP Hub-এ যুক্ত যেকোনো এক্সটার্নাল SSE/HTTP বা stdio MCP সার্ভারের টুল (fetch_article_markdown, fs_read_dir বা কাস্টম MCP সার্ভার) সরাসরি ওয়ার্কফ্লো থেকে কল করে।', desc_en: 'Directly calls any tool exposed by external SSE/HTTP or stdio MCP servers registered in MCP Hub, with automatic inputSchema sample generation.', cfg_hint: 'server_id, tool_name, args_json' },
  { type: 'python_transform', cat: 'action', icon: '🐍', color: '#eab308', title_bn: 'Python Data Transform', title_en: 'Python Data Transform', desc_bn: 'কাস্টম Python স্ক্রিপ্টে prev_output, prev_json, prev_all, vars (সিক্রেটস), nodes_data ও trigger ব্যবহার করে ডেটা ফিল্টারিং, JSON পার্সিং ও টেবিল তৈরি করে।', desc_en: 'Runs custom Python with pre-injected prev_output, prev_json, prev_all, vars/secrets, nodes_data, trigger, json, re, statistics, pandas & numpy.', cfg_hint: 'code (uses stdout print output)' },
  { type: 'loop_foreach', cat: 'logic', icon: '🔁', color: '#6366f1', title_bn: 'ForEach Batch Loop', title_en: 'ForEach Batch Loop', desc_bn: 'সর্বোচ্চ ২৫টি IP, URL বা টার্গেটের ওপর একসাথে ICMP/TCP পিং, টুল কল বা HTTP চেক চালিয়ে একীভূত Markdown টেবিল দেয়।', desc_en: 'Iterates over up to 25 newline/comma/JSON items running ICMP ping, Agent Tool, or HTTP GET/POST per {{item}}.', cfg_hint: 'items_text, action_type (ping|tool|http)' },
  { type: 'delay_wait', cat: 'logic', icon: '⏳', color: '#64748b', title_bn: 'Delay / Wait Timer', title_en: 'Delay / Wait Timer', desc_bn: 'এপিআই রেট-লিমিট বা সার্ভিস রিস্টার্টের পর 0.1–60 সেকেন্ড বিরতি দিয়ে পূর্ববর্তী আউটপুট অক্ষুণ্ণ রেখে পরবর্তী ধাপে যায়।', desc_en: 'Pauses execution cleanly for 0.1s–60s between steps while forwarding {{prev.output}} downstream.', cfg_hint: 'seconds (0.1 - 60)' },
  { type: 'condition', cat: 'logic', icon: '🔀', color: '#f59e0b', title_bn: 'IF / Else Condition Router', title_en: 'IF / Else Condition', desc_bn: 'contains, equals, regex, not_empty, greater_than, less_than যাচাই করে TRUE বা FALSE শাখায় রাউট করে (অন্য শাখা SKIPPED হয়)।', desc_en: 'Evaluates text, regex, or numeric rules to route execution down TRUE or FALSE ports while marking untaken branch nodes SKIPPED.', cfg_hint: 'target, operator, value' },
  { type: 'http_request', cat: 'action', icon: '📡', color: '#0284c7', title_bn: 'HTTP / Webhook Request', title_en: 'HTTP Request', desc_bn: 'যেকোনো বাহ্যিক REST API-তে ডাইনামিক JSON বডি ও হেডারসহ GET, POST, PUT, PATCH বা DELETE কল করে।', desc_en: 'Performs GET, POST, PUT, PATCH, or DELETE HTTP calls with dynamic templated headers and JSON payload.', cfg_hint: 'method, url, headers_json, body_json' },
  { type: 'save_report', cat: 'output', icon: '📄', color: '#10b981', title_bn: 'Save Executive Report', title_en: 'Save Executive Report', desc_bn: 'Markdown ফাইল আর্কাইভ করে ও reports.db-তে সংরক্ষণ করে — যাতে সরাসরি AI Reports ট্যাবে পড়া, ডাউনলোড ও সার্চ করা যায়।', desc_en: 'Saves structured Markdown reports both on disk and in reports.db so they immediately appear in the AI Reports UI tab.', cfg_hint: 'title, report_type, content, index_in_memory' },
  { type: 'memory_save', cat: 'output', icon: '💾', color: '#14b8a6', title_bn: 'Save Project Memory', title_en: 'Save Project Memory', desc_bn: 'নির্দিষ্ট প্রজেক্ট নেম ও কী-এর অধীনে ProjectMemoryStore এবং Hybrid Vector RAG স্টোরে স্থায়ীভাবে নোট সংরক্ষণ করে।', desc_en: 'Persists dated daily logs and insights into ProjectMemoryStore + Vector Memory for future chats and MCP clients.', cfg_hint: 'project_name, key, category, content' },
  { type: 'notify_channel', cat: 'output', icon: '📣', color: '#ec4899', title_bn: 'Notify Chat & Channels', title_en: 'Notify Chat & Channels', desc_bn: 'চ্যাট হিস্ট্রির "📅 Daily Automated Agent Reports" সেশনে পাঠায় এবং সক্রিয় Telegram, Discord, Slack ও কাস্টম ওয়েবহুকে ব্রডকাস্ট করে।', desc_en: 'Posts digest to Chat session "session_daily_automations" and dispatches alerts to configured Telegram/Discord/Slack/Webhook targets.', cfg_hint: 'target, title, message, custom_webhook_url' },
  { type: 'merge_combine', cat: 'logic', icon: '🤝', color: '#14b8a6', title_bn: 'Merge Parallel Branches', title_en: 'Merge Branches', desc_bn: 'একসাথে চলা একাধিক প্যারালাল শাখার (Fan-Out) ফলাফলকে একত্রিত Markdown বা JSON আকারে পরবর্তী নোডে পাঠায়।', desc_en: 'Joins outputs from multiple concurrent parallel branches (Fan-Out) into a single unified Markdown dossier or JSON array.', cfg_hint: 'mode (markdown_sections | json_array)' },
  { type: 'switch_router', cat: 'logic', icon: '🚦', color: '#f97316', title_bn: 'Multi-Way Switch Router', title_en: 'Multi-Way Switch Router', desc_bn: 'Route 1, Route 2 ও Default — এই ৩+ পথে ডাইনামিক রাউটিং করে (যেমন CRITICAL -> Urgent Alert, WARNING -> Log, OK -> Archive)।', desc_en: '3-way conditional router evaluating Route 1, Route 2, and Default ports with color-coded branching.', cfg_hint: 'target, route1_op/val, route2_op/val' },
  { type: 'sub_workflow', cat: 'action', icon: '🔗', color: '#8b5cf6', title_bn: 'Call Sub-Workflow', title_en: 'Call Sub-Workflow', desc_bn: 'অন্য একটি বিদ্যমান ওয়ার্কফ্লোকে সাব-মডিউল হিসেবে রান করে এবং তার চূড়ান্ত আউটপুট গ্রহণ করে (সর্বোচ্চ ৩ স্তর রিকার্শন)।', desc_en: 'Invokes another saved workflow modularly with custom JSON payload and returns its final_output cleanly.', cfg_hint: 'target_workflow_id, payload_json' },
  { type: 'knowledge_db_query', cat: 'action', icon: '🗄️', color: '#0ea5e9', title_bn: 'SQLite DB & RAG Knowledge Query', title_en: 'DB SQL & RAG Query', desc_bn: 'ops.db, reports.db, project_memory.db ইত্যাদি SQLite ডাটাবেসে নিরাপদ SELECT কোয়েরি অথবা Vector নলেজ সার্চ চালায়।', desc_en: 'Runs read-only SELECT/PRAGMA SQL queries on internal SQLite DBs or semantic RAG searches across vector memory.', cfg_hint: 'query_mode (sqlite|rag), db_name, sql_query' }
];

const WF_DOC_VARIABLES = [
  { token: '{{trigger.date}}', desc_bn: 'আজকের তারিখ (Asia/Dhaka), যেমন 2026-11-10', desc_en: 'Local trigger date YYYY-MM-DD' },
  { token: '{{trigger.time}}', desc_bn: 'ট্রিগারের সময় (HH:MM:SS)', desc_en: 'Local trigger time HH:MM:SS' },
  { token: '{{trigger.datetime}}', desc_bn: 'পূর্ণ তারিখ ও সময়', desc_en: 'Combined local date & time' },
  { token: '{{trigger.iso}}', desc_bn: 'ISO-8601 টাইমস্ট্যাম্প (+06:00 সহ)', desc_en: 'Timezone-aware ISO timestamp' },
  { token: '{{trigger.payload}}', desc_bn: 'ওয়েবহুক POST-এ পাঠানো সম্পূর্ণ JSON পেলোড', desc_en: 'Full inbound webhook JSON body' },
  { token: '{{trigger.payload.server}}', desc_bn: 'পেলোডের নির্দিষ্ট কী পড়া (যেমন .server)', desc_en: 'Dot-path access inside webhook payload JSON' },
  { token: '{{prev.output}}', desc_bn: 'ঠিক পূর্ববর্তী নোডের সম্পূর্ণ আউটপুট', desc_en: 'Full text output from immediately preceding node' },
  { token: '{{prev.output|500}}', desc_bn: 'পূর্ববর্তী আউটপুট সর্বোচ্চ ৫০০ অক্ষরে সীমিত করে নেওয়া', desc_en: 'Truncated upstream output (custom char limit)' },
  { token: '{{prev.json.status}}', desc_bn: 'পূর্ববর্তী নোডের JSON আউটপুট থেকে নির্দিষ্ট ফিল্ড পড়া', desc_en: 'Parse upstream JSON output by dot path' },
  { token: '{{prev.error}}', desc_bn: 'Continue-on-Fail চালু থাকলে পূর্বের ত্রুটির বার্তা', desc_en: 'Upstream error string when continue_on_fail is enabled' },
  { token: '{{nodes.node_2.output}}', desc_bn: 'নির্দিষ্ট নোডের (যেমন node_2) আউটপুট রেফারেন্স', desc_en: 'Specific node output anywhere downstream' },
  { token: '{{workflow.name}}', desc_bn: 'বর্তমান ওয়ার্কফ্লোর শিরোনাম', desc_en: 'Current active workflow title' },
  { token: '{{vars.API_TOKEN}}', desc_bn: '🔐 Global Vault-এ এনক্রিপ্টেড ভেরিয়েবল/সিক্রেট ইনজেক্ট (লগে ***REDACTED*** থাকে)', desc_en: 'Inject AES-256 encrypted secret/var from Global Vault (auto-redacted in logs)' }
];

const WF_DOC_FAQS = [
  {
    q_bn: '১. ডকার সার্ভার UTC টাইমজোনে থাকলেও কি প্রতিদিন ঠিক বাংলাদেশ সময় (Asia/Dhaka +06:00) অনুযায়ী কাজ চলবে?',
    q_en: '1. Will daily tasks fire accurately in Asia/Dhaka (+06:00) even when the Docker host uses UTC?',
    a_bn: 'হ্যাঁ। WorkflowStore-এ Asia/Dhaka (+06:00) অনুযায়ী পরবর্তী রান হিসাব করে UTC epoch (next_run_ts) ডাটাবেসে সেভ করা হয় এবং CronScheduler প্রতি ২০ সেকেন্ডে next_run_ts যাচাই করে টাস্ক চালায়।',
    a_en: 'Yes. WorkflowStore calculates the upcoming local fire time in Asia/Dhaka (+06:00), converts it to UTC epoch next_run_ts, and CronScheduler checks due workflows every 20 seconds.'
  },
  {
    q_bn: '২. "AI Agent failed: Connection error" দেখালে কী করতে হবে?',
    q_en: '2. What causes "AI Agent failed: Connection error" and how do I fix it?',
    a_bn: 'আপনার কনফিগার করা প্রাইমারি LLM সার্ভার (যেমন LAN LM Studio) যদি বন্ধ বা অফলাইন থাকে তখন AI নোড সংযোগ পায় না। Settings-এ OpenRouter API Key সেভ করলে MyAgent স্বয়ংক্রিয়ভাবে openrouter/free মডেলে ফেইলওভার করবে। এছাড়া প্রতিটি AI নোডে "🛡️ Offline Digest Fallback" চালু রাখলে LLM ছাড়াও পূর্ববর্তী পিং/টুল টেলিমেট্রি রিপোর্ট স্বয়ংক্রিয়ভাবে ডেলিভারি হবে।',
    a_en: 'It happens if the primary LAN LLM server (e.g. LM Studio) is powered off. Add an OpenRouter API Key in Settings for automatic cloud failover, or enable "🛡️ Offline Digest Fallback" on the AI Agent node so upstream tool telemetry still gets delivered cleanly.'
  },
  {
    q_bn: '৩. দৈনিক অটোমেটিক কাজের রিপোর্ট ও চ্যাট মেসেজ কোথায় দেখা যাবে?',
    q_en: '3. Where can I view the generated reports and chat digests from daily workflows?',
    a_bn: 'Save Executive Report নোডের আউটপুট সাথে সাথে "📄 AI Report Generator" (AI Reports) ট্যাবে সেভ হয়। আর Notify Chat নোডের মেসেজ চ্যাট সাইডবারে "📅 Daily Automated Agent Reports" সেশনে জমা থাকে। প্রতি রানের বিস্তারিত টাইমলাইন দেখা যাবে Workflows -> Execution History ট্যাবে।',
    a_en: 'Save Executive Report writes directly to reports.db so items appear immediately under AI Reports. Notify Chat posts to persistent session "📅 Daily Automated Agent Reports". Step-by-step latency & trace logs appear in Workflows -> Execution History.'
  },
  {
    q_bn: '৪. বাহ্যিক স্ক্রিপ্ট বা Claude Code / Cursor IDE (MCP) থেকে কীভাবে দৈনিক ওয়ার্কফ্লো তৈরি বা রান করবো?',
    q_en: '4. How can Claude Code, Cursor IDE, or external scripts create and trigger daily workflows?',
    a_bn: 'MyAgent MCP সার্ভারে create_daily_agent_task, architect_workflow_from_goal, list_workflows এবং run_workflow_now টুল বিল্ট-ইন রয়েছে। এছাড়া প্রতিটি ওয়ার্কফ্লোর 🔗 Webhook URL-এ যেকোনো সিস্টেম থেকে HTTP POST পাঠিয়েও তৎক্ষণাৎ রান করা যায়।',
    a_en: 'MyAgent MCP Server exposes create_daily_agent_task, architect_workflow_from_goal, list_workflows, and run_workflow_now via JSON-RPC. Any script can also trigger workflows via HTTP POST to the workflow\'s 🔗 Webhook URL.'
  },
  {
    q_bn: '৫. লোকাল LAN সার্ভার (192.168.9.9)-এ পাবলিক ডোমেইন বা HTTPS ছাড়া কি Telegram টু-ওয়ে চ্যাট কাজ করবে?',
    q_en: '5. Will Telegram Two-Way Chat work on a private LAN server (192.168.9.9) without a public HTTPS domain?',
    a_bn: 'হ্যাঁ! MyAgent TelegramChatListener বিল্ট-ইন Long-Polling (/getUpdates) ব্যবহার করে। তাই কোনো পাবলিক ডোমেইন বা পোর্ট ফরওয়ার্ডিং ছাড়াই টেলিগ্রাম থেকে ping 192.168.9.2, /status বা /run কমান্ড দিলে সাথে সাথে উত্তর ও ওয়ার্কফ্লো রিপোর্ট পাঠায়।',
    a_en: 'Yes! MyAgent uses built-in Telegram Long-Polling (/getUpdates) inside TelegramChatListener, so two-way chat commands (ping 192.168.9.2, /status, /run) work cleanly inside private LANs with zero public domain or inbound ports.'
  },
  {
    q_bn: '৬. Telegram কানেক্ট করার সময় Auto-Detect Chat ID খালি দেখালে বা HTTP 401 / 409 ত্রুটি এলে কী করবো?',
    q_en: '6. How do I fix empty Auto-Detect Chat ID or HTTP 401 / 409 errors when connecting Telegram?',
    a_bn: 'প্রথমে টেলিগ্রামে আপনার নতুন বটটি ওপেন করে অবশ্যই /start বা যেকোনো একটি মেসেজ পাঠান, তারপর 🔍 Auto-Detect ক্লিক করুন। ভুল বা বাতিল টোকেন হলে HTTP 401 আসে (@BotFather থেকে /token দিয়ে নতুন টোকেন নিন)। অন্য কোথাও Webhook চালু থাকলেও HTTP 409 হয় — MyAgent এখন Auto-Detect/Polling চলাকালীন স্বয়ংক্রিয়ভাবে deleteWebhook চালিয়ে তা ঠিক করে দেয়।',
    a_en: 'First open your bot in Telegram and send /start or hello before clicking 🔍 Auto-Detect. HTTP 401 means an invalid/revoked Bot Token (regenerate in @BotFather). HTTP 409 Webhook Conflict is automatically resolved by MyAgent calling deleteWebhook during detection/polling.'
  }
];

function wfDocsEsc(s) {
  if (typeof escapeHtml === 'function') return escapeHtml(s == null ? '' : String(s));
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function wfDocsCopy(text, label = '') {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text);
  }
  const msg = label
    ? `📋 কপি হয়েছে: ${label}`
    : (wfDocsState.lang === 'en' ? '📋 Copied to clipboard!' : '📋 ক্লিপবোর্ডে কপি হয়েছে!');
  if (typeof showToast === 'function') {
    showToast(msg, 'success');
  } else {
    alert(msg);
  }
}

function wfDocsCopyRecipePrompt(recipeKey) {
  const rec = WF_DOC_RECIPES.find(r => r.key === recipeKey);
  if (!rec) return;
  wfDocsCopy(rec.prompt, wfDocsState.lang === 'en' ? 'Prompt' : 'প্রম্পট');
}

function wfDocsCopyCurl() {
  const originUrl = window.location.origin || 'http://192.168.9.9:3399';
  const curlSample = `curl -X POST "${originUrl}/api/workflows/webhook/YOUR_WORKFLOW_ID?secret=YOUR_SECRET" -H "Content-Type: application/json" -d '{"server": "192.168.9.9", "event": "check"}'`;
  wfDocsCopy(curlSample, 'Webhook cURL');
}

function setWfDocsLanguage(lang) {
  wfDocsState.lang = lang === 'en' ? 'en' : 'bn';
  renderWorkflowDocsPage();
}

function setWfDocsNodeCat(cat) {
  wfDocsState.nodeCategory = cat;
  renderWorkflowDocsPage();
}

function handleWfDocsSearch(val) {
  wfDocsState.search = (val || '').trim().toLowerCase();
  renderWorkflowDocsPage();
  const inp = document.getElementById('wf-docs-search-input');
  if (inp) {
    inp.focus();
    const len = inp.value.length;
    inp.setSelectionRange(len, len);
  }
}

function launchRecipeInStudio(recipeKey) {
  const rec = WF_DOC_RECIPES.find(r => r.key === recipeKey);
  if (!rec) return;

  // Standalone guide fallback: redirect into SPA with query params
  if (typeof switchTab !== 'function') {
    window.location.href = `/?tab=workflows&recipe=${encodeURIComponent(recipeKey)}`;
    return;
  }

  switchTab('workflows');
  setTimeout(() => {
    const body = document.getElementById('wf-quick-builder-body');
    if (body) body.style.display = 'block';

    const isEn = wfDocsState.lang === 'en';
    const nameEl = document.getElementById('wf-quick-name');
    const timeEl = document.getElementById('wf-quick-time');
    const freqEl = document.getElementById('wf-quick-frequency');
    const instEl = document.getElementById('wf-quick-instruction');
    const repEl = document.getElementById('wf-quick-save-report');
    const memEl = document.getElementById('wf-quick-save-memory');
    const chEl = document.getElementById('wf-quick-notify-channels');

    if (nameEl) nameEl.value = isEn ? rec.name_en : rec.name_bn;
    if (timeEl) timeEl.value = rec.time;
    if (freqEl) freqEl.value = rec.frequency;
    if (instEl) instEl.value = rec.prompt;
    if (repEl) repEl.checked = !!rec.saveReport;
    if (memEl) memEl.checked = !!rec.saveMemory;
    if (chEl) chEl.checked = !!rec.notifyChannels;

    const card = document.getElementById('wf-quick-daily-card');
    if (card) card.scrollIntoView({ behavior: 'smooth', block: 'start' });

    if (typeof showToast === 'function') {
      showToast(
        isEn
          ? `✅ Recipe "${rec.name_en}" loaded into Quick Builder! Click "AI Multi-Node Architect" or "Create & Activate".`
          : `✅ রেসিপি "${rec.name_bn}" কুইক বিল্ডারে লোড হয়েছে! এখন "AI Multi-Node Architect" বা "তৈরি ও অ্যাক্টিভেট করুন" বাটনে ক্লিক করুন।`,
        'success'
      );
    }
  }, 120);
}

function goBackToWorkflowStudio(subTab = null) {
  if (typeof switchTab === 'function') {
    switchTab('workflows', subTab);
  } else {
    const qs = subTab ? `?tab=workflows&subtab=${encodeURIComponent(subTab)}` : '?tab=workflows';
    window.location.href = `/${qs}`;
  }
}

function openTelegramConnectionFromDocs() {
  goBackToWorkflowStudio('telegram');
}

async function refreshDocsTelegramLiveBadge() {
  const pillEl = document.getElementById('wfd-tg-live-pill');
  const metaEl = document.getElementById('wfd-tg-live-meta');
  if (!pillEl) return;
  const isEn = wfDocsState.lang === 'en';
  try {
    const res = await fetch('/api/workflows/telegram/status');
    const data = await res.json();
    const tg = data?.telegram || {};
    if (tg.connected) {
      pillEl.className = 'wfd-tg-status-pill connected';
      pillEl.textContent = `🟢 CONNECTED${tg.bot_username ? ' (' + tg.bot_username + ')' : ''}`;
      if (metaEl) {
        metaEl.textContent = isEn
          ? `Chat ID: ${tg.chat_id || '-'} • Sent: ${tg.sent_count || 0} • Listener: ${tg.listener_running ? 'Active' : 'Idle'}`
          : `Chat ID: ${tg.chat_id || '-'} • পাঠানো হয়েছে: ${tg.sent_count || 0}টি • লিসেনার: ${tg.listener_running ? 'চালু' : 'বন্ধ'}`;
      }
    } else if (tg.status === 'Error') {
      pillEl.className = 'wfd-tg-status-pill error';
      pillEl.textContent = '🟠 ERROR';
      if (metaEl) metaEl.textContent = tg.last_error || 'Verification failed';
    } else {
      pillEl.className = 'wfd-tg-status-pill disconnected';
      pillEl.textContent = isEn ? '🔴 NOT CONNECTED YET' : '🔴 এখনও সংযুক্ত নয়';
      if (metaEl) {
        metaEl.textContent = tg.has_token
          ? (isEn ? 'Bot token saved; add Chat ID & enable connection in Telegram tab.' : 'Bot টোকেন সেভ আছে; Chat ID দিয়ে Telegram ট্যাবে কানেক্ট করুন।')
          : (isEn ? 'Follow the 4 steps below, then click "Open Telegram Settings" to connect your bot.' : 'নিচের ৪টি ধাপ অনুসরণ করে "Telegram কানেকশন খুলুন" বাটনে গিয়ে আপনার বট সংযুক্ত করুন।');
      }
    }
  } catch (_) {
    pillEl.className = 'wfd-tg-status-pill disconnected';
    pillEl.textContent = '⚪ Offline / Unknown';
  }
}

function renderWorkflowDocsPage(targetContainerId = 'wf-docs-root') {
  const root = document.getElementById(targetContainerId);
  if (!root) return;

  const isEn = wfDocsState.lang === 'en';
  const q = wfDocsState.search;
  const matchQ = (txt) => !q || String(txt || '').toLowerCase().includes(q);

  const filteredNodes = WF_DOC_NODES.filter(n => {
    const catOk = wfDocsState.nodeCategory === 'all' || n.cat === wfDocsState.nodeCategory;
    const textMatch = matchQ(`${n.type} ${n.title_bn} ${n.title_en} ${n.desc_bn} ${n.desc_en} ${n.cfg_hint}`);
    return catOk && textMatch;
  });

  const filteredVars = WF_DOC_VARIABLES.filter(v => matchQ(`${v.token} ${v.desc_bn} ${v.desc_en}`));
  const filteredRecipes = WF_DOC_RECIPES.filter(r => matchQ(`${r.name_bn} ${r.name_en} ${r.desc_bn} ${r.desc_en} ${r.prompt}`));
  const filteredFaqs = WF_DOC_FAQS.filter(f => matchQ(`${f.q_bn} ${f.q_en} ${f.a_bn} ${f.a_en}`));

  const originUrl = window.location.origin || 'http://192.168.9.9:3399';
  const curlWebhookSample = `curl -X POST "${originUrl}/api/workflows/webhook/YOUR_WORKFLOW_ID?secret=YOUR_SECRET" -H "Content-Type: application/json" -d '{"server": "192.168.9.9", "event": "check"}'`;
  const standaloneHref = `${originUrl}/workflow-guide.html`;

  root.innerHTML = `
    <div class="wfd-container">
      <!-- Hero Banner -->
      <div class="wfd-hero">
        <div class="wfd-hero-left">
          <div class="wfd-badge-row">
            <span class="wfd-pill-badge">📚 COMPLETE AUTOMATION DOCUMENTATION</span>
            <span class="wfd-pill-version">MyAgent v3.5 Engine</span>
          </div>
          <h2>${isEn ? 'How to Create Automatic Daily AI Work Tasks & n8n Workflows' : 'দৈনিক অটোমেটিক এআই কাজ (Auto Work Tasks) ও ওয়ার্কফ্লো তৈরির সম্পূর্ণ গাইড ও ডকুমেন্টেশন'}</h2>
          <p>${isEn
            ? 'Configure daily scheduled autonomous AI agents, multi-node n8n visual pipelines, IF/Else alert branching, Python transforms, reports & Chat/Telegram digests in minutes.'
            : 'প্রতিদিন নির্দিষ্ট সময়ে সার্ভার মনিটরিং, প্রজেক্ট মেমোরি আপডেট, AI রিপোর্ট তৈরি, Python ডেটা প্রসেসিং এবং Telegram/Discord/Chat ডাইজেস্ট অটোমেট করার পূর্ণাঙ্গ ব্যবহারবিধি ও রেফারেন্স।'}</p>
          <div class="wfd-hero-actions">
            <button type="button" class="btn-primary" onclick="goBackToWorkflowStudio()">
              ⚡ ${isEn ? 'Open Workflows Studio' : 'ওয়ার্কফ্লো স্টুডিও খুলুন'}
            </button>
            <button type="button" class="btn-secondary" onclick="openTelegramConnectionFromDocs()">
              ✈️ ${isEn ? 'Connect Telegram Bot' : 'টেলিগ্রাম কানেক্ট করুন'}
            </button>
            <button type="button" class="btn-secondary" onclick="launchRecipeInStudio('fleet_ping')">
              🚀 ${isEn ? 'Load Sample Daily Task' : '১-ক্লিকে উদাহরণ টাস্ক লোড করুন'}
            </button>
            <a href="${wfDocsEsc(standaloneHref)}" target="_blank" class="btn-secondary" style="text-decoration:none;">
              🔗 ${isEn ? 'Standalone Docs URL' : 'আলাদা ট্যাবে ওপেন করুন'}
            </a>
          </div>
        </div>
        <div class="wfd-hero-right">
          <div class="wfd-lang-switch">
            <button type="button" class="${!isEn ? 'active' : ''}" onclick="setWfDocsLanguage('bn')">🇧🇩 বাংলা গাইড</button>
            <button type="button" class="${isEn ? 'active' : ''}" onclick="setWfDocsLanguage('en')">🇬🇧 English Docs</button>
          </div>
          <div class="wfd-search-box">
            <input type="text" id="wf-docs-search-input" class="text-input"
                   value="${wfDocsEsc(wfDocsState.search)}"
                   oninput="handleWfDocsSearch(this.value)"
                   placeholder="${isEn ? '🔍 Search nodes, {{variables}}, Telegram, API, FAQ...' : '🔍 নোড, {{ভেরিয়েবল}}, টেলিগ্রাম, API বা প্রশ্ন খুঁজুন...'}">
          </div>
          <div class="wfd-toc-links">
            <a href="#wfd-sec-steps">${isEn ? '1. Step-by-Step Guide' : '১. দৈনিক টাস্ক তৈরির ধাপ'}</a>
            <a href="#wfd-sec-recipes">${isEn ? '2. Ready Recipes' : '২. রেডিমেড রেসিপি'}</a>
            <a href="#wfd-sec-nodes">${isEn ? '3. 18 Node Reference' : '৩. ১৮টি নোড রেফারেন্স'}</a>
            <a href="#wfd-sec-vars">${isEn ? '4. Template Variables' : '৪. ডাইনামিক ভেরিয়েবল'}</a>
            <a href="#wfd-sec-api">${isEn ? '5. Webhook, API & MCP' : '৫. ওয়েবহুক, API ও MCP'}</a>
            <a href="#wfd-sec-telegram">${isEn ? '6. Telegram Bot Guide' : '৬. টেলিগ্রাম কানেকশন গাইড'}</a>
            <a href="#wfd-sec-faq">${isEn ? '7. FAQ & Troubleshooting' : '৭. সমস্যা ও সমাধান (FAQ)'}</a>
          </div>
        </div>
      </div>

      <!-- SECTION 1: Step-by-Step 4 Creation Methods -->
      <section class="wfd-section" id="wfd-sec-steps">
        <div class="wfd-sec-head">
          <h3><span>🧭</span> ${isEn ? '1. Four Ways to Create Automatic Daily Work Tasks' : '১. দৈনিক অটোমেটিক কাজ তৈরি করার ৪টি সহজ পদ্ধতি'}</h3>
          <span class="wfd-sec-sub">${isEn ? 'Start simple with Quick Daily Builder or design complex multi-branch pipelines' : 'সহজ ১-ক্লিক বিল্ডার থেকে শুরু করে পূর্ণাঙ্গ ভিজ্যুয়াল n8n ক্যানভাস ও MCP অটোমেশন'}</span>
        </div>

        <div class="wfd-steps-grid">
          <div class="wfd-step-card">
            <div class="wfd-step-num">পদ্ধতি ১ • 1-CLICK SIMPLE</div>
            <h4>⚡ ${isEn ? 'Quick Daily Auto-Task Builder' : 'কুইক ডেইলি বিল্ডার (সবচেয়ে সহজ)'}</h4>
            <ol>
              <li>${isEn ? 'Open <b>WORKFLOWS</b> tab in the sidebar.' : 'বাম সাইডবার থেকে <b>WORKFLOWS (অটো টাস্ক)</b> ট্যাবে যান।'}</li>
              <li>${isEn ? 'Enter Task Name, Time (<code>HH:MM Asia/Dhaka</code>) & Frequency (Daily, Hourly, Every 6h, Weekly, 15m).' : '<b>দৈনিক কাজের নাম</b>, <b>সময় (HH:MM Asia/Dhaka)</b> এবং ফ্রিকোয়েন্সি (Daily / Hourly / Every 6h / Weekly / 15m) সিলেক্ট করুন।'}</li>
              <li>${isEn ? 'Pick AI Model (OxionAI / Local / OpenRouter Free) and write daily agent instructions.' : 'AI মডেল নির্বাচন করুন এবং এজেন্ট প্রতিদিন কী কাজ করবে তা বাংলা বা ইংরেজিতে লিখুন।'}</li>
              <li>${isEn ? 'Check outputs (AI Reports, Project Memory, Chat Session, Telegram/Discord) & click Activate!' : 'আউটপুট অপশন (AI Reports, Project Memory, Chat Session, Telegram/Discord) টিক দিয়ে <b>অ্যাক্টিভেট</b> চাপুন!'}</li>
            </ol>
          </div>

          <div class="wfd-step-card wfd-step-highlight">
            <div class="wfd-step-num">পদ্ধতি ২ • AI ARCHITECT</div>
            <h4>🧠 ${isEn ? 'AI Multi-Node Workflow Architect' : 'AI Multi-Node আর্কিটেক্ট (স্মার্ট পাইপলাইন)'}</h4>
            <ol>
              <li>${isEn ? 'Write a multi-step goal in the prompt box mentioning IPs, ports, URLs, Python, alerts, or memory.' : 'প্রম্পট বক্সে সার্ভার IP, পোর্ট স্ক্যান, API URL, Python হিসাব ও শর্তাবলীসহ আপনার লক্ষ্য লিখুন।'}</li>
              <li>${isEn ? 'Click <b>🧠 AI Multi-Node Architect</b> button.' : '<b>🧠 AI Multi-Node Architect</b> বাটনে ক্লিক করুন।'}</li>
              <li>${isEn ? 'MyAgent detects intents and auto-wires parallel ForEach Ping, Port Scan, HTTP, Python Transform, AI Agent, and IF/Else Alert branches.' : 'সিস্টেম স্বয়ংক্রিয়ভাবে প্যারালাল পিং/পোর্ট/HTTP নোড, Python প্রসেসিং, AI এজেন্ট এবং IF/Else অ্যালার্ট ব্রাঞ্চসহ পূর্ণাঙ্গ গ্রাফ বানিয়ে দেবে।'}</li>
              <li>${isEn ? 'Verify upcoming 3 local runs in the green schedule bar above the canvas.' : 'ক্যানভাসের ওপরে সবুজ বারে পরবর্তী ৩টি রানের সময় নিশ্চিত করুন।'}</li>
            </ol>
          </div>

          <div class="wfd-step-card">
            <div class="wfd-step-num">পদ্ধতি ৩ • VISUAL STUDIO</div>
            <h4>🎨 ${isEn ? 'Visual Drag-and-Drop n8n Canvas' : 'ভিজ্যুয়াল ক্যানভাস ও নোড এডিটর'}</h4>
            <ol>
              <li>${isEn ? 'Click any of the 13 blocks in the left <b>Node Palette</b> to drop it onto the dotted canvas.' : 'বাম পাশের <b>নোড প্যালেট</b> থেকে প্রয়োজনীয় নোড ক্লিক করে ডটেড ক্যানভাসে যোগ করুন।'}</li>
              <li>${isEn ? 'Click a node\'s right output port (<code>●</code>, <code>T</code>, or <code>F</code>) then click the target node\'s left input port to wire.' : 'এক নোডের ডান আউটপুট পোর্ট (<code>●</code>, <code>T</code> বা <code>F</code>) থেকে অন্য নোডের বাম ডটে ক্লিক করে কানেক্ট করুন।'}</li>
              <li>${isEn ? 'Click any node to edit prompts, set <code>Retries (0-3)</code>, <code>Continue on Fail</code>, or test individually with <b>🧪 Test This Node</b>.' : 'যেকোনো নোডে ক্লিক করে ডান ইন্সপেক্টর থেকে সেটিংস, অটো রিট্রাই ও <b>🧪 Test This Node</b> দিয়ে আলাদাভাবে টেস্ট করুন।'}</li>
              <li>${isEn ? 'Use <code>Ctrl+S</code> to save, <code>▶ Run Now</code> for live pulsing step animation, or ⬇️ Export JSON to share.' : '<code>Ctrl+S</code> দিয়ে সেভ করুন ও <code>▶ Run Now</code> চেপে লাইভ নোড-বাই-নোড অ্যানিমেশন দেখুন।'}</li>
            </ol>
          </div>

          <div class="wfd-step-card">
            <div class="wfd-step-num">পদ্ধতি ৪ • EXTERNAL AI & MCP</div>
            <h4>🔌 ${isEn ? 'Create via Claude, Cursor or Antigravity MCP' : 'Claude / IDE (MCP) ও ওয়েবহুক অটোমেশন'}</h4>
            <ol>
              <li>${isEn ? 'Connect your IDE or AI client to MyAgent MCP Server endpoint (<code>/api/mcp/server/rpc</code>).' : 'আপনার Antigravity IDE, Claude বা Cursor-কে MyAgent MCP সার্ভারের সাথে যুক্ত করুন।'}</li>
              <li>${isEn ? 'Ask AI: <i>"Create a daily 9am workflow using MyAgent to check all servers and save a report."</i>' : 'AI-কে বলুন: <i>"MyAgent-এ প্রতিদিন সকাল ৯টায় সার্ভার ও ডাটাবেস চেক করার একটি ডেইলি ওয়ার্কফ্লো বানাও।"</i>'}</li>
              <li>${isEn ? 'Available MCP tools: <code>create_daily_agent_task</code>, <code>architect_workflow_from_goal</code>, <code>list_workflows</code>, <code>run_workflow_now</code>.' : 'সক্রিয় MCP টুলসমূহ: <code>create_daily_agent_task</code>, <code>architect_workflow_from_goal</code>, <code>list_workflows</code> ও <code>run_workflow_now</code>।'}</li>
              <li>${isEn ? 'Or trigger externally anytime via <code>POST /api/workflows/webhook/{id}</code>.' : 'অথবা বাহ্যিক স্ক্রিপ্ট থেকে <code>🔗 Webhook URL</code> দিয়ে যেকোনো সময় ট্রিগার করুন।'}</li>
            </ol>
          </div>
        </div>

        <!-- Cron Schedule Cheatsheet Strip -->
        <div class="wfd-cron-strip">
          <div class="wfd-cron-title">⏱️ ${isEn ? 'Built-in Daily & Recurring Frequency Mapping (Asia/Dhaka +06:00)' : 'স্বয়ংক্রিয় সময়সূচি ও Cron ম্যাপিং (বাংলাদেশ সময় Asia/Dhaka +06:00)'}</div>
          <div class="wfd-cron-pills">
            <span><b>Daily 09:00</b> → <code>0 9 * * *</code></span>
            <span><b>Every 15m</b> → <code>*/15 * * * *</code></span>
            <span><b>Hourly (:MM)</b> → <code>0 * * * *</code></span>
            <span><b>Every 6h</b> → <code>0 */6 * * *</code></span>
            <span><b>Weekly Sun</b> → <code>0 9 * * 0</code></span>
            <span><b>Webhook</b> → <code>HTTP POST /api/workflows/webhook/{id}</code></span>
          </div>
        </div>
      </section>

      <!-- SECTION 2: Interactive Ready-to-Use Recipes -->
      <section class="wfd-section" id="wfd-sec-recipes">
        <div class="wfd-sec-head">
          <h3><span>🧪</span> ${isEn ? '2. Real-World Daily Task Recipes (1-Click Try in Studio)' : '২. বাস্তব কাজের প্রম্পট রেসিপি (১-ক্লিকে স্টুডিওতে লোড করুন)'}</h3>
          <span class="wfd-sec-sub">${isEn ? 'Click "Load in Builder" to prefill a production daily task instantly' : 'যেকোনো উদাহরণ ১-ক্লিকে কুইক বিল্ডারে লোড করে কাস্টমাইজ করুন'}</span>
        </div>

        <div class="wfd-recipes-grid">
          ${filteredRecipes.length ? filteredRecipes.map(r => `
            <div class="wfd-recipe-card">
              <div class="wfd-recipe-top">
                <span class="wfd-recipe-icon">${wfDocsEsc(r.icon)}</span>
                <div style="flex:1;">
                  <h4>${wfDocsEsc(isEn ? r.name_en : r.name_bn)}</h4>
                  <span class="wfd-recipe-time">⏰ ${wfDocsEsc(isEn ? r.badge_en : r.badge_bn)}</span>
                </div>
              </div>
              <p class="wfd-recipe-desc">${wfDocsEsc(isEn ? r.desc_en : r.desc_bn)}</p>
              <div class="wfd-recipe-chain">${r.nodesPreview.map(n => `<span>${wfDocsEsc(n)}</span>`).join(' → ')}</div>
              <pre class="wfd-recipe-prompt">${wfDocsEsc(r.prompt)}</pre>
              <div class="wfd-recipe-actions">
                <button type="button" class="btn-sm-action-cyber" onclick="wfDocsCopyRecipePrompt('${wfDocsEsc(r.key)}')">📋 ${isEn ? 'Copy Prompt' : 'প্রম্পট কপি'}</button>
                <button type="button" class="btn-primary" style="padding:6px 12px; font-size:0.8rem;" onclick="launchRecipeInStudio('${wfDocsEsc(r.key)}')">🚀 ${isEn ? 'Load in Builder' : 'বিল্ডারে লোড করুন'}</button>
              </div>
            </div>
          `).join('') : `<div class="wf-empty-hint">${isEn ? 'No matching recipes found.' : 'খুঁজে পাওয়া যায়নি।'}</div>`}
        </div>
      </section>

      <!-- SECTION 3: All 13 Workflow Nodes Reference -->
      <section class="wfd-section" id="wfd-sec-nodes">
        <div class="wfd-sec-head" style="flex-wrap:wrap; gap:10px;">
          <div>
            <h3><span>🧩</span> ${isEn ? '3. Complete 18-Node Parallel Engine Reference' : '৩. ১৮টি ওয়ার্কফ্লো নোডের সম্পূর্ণ রেফারেন্স (প্যারালাল DAG)'}</h3>
            <span class="wfd-sec-sub">${isEn ? 'Triggers, AI agents, parallel merge, switch router, loops, Python, SQL/RAG, MCP tools, sub-workflows & outputs' : 'ট্রিগার, AI, প্যারালাল মার্জ, সুইচ রাউটার, লুপ, পাইথন, MCP টুল, SQLite/RAG ও আউটপুট নোডসমূহ'}</span>
          </div>
          <div class="wfd-cat-filters">
            ${[
              ['all', isEn ? 'All (18)' : 'সবগুলো (১৮)'],
              ['trigger', isEn ? 'Triggers' : 'ট্রিগার'],
              ['ai', isEn ? 'AI & SubAgents' : 'এআই ও সাব-এজেন্ট'],
              ['logic', isEn ? 'Logic & Loop' : 'লজিক ও লুপ'],
              ['action', isEn ? 'Tools, Python, HTTP' : 'টুল, পাইথন, HTTP'],
              ['output', isEn ? 'Reports, Memory, Notify' : 'রিপোর্ট, মেমোরি, চ্যানেল']
            ].map(([cid, clabel]) => `
              <button type="button" class="wfd-cat-btn ${wfDocsState.nodeCategory === cid ? 'active' : ''}" onclick="setWfDocsNodeCat('${cid}')">${wfDocsEsc(clabel)}</button>
            `).join('')}
          </div>
        </div>

        <div class="wfd-nodes-grid">
          ${filteredNodes.length ? filteredNodes.map(n => `
            <div class="wfd-node-doc-card" style="--wfd-node-color:${n.color};">
              <div class="wfd-nd-head">
                <span class="wfd-nd-icon">${wfDocsEsc(n.icon)}</span>
                <div>
                  <div class="wfd-nd-title">${wfDocsEsc(isEn ? n.title_en : n.title_bn)}</div>
                  <code class="wfd-nd-type">${wfDocsEsc(n.type)}</code>
                </div>
                <span class="wfd-nd-cat">${wfDocsEsc(n.cat.toUpperCase())}</span>
              </div>
              <p class="wfd-nd-desc">${wfDocsEsc(isEn ? n.desc_en : n.desc_bn)}</p>
              <div class="wfd-nd-cfg">⚙️ <b>Config:</b> <code>${wfDocsEsc(n.cfg_hint)}</code></div>
            </div>
          `).join('') : `<div class="wf-empty-hint">${isEn ? 'No matching nodes found.' : 'কোনো নোড পাওয়া যায়নি।'}</div>`}
        </div>
      </section>

      <!-- SECTION 4: Template Variables & Data Passing -->
      <section class="wfd-section" id="wfd-sec-vars">
        <div class="wfd-sec-head">
          <h3><span>🧬</span> ${isEn ? '4. Dynamic Data Passing & Template Variables' : '৪. ডাইনামিক ডেটা ও টেমপ্লেট ভেরিয়েবল রেফারেন্স'}</h3>
          <span class="wfd-sec-sub">${isEn ? 'Click any variable token to copy and paste into AI Prompts, URLs, Reports, Memory Keys, or Notifications' : 'এক নোডের ফলাফল পরবর্তী নোডের প্রম্পট, রিপোর্ট বা URL-এ পাঠাতে নিচের যেকোনো টোকেন কপি করে ব্যবহার করুন'}</span>
        </div>

        <div class="wfd-vars-grid">
          ${filteredVars.map(v => `
            <div class="wfd-var-card" onclick="wfDocsCopy('${wfDocsEsc(v.token)}', '${wfDocsEsc(v.token)}')" title="Click to copy">
              <div style="display:flex; justify-content:space-between; align-items:center; gap:8px;">
                <code class="wfd-var-token">${wfDocsEsc(v.token)}</code>
                <span style="font-size:0.72rem; color:#38bdf8;">📋 Copy</span>
              </div>
              <div class="wfd-var-desc">${wfDocsEsc(isEn ? v.desc_en : v.desc_bn)}</div>
            </div>
          `).join('')}
        </div>
      </section>

      <!-- SECTION 5: Webhook Curl, Resilience & API Reference -->
      <section class="wfd-section" id="wfd-sec-api">
        <div class="wfd-sec-head">
          <h3><span>🔗</span> ${isEn ? '5. Error Handling, Webhook Triggers, REST API & MCP' : '৫. এরর হ্যান্ডলিং, ওয়েবহুক, REST API এবং MCP রেফারেন্স'}</h3>
          <span class="wfd-sec-sub">${isEn ? 'Production-grade resilience policies & programmatic automation endpoints' : 'অটো রিট্রাই, অফলাইন ডাইজেস্ট ও বহিরাগত সিস্টেম থেকে ট্রিগার করার নিয়ম'}</span>
        </div>

        <div class="wfd-two-col">
          <div class="wfd-info-panel">
            <h4>🛡️ ${isEn ? 'Per-Node Reliability & Error Controls' : 'প্রতিটি নোডের নির্ভরযোগ্যতা ও এরর পলিসি'}</h4>
            <ul class="wfd-clean-list">
              <li><b>Auto Retries (0–3):</b> ${isEn ? 'Automatically retries transient HTTP/network failures with backoff delay.' : 'অস্থায়ী নেটওয়ার্ক বা HTTP ত্রুটি হলে স্বয়ংক্রিয়ভাবে সর্বোচ্চ ৩ বার পুনঃচেষ্টা করে।'}</li>
              <li><b>Continue Workflow on Fail:</b> ${isEn ? 'Propagates error details in <code>{{prev.error}}</code> downstream instead of halting alerts.' : 'কোনো নোড ব্যর্থ হলেও পুরো পাইপলাইন না থামিয়ে <code>{{prev.error}}</code> সহ পরবর্তী অ্যালার্ট ধাপে এগিয়ে যায়।'}</li>
              <li><b>⏸️ Mute / Bypass Node:</b> ${isEn ? 'Temporarily skips a node during testing while transparently forwarding upstream output.' : 'টেস্টিংয়ের সময় নোড ডিলিট না করেই মিউট রাখলে পূর্বের ডেটা সোজা পরের ধাপে চলে যায়।'}</li>
              <li><b>🛡️ Offline Telemetry Digest:</b> ${isEn ? 'If primary LAN LLM is unreachable, consolidates collected ping/port/system metrics with clear WARNING header.' : 'LAN LLM সার্ভার বন্ধ থাকলে AI Agent নোড সংগৃহীত পিং/সিস্টেম ডেটাসহ WARNING ডাইজেস্ট তৈরি করে।'}</li>
            </ul>
          </div>

          <div class="wfd-info-panel">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <h4 style="margin:0;">🌐 ${isEn ? 'Trigger Workflow via Webhook cURL' : 'বাহ্যিক সার্ভার/স্ক্রিপ্ট থেকে Webhook ট্রিগার (cURL)'}</h4>
              <button type="button" class="mini-btn-copy" onclick="wfDocsCopyCurl()">📋 Copy</button>
            </div>
            <pre class="wfd-code-block">${wfDocsEsc(curlWebhookSample)}</pre>
            <div style="font-size:0.78rem; color:var(--text-secondary); margin-top:8px;">
              ${isEn
                ? 'Passed JSON body becomes accessible in any node as <code>{{trigger.payload}}</code> or <code>{{trigger.payload.server}}</code>.'
                : 'পাঠানো JSON বডিটি যেকোনো নোডে <code>{{trigger.payload}}</code> বা <code>{{trigger.payload.server}}</code> হিসেবে পাওয়া যাবে।'}
            </div>
          </div>
        </div>

        <div class="wfd-table-wrap" style="margin-top:12px;">
          <table class="wfd-api-table">
            <thead>
              <tr>
                <th>Method</th>
                <th>Endpoint / MCP Tool</th>
                <th>${isEn ? 'Purpose' : 'কাজ ও ব্যবহার'}</th>
              </tr>
            </thead>
            <tbody>
              <tr><td><span class="wfd-m-get">GET</span></td><td><code>/api/workflows</code></td><td>${isEn ? 'List all workflows, next run schedule preview, and KPI summary' : 'সব ওয়ার্কফ্লো, আসন্ন ৩টি রানের সময় ও KPI পরিসংখ্যান দেখা'}</td></tr>
              <tr><td><span class="wfd-m-post">POST</span></td><td><code>/api/workflows/quick-daily</code></td><td>${isEn ? 'Create & schedule a daily autonomous AI workflow from natural text' : 'সাধারণ নির্দেশনা থেকে ৫-নোডের দৈনিক অটো ওয়ার্কফ্লো তৈরি ও অ্যাক্টিভেট'}</td></tr>
              <tr><td><span class="wfd-m-post">POST</span></td><td><code>/api/workflows/ai-architect</code></td><td>${isEn ? 'Auto-design a branched multi-node DAG (Ping/Port/Python/AI/IF-Else)' : 'জটিল লক্ষ্য থেকে স্বয়ংক্রিয়ভাবে ব্রাঞ্চড মাল্টি-নোড DAG আর্কিটেক্ট করা'}</td></tr>
              <tr><td><span class="wfd-m-post">POST</span></td><td><code>/api/workflows/{id}/run</code></td><td>${isEn ? 'Trigger immediate execution (supports payload & dry_run) with full parallel trace' : 'তাৎক্ষণিক ওয়ার্কফ্লো রান (পেলোড ও Dry-Run সমর্থিত) ও প্যারালাল ট্রেস দেখা'}</td></tr>
              <tr><td><span class="wfd-m-post">POST</span></td><td><code>/api/workflows/{id}/stop</code></td><td>${isEn ? 'Gracefully cancel a currently running workflow execution' : 'চলমান ওয়ার্কফ্লো নিরাপদভাবে মাঝপথে থামানো'}</td></tr>
              <tr><td><span class="wfd-m-get">GET</span></td><td><code>/api/workflows/{id}/live-status</code></td><td>${isEn ? 'Poll real-time concurrent active node wave & completed step outputs' : 'চলমান ওয়ার্কফ্লোর লাইভ প্যারালাল নোড ও প্রোগ্রেস পর্যবেক্ষণ'}</td></tr>
              <tr><td><span class="wfd-m-get">GET</span> / <span class="wfd-m-post">POST</span></td><td><code>/api/workflows/{id}/versions</code> & <code>.../restore</code></td><td>${isEn ? 'List saved revision snapshots and restore any previous version cleanly' : 'স্বয়ংক্রিয় ভার্সন হিস্ট্রি দেখা এবং যেকোনো পুরানো ভার্সনে রোলব্যাক করা'}</td></tr>
              <tr><td><span class="wfd-m-get">GET</span> / <span class="wfd-m-post">POST</span></td><td><code>/api/workflows/vars/list</code> & <code>/vars/save</code></td><td>${isEn ? 'Manage AES-256 encrypted secrets & global variables ({{vars.KEY}})' : 'গ্লোবাল AES-256 এনক্রিপ্টেড ভেরিয়েবল ও সিক্রেট ({{vars.KEY}}) ম্যানেজ করা'}</td></tr>
              <tr><td><span class="wfd-m-get">GET</span> / <span class="wfd-m-post">POST</span></td><td><code>/api/workflows/telegram/status</code>, <code>.../connect</code>, <code>.../test</code> & <code>.../logs</code></td><td>${isEn ? 'Connect Telegram Bot with live getMe status, Chat ID auto-detect, test & logs' : 'টেলিগ্রাম বট কানেক্ট, লাইভ Connected স্ট্যাটাস চেক, Chat ID ডিটেক্ট, টেস্ট ও ডেলিভারি লগ দেখা'}</td></tr>
              <tr><td><span class="wfd-m-get">GET</span> / <span class="wfd-m-post">POST</span></td><td><code>/api/workflows/telegram/chats</code>, <code>.../chat/command</code> & <code>.../send-report</code></td><td>${isEn ? 'Two-way Telegram chat commands (ping 192.168.9.2, /status, /run) & automatic WORKFLOWS (Auto) status reports' : 'টেলিগ্রামে টু-ওয়ে চ্যাট কমান্ড (ping 192.168.9.2, /status, /run) ও WORKFLOWS (Auto) অটো রিপোর্ট পাঠানো'}</td></tr>
              <tr><td><span class="wfd-m-get">GET</span> / <span class="wfd-m-post">POST</span></td><td><code>/api/workflows/mcp/servers</code> & <code>.../mcp/ping/{id}</code></td><td>${isEn ? 'Inspect registered MCP Hub servers/tools & ping-refresh external MCP servers for Workflows' : 'WORKFLOWS (Auto)-তে এক্সটার্নাল MCP সার্ভার ও টুল তালিকা দেখা ও পিং-রিফ্রেশ করা'}</td></tr>
              <tr><td><span class="wfd-m-post">POST</span></td><td><code>/api/workflows/node/test</code></td><td>${isEn ? 'Unit-test a single node in Studio Inspector with sample prev output' : 'ক্যানভাস ইন্সপেক্টরে সিঙ্গেল নোড আলাদাভাবে লাইভ টেস্ট করা'}</td></tr>
              <tr><td><span class="wfd-m-post">POST</span></td><td><code>/api/workflows/{id}/duplicate</code></td><td>${isEn ? 'Clone an existing workflow cleanly with new ID & webhook secret' : 'বিদ্যমান ওয়ার্কফ্লোর হুবহু কপি তৈরি করা'}</td></tr>
              <tr><td><span class="wfd-m-get">GET</span> / <span class="wfd-m-post">POST</span></td><td><code>/api/workflows/{id}/export</code> & <code>/import</code></td><td>${isEn ? 'Portable JSON backup, export & team sharing of visual pipelines' : 'ভিজ্যুয়াল ওয়ার্কফ্লো JSON আকারে ব্যাকআপ/এক্সপোর্ট ও ইমপোর্ট করা'}</td></tr>
              <tr><td><span class="wfd-m-mcp">MCP RPC</span></td><td><code>create_daily_agent_task</code>, <code>architect_workflow_from_goal</code>, <code>list_workflows</code>, <code>run_workflow_now</code></td><td>${isEn ? 'Direct workflow creation & execution from external AI IDEs & Claude' : 'Claude / IDE / বাইরের AI এজেন্ট থেকে ডেইলি টাস্ক তৈরি ও পরিচালনা'}</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- SECTION 6: Telegram Bot Connection & Two-Way Chat Guide -->
      <section class="wfd-section" id="wfd-sec-telegram">
        <div class="wfd-sec-head" style="flex-wrap:wrap; gap:10px;">
          <div>
            <h3><span>✈️</span> ${isEn ? '6. How to Connect Your Telegram Bot to WORKFLOWS (Auto)' : '৬. কীভাবে আপনার টেলিগ্রাম বট MyAgent WORKFLOWS (Auto)-তে যুক্ত করবেন'}</h3>
            <span class="wfd-sec-sub">${isEn ? 'Receive automatic daily workflow reports & run live two-way commands (ping servers, check status, run workflows) right from Telegram' : 'প্রতিদিনের অটো ওয়ার্কফ্লো রিপোর্ট টেলিগ্রামে পান এবং সরাসরি Telegram চ্যাট থেকেই সার্ভার পিং ও ওয়ার্কফ্লো কমান্ড চালান'}</span>
          </div>
          <button type="button" class="btn-primary" style="padding:7px 14px; font-size:0.82rem;" onclick="openTelegramConnectionFromDocs()">
            ✈️ ${isEn ? 'Open Telegram Connection Settings' : 'Telegram কানেকশন সেটিংস খুলুন'}
          </button>
        </div>

        <div class="wfd-tg-live-bar">
          <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
            <span id="wfd-tg-live-pill" class="wfd-tg-status-pill disconnected">⏳ ${isEn ? 'Checking Telegram status...' : 'স্ট্যাটাস যাচাই হচ্ছে...'}</span>
            <span id="wfd-tg-live-meta" style="font-size:0.8rem; color:var(--text-secondary);"></span>
          </div>
          <button type="button" class="btn-sm-action-cyber" onclick="refreshDocsTelegramLiveBadge()">🔄 ${isEn ? 'Refresh Status' : 'রিফ্রেশ'}</button>
        </div>

        <div class="wfd-steps-grid" style="margin-top:14px;">
          <div class="wfd-step-card">
            <div class="wfd-step-num">STEP 1 • BOTFATHER TOKEN</div>
            <h4>🤖 ${isEn ? 'Create a Bot & Copy Token' : '@BotFather থেকে নতুন বট ও টোকেন নিন'}</h4>
            <ol>
              <li>${isEn ? 'Open Telegram and search for official verified <code>@BotFather</code>.' : 'আপনার টেলিগ্রাম অ্যাপে গিয়ে ভেরিফায়েড <code>@BotFather</code> সার্চ করে ওপেন করুন।'}</li>
              <li>${isEn ? 'Send <code>/newbot</code>, give a display name (e.g. <i>MyAgent Ops Bot</i>), and choose a username ending in <code>_bot</code>.' : '<code>/newbot</code> মেসেজ পাঠান, বটের একটি নাম দিন এবং শেষে <code>_bot</code> আছে এমন ইউজারনেম দিন।'}</li>
              <li>${isEn ? 'Copy the HTTP API Bot Token (looks like <code>1234567890:ABCdef...</code>) — MyAgent encrypts it with AES-256.' : 'পাওয়া HTTP API Bot Token (যেমন: <code>1234567890:ABCdef...</code>) কপি করুন — এটি AES-256 এনক্রিপ্টেড থাকবে।'}</li>
            </ol>
          </div>

          <div class="wfd-step-card">
            <div class="wfd-step-num">STEP 2 • CHAT ID DETECT</div>
            <h4>🆔 ${isEn ? 'Start Bot & Auto-Detect Chat ID' : 'বটে /start পাঠিয়ে Chat ID ডিটেক্ট করুন'}</h4>
            <ol>
              <li>${isEn ? 'Click your new bot link (<code>t.me/your_bot</code>) in Telegram and tap <b>Start</b> (or send <code>/start</code>).' : 'টেলিগ্রামে আপনার নতুন বটটি ওপেন করে <b>Start</b> চাপুন বা <code>/start</code> লিখুন।'}</li>
              <li>${isEn ? 'For a Group/Channel: add the bot to the group as Admin and send any test message.' : 'গ্রুপ বা চ্যানেলে অ্যালার্ট চাইলে বটকে গ্রুপের Admin হিসেবে যোগ করে একটি মেসেজ দিন।'}</li>
              <li>${isEn ? 'Go to <b>WORKFLOWS (Auto) → ✈️ Telegram Connection & Logs</b>, paste your token, and click <b>🔍 Auto-Detect</b> to fill Chat ID automatically!' : '<b>WORKFLOWS (অটো) → ✈️ টেলিগ্রাম কানেকশন ও লগ</b> ট্যাবে টোকেন বসিয়ে <b>🔍 Auto-Detect</b> চাপলেই Chat ID অটো বসে যাবে!'}</li>
            </ol>
          </div>

          <div class="wfd-step-card wfd-step-highlight">
            <div class="wfd-step-num">STEP 3 • CONNECT & VERIFY</div>
            <h4>🟢 ${isEn ? 'Verify Live & Send Test Alert' : 'কানেক্ট, লাইভ ভেরিফাই ও টেস্ট মেসেজ'}</h4>
            <ol>
              <li>${isEn ? 'Keep <b>Two-Way Telegram Chat Listener</b> and <b>Auto-Send Reports</b> checked.' : '<b>Two-Way Chat Listener</b> ও <b>Auto-Send Workflow Reports</b> অপশন দুটি চালু রাখুন।'}</li>
              <li>${isEn ? 'Click <b>🔗 Connect & Verify Bot</b> — MyAgent verifies live via <code>api.telegram.org/getMe</code> and turns status 🟢 <b>CONNECTED</b>.' : '<b>🔗 Connect & Verify Bot</b> ক্লিক করুন — <code>getMe</code> API যাচাই শেষে স্ট্যাটাস 🟢 <b>CONNECTED</b> হবে।'}</li>
              <li>${isEn ? 'Click <b>📨 Send Test</b> to confirm the test notification arrives in your Telegram app instantly.' : '<b>📨 Send Test</b> বাটনে ক্লিক করে আপনার টেলিগ্রামে টেস্ট মেসেজ আসছে কিনা নিশ্চিত করুন।'}</li>
            </ol>
          </div>

          <div class="wfd-step-card">
            <div class="wfd-step-num">STEP 4 • WORKFLOWS & TWO-WAY CHAT</div>
            <h4>📣 ${isEn ? 'Use in Daily Tasks & Chat Commands' : 'ডেইলি ওয়ার্কফ্লো ও টু-ওয়ে চ্যাট ব্যবহার'}</h4>
            <ol>
              <li>${isEn ? 'In Quick Daily Builder, check <b>📡 Telegram/Discord</b> — or use <code>📣 Notify Chat & Channels</code> with target <code>telegram</code>.' : 'কুইক বিল্ডারে <b>📡 Telegram/Discord</b> টিক দিন অথবা ক্যানভাসে <code>📣 Notify Chat & Channels</code> নোডে টার্গেট <code>telegram</code> দিন।'}</li>
              <li>${isEn ? 'Works on private LAN <code>192.168.9.9</code> with zero public HTTPS domain via Long-Polling.' : 'কোনো পাবলিক ডোমেইন বা পোর্ট ফরওয়ার্ডিং ছাড়াই লোকাল LAN (<code>192.168.9.9</code>)-এ Long-Polling দিয়ে টু-ওয়ে চ্যাট কাজ করে।'}</li>
              <li>${isEn ? 'Optionally list extra teammate Chat IDs (comma-separated) in <b>Allowed Chat IDs</b>.' : 'একাধিক ইউজার ব্যবহার করতে চাইলে <b>Allowed Chat IDs</b> ঘরে কমা দিয়ে বাড়তি ID বসাতে পারেন।'}</li>
            </ol>
          </div>
        </div>

        <div class="wfd-info-panel" style="margin-top:14px;">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:10px;">
            <h4 style="margin:0;">💬 ${isEn ? 'Supported Two-Way Telegram Chat Commands (Click to Copy)' : 'টেলিগ্রাম বটে সরাসরি ব্যবহারযোগ্য টু-ওয়ে চ্যাট কমান্ডসমূহ (ক্লিক করে কপি করুন)'}</h4>
            <span style="font-size:0.74rem; color:var(--text-muted);">${isEn ? 'Every reply automatically includes live WORKFLOWS (Auto) status' : 'প্রতিটি উত্তরের সাথে WORKFLOWS (Auto)-এর লাইভ স্ট্যাটাস রিপোর্ট যুক্ত থাকে'}</span>
          </div>
          <div class="wfd-tg-cmd-grid">
            ${[
              ['ping 192.168.9.2 server and show status', isEn ? 'ICMP Ping server(s) + full WORKFLOWS (Auto) report' : 'সার্ভার পিং (ICMP ল্যাটেন্সি/লস) ও WORKFLOWS (Auto) স্ট্যাটাস'],
              ['/port 192.168.9.2', isEn ? 'TCP Port scan on target host + workflow digest' : 'সার্ভারের খোলা পোর্ট স্ক্যান ও ওয়ার্কফ্লো ডাইজেস্ট'],
              ['/status', isEn ? 'Show active daily schedules, recent runs & success rate' : 'সকল সক্রিয় ওয়ার্কফ্লো ও সাম্প্রতিক রানের পূর্ণ রিপোর্ট'],
              ['/run morning', isEn ? 'Immediately execute matching workflow & send trace report' : 'নাম বা ID অনুযায়ী সাথে সাথে ওয়ার্কফ্লো রান করে রিপোর্ট দেখা'],
              ['/create Daily 08:30 ping 192.168.9.2 and save report', isEn ? 'AI-architect & activate a new daily workflow directly from Telegram' : 'টেলিগ্রাম থেকেই নতুন ডেইলি অটো ওয়ার্কফ্লো তৈরি ও চালু করা'],
              ['/id', isEn ? 'Returns your Telegram Chat ID + workflow summary' : 'আপনার Telegram Chat ID ও ওয়ার্কফ্লো সামারি জানা'],
            ].map(([cmd, desc]) => `
              <div class="wfd-tg-cmd-chip" onclick="wfDocsCopy('${wfDocsEsc(cmd)}', '${wfDocsEsc(cmd)}')" title="Click to copy command">
                <code>${wfDocsEsc(cmd)}</code>
                <span>${wfDocsEsc(desc)}</span>
              </div>
            `).join('')}
          </div>
        </div>
      </section>

      <!-- SECTION 7: FAQ & Troubleshooting -->
      <section class="wfd-section" id="wfd-sec-faq">
        <div class="wfd-sec-head">
          <h3><span>❓</span> ${isEn ? '7. Frequently Asked Questions & Best Practices' : '৭. সচরাচর জিজ্ঞাসিত প্রশ্ন (FAQ) ও টিপস'}</h3>
        </div>
        <div class="wfd-faq-list">
          ${filteredFaqs.map(f => `
            <details class="wfd-faq-item" open>
              <summary>${wfDocsEsc(isEn ? f.q_en : f.q_bn)}</summary>
              <div class="wfd-faq-ans">${wfDocsEsc(isEn ? f.a_en : f.a_bn)}</div>
            </details>
          `).join('')}
        </div>
      </section>
    </div>
  `;
  refreshDocsTelegramLiveBadge();
}

// Keep language synced cleanly inside SPA
window.addEventListener('appLanguageChanged', (e) => {
  const newLang = e?.detail?.language;
  if (newLang === 'bn' || newLang === 'en') {
    wfDocsState.lang = newLang;
    const viewEl = document.getElementById('view-workflow-docs');
    if (viewEl && viewEl.classList.contains('active')) {
      renderWorkflowDocsPage();
    }
  }
});

window.renderWorkflowDocsPage = renderWorkflowDocsPage;
window.setWfDocsLanguage = setWfDocsLanguage;
window.setWfDocsNodeCat = setWfDocsNodeCat;
window.handleWfDocsSearch = handleWfDocsSearch;
window.launchRecipeInStudio = launchRecipeInStudio;
window.goBackToWorkflowStudio = goBackToWorkflowStudio;
window.wfDocsCopy = wfDocsCopy;
window.wfDocsCopyRecipePrompt = wfDocsCopyRecipePrompt;
window.wfDocsCopyCurl = wfDocsCopyCurl;
window.openTelegramConnectionFromDocs = openTelegramConnectionFromDocs;
window.refreshDocsTelegramLiveBadge = refreshDocsTelegramLiveBadge;
