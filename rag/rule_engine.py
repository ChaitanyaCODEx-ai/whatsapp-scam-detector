"""
rag/rule_engine.py

Deterministic keyword/pattern heuristics. These never replace the LLM
classifier, but act as a guardrail: they catch obvious red flags even if the
LLM is unavailable, rate-limited, or unsure, and they give the Classifier
Agent extra grounded signals to reason over (this is what makes the pipeline
"agentic" rather than a single model call - agents cross-check each other).
"""

import re

URGENCY_WORDS = [
    "urgent", "immediately", "act now", "within 24 hours", "expire",
    "last chance", "final notice", "verify now", "suspended", "blocked",
    "will be disconnected", "limited slots", "hurry",
]

MONEY_REQUEST_WORDS = [
    "processing fee", "registration fee", "clearance fee", "transfer",
    "deposit", "pay now", "send money", "gift card", "bitcoin", "crypto",
    "upi id", "bank details", "account number", "loan approved",
]

CREDENTIAL_REQUEST_WORDS = [
    "otp", "one time password", "pin", "cvv", "password", "aadhaar",
    "kyc", "verify your account", "confirm your details",
]

PRIZE_WORDS = [
    "congratulations", "you have won", "you've won", "you won", "you are the winner",
    "lucky draw", "lottery", "prize", "kbc", "winner", "claim your", "jackpot",
]

# Large money amounts (Rs 25,00,000 / 1 million rupees / $5000 / 10 lakh ...)
AMOUNT_REGEX = re.compile(
    r"(?:rs\.?|inr|\u20b9|\$|usd)\s*\d[\d,\.]*"
    r"|\d[\d,\.]*\s*(?:rs\b|rupees?|lakhs?|crores?|million|billion|dollars?|usd|inr)",
    re.IGNORECASE,
)

THREAT_WORDS = [
    "we have recorded", "pay or", "expose you", "send it to your contacts",
    "legal action", "arrest warrant",
]

SHORTENER_DOMAINS = [
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "rebrand.ly", "is.gd", "cutt.ly",
]

URL_REGEX = re.compile(r"(https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9\-]+\.(?:com|net|xyz|link|info|top|click)\b[^\s]*)", re.IGNORECASE)


def find_urls(text: str) -> list[str]:
    return URL_REGEX.findall(text)


def score_message(text: str) -> dict:
    """Return a heuristic risk score (0-100) plus the specific flags found."""
    lowered = text.lower()
    flags = []
    score = 0

    def _hit(words, label, weight):
        nonlocal score
        # Whole-word match so "pin" doesn't fire on "shipping", "otp" on "hotpot", etc.
        found = [w for w in words if re.search(r"(?<!\w)" + re.escape(w) + r"(?!\w)", lowered)]
        if found:
            flags.append({"label": label, "matched": found})
            score += weight

    _hit(URGENCY_WORDS, "Creates urgency / pressure", 15)
    _hit(MONEY_REQUEST_WORDS, "Requests money or payment details", 25)
    _hit(CREDENTIAL_REQUEST_WORDS, "Requests OTP / credentials / ID numbers", 30)
    _hit(PRIZE_WORDS, "Unsolicited prize or lottery claim", 20)
    _hit(THREAT_WORDS, "Uses threats or extortion language", 30)

    amounts = AMOUNT_REGEX.findall(text)
    if amounts:
        flags.append({"label": "Mentions a large money amount", "matched": [a.strip() for a in amounts]})
        score += 15
        # A prize claim + a money amount is the classic lottery scam shape.
        if any(f["label"] == "Unsolicited prize or lottery claim" for f in flags):
            score += 25

    urls = find_urls(text)
    if urls:
        suspicious_links = [u for u in urls if any(d in u.lower() for d in SHORTENER_DOMAINS)]
        if suspicious_links:
            flags.append({"label": "Contains shortened/masked link", "matched": suspicious_links})
            score += 20
        else:
            flags.append({"label": "Contains an external link", "matched": urls})
            score += 8

    score = min(score, 100)
    return {"heuristic_score": score, "flags": flags, "urls": urls}
