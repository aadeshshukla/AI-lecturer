"""Knowledge retrieval tool for the AI Autonomous Lecturer MCP server.

Delegates to the KnowledgeAgent singleton for ChromaDB-backed semantic search.
"""

import logging
from typing import List

from backend.websocket.events import EventType, create_event
from backend.websocket.hub import ws_hub

logger = logging.getLogger(__name__)


async def query_knowledge(query: str, top_k: int = 3) -> dict:
    """Perform a semantic search over the lecture knowledge base.

    Delegates to ``knowledge_agent.query()`` which uses sentence-transformers
    embeddings and ChromaDB for retrieval.

    Args:
        query: Natural-language query string.
        top_k: Maximum number of relevant chunks to return.

    Returns:
        dict with key ``results`` — a list of dicts each containing
        ``text``, ``source``, and ``score``.
    """
    from backend.agents.knowledge_agent import knowledge_agent  # local import

    logger.info("query_knowledge: query=%s top_k=%d", query, top_k)

    await ws_hub.broadcast(
        create_event(EventType.TOOL_CALLED, {"tool_name": "query_knowledge", "args": {"query": query}})
    )

    results: List[dict] = await knowledge_agent.query(query, top_k=top_k)
    return {"results": results}
