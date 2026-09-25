# 🛡️ Scam Shield — A RAG + Agentic AI Scam/Spam Detector for WhatsApp

## Problem Statement
WhatsApp is one of the most widely used messaging platforms in the world, and that scale makes
it a prime target for scams: fake lottery wins, bank/OTP phishing, fake job offers, romance and
investment scams, and impersonation of family members. WhatsApp offers basic reporting/blocking,
but it does not give users an **in-the-moment, explainable risk assessment** of a specific message
before they act on it, and it does not proactively protect the personal data a user might be about
to expose while investigating a suspicious message.

## Our Solution
**Scam Shield** is a standalone web app, styled like WhatsApp itself, where a user pastes any
suspicious message and gets back:
1. A clear verdict (**Safe / Spam / Suspicious / Scam**) with a confidence score and plain-language
   reasoning.
2. The specific known scam patterns the message resembles (via retrieval, not just a black-box score).
3. Any personal information (phone numbers, OTPs, bank/card numbers, UPI IDs, etc.) found in the
   message — redacted before it is ever sent to an external AI model.
4. Concrete next steps (block/report, don't click links, don't share OTPs, verify independently, etc.)

## Architecture: RAG + Agentic AI

```
 User message
      │
      ▼
┌─────────────────┐   redacts PII locally, nothing sensitive
│  Privacy Agent   │   leaves the device unredacted
└────────┬─────────┘
         ▼
┌─────────────────┐   TF-IDF similarity search over a curated
│ Retrieval Agent  │   knowledge base of known scam patterns (RAG)
└────────┬─────────┘
         ▼
┌─────────────────┐   combines redacted text + retrieved context +
│ Classifier Agent │   rule-based red flags → asks Gemini for a
└────────┬─────────┘   structured verdict (falls back to local
         ▼              heuristics if no API key is configured)
┌─────────────────┐
│  Action Agent    │   turns the verdict into a risk level, color,
└────────┬─────────┘   and a specific checklist of recommended actions
         ▼
   Report shown to user
```

Each agent consumes the *structured output* of the one before it (not just the raw message),
and the pipeline can fall back to a fully local, deterministic mode if no LLM is configured —
this is what makes it agentic rather than a single prompt-to-model call.

- **RAG**: `rag/vector_store.py` — TF-IDF + cosine similarity over `data/scam_patterns.json`,
  a curated set of 16 real-world WhatsApp scam categories (lottery, OTP phishing, job scams,
  romance scams, loan app scams, sextortion, etc.).
- **Agentic AI**: `agents/` — four cooperating agents (`privacy_agent`, `retrieval_agent`,
  `classifier_agent`, `action_agent`) orchestrated by `agents/orchestrator.py`.
- **LLM**: Google **Gemini** (`utils/gemini_client.py`), used for the reasoning step only,
  and only on already-redacted text.
- **Privacy-by-design**: PII is detected and redacted *before* retrieval or LLM calls happen.

## Tech Stack
- Python 3.11+, Flask
- scikit-learn (TF-IDF retrieval)
- Google Generative AI SDK (Gemini)
- Vanilla HTML/CSS/JS frontend styled after WhatsApp's UI

## Setup

```bash
git clone <this-repo>
cd whatsapp-guardian
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# then edit .env and paste your free Gemini API key from
# https://aistudio.google.com/app/apikey

python app.py
```

Open **http://localhost:5000**.

> The app works even without a Gemini key — it automatically falls back to a transparent,
> rule-based classifier so retrieval, privacy redaction, and the UI can still be demoed offline.

## Project Structure
```
whatsapp-guardian/
├── app.py                     # Flask app + API route
├── agents/
│   ├── orchestrator.py        # Wires all agents together
│   ├── privacy_agent.py       # PII detection & redaction
│   ├── retrieval_agent.py     # RAG retrieval wrapper
│   ├── classifier_agent.py    # Gemini reasoning + heuristic fallback
│   └── action_agent.py        # Final verdict + recommended actions
├── rag/
│   ├── vector_store.py        # TF-IDF retrieval over the knowledge base
│   └── rule_engine.py         # Deterministic scam heuristics
├── utils/
│   └── gemini_client.py       # Gemini API wrapper
├── data/
│   └── scam_patterns.json     # Curated scam knowledge base
├── templates/index.html
└── static/{css,js}/
```

## Possible Extensions
- Swap TF-IDF for real sentence embeddings + a vector DB (e.g. FAISS/Chroma) for larger knowledge bases.
- Add a feedback loop where user-confirmed scams are added back into the knowledge base.
- Integrate with the real WhatsApp Business Cloud API to analyze messages in-line.
- Add multi-language support for regional-language scams.
