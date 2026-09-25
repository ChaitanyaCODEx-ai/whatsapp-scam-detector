"""
agents/classifier_agent.py

The reasoning core of the pipeline. Builds a grounded prompt out of:
  1. the (already privacy-redacted) message text
  2. the scam patterns the Retrieval Agent found similar (RAG context)
  3. the deterministic rule-engine flags
and asks Gemini for a structured verdict. If Gemini is not configured or the
call fails, falls back to a transparent heuristic-only classification so the
app still produces a usable result.
"""

from dataclasses import dataclass, field

from rag.rule_engine import score_message
from utils.gemini_client import generate_json, is_available

SYSTEM_INSTRUCTION = """You are Scam Shield, a friendly safety assistant helping an everyday person figure \
out whether a WhatsApp message they received is safe. You will be given the message (with personal details \
already redacted), a list of similar known scam patterns retrieved from a reference database, and rule-based \
red flags detected in the text. Decide whether the message is SAFE, SPAM, SCAM, or SUSPICIOUS (needs human review).

Write the "reasoning" like you're talking directly to the person who got this message, not like a report. \
Use "I" and "you" ("I'd be careful with this one because..."), keep it warm and plain-spoken, 2-3 sentences, \
no jargon, no bullet points inside the string.

Respond with ONLY a JSON object, no other text, in exactly this shape:
{
  "label": "SAFE" | "SPAM" | "SCAM" | "SUSPICIOUS",
  "confidence": <integer 0-100>,
  "reasoning": "<2-3 sentence first-person, conversational explanation for a non-technical user>",
  "risk_factors": ["<short phrase>", ...]
}
"""


@dataclass
class ClassificationResult:
    label: str
    confidence: int
    reasoning: str
    risk_factors: list[str] = field(default_factory=list)
    source: str = "heuristic"  # "gemini" or "heuristic"


def _heuristic_fallback(heuristic: dict) -> ClassificationResult:
    score = heuristic["heuristic_score"]
    factors = [f["label"] for f in heuristic["flags"]]

    if score >= 60:
        label, reasoning = "SCAM", (
            "I'd steer clear of this one — it's got several classic scam signs, like pressure to act fast, "
            "a request for money, or a request for an OTP or password. I wouldn't reply, click anything, or share any details."
        )
    elif score >= 30:
        label, reasoning = "SUSPICIOUS", (
            "A few things about this message don't quite add up, though it doesn't match a known scam exactly. "
            "I'd double-check who actually sent it before doing anything it asks."
        )
    elif score >= 10:
        label, reasoning = "SPAM", (
            "This looks like spam to me rather than a scam — a bit promotional or low-trust, but nothing that's "
            "trying to steal money or information."
        )
    else:
        label, reasoning = "SAFE", "This one looks fine to me — I didn't spot any scam or spam red flags in it."

    return ClassificationResult(
        label=label,
        confidence=min(95, max(40, score)),
        reasoning=reasoning,
        risk_factors=factors,
        source="heuristic",
    )


class ClassifierAgent:
    def run(self, redacted_message: str, retrieved_patterns: list, privacy_types: list[str]) -> ClassificationResult:
        heuristic = score_message(redacted_message)

        if not is_available():
            return _heuristic_fallback(heuristic)

        context_block = "\n".join(
            f"- [{p.category}, similarity {p.score}] {p.description}" for p in retrieved_patterns
        ) or "- No closely matching known scam pattern was found."

        flags_block = "\n".join(
            f"- {f['label']} (matched: {', '.join(f['matched'])})" for f in heuristic["flags"]
        ) or "- No rule-based red flags detected."

        prompt = f"""Message to analyze (personal data already redacted):
\"\"\"{redacted_message}\"\"\"

Similar known scam patterns from our reference database:
{context_block}

Rule-based red flags detected in the text:
{flags_block}

Personal information types already found and redacted from this message: {privacy_types or 'none'}

Classify this message now."""

        result = generate_json(SYSTEM_INSTRUCTION, prompt)
        if not result:
            return _heuristic_fallback(heuristic)

        try:
            return ClassificationResult(
                label=str(result.get("label", "SUSPICIOUS")).upper(),
                confidence=int(result.get("confidence", 50)),
                reasoning=str(result.get("reasoning", "")),
                risk_factors=list(result.get("risk_factors", [])),
                source="gemini",
            )
        except (ValueError, TypeError):
            return _heuristic_fallback(heuristic)
