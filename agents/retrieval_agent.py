"""
agents/retrieval_agent.py

Thin agent wrapper around rag.vector_store. Kept as its own agent (rather than
calling the store directly from the orchestrator) so it can later be swapped
for a real embedding model or a larger/external knowledge base without
touching the rest of the pipeline.
"""

from rag.vector_store import store, RetrievedPattern


class RetrievalAgent:
    def run(self, message: str, top_k: int = 3) -> list[RetrievedPattern]:
        return store.query(message, top_k=top_k)
