"""
agents/orchestrator.py

Coordinates the full agentic pipeline for one incoming message:

  1. Privacy Agent   -> detect & redact PII before anything leaves the device
  2. Retrieval Agent -> pull similar known scam patterns from the RAG store
  3. Classifier Agent-> reason over redacted text + retrieved context + rules
  4. Action Agent    -> turn the verdict into a risk level + recommendations

Each step's output is included in the final result so the UI can show the
pipeline "thinking" stage by stage, which is also what makes this agentic
rather than a single prompt-to-model call: later agents consume earlier
agents' structured output, not just the raw message.
"""

from agents.privacy_agent import scan_and_redact, privacy_recommendations
from agents.retrieval_agent import RetrievalAgent
from agents.classifier_agent import ClassifierAgent
from agents.action_agent import ActionAgent
from rag.rule_engine import score_message

retrieval_agent = RetrievalAgent()
classifier_agent = ClassifierAgent()
action_agent = ActionAgent()


def analyze_message(raw_message: str) -> dict:
    if not raw_message or not raw_message.strip():
        raise ValueError("Message text is empty.")

    # Step 1: Privacy first — redact before this text is used anywhere else.
    privacy_findings = scan_and_redact(raw_message)
    tips = privacy_recommendations(privacy_findings)

    # Step 2: Retrieve similar known scam patterns (RAG).
    retrieved = retrieval_agent.run(privacy_findings.redacted_text)

    # Step 3: Rule-based signals (used both standalone and as LLM grounding).
    heuristic = score_message(privacy_findings.redacted_text)

    # Step 4: Classify using retrieved context + rules (Gemini, with fallback).
    classification = classifier_agent.run(
        redacted_message=privacy_findings.redacted_text,
        retrieved_patterns=retrieved,
        privacy_types=privacy_findings.detected_types,
    )

    # Step 5: Decide the final verdict + recommended actions.
    result = action_agent.run(
        classification=classification,
        heuristic_urls=heuristic["urls"],
        privacy_tips=tips,
    )

    result["privacy"] = {
        "pii_detected": privacy_findings.detected_types,
        "pii_counts": privacy_findings.detail_counts,
        "redacted_preview": privacy_findings.redacted_text,
    }
    result["matched_patterns"] = [
        {
            "category": p.category,
            "risk_level": p.risk_level,
            "similarity": p.score,
        }
        for p in retrieved
    ]
    result["rule_flags"] = [f["label"] for f in heuristic["flags"]]
    return result
