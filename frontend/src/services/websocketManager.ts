/**
 * WebSocket Manager - Singleton pattern to ensure only one connection per endpoint
 * This prevents multiple components from creating duplicate connections
 */

type Listener = (data: unknown) => void;

interface WebSocketConnection {
  ws: WebSocket;
  listeners: Set<Listener>;
  reconnectTimeout?: NodeJS.Timeout;
  reconnectCount: number;
}

class WebSocketManager {
  private connections: Map<string, WebSocketConnection> = new Map();
  private reconnectInterval = 3000;
  private reconnectAttempts = 5;

  private getWebSocketUrl(): string {
    if (import.meta.env.VITE_WS_URL) {
      return import.meta.env.VITE_WS_URL;
    }
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    return `${protocol}//${host}`;
  }

  subscribe(endpoint: string, listener: Listener): () => void {
    if (!endpoint) {
      return () => {};
    }

    let connection = this.connections.get(endpoint);

    if (!connection) {
      // Create new connection
      const url = `${this.getWebSocketUrl()}${endpoint}`;
      const ws = new WebSocket(url);

      connection = {
        ws,
        listeners: new Set([listener]),
        reconnectCount: 0,
      };

      this.connections.set(endpoint, connection);
      this.setupWebSocket(endpoint, connection);
    } else {
      // Add listener to existing connection
      connection.listeners.add(listener);
    }

    // Return unsubscribe function
    return () => {
      const conn = this.connections.get(endpoint);
      if (conn) {
        conn.listeners.delete(listener);

        // If no more listeners, close connection
        if (conn.listeners.size === 0) {
          this.closeConnection(endpoint);
        }
      }
    };
  }

  private setupWebSocket(
    endpoint: string,
    connection: WebSocketConnection
  ): void {
    const { ws } = connection;

    ws.onopen = () => {
      console.log(`WebSocket connected: ${endpoint}`);
      connection.reconnectCount = 0;
    };

    ws.onclose = (event) => {
      console.log(`WebSocket closed: ${endpoint}`);

      // Only reconnect if there are still listeners
      if (
        connection.listeners.size > 0 &&
        connection.reconnectCount < this.reconnectAttempts &&
        !event.wasClean
      ) {
        connection.reconnectTimeout = setTimeout(() => {
          this.reconnect(endpoint);
        }, this.reconnectInterval);
      } else {
        // Clean up connection
        this.connections.delete(endpoint);
      }
    };

    ws.onerror = (error) => {
      console.error(`WebSocket error on ${endpoint}:`, error);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        // Notify all listeners
        connection.listeners.forEach((listener) => {
          try {
            listener(data);
          } catch (err) {
            console.error('Error in WebSocket listener:', err);
          }
        });
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };
  }

  private reconnect(endpoint: string): void {
    const connection = this.connections.get(endpoint);
    if (!connection || connection.listeners.size === 0) {
      return;
    }

    connection.reconnectCount++;
    console.log(
      `Reconnecting WebSocket ${endpoint} (attempt ${connection.reconnectCount})`
    );

    const url = `${this.getWebSocketUrl()}${endpoint}`;
    const ws = new WebSocket(url);
    connection.ws = ws;
    this.setupWebSocket(endpoint, connection);
  }

  private closeConnection(endpoint: string): void {
    const connection = this.connections.get(endpoint);
    if (connection) {
      if (connection.reconnectTimeout) {
        clearTimeout(connection.reconnectTimeout);
      }
      if (
        connection.ws.readyState === WebSocket.OPEN ||
        connection.ws.readyState === WebSocket.CONNECTING
      ) {
        connection.ws.close();
      }
      this.connections.delete(endpoint);
    }
  }

  getReadyState(endpoint: string): number {
    const connection = this.connections.get(endpoint);
    return connection ? connection.ws.readyState : WebSocket.CLOSED;
  }

  send(endpoint: string, data: Record<string, unknown>): void {
    const connection = this.connections.get(endpoint);
    if (connection && connection.ws.readyState === WebSocket.OPEN) {
      connection.ws.send(JSON.stringify(data));
    } else {
      console.warn(`WebSocket not connected: ${endpoint}`);
    }
  }
}

// Export singleton instance
export const wsManager = new WebSocketManager();
