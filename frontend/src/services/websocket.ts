import useWebSocket from 'react-use-websocket'
import { useCallback } from 'react'
import useAppStore from '@/store'

export interface WebSocketMessage {
  type: 'job_progress' | 'job_complete' | 'job_failed' | 'notification' | 'sync_update'
  data: any
}

const WS_URL = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`

export const useWebSocketClient = () => {
  const { showNotification } = useAppStore()

  const onMessage = useCallback((event: MessageEvent) => {
    try {
      const message: WebSocketMessage = JSON.parse(event.data)
      
      switch (message.type) {
        case 'job_progress':
          // Handle job progress updates
          // You might want to update a job store here
          console.log('Job progress:', message.data)
          break
          
        case 'job_complete':
          showNotification({
            type: 'success',
            content: `Job ${message.data.name} completed successfully`,
          })
          break
          
        case 'job_failed':
          showNotification({
            type: 'error',
            content: `Job ${message.data.name} failed: ${message.data.error}`,
          })
          break
          
        case 'notification':
          showNotification({
            type: message.data.type || 'info',
            content: message.data.message,
          })
          break
          
        case 'sync_update':
          // Handle sync status updates
          console.log('Sync update:', message.data)
          break
          
        default:
          console.warn('Unknown WebSocket message type:', message.type)
      }
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error)
    }
  }, [showNotification])

  const {
    sendMessage,
    lastMessage,
    readyState,
    getWebSocket,
  } = useWebSocket(WS_URL, {
    onOpen: () => console.log('WebSocket connected'),
    onClose: () => console.log('WebSocket disconnected'),
    onError: (error) => console.error('WebSocket error:', error),
    onMessage,
    shouldReconnect: () => true,
    reconnectAttempts: 10,
    reconnectInterval: 3000,
  })

  return {
    sendMessage,
    lastMessage,
    readyState,
    getWebSocket,
  }
}

// WebSocket manager for use outside of React components
class WebSocketManager {
  private ws: WebSocket | null = null
  private reconnectTimeout: NodeJS.Timeout | null = null
  private messageHandlers: Map<string, (data: any) => void> = new Map()

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return
    }

    this.ws = new WebSocket(WS_URL)

    this.ws.onopen = () => {
      console.log('WebSocket connected')
      if (this.reconnectTimeout) {
        clearTimeout(this.reconnectTimeout)
        this.reconnectTimeout = null
      }
    }

    this.ws.onclose = () => {
      console.log('WebSocket disconnected')
      this.scheduleReconnect()
    }

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    this.ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data)
        const handler = this.messageHandlers.get(message.type)
        if (handler) {
          handler(message.data)
        }
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error)
      }
    }
  }

  disconnect() {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout)
      this.reconnectTimeout = null
    }
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  private scheduleReconnect() {
    if (this.reconnectTimeout) {
      return
    }
    this.reconnectTimeout = setTimeout(() => {
      this.reconnectTimeout = null
      this.connect()
    }, 3000)
  }

  send(message: any) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket is not connected')
    }
  }

  on(type: string, handler: (data: any) => void) {
    this.messageHandlers.set(type, handler)
  }

  off(type: string) {
    this.messageHandlers.delete(type)
  }
}

export const wsManager = new WebSocketManager()
export default wsManager