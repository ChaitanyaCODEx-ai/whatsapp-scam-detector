"""
agents/action_agent.py

Takes the Classifier Agent's verdict plus the Privacy Agent's findings and
decides the final risk level, color, and concrete recommended actions shown
to the user. This is the "what should I actually do about it" layer.
"""

LABEL_TO_LEVEL = {
    "SAFE": {"level": "SAFE", "color": "#25D366", "emoji": "✅"},
    "SPAM": {"level": "LOW", "color": "#F0AD4E", "emoji": "🟡"},
    "SUSPICIOUS": {"level": "MEDIUM", "color": "#FF8C00", "emoji": "🟠"},
    "SCAM": {"level": "HIGH", "color": "#D9534F", "emoji": "🚨"},
}

CHAT_SUMMARY = {
    "SAFE": "Good news — this looks safe to me! ✅",
    "SPAM": "This looks like spam — not dangerous, but I'd ignore it. 🟡",
    "SUSPICIOUS": "Hmm, a few things here don't add up. Worth double-checking. 🟠",
    "SCAM": "Careful — this has strong signs of a scam. Don't reply or click anything. 🚨",
}

BASE_ACTIONS = {
    "SAFE": [
        "No action needed, but always stay cautious with unexpected requests for money or personal data.",
    ],
    "SPAM": [
        "Consider blocking or reporting the sender in WhatsApp.",
        "Don't engage or reply — that confirms your number is active.",
    ],
    "SUSPICIOUS": [
        "Don't click any links or reply with personal information.",
        "Verify the sender independently through an official number or website before doing anything.",
    ],
    "SCAM": [
        "Do not click any links or reply.",
        "Do not share OTPs, PINs, passwords, or bank details.",
        "Block and report this contact in WhatsApp (Report > Block).",
        "If money was already sent, contact your bank immediately.",
    ],
}


class ActionAgent:
    def run(self, classification, heuristic_urls: list[str], privacy_tips: list[str]) -> dict:
        meta = LABEL_TO_LEVEL.get(classification.label, LABEL_TO_LEVEL["SUSPICIOUS"])
        actions = list(BASE_ACTIONS.get(classification.label, BASE_ACTIONS["SUSPICIOUS"]))

        if heuristic_urls and classification.label != "SAFE":
            actions.append("Treat any link in this message as unsafe until verified through an official channel.")

        actions.extend(privacy_tips)

        return {
            "chat_summary": CHAT_SUMMARY.get(classification.label, CHAT_SUMMARY["SUSPICIOUS"]),
            "label": classification.label,
            "risk_level": meta["level"],
            "color": meta["color"],
            "emoji": meta["emoji"],
            "confidence": classification.confidence,
            "reasoning": classification.reasoning,
            "risk_factors": classification.risk_factors,
            "recommended_actions": actions,
            "analysis_source": classification.source,
        }
