import { useEffect, useRef, useState, useCallback } from 'react';

const WS_URL = '/ws'; // Proxied by Vite to ws://localhost:8000/ws

/**
 * Custom hook that maintains a WebSocket connection to the backend.
 *
 * Features:
 *  - Auto-reconnects on disconnect with exponential backoff (max 30 s).
 *  - Parses all incoming JSON frames into { type, timestamp, data }.
 *  - Exposes sendMessage(obj) for client → server communication.
 *
 * @returns {{ lastEvent: object|null, isConnected: boolean, sendMessage: Function }}
 */
export default function useWebSocket() {
  const [lastEvent, setLastEvent] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef(null);
  const retryDelay = useRef(1000);
  const retryTimer = useRef(null);
  const unmounted = useRef(false);

  const connect = useCallback(() => {
    if (unmounted.current) return;

    // Build the WebSocket URL — in dev Vite proxies /ws → ws://localhost:8000/ws
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}${WS_URL}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      retryDelay.current = 1000; // reset backoff on successful connect
    };

    ws.onmessage = (evt) => {
      try {
        const event = JSON.parse(evt.data);
        setLastEvent(event);
      } catch {
        // ignore malformed frames
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      if (unmounted.current) return;
      // Exponential back-off: 1 s → 2 s → 4 s → … → 30 s max
      retryTimer.current = setTimeout(() => {
        retryDelay.current = Math.min(retryDelay.current * 2, 30_000);
        connect();
      }, retryDelay.current);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      unmounted.current = true;
      clearTimeout(retryTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  /** Send a plain JS object as a JSON string to the server. */
  const sendMessage = useCallback((obj) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(obj));
    }
  }, []);

  return { lastEvent, isConnected, sendMessage };
}
