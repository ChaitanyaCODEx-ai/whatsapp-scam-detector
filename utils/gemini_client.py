"""
utils/gemini_client.py

Thin wrapper around Google's Gemini API. Import of the google-generativeai
package and the API key are both optional at runtime: if either is missing,
`generate_json` returns None and callers (the Classifier Agent) fall back to
the local rule-based heuristic. This means the app still runs end-to-end for
development/demo purposes even without a configured API key, and switches to
live reasoning automatically once GEMINI_API_KEY is set.
"""

import json
import os
import re

_MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

_client_ready = False
_genai = None

try:
    import google.generativeai as genai  # type: ignore

    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        _genai = genai
        _client_ready = True
except ImportError:
    pass


def is_available() -> bool:
    return _client_ready


def _extract_json(raw: str) -> dict | None:
    """Gemini sometimes wraps JSON in markdown fences; strip those before parsing."""
    cleaned = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find the first {...} block as a last resort
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
        return None


def generate_json(system_instruction: str, prompt: str) -> dict | None:
    """Call Gemini with a prompt that asks for a JSON object back.

    Returns the parsed dict, or None if the client isn't configured or the
    call/parsing fails for any reason (network, quota, malformed output).
    """
    if not _client_ready:
        return None

    try:
        model = _genai.GenerativeModel(
            model_name=_MODEL_NAME,
            system_instruction=system_instruction,
        )
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"},
        )
        return _extract_json(response.text)
    except Exception as exc:
        # Any API/network failure: caller falls back to heuristics, but log WHY
        # so a bad key / retired model / quota error isn't invisible.
        print(f"[gemini_client] Gemini call failed ({type(exc).__name__}): {exc}")
        return None
