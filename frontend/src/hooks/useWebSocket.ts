import { useState, useEffect, useRef } from 'react';
import { wsManager } from '@/services/websocketManager';

export interface WebSocketOptions {
  reconnect?: boolean;
  reconnectInterval?: number;
  reconnectAttempts?: number;
  onOpen?: (event: Event) => void;
  onClose?: (event: CloseEvent) => void;
  onError?: (event: Event) => void;
  onMessage?: (data: unknown) => void;
}

export interface UseWebSocketReturn {
  sendMessage: (data: Record<string, unknown>) => void;
  lastMessage: unknown;
  readyState: number;
  message: unknown;
  connect: () => void;
  disconnect: () => void;
}

export function useWebSocket(
  endpoint: string | null,
  options: WebSocketOptions = {}
): UseWebSocketReturn {
  const [lastMessage, setLastMessage] = useState<unknown>(null);
  const [message, setMessage] = useState<unknown>(null);
  const [readyState, setReadyState] = useState<number>(WebSocket.CLOSED);

  const unsubscribeRef = useRef<(() => void) | null>(null);
  const { onMessage } = options;

  useEffect(() => {
    if (!endpoint) return;

    // Subscribe to WebSocket manager
    const unsubscribe = wsManager.subscribe(endpoint, (data) => {
      setLastMessage(data);
      setMessage(data);
      if (onMessage) {
        onMessage(data);
      }
    });

    unsubscribeRef.current = unsubscribe;

    // Update ready state periodically
    const interval = setInterval(() => {
      setReadyState(wsManager.getReadyState(endpoint));
    }, 500);

    // Cleanup
    return () => {
      if (unsubscribeRef.current) {
        unsubscribeRef.current();
        unsubscribeRef.current = null;
      }
      clearInterval(interval);
    };
  }, [endpoint, onMessage]);

  const sendMessage = (data: Record<string, unknown>) => {
    if (endpoint) {
      wsManager.send(endpoint, data);
    }
  };

  const connect = () => {
    // Connection is handled automatically by the manager
    if (endpoint) {
      setReadyState(wsManager.getReadyState(endpoint));
    }
  };

  const disconnect = () => {
    // Unsubscribe from manager
    if (unsubscribeRef.current) {
      unsubscribeRef.current();
      unsubscribeRef.current = null;
    }
    setReadyState(WebSocket.CLOSED);
  };

  return {
    sendMessage,
    lastMessage,
    readyState,
    message,
    connect,
    disconnect,
  };
}
