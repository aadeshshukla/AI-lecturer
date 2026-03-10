"""WebSocket broadcast hub for the AI Autonomous Lecturer System.

The WebSocketHub maintains a set of all connected browser clients and
exposes methods to broadcast events to everyone or to a specific client.

A module-level singleton (``ws_hub``) is imported by all other modules
so that any component can broadcast events without circular imports.
"""

import json
import logging
from typing import Set

from fastapi import WebSocket

from backend.websocket.events import WSEvent

logger = logging.getLogger(__name__)


class WebSocketHub:
    """Manages all active WebSocket client connections.

    Usage::

        from backend.websocket.hub import ws_hub

        await ws_hub.broadcast(create_event("speaking_start", {"text": "Hello"}))
    """

    def __init__(self) -> None:
        self._clients: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection.

        Args:
            websocket: The incoming FastAPI WebSocket object.
        """
        await websocket.accept()
        self._clients.add(websocket)
        logger.info(
            "WebSocket client connected — total clients: %d", len(self._clients)
        )

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a client from the registry (call on disconnect or error).

        Args:
            websocket: The WebSocket that disconnected.
        """
        self._clients.discard(websocket)
        logger.info(
            "WebSocket client disconnected — total clients: %d", len(self._clients)
        )

    async def broadcast(self, event: WSEvent) -> None:
        """Send an event to every connected client.

        Clients that fail to receive the message are silently removed from
        the registry to avoid blocking the broadcast loop.

        Args:
            event: The WSEvent to broadcast.
        """
        if not self._clients:
            return

        payload = json.dumps(event.to_dict())
        dead: Set[WebSocket] = set()

        for client in self._clients:
            try:
                await client.send_text(payload)
            except Exception:
                logger.warning("Failed to send to a WebSocket client; removing it.")
                dead.add(client)

        self._clients -= dead

    async def send_to(self, websocket: WebSocket, event: WSEvent) -> None:
        """Send an event to a single specific client.

        Args:
            websocket: The target WebSocket connection.
            event: The WSEvent to send.
        """
        try:
            await websocket.send_text(json.dumps(event.to_dict()))
        except Exception:
            logger.warning(
                "Failed to send event to specific WebSocket client; disconnecting."
            )
            self.disconnect(websocket)

    @property
    def client_count(self) -> int:
        """Return the number of currently connected clients."""
        return len(self._clients)


# ---------------------------------------------------------------------------
# Module-level singleton — import this everywhere
# ---------------------------------------------------------------------------
ws_hub = WebSocketHub()
