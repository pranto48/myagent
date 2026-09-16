# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 3.0.0
import re
import base64
import logging
from typing import Dict, Any, List, Optional
from config import settings

logger = logging.getLogger(__name__)

class PromptFirewall:
    """
    AI Prompt Injection & Jailbreak Defense Firewall.
    Detects and mitigates system prompt overrides, DAN/Jailbreaks,
    system prompt exfiltration attempts, and delimiter escape attacks.
    """

    INJECTION_PATTERNS = [
        (re.compile(r'(?i)\bignore\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions|prompts|rules|commands)\b'),
         "SYSTEM_OVERRIDE", "Attempt to override system prompt instructions"),
        (re.compile(r'(?i)\bdisregard\s+(?:all\s+)?(?:previous|prior|system)\s+(?:guidelines|rules|instructions)\b'),
         "SYSTEM_OVERRIDE", "Attempt to disregard system prompt guidelines"),
        (re.compile(r'(?i)\byou\s+are\s+now\s+(?:in\s+)?(?:dan|developer\s+mode|unrestricted|god\s+mode|jailbreak)\b'),
         "JAILBREAK_DAN", "Attempt to force unconstrained persona (DAN mode)"),
        (re.compile(r'(?i)\b(?:print|repeat|output|show|reveal|display|leak)\s+(?:your\s+)?(?:initial|system|original)\s+(?:prompt|instructions|rules)\b'),
         "PROMPT_LEAK", "Attempt to exfiltrate system prompt"),
        (re.compile(r'(?i)\b(?:what\s+is\s+your\s+system\s+prompt|verbatim\s+system\s+prompt)\b'),
         "PROMPT_LEAK", "Attempt to reveal verbatim system prompt"),
        (re.compile(r'(?i)<\s*\|\s*im_start\s*\|\s*system>'),
         "DELIMITER_INJECTION", "Attempt to inject chat template delimiter <|im_start|>"),
        (re.compile(r'(?i)\[\s*system\s*\]|\{\s*\"role\"\s*:\s*\"system\"\s*\}'),
         "ROLE_CONFUSION", "Attempt to inject synthetic system role block"),
        (re.compile(r'(?i)\b(?:eval\s*\(|exec\s*\(|__import__\s*\(|os\.system\s*\(|subprocess\.Popen)\b'),
         "CODE_INJECTION", "Attempt to execute dangerous Python code in prompt")
    ]

    @classmethod
    def inspect_prompt(cls, prompt: str) -> Dict[str, Any]:
        """
        Inspects a user prompt for potential jailbreaks and injection attacks.
        Returns safety assessment, threat level, and sanitized prompt.
        """
        if not settings.FIREWALL_ENABLED or not prompt:
            return {
                "is_safe": True,
                "threat_level": "CLEAN",
                "threat_types": [],
                "sanitized_prompt": prompt,
                "blocked": False,
                "reason": None
            }

        detected_threats = []
        reasons = []

        # 1. Pattern matching against direct injection signatures
        for pattern, threat_name, reason in cls.INJECTION_PATTERNS:
            if pattern.search(prompt):
                detected_threats.append(threat_name)
                reasons.append(reason)

        # 2. Check for suspicious base64 payloads
        b64_matches = re.findall(r'\b[A-Za-z0-9+/]{32,}={0,2}\b', prompt)
        for b64 in b64_matches:
            try:
                decoded = base64.b64decode(b64).decode('utf-8', errors='ignore')
                for pattern, threat_name, reason in cls.INJECTION_PATTERNS:
                    if pattern.search(decoded):
                        detected_threats.append(f"ENCODED_{threat_name}")
                        reasons.append(f"Encoded payload: {reason}")
                        break
            except Exception:
                pass

        # 3. Threat Assessment
        is_blocked = False
        threat_level = "CLEAN"
        sanitized_prompt = prompt

        if detected_threats:
            if any(t in ["SYSTEM_OVERRIDE", "JAILBREAK_DAN", "CODE_INJECTION"] for t in detected_threats):
                threat_level = "HIGH"
                is_blocked = True
                # Sanitize the prompt to defuse the exploit
                sanitized_prompt = re.sub(
                    r'(?i)\b(ignore|disregard)\s+(previous|prior|above)\s+(instructions|prompts|rules)',
                    '[FILTERED_INJECTION]', prompt
                )
            else:
                threat_level = "MEDIUM"

        return {
            "is_safe": not is_blocked,
            "threat_level": threat_level,
            "threat_types": detected_threats,
            "sanitized_prompt": sanitized_prompt,
            "blocked": is_blocked,
            "reason": "; ".join(reasons) if reasons else None
        }
