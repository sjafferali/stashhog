import { useState, useEffect, useRef, useCallback } from 'react';
import { message as antdMessage } from 'antd';

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

const WEBSOCKET_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

export function useWebSocket(
  endpoint: string | null,
  options: WebSocketOptions = {}
): UseWebSocketReturn {
  const [lastMessage, setLastMessage] = useState<unknown>(null);
  const [message, setMessage] = useState<unknown>(null);
  const [readyState, setReadyState] = useState<number>(WebSocket.CLOSED);

  const ws = useRef<WebSocket | null>(null);
  const reconnectCount = useRef(0);
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);

  const {
    reconnect = true,
    reconnectInterval = 3000,
    reconnectAttempts = 5,
    onOpen,
    onClose,
    onError,
    onMessage,
  } = options;

  const connect = useCallback(() => {
    if (!endpoint) return;

    try {
      // Clean up existing connection
      if (ws.current) {
        ws.current.close();
      }

      const url = `${WEBSOCKET_URL}${endpoint}`;
      ws.current = new WebSocket(url);

      ws.current.onopen = (event) => {
        setReadyState(WebSocket.OPEN);
        reconnectCount.current = 0;
        onOpen?.(event);
      };

      ws.current.onclose = (event) => {
        setReadyState(WebSocket.CLOSED);
        onClose?.(event);

        // Attempt to reconnect
        if (
          reconnect &&
          reconnectCount.current < reconnectAttempts &&
          !event.wasClean
        ) {
          reconnectTimeout.current = setTimeout(() => {
            reconnectCount.current++;
            connect();
          }, reconnectInterval);
        }
      };

      ws.current.onerror = (event) => {
        onError?.(event);
        void antdMessage.error('WebSocket connection error');
      };

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setLastMessage(data);
          setMessage(data);
          onMessage?.(data);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
    }
  }, [
    endpoint,
    reconnect,
    reconnectInterval,
    reconnectAttempts,
    onOpen,
    onClose,
    onError,
    onMessage,
  ]);

  const disconnect = useCallback(() => {
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
    }

    if (ws.current) {
      ws.current.close();
      ws.current = null;
    }

    setReadyState(WebSocket.CLOSED);
  }, []);

  const sendMessage = useCallback((data: Record<string, unknown>) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(data));
    } else {
      console.warn('WebSocket is not connected');
    }
  }, []);

  // Connect on mount and cleanup on unmount
  useEffect(() => {
    connect();

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  // Update ready state
  useEffect(() => {
    const interval = setInterval(() => {
      if (ws.current) {
        setReadyState(ws.current.readyState);
      }
    }, 100);

    return () => clearInterval(interval);
  }, []);

  return {
    sendMessage,
    lastMessage,
    readyState,
    message,
    connect,
    disconnect,
  };
}
