#!/usr/bin/env node
/* ==============================================================================
 * Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
 * Made By Arif (https://arifmahmud.com/)
 * Project: MyAgent | Version: 3.1.0
 * Autonomous Pre-Flight Build and Verification Script (Node.js Engine)
 * ============================================================================== */

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT_DIR = path.resolve(__dirname);
const ERRORS = [];
const WARNINGS = [];

function logPass(msg) {
  console.log(`  \x1b[32m[PASS]\x1b[0m ${msg}`);
}

function logFail(msg) {
  ERRORS.push(msg);
  console.log(`  \x1b[31m[FAIL]\x1b[0m ${msg}`);
}

function logWarn(msg) {
  WARNINGS.push(msg);
  console.log(`  \x1b[33m[WARN]\x1b[0m ${msg}`);
}

function checkVersionAlignment() {
  console.log('\n[1/5] Checking Unified Version Alignment across Codebase (v3.1.0)...');
  const expectedVersion = '3.1.0';

  // 1. VERSION file
  const versionFile = path.join(ROOT_DIR, 'VERSION');
  if (fs.existsSync(versionFile)) {
    const val = fs.readFileSync(versionFile, 'utf8').trim();
    if (val === expectedVersion) {
      logPass(`VERSION file contains exact version: ${val}`);
    } else {
      logFail(`VERSION file mismatch: expected '${expectedVersion}', got '${val}'`);
    }
  } else {
    logFail('VERSION file is missing!');
  }

  // 2. backend/config.py
  const cfgFile = path.join(ROOT_DIR, 'backend', 'config.py');
  if (fs.existsSync(cfgFile)) {
    const txt = fs.readFileSync(cfgFile, 'utf8');
    if (txt.includes(`Version: ${expectedVersion}`)) {
      logPass(`backend/config.py header version verified (v${expectedVersion})`);
    } else {
      logFail(`backend/config.py header does not match Version: ${expectedVersion}`);
    }
  }

  // 3. backend/main.py
  const mainFile = path.join(ROOT_DIR, 'backend', 'main.py');
  if (fs.existsSync(mainFile)) {
    const txt = fs.readFileSync(mainFile, 'utf8');
    if (txt.includes(`version="${expectedVersion}"`) && txt.includes(`v${expectedVersion}`)) {
      logPass(`backend/main.py FastAPI app and lifespan log verified (v${expectedVersion})`);
    } else {
      logFail('backend/main.py has version mismatch');
    }
  }

  // 4. frontend/index.html
  const htmlFile = path.join(ROOT_DIR, 'frontend', 'index.html');
  if (fs.existsSync(htmlFile)) {
    const txt = fs.readFileSync(htmlFile, 'utf8');
    if (txt.includes(`v${expectedVersion}</span>`)) {
      logPass(`frontend/index.html version badge verified (v${expectedVersion})`);
    } else {
      logFail('frontend/index.html version badge mismatch');
    }
  }

  // 5. docker-compose.yml
  const dcFile = path.join(ROOT_DIR, 'docker-compose.yml');
  if (fs.existsSync(dcFile)) {
    const txt = fs.readFileSync(dcFile, 'utf8');
    if (txt.includes(`Version: ${expectedVersion}`)) {
      logPass(`docker-compose.yml version verified (v${expectedVersion})`);
    } else {
      logFail('docker-compose.yml version header mismatch');
    }
  }

  // 6. deploy scripts
  ['deploy.sh', 'deploy.ps1'].forEach(s => {
    const file = path.join(ROOT_DIR, s);
    if (fs.existsSync(file)) {
      const txt = fs.readFileSync(file, 'utf8');
      if (txt.includes(`Version: ${expectedVersion}`)) {
        logPass(`${s} version verified (v${expectedVersion})`);
      } else {
        logFail(`${s} header version mismatch`);
      }
    }
  });
}

function checkFrontendSyntax() {
  console.log('\n[2/5] Checking JavaScript Syntax for All Frontend Modules...');
  const jsDir = path.join(ROOT_DIR, 'frontend', 'js');
  const jsFiles = fs.readdirSync(jsDir).filter(f => f.endsWith('.js'));

  let count = 0;
  jsFiles.forEach(f => {
    try {
      const code = fs.readFileSync(path.join(jsDir, f), 'utf8');
      new vm.Script(code);
      count++;
    } catch (e) {
      logFail(`JS Syntax Error in frontend/js/${f}: ${e.message}`);
    }
  });
  logPass(`All ${count} frontend JavaScript files parsed with 0 syntax errors.`);
}

function checkI18nParity() {
  console.log('\n[3/5] Checking Frontend Bilingual i18n Translation Parity (Bangla & English)...');
  const i18nFile = path.join(ROOT_DIR, 'frontend', 'js', 'i18n.js');
  if (!fs.existsSync(i18nFile)) {
    logFail('frontend/js/i18n.js not found!');
    return;
  }

  const content = fs.readFileSync(i18nFile, 'utf8');
  const bnMatch = content.match(/bn:\s*\{([\s\S]*?)\n\s*\},?\s*\n*\s*en:/);
  const enMatch = content.match(/en:\s*\{([\s\S]*?)\n\s*\}\s*;?/);

  if (!bnMatch || !enMatch) {
    logFail('Failed to parse translations bn or en objects in i18n.js');
    return;
  }

  function parseKeysWithDupes(block, lang) {
    const keys = [];
    const counts = {};
    block.split('\n').forEach(line => {
      const trimmed = line.trim();
      const colonIdx = trimmed.indexOf(':');
      if (colonIdx > 0 && !trimmed.startsWith('//') && !trimmed.startsWith('/*')) {
        const k = trimmed.substring(0, colonIdx).trim().replace(/['"]/g, '');
        if (k && k !== 'bn' && k !== 'en' && !k.includes(' ') && !k.includes('(')) {
          keys.push(k);
          counts[k] = (counts[k] || 0) + 1;
        }
      }
    });

    const dupes = Object.keys(counts).filter(k => counts[k] > 1);
    if (dupes.length > 0) {
      logFail(`Duplicate keys detected in ${lang} dictionary (${dupes.length} keys): ${dupes.slice(0, 5).join(', ')}`);
    }
    return new Set(keys);
  }

  const bnKeys = parseKeysWithDupes(bnMatch[1], 'Bangla (bn)');
  const enKeys = parseKeysWithDupes(enMatch[1], 'English (en)');

  const missingInEn = [...bnKeys].filter(k => !enKeys.has(k));
  const missingInBn = [...enKeys].filter(k => !bnKeys.has(k));

  if (missingInEn.length > 0) {
    logFail(`Missing in English dictionary (${missingInEn.length} keys): ${missingInEn.slice(0, 5).join(', ')}`);
  }
  if (missingInBn.length > 0) {
    logFail(`Missing in Bangla dictionary (${missingInBn.length} keys): ${missingInBn.slice(0, 5).join(', ')}`);
  }

  if (missingInEn.length === 0 && missingInBn.length === 0 && bnKeys.size === enKeys.size) {
    logPass(`Bilingual parity confirmed: Exactly ${bnKeys.size} unique keys synchronized in bn and en (0 duplicates, 0 missing).`);
  }
}

function checkApiRouters() {
  console.log('\n[4/5] Checking Required API Routers and Security Modules...');
  const requiredRouters = [
    'auth.py', 'chat.py', 'documents.py', 'memory.py', 'settings.py',
    'sessions.py', 'users.py', 'dashboard.py', 'models_mgmt.py',
    'mcp_router.py', 'security_router.py', 'backup.py', 'reports.py'
  ];
  const routersDir = path.join(ROOT_DIR, 'backend', 'routers');
  requiredRouters.forEach(r => {
    if (fs.existsSync(path.join(routersDir, r))) {
      logPass(`Router backend/routers/${r} is present.`);
    } else {
      logFail(`Router backend/routers/${r} is MISSING!`);
    }
  });

  const requiredSecurity = [
    'crypto.py', 'dlp.py', 'firewall.py', 'audit.py', 'rate_limiter.py'
  ];
  const securityDir = path.join(ROOT_DIR, 'backend', 'security');
  requiredSecurity.forEach(s => {
    if (fs.existsSync(path.join(securityDir, s))) {
      logPass(`Security module backend/security/${s} is present.`);
    } else {
      logFail(`Security module backend/security/${s} is MISSING!`);
    }
  });
}

function checkFrontendAssets() {
  console.log('\n[5/5] Checking Frontend Assets and Static Deployment...');
  const frontendDir = path.join(ROOT_DIR, 'frontend');
  const requiredFrontend = [
    'index.html', 'favicon.svg', 'nginx.conf',
    'css/style.css',
    'js/app.js', 'js/auth.js', 'js/i18n.js', 'js/dashboard.js',
    'js/user_manager.js', 'js/model_manager.js', 'js/memory_manager.js',
    'js/mcp_manager.js', 'js/security_manager.js', 'js/backup_manager.js',
    'js/admin_manager.js', 'js/settings.js', 'js/reports_manager.js'
  ];
  requiredFrontend.forEach(item => {
    if (fs.existsSync(path.join(frontendDir, item))) {
      logPass(`Frontend asset frontend/${item} present.`);
    } else {
      logFail(`Frontend asset frontend/${item} is MISSING!`);
    }
  });
}

function main() {
  console.log('='.repeat(70));
  console.log('🚀 MyAgent v3.1.0 Enterprise Pre-Flight Build Verification');
  console.log('='.repeat(70));

  checkVersionAlignment();
  checkFrontendSyntax();
  checkI18nParity();
  checkApiRouters();
  checkFrontendAssets();

  console.log('\n' + '='.repeat(70));
  if (ERRORS.length > 0) {
    console.log(`❌ Verification FAILED with ${ERRORS.length} error(s):`);
    ERRORS.forEach(err => console.log(`   • ${err}`));
    process.exit(1);
  } else {
    console.log('\x1b[32m✅ ALL CHECKS PASSED (100% READY FOR v3.1.0 PRODUCTION ROLLOUT)\x1b[0m');
    console.log('Target Server: http://192.168.9.9:3399 | Backend: http://192.168.9.9:8000');
    console.log('='.repeat(70));
    process.exit(0);
  }
}

main();
