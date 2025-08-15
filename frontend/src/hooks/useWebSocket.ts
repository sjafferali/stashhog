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

const getWebSocketUrl = () => {
  if (import.meta.env.VITE_WS_URL) {
    return import.meta.env.VITE_WS_URL;
  }
  // Use the current location to build the WebSocket URL
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  return `${protocol}//${host}`;
};

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

  // Store callbacks in refs to prevent reconnections when they change
  const onMessageRef = useRef(onMessage);
  const onOpenRef = useRef(onOpen);
  const onCloseRef = useRef(onClose);
  const onErrorRef = useRef(onError);

  // Update refs when callbacks change
  useEffect(() => {
    onMessageRef.current = onMessage;
    onOpenRef.current = onOpen;
    onCloseRef.current = onClose;
    onErrorRef.current = onError;
  }, [onMessage, onOpen, onClose, onError]);

  const connect = useCallback(() => {
    if (!endpoint) return;

    try {
      // Clean up existing connection
      if (ws.current) {
        ws.current.close();
      }

      const url = `${getWebSocketUrl()}${endpoint}`;
      ws.current = new WebSocket(url);

      ws.current.onopen = (event) => {
        setReadyState(WebSocket.OPEN);
        reconnectCount.current = 0;
        onOpenRef.current?.(event);
      };

      ws.current.onclose = (event) => {
        setReadyState(WebSocket.CLOSED);
        onCloseRef.current?.(event);

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
        onErrorRef.current?.(event);
        void antdMessage.error('WebSocket connection error');
      };

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setLastMessage(data);
          setMessage(data);
          onMessageRef.current?.(data);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
    }
  }, [endpoint, reconnect, reconnectInterval, reconnectAttempts]);

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
    if (!endpoint) return;

    // Connect to WebSocket
    connect();

    // Cleanup function
    return () => {
      // Clear any reconnect timeouts
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
        reconnectTimeout.current = null;
      }

      // Close WebSocket connection
      if (ws.current) {
        ws.current.close();
        ws.current = null;
      }

      setReadyState(WebSocket.CLOSED);
    };
  }, [endpoint, connect]); // Include connect in dependencies

  // Update ready state with proper cleanup
  useEffect(() => {
    // Only set up the interval if we have an endpoint
    if (!endpoint) return;

    const interval = setInterval(() => {
      if (ws.current) {
        setReadyState(ws.current.readyState);
      }
    }, 500); // Reduced frequency from 100ms to 500ms to reduce overhead

    return () => {
      clearInterval(interval);
    };
  }, [endpoint]); // Depend on endpoint to ensure cleanup when component unmounts

  return {
    sendMessage,
    lastMessage,
    readyState,
    message,
    connect,
    disconnect,
  };
}
