export interface WebSocketOptions {
  reconnect?: boolean;
  reconnectInterval?: number;
  reconnectAttempts?: number;
  onOpen?: (event: Event) => void;
  onClose?: (event: CloseEvent) => void;
  onError?: (event: Event) => void;
  onMessage?: (event: MessageEvent) => void;
}

export const useWebSocket = (_url: string, _options?: WebSocketOptions) => {
  return {
    sendMessage: jest.fn(),
    lastMessage: null,
    readyState: 1, // OPEN state
    connect: jest.fn(),
    disconnect: jest.fn(),
  };
};
