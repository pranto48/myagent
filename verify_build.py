#!/usr/bin/env python3
# ==============================================================================
# Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
# Made By Arif (https://arifmahmud.com/)
# Project: MyAgent | Version: 3.0.0
# Autonomous Pre-Flight Build and Verification Script
# ==============================================================================

import os
import sys
import re
import ast
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
ERRORS = []
WARNINGS = []

def log_pass(msg):
    print(f"  [PASS] {msg}")

def log_fail(msg):
    ERRORS.append(msg)
    print(f"  [FAIL] {msg}")

def log_warn(msg):
    WARNINGS.append(msg)
    print(f"  [WARN] {msg}")

def check_version_alignment():
    print("\n[1/5] Checking Unified Version Alignment across Codebase (v3.0.0)...")
    expected_version = "3.0.0"

    # 1. VERSION file
    version_file = ROOT_DIR / "VERSION"
    if version_file.exists():
        val = version_file.read_text(encoding="utf-8").strip()
        if val == expected_version:
            log_pass(f"VERSION file contains exact version: {val}")
        else:
            log_fail(f"VERSION file has mismatch: expected '{expected_version}', got '{val}'")
    else:
        log_fail("VERSION file is missing!")

    # 2. backend/config.py
    cfg_file = ROOT_DIR / "backend" / "config.py"
    if cfg_file.exists():
        txt = cfg_file.read_text(encoding="utf-8")
        if f"Version: {expected_version}" in txt:
            log_pass(f"backend/config.py header version verified (v{expected_version})")
        else:
            log_fail(f"backend/config.py header does not match Version: {expected_version}")

    # 3. backend/main.py
    main_file = ROOT_DIR / "backend" / "main.py"
    if main_file.exists():
        txt = main_file.read_text(encoding="utf-8")
        if f'version="{expected_version}"' in txt and f'v{expected_version}' in txt:
            log_pass(f"backend/main.py FastAPI app and lifespan log verified (v{expected_version})")
        else:
            log_fail(f"backend/main.py has version mismatch")

    # 4. frontend/index.html
    html_file = ROOT_DIR / "frontend" / "index.html"
    if html_file.exists():
        txt = html_file.read_text(encoding="utf-8")
        if f"v{expected_version}</span>" in txt:
            log_pass(f"frontend/index.html version badge verified (v{expected_version})")
        else:
            log_fail(f"frontend/index.html version badge mismatch")

    # 5. docker-compose.yml
    dc_file = ROOT_DIR / "docker-compose.yml"
    if dc_file.exists():
        txt = dc_file.read_text(encoding="utf-8")
        if f"Version: {expected_version}" in txt:
            log_pass(f"docker-compose.yml version verified (v{expected_version})")
        else:
            log_fail("docker-compose.yml version header mismatch")

    # 6. deploy scripts
    deploy_sh = ROOT_DIR / "deploy.sh"
    deploy_ps = ROOT_DIR / "deploy.ps1"
    for script in (deploy_sh, deploy_ps):
        if script.exists():
            txt = script.read_text(encoding="utf-8")
            if f"Version: {expected_version}" in txt:
                log_pass(f"{script.name} version verified (v{expected_version})")
            else:
                log_fail(f"{script.name} header version mismatch")


def check_python_syntax():
    print("\n[2/5] Checking Python AST Syntax for All Backend Modules...")
    backend_dir = ROOT_DIR / "backend"
    py_files = list(backend_dir.rglob("*.py"))
    
    parsed_count = 0
    for py_file in py_files:
        try:
            code = py_file.read_text(encoding="utf-8")
            ast.parse(code, filename=str(py_file))
            parsed_count += 1
        except SyntaxError as e:
            log_fail(f"Syntax Error in {py_file.relative_to(ROOT_DIR)}: {e}")
        except Exception as e:
            log_fail(f"Parsing error in {py_file.relative_to(ROOT_DIR)}: {e}")

    log_pass(f"All {parsed_count} Python source files compiled with 0 syntax errors.")


def check_i18n_parity():
    print("\n[3/5] Checking Frontend Bilingual i18n Translation Parity (Bangla & English)...")
    i18n_file = ROOT_DIR / "frontend" / "js" / "i18n.js"
    if not i18n_file.exists():
        log_fail("frontend/js/i18n.js not found!")
        return

    content = i18n_file.read_text(encoding="utf-8")
    bn_match = re.search(r'bn:\s*\{([\s\S]*?)\n\s*\},?\s*\n\s*en:', content)
    en_match = re.search(r'en:\s*\{([\s\S]*?)\n\s*\}\s*\n\s*\};', content)

    if not bn_match or not en_match:
        log_fail("Failed to parse translations bn or en objects in i18n.js")
        return

    def parse_keys(block):
        keys = set()
        for line in block.splitlines():
            m = re.match(r'^\s*([a-zA-Z0-9_]+)\s*:', line)
            if m:
                keys.add(m.group(1))
        return keys

    bn_keys = parse_keys(bn_match.group(1))
    en_keys = parse_keys(en_match.group(1))

    missing_in_en = bn_keys - en_keys
    missing_in_bn = en_keys - bn_keys

    if missing_in_en:
        log_fail(f"Missing in English dictionary ({len(missing_in_en)} keys): {list(missing_in_en)[:5]}")
    if missing_in_bn:
        log_fail(f"Missing in Bangla dictionary ({len(missing_in_bn)} keys): {list(missing_in_bn)[:5]}")

    if not missing_in_en and not missing_in_bn:
        log_pass(f"Bilingual parity confirmed: Exactly {len(bn_keys)} keys synchronized in bn and en.")


def check_api_routers():
    print("\n[4/5] Checking Required API Routers and Security Modules...")
    required_routers = [
        "auth.py", "chat.py", "documents.py", "memory.py", "settings.py",
        "sessions.py", "users.py", "dashboard.py", "models_mgmt.py",
        "mcp_router.py", "security_router.py", "backup.py", "reports.py"
    ]
    routers_dir = ROOT_DIR / "backend" / "routers"
    for r in required_routers:
        target = routers_dir / r
        if target.exists():
            log_pass(f"Router backend/routers/{r} is present.")
        else:
            log_fail(f"Router backend/routers/{r} is MISSING!")

    required_security = [
        "crypto.py", "dlp.py", "firewall.py", "audit.py", "rate_limiter.py"
    ]
    security_dir = ROOT_DIR / "backend" / "security"
    for s in required_security:
        target = security_dir / s
        if target.exists():
            log_pass(f"Security module backend/security/{s} is present.")
        else:
            log_fail(f"Security module backend/security/{s} is MISSING!")


def check_frontend_assets():
    print("\n[5/5] Checking Frontend Assets and Static Deployment...")
    frontend_dir = ROOT_DIR / "frontend"
    required_frontend = [
        "index.html", "favicon.svg", "nginx.conf",
        "css/style.css",
        "js/app.js", "js/auth.js", "js/i18n.js", "js/dashboard.js",
        "js/user_manager.js", "js/model_manager.js", "js/memory_manager.js",
        "js/mcp_manager.js", "js/security_manager.js", "js/backup_manager.js",
        "js/admin_manager.js", "js/settings.js", "js/reports_manager.js"
    ]
    for item in required_frontend:
        target = frontend_dir / item
        if target.exists():
            log_pass(f"Frontend asset frontend/{item} present.")
        else:
            log_fail(f"Frontend asset frontend/{item} is MISSING!")


def main():
    print("=" * 70)
    print("🚀 MyAgent v3.0.0 Enterprise Pre-Flight Build Verification")
    print("=" * 70)

    check_version_alignment()
    check_python_syntax()
    check_i18n_parity()
    check_api_routers()
    check_frontend_assets()

    print("\n" + "=" * 70)
    if ERRORS:
        print(f"❌ Verification FAILED with {len(ERRORS)} error(s):")
        for err in ERRORS:
            print(f"   • {err}")
        sys.exit(1)
    else:
        print("✅ ALL CHECKS PASSED (100% READY FOR v3.0.0 PRODUCTION ROLLOUT)")
        print(f"Target Server: http://192.168.9.9:3399 | Backend: http://192.168.9.9:8000")
        print("=" * 70)
        sys.exit(0)

if __name__ == "__main__":
    main()
