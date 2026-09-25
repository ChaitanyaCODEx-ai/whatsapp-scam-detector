"""
agents/smalltalk.py

Not every message pasted in is a message to analyze - people also say "hi",
ask "who are you", or say "thanks". Running the full scam pipeline on those
produces a nonsensical SAFE verdict card instead of a normal reply. This
module catches that small talk early so the orchestrator is only invoked for
things that actually look like a forwarded message.

Deliberately conservative: if there's any doubt, we fall through to the real
analysis pipeline. It's fine to analyze a greeting by mistake; it's not fine
to skip analyzing something that might be a scam.
"""

import re

_GREETING_RE = re.compile(
    r"^(hi+|hello+|hey+|yo|sup|good\s?(morning|afternoon|evening|night)|namaste)[\s!.,]*$",
    re.IGNORECASE,
)

_HOWAREYOU_RE = re.compile(r"^(how('?s| is| are) (it going|you|things)|what'?s up|wassup)[\s?!.,]*$", re.IGNORECASE)

_WHOAREYOU_RE = re.compile(
    r"^(who are you|what are you|what do you do|what is this|how does this work|"
    r"what can you do|help)[\s?!.,]*$",
    re.IGNORECASE,
)

_THANKS_RE = re.compile(r"^(thanks?( you)?|thank you( so much)?|ty|thx|appreciate it|cool|nice|great|ok(ay)?|got it)[\s!.,]*$", re.IGNORECASE)

_BYE_RE = re.compile(r"^(bye|goodbye|see ya|see you|later|cya)[\s!.,]*$", re.IGNORECASE)


def small_talk_reply(text: str) -> str | None:
    """Return a friendly reply if `text` is small talk, else None.

    Only matches short, whole-message greetings/chit-chat - anything that
    looks like a forwarded/pasted message (longer, or containing things like
    links, numbers, or a mix of sentences) falls through to real analysis.
    """
    stripped = text.strip()
    if not stripped or len(stripped) > 60:
        return None

    if _GREETING_RE.match(stripped):
        return "Hey! 👋 Paste a message you got on WhatsApp and I'll check it for scams, spam, or anything sketchy."

    if _HOWAREYOU_RE.match(stripped):
        return "I'm doing well, thanks for asking! Send me a message you want me to check whenever you're ready."

    if _WHOAREYOU_RE.match(stripped):
        return (
            "I'm Scam Shield 🛡️ — paste any WhatsApp message here and I'll scan it for scam and spam signs, "
            "flag anything sensitive like OTPs or bank details, and tell you what to do about it. "
            "Everything runs on your device first, before anything (redacted) goes to the AI."
        )

    if _THANKS_RE.match(stripped):
        return "Anytime! Send over another message if you want me to take a look."

    if _BYE_RE.match(stripped):
        return "Take care, and stay safe out there! 👋"

    return None
