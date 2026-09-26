"""CONTINUITY Enterprise Log Security Guard.

Screening layer inspired by Google Cloud Model Armor to neutralize indirect prompt injection
and credential leaks embedded in raw Loki/PromQL telemetry logs before ingestion by Gemini.
"""

from __future__ import annotations

import re
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("continuity.security")


class LogSecurityGuard:
    """Enterprise screening layer neutralizing prompt injection and credential leaks in telemetry logs."""

    # Patterns indicating indirect prompt injection or adversarial role override
    INJECTION_PATTERNS: List[Tuple[re.Pattern, str]] = [
        (re.compile(r"ignore\s+(?:(?:all|previous|prior)\s+)*instructions?", re.IGNORECASE), "INSTRUCTION_OVERRIDE"),
        (re.compile(r"system\s+prompt\s+override", re.IGNORECASE), "SYSTEM_PROMPT_OVERRIDE"),
        (re.compile(r"you\s+are\s+now\s+(?:an?\s+)?(?:unrestricted|DAN|jailbreak)", re.IGNORECASE), "ROLE_HIJACK"),
        (re.compile(r"disregard\s+(?:all\s+)?safety", re.IGNORECASE), "SAFETY_BYPASS"),
        (re.compile(r"admin\s+access\s+granted", re.IGNORECASE), "PRIVILEGE_ESCALATION"),
        (re.compile(r"execute\s+(?:halt|shutdown|wipe|delete_all|drop_database)", re.IGNORECASE), "DESTRUCTIVE_COMMAND"),
        (re.compile(r"(?:eval|exec)\s*\([^\)]+\)", re.IGNORECASE), "CODE_EXECUTION"),
        (re.compile(r"<\s*script[^>]*>.*?<\s*/\s*script\s*>", re.IGNORECASE | re.DOTALL), "SCRIPT_TAG"),
    ]

    # Secret and credential leak patterns
    SECRET_PATTERNS: List[Tuple[re.Pattern, str]] = [
        (re.compile(r"glsa_[A-Za-z0-9_]{20,}", re.IGNORECASE), "[REDACTED_GRAFANA_SERVICE_TOKEN]"),
        (re.compile(r"(?:Bearer\s+)[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE), "Bearer [REDACTED_BEARER_TOKEN]"),
        (re.compile(r"ey[A-Za-z0-9_\-]{15,}\.ey[A-Za-z0-9_\-]{15,}\.[A-Za-z0-9_\-]{15,}", re.IGNORECASE), "[REDACTED_JWT_TOKEN]"),
        (re.compile(r"(?:sk-|apiKey=|api_key=|api-key=)[A-Za-z0-9_\-]{16,}", re.IGNORECASE), "[REDACTED_API_KEY]"),
    ]

    def __init__(self):
        self._total_scanned_lines: int = 0
        self._flagged_injections: int = 0
        self._redacted_credentials: int = 0
        self._audit_events: List[Dict[str, Any]] = []

    def sanitize_log_line(self, line: str) -> Tuple[str, bool, Optional[str]]:
        """Sanitizes a single log line.

        Returns:
            Tuple of (sanitized_line, was_flagged_for_injection, injection_category)
        """
        if not line or not isinstance(line, str):
            return line, False, None

        self._total_scanned_lines += 1

        # Strip non-printable ASCII control characters (keeping standard whitespace)
        cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", line).strip()

        # 1. Redact credentials
        for pattern, replacement in self.SECRET_PATTERNS:
            if pattern.search(cleaned):
                cleaned = pattern.sub(replacement, cleaned)
                self._redacted_credentials += 1

        # 2. Check for prompt injection markers
        for pattern, category in self.INJECTION_PATTERNS:
            if pattern.search(cleaned):
                self._flagged_injections += 1
                sanitized = f"[SECURITY_SHIELD_FLAGGED_CONTENT: category={category}]"
                event = {
                    "category": category,
                    "original_snippet": cleaned[:120],
                    "action": "neutralized"
                }
                self._audit_events.append(event)
                logger.warning(f"[Security Guard] Adversarial log injection intercepted: {category} in line: '{cleaned[:80]}'")
                return sanitized, True, category

        return cleaned, False, None

    def sanitize_log_lines(self, lines: List[str]) -> List[str]:
        """Sanitizes a list of log lines."""
        if not lines:
            return []
        sanitized = []
        for line in lines:
            clean_line, _, _ = self.sanitize_log_line(line)
            sanitized.append(clean_line)
        return sanitized

    def sanitize_loki_result(self, result: Any) -> Any:
        """Sanitizes in-place or returns a sanitized LokiQueryResult."""
        if result is None:
            return None
        lines = getattr(result, "lines", None)
        if isinstance(lines, list):
            result.lines = self.sanitize_log_lines(lines)
        return result

    def get_security_metrics(self) -> Dict[str, Any]:
        """Returns security shield metrics for telemetry and dashboard reporting."""
        return {
            "total_scanned_lines": self._total_scanned_lines,
            "flagged_injections": self._flagged_injections,
            "redacted_credentials": self._redacted_credentials,
            "recent_audit_events": self._audit_events[-10:]
        }


# Singleton instance for application-wide use
security_guard = LogSecurityGuard()
