# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 2.2.0
import re
import logging
from typing import Dict, Any, List, Tuple
from config import settings

logger = logging.getLogger(__name__)

def _luhn_checksum_valid(card_number_str: str) -> bool:
    """Validates credit card number string using Luhn algorithm."""
    digits = [int(c) for c in card_number_str if c.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    reverse_digits = digits[::-1]
    for i, d in enumerate(reverse_digits):
        if i % 2 == 1:
            d = d * 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0

class DLPEngine:
    """
    Enterprise Data Loss Prevention (DLP) & PII Redaction Engine.
    Detects and sanitizes sensitive data (Credit Cards, API Keys, Private Keys,
    Emails, Phone Numbers, Passwords) to prevent unauthorized leaks.
    """
    
    # Regex Patterns for Sensitive Data Detection
    PATTERNS = {
        "CREDIT_CARD": re.compile(
            r'\b(?:\d[ -]*?){13,19}\b'
        ),
        "API_KEY_OPENAI": re.compile(
            r'\bsk-(?:proj-|live-)?[a-zA-Z0-9_\-]{20,}\b'
        ),
        "API_KEY_GITHUB": re.compile(
            r'\b(?:ghp|gho|ghu|ghs|ghr)_[a-zA-Z0-9]{36,}\b'
        ),
        "API_KEY_AWS": re.compile(
            r'\b(?:AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}\b'
        ),
        "PRIVATE_KEY": re.compile(
            r'-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----[\s\S]*?-----END (?:[A-Z ]+ )?PRIVATE KEY-----'
        ),
        "JWT_TOKEN": re.compile(
            r'\beyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_\-.+/=]{10,}\b'
        ),
        "PASSWORD_FIELD": re.compile(
            r'(?i)\b(?:password|passwd|secret_key|api_secret|auth_token)\s*[:=]\s*["\']?([^"\'\s,;]+)["\']?'
        ),
        "EMAIL": re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
        ),
        "PHONE_BD": re.compile(
            r'(?:\+8801|8801|01)[3-9]\d{8}\b'
        ),
        "PHONE_INTL": re.compile(
            r'\b(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'
        )
    }

    @classmethod
    def inspect_text(cls, text: str) -> Dict[str, Any]:
        """
        Inspects input text, returns detected findings and a sanitized copy.
        """
        if not text or not isinstance(text, str):
            return {"findings": [], "redacted_count": 0, "sanitized_text": text}

        findings = []
        sanitized = text

        # 1. Private Keys
        for match in cls.PATTERNS["PRIVATE_KEY"].finditer(text):
            findings.append({"type": "PRIVATE_KEY", "match": match.group(0)[:30] + "..."})
            sanitized = sanitized.replace(match.group(0), "[REDACTED_RSA_PRIVATE_KEY]")

        # 2. API Keys & Secrets
        for key_type in ["API_KEY_OPENAI", "API_KEY_GITHUB", "API_KEY_AWS", "JWT_TOKEN"]:
            if settings.DLP_MASK_API_KEYS:
                for match in cls.PATTERNS[key_type].finditer(sanitized):
                    val = match.group(0)
                    findings.append({"type": key_type, "match": val[:6] + "..."})
                    sanitized = sanitized.replace(val, f"[REDACTED_{key_type}]")

        # 3. Passwords in key-value configurations
        if settings.DLP_MASK_API_KEYS:
            for match in cls.PATTERNS["PASSWORD_FIELD"].finditer(sanitized):
                secret_val = match.group(1)
                if len(secret_val) > 2 and secret_val not in ["[REDACTED_API_KEY]"]:
                    findings.append({"type": "PASSWORD", "match": "***"})
                    full_match = match.group(0)
                    replaced = full_match.replace(secret_val, "[REDACTED_PASSWORD]")
                    sanitized = sanitized.replace(full_match, replaced)

        # 4. Credit Cards (with Luhn algorithm filter to prevent false matches)
        if settings.DLP_MASK_CREDIT_CARDS:
            for match in cls.PATTERNS["CREDIT_CARD"].finditer(sanitized):
                raw = match.group(0)
                clean_digits = re.sub(r'\D', '', raw)
                if 13 <= len(clean_digits) <= 19 and _luhn_checksum_valid(clean_digits):
                    findings.append({"type": "CREDIT_CARD", "match": f"****-****-****-{clean_digits[-4:]}"})
                    sanitized = sanitized.replace(raw, f"[REDACTED_CARD_****{clean_digits[-4:]}]")

        # 5. Phone numbers
        if settings.DLP_MASK_PHONES:
            for p_type in ["PHONE_BD", "PHONE_INTL"]:
                for match in cls.PATTERNS[p_type].finditer(sanitized):
                    num = match.group(0)
                    findings.append({"type": "PHONE", "match": num[:4] + "****"})
                    sanitized = sanitized.replace(num, "[REDACTED_PHONE]")

        # 6. Emails
        if settings.DLP_MASK_EMAILS:
            for match in cls.PATTERNS["EMAIL"].finditer(sanitized):
                email = match.group(0)
                parts = email.split('@')
                masked = f"{parts[0][:2]}***@{parts[1]}" if len(parts[0]) > 2 else f"*@{parts[1]}"
                findings.append({"type": "EMAIL", "match": masked})
                sanitized = sanitized.replace(email, f"[REDACTED_EMAIL:{masked}]")

        return {
            "findings": findings,
            "redacted_count": len(findings),
            "sanitized_text": sanitized
        }

    @classmethod
    def sanitize(cls, text: str) -> str:
        """Fast helper to sanitize text directly."""
        if not settings.DLP_ENABLED:
            return text
        result = cls.inspect_text(text)
        return result["sanitized_text"]
