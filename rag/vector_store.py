"""
rag/vector_store.py

Lightweight local retrieval layer for the RAG pipeline.

We deliberately avoid depending on a downloaded embedding model (so the app
works offline / without extra API calls just to retrieve context) and instead
use TF-IDF + cosine similarity (pure Python) over the curated scam-pattern knowledge base.
This is swapped in as the "R" in RAG: given an incoming message, we retrieve
the most similar known scam patterns and hand them to the Classifier Agent as
grounding context before it reasons about the new message.
"""

import json
import math
import os
import re
from collections import Counter
from dataclasses import dataclass

# NOTE: implemented in pure Python (no scikit-learn / numpy) so it runs on
# locked-down Windows machines where Application Control blocks compiled
# .pyd/.dll files, and on any Python version without wheel issues.

_STOPWORDS = frozenset(
    """a about above after again all am an and any are as at be because been before being
    below between both but by can did do does doing down during each few for from further had
    has have having he her here hers him his how i if in into is it its me more most my no nor
    not of off on once only or other our out over own same she should so some such than that the
    their them then there these they this those through to too under until up very was we were
    what when where which while who whom why will with you your yours""".split()
)
_TOKEN_RE = re.compile(r"(?u)\b\w\w+\b")


def _terms(text: str) -> list[str]:
    """Lowercase unigrams + bigrams (stop words removed), like TfidfVectorizer(ngram_range=(1,2))."""
    words = [w for w in _TOKEN_RE.findall(text.lower()) if w not in _STOPWORDS]
    return words + [f"{a} {b}" for a, b in zip(words, words[1:])]


def _normalize(vec: dict) -> dict:
    norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
    return {t: v / norm for t, v in vec.items()}

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "scam_patterns.json")


@dataclass
class RetrievedPattern:
    id: str
    category: str
    risk_level: str
    example: str
    description: str
    score: float


class ScamPatternStore:
    """Loads the scam knowledge base once and serves similarity queries."""

    def __init__(self, data_path: str = DATA_PATH):
        with open(data_path, "r", encoding="utf-8") as f:
            self.patterns = json.load(f)

        # Combine example + description so both the phrasing and the intent
        # of each scam pattern contribute to the similarity match.
        self._corpus = [
            f"{p['category']}. {p['example']} {p['description']}" for p in self.patterns
        ]

        # Document frequency -> smoothed IDF (same formula scikit-learn uses).
        doc_terms = [Counter(_terms(doc)) for doc in self._corpus]
        n_docs = len(doc_terms)
        df = Counter(t for counts in doc_terms for t in counts)
        self._idf = {t: math.log((1 + n_docs) / (1 + d)) + 1 for t, d in df.items()}
        self._matrix = [
            _normalize({t: c * self._idf[t] for t, c in counts.items()}) for counts in doc_terms
        ]

    def query(self, text: str, top_k: int = 3, min_score: float = 0.05) -> list[RetrievedPattern]:
        """Return the top_k most similar known scam patterns to `text`."""
        if not text or not text.strip():
            return []

        q_counts = Counter(t for t in _terms(text) if t in self._idf)
        if not q_counts:
            return []
        q_vec = _normalize({t: c * self._idf[t] for t, c in q_counts.items()})

        sims = []
        for doc_vec in self._matrix:
            small, big = (q_vec, doc_vec) if len(q_vec) <= len(doc_vec) else (doc_vec, q_vec)
            sims.append(sum(v * big.get(t, 0.0) for t, v in small.items()))

        ranked_idx = sorted(range(len(sims)), key=lambda i: sims[i], reverse=True)[:top_k]
        results = []
        for idx in ranked_idx:
            score = float(sims[idx])
            if score < min_score:
                continue
            p = self.patterns[idx]
            results.append(
                RetrievedPattern(
                    id=p["id"],
                    category=p["category"],
                    risk_level=p["risk_level"],
                    example=p["example"],
                    description=p["description"],
                    score=round(score, 4),
                )
            )
        return results


# Singleton instance used across the app
store = ScamPatternStore()
