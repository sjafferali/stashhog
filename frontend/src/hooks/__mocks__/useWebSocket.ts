export const useWebSocket = () => ({
  sendMessage: jest.fn(),
  lastMessage: null,
  readyState: WebSocket.CLOSED,
  message: null,
  connect: jest.fn(),
  disconnect: jest.fn(),
});
