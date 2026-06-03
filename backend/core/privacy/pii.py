"""Real PII detection and masking.

Regex-based detector covering the types claimed in the User Manual:
email, phone, ssn, credit_card (Luhn-validated), ip_address, date_of_birth, name.
Masking supports the documented strategies: redact, hash, replace, partial.

No external dependencies — safe to import anywhere in the backend.
"""
from __future__ import annotations

import hashlib
import re
from typing import Dict, List

# --- Patterns -------------------------------------------------------------
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
# US-style phone: optional +1, separators ., -, space, or none. 10 digits.
_PHONE_RE = re.compile(
    r"(?<!\d)(?:\+?1[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}(?!\d)"
)
_SSN_RE = re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)")
# Candidate 13-19 digit card numbers (with optional spaces/dashes) — Luhn-checked below.
_CC_RE = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
_IPV4_RE = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b"
)
# Date of birth: explicit DOB label, or common date formats.
_DOB_RE = re.compile(
    r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}|"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})\b"
)
# Name heuristic: two or three consecutive Capitalized words. Lower precision —
# applied last and never overrides a higher-confidence span.
_NAME_RE = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}\b")

# Detection priority — higher index = lower priority when spans overlap.
_DETECTORS = [
    ("credit_card", _CC_RE),
    ("ssn", _SSN_RE),
    ("email", _EMAIL_RE),
    ("phone", _PHONE_RE),
    ("ip_address", _IPV4_RE),
    ("date_of_birth", _DOB_RE),
    ("name", _NAME_RE),
]

_PLACEHOLDERS = {
    "email": "user@example.com",
    "phone": "(000) 000-0000",
    "ssn": "000-00-0000",
    "credit_card": "0000 0000 0000 0000",
    "ip_address": "0.0.0.0",
    "date_of_birth": "0000-00-00",
    "name": "Jane Doe",
}


def _luhn_ok(number: str) -> bool:
    digits = [int(c) for c in number if c.isdigit()]
    if not 13 <= len(digits) <= 19:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def find_entities(text: str) -> List[Dict]:
    """Return non-overlapping PII entities sorted by position.

    Each entity: {"type", "value", "start", "end"}.
    """
    spans: List[Dict] = []
    occupied: List[tuple] = []

    def overlaps(start: int, end: int) -> bool:
        return any(not (end <= s or start >= e) for s, e in occupied)

    for pii_type, pattern in _DETECTORS:
        for m in pattern.finditer(text or ""):
            start, end = m.start(), m.end()
            if overlaps(start, end):
                continue
            if pii_type == "credit_card" and not _luhn_ok(m.group()):
                continue
            spans.append({"type": pii_type, "value": m.group(), "start": start, "end": end})
            occupied.append((start, end))

    spans.sort(key=lambda s: s["start"])
    return spans


def detect(text: str) -> Dict:
    """Detection summary matching the manual's /privacy/detect-pii contract."""
    entities = find_entities(text)
    types = sorted({e["type"] for e in entities})
    return {
        "has_pii": len(entities) > 0,
        "pii_types": types,
        "count": len(entities),
        "entities": [{"type": e["type"], "start": e["start"], "end": e["end"]} for e in entities],
    }


def _mask_value(value: str, pii_type: str, strategy: str) -> str:
    if strategy == "hash":
        return f"[{pii_type.upper()}:{hashlib.sha256(value.encode()).hexdigest()[:10]}]"
    if strategy == "replace":
        return _PLACEHOLDERS.get(pii_type, "[REDACTED]")
    if strategy == "partial":
        digits_or_chars = re.sub(r"\s|-", "", value)
        if len(digits_or_chars) <= 4:
            return f"[{pii_type.upper()}]"
        return f"{'*' * (len(digits_or_chars) - 4)}{digits_or_chars[-4:]}"
    # default: redact
    return f"[{pii_type.upper()}]"


def mask(text: str, strategy: str = "redact") -> Dict:
    """Mask all detected PII using the chosen strategy.

    Strategies: redact (default), hash, replace, partial.
    """
    if strategy not in ("redact", "hash", "replace", "partial"):
        strategy = "redact"
    entities = find_entities(text)
    masked = text or ""
    # Replace right-to-left so earlier offsets stay valid.
    for e in sorted(entities, key=lambda s: s["start"], reverse=True):
        replacement = _mask_value(e["value"], e["type"], strategy)
        masked = masked[: e["start"]] + replacement + masked[e["end"] :]
    return {
        "masked_text": masked,
        "pii_found": sorted({e["type"] for e in entities}),
        "strategy": strategy,
    }
