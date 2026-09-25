"""
agents/privacy_agent.py

The Privacy Agent is responsible for the "extra privacy measures" half of the
project. Before any message text is sent to an external LLM API, this agent
scans it for personally identifiable information (PII) and produces a
redacted version. The rest of the pipeline (retrieval + classification) works
on the redacted text wherever possible, so real phone numbers, card numbers,
OTPs etc. never leave the user's machine unnecessarily.
"""

import re
from dataclasses import dataclass, field

PATTERNS = {
    "phone_number": re.compile(r"(?:\+?\d{1,3}[\s-]?)?\d{10}\b"),
    "email": re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
    "credit_card": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    "aadhaar_like_id": re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),
    "upi_id": re.compile(r"\b[\w.\-]{2,256}@[a-zA-Z]{2,64}\b"),
    "bank_account": re.compile(r"\b\d{9,18}\b"),
}

# Order matters: check more specific patterns before generic ones so a credit
# card number isn't double-flagged as a bank account, etc.
CHECK_ORDER = [
    "email",
    "upi_id",
    "credit_card",
    "aadhaar_like_id",
    "phone_number",
    "bank_account",
]

# OTP codes are only redacted near the word "otp"/"pin"/"code" - a bare 4-8
# digit number on its own is too common (times, amounts, etc.) to safely
# redact without that context. We redact only the digits, not the keyword
# itself, so downstream scam-keyword detection ("OTP" is itself a red flag)
# still works on the redacted text.
_OTP_CONTEXT_RE = re.compile(
    r"\b(?:otp|one[\s-]?time[\s-]?password|pin|verification code)\b\D{0,15}?(\d{4,8})"
    r"|(\d{4,8})\D{0,15}?\b(?:is your otp|is your code|is your pin)\b",
    re.IGNORECASE,
)


def _redact_otp_codes(text: str) -> tuple[str, int]:
    count = 0

    def _sub(m):
        nonlocal count
        count += 1
        digits = m.group(1) or m.group(2)
        return m.group(0).replace(digits, "[REDACTED_OTP_CODE]")

    new_text = _OTP_CONTEXT_RE.sub(_sub, text)
    return new_text, count


@dataclass
class PrivacyFindings:
    redacted_text: str
    detected_types: list[str] = field(default_factory=list)
    detail_counts: dict = field(default_factory=dict)


def scan_and_redact(text: str) -> PrivacyFindings:
    redacted = text
    detected_types = []
    detail_counts = {}
    already_redacted_spans = []

    # OTPs first, and handled separately so we only strip the digits.
    redacted, otp_count = _redact_otp_codes(redacted)
    if otp_count:
        detected_types.append("otp_code")
        detail_counts["otp_code"] = otp_count

    for kind in CHECK_ORDER:
        pattern = PATTERNS[kind]
        matches = list(pattern.finditer(redacted))
        if not matches:
            continue

        count = 0
        new_text = []
        last_end = 0
        for m in matches:
            # Skip overlaps with something already redacted in this pass
            if any(a <= m.start() < b for a, b in already_redacted_spans):
                continue
            new_text.append(redacted[last_end:m.start()])
            new_text.append(f"[REDACTED_{kind.upper()}]")
            last_end = m.end()
            already_redacted_spans.append((m.start(), m.end()))
            count += 1
        new_text.append(redacted[last_end:])
        if count:
            redacted = "".join(new_text)
            detected_types.append(kind)
            detail_counts[kind] = count

    return PrivacyFindings(
        redacted_text=redacted,
        detected_types=detected_types,
        detail_counts=detail_counts,
    )


def privacy_recommendations(findings: PrivacyFindings) -> list[str]:
    tips = []
    if "phone_number" in findings.detected_types:
        tips.append("Avoid sharing or forwarding phone numbers found in unsolicited messages.")
    if "otp_code" in findings.detected_types:
        tips.append("Never share an OTP with anyone, even someone claiming to be your bank.")
    if "bank_account" in findings.detected_types or "credit_card" in findings.detected_types:
        tips.append("Never send bank account or card numbers over chat.")
    if "aadhaar_like_id" in findings.detected_types:
        tips.append("Avoid sharing government ID numbers over chat; verify the requester independently.")
    if "upi_id" in findings.detected_types:
        tips.append("Double-check any UPI ID against the sender's official channel before paying.")
    if not tips:
        tips.append("No direct personal data was found in this message, but stay cautious with links and requests for money.")
    return tips
