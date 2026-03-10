"""Knowledge retrieval tool stub for the AI Autonomous Lecturer MCP server.

TODO PR2: Replace stub with real LlamaIndex + ChromaDB RAG implementation.
"""

import logging
from typing import List

from backend.websocket.events import EventType, create_event
from backend.websocket.hub import ws_hub

logger = logging.getLogger(__name__)


async def query_knowledge(query: str, top_k: int = 3) -> dict:
    """Perform a semantic search over the lecture knowledge base.

    Stub: will be replaced with real LlamaIndex + ChromaDB query in PR2.

    Args:
        query: Natural-language query string.
        top_k: Maximum number of relevant chunks to return.

    Returns:
        dict with key ``results`` — a list of dicts each containing
        ``text`` and ``source``.
    """
    logger.info("[STUB] query_knowledge: query=%s top_k=%d", query, top_k)
    # TODO PR2: Real LlamaIndex semantic search
    placeholder_results: List[dict] = [
        {"text": f"[STUB] Placeholder knowledge for: {query}", "source": "knowledge_base"}
    ]
    await ws_hub.broadcast(
        create_event(EventType.TOOL_CALLED, {"tool_name": "query_knowledge", "args": {"query": query}})
    )
    return {"results": placeholder_results}
