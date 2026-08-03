import type { PipelineUpdate } from '../types';

type MessageHandler = (message: PipelineUpdate) => void;
type ConnectionHandler = () => void;

interface WebSocketClientOptions {
  onMessage: MessageHandler;
  onConnect?: ConnectionHandler;
  onDisconnect?: () => void;
  baseUrl?: string;
}

export class PipelineWebSocket {
  private ws: WebSocket | null = null;
  private url: string;
  private onMessage: MessageHandler;
  private onConnect?: ConnectionHandler;
  private onDisconnect?: () => void;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 3;
  private reconnectDelay = 1000; // Start at 1s, exponential backoff
  private heartbeatInterval: ReturnType<typeof setInterval> | null = null;
  private heartbeatTimeout: ReturnType<typeof setTimeout> | null = null;
  private sequenceNumber = 0;

  constructor(options: WebSocketClientOptions) {
    this.onMessage = options.onMessage;
    this.onConnect = options.onConnect;
    this.onDisconnect = options.onDisconnect;

    const base = options.baseUrl || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    // Strip http/https prefix for WebSocket protocol
    const wsProtocol = base.startsWith('https') ? 'wss' : 'ws';
    const host = base.replace(/^https?:\/\//, '');
    this.url = `${wsProtocol}://${host}/ws/`;
  }

  connect(sessionId: string): void {
    if (this.ws && (this.ws.readyState === WebSocket.CONNECTING || this.ws.readyState === WebSocket.OPEN)) {
      return; // Already connecting or connected
    }

    try {
      this.ws = new WebSocket(`${this.url}/${sessionId}`);

      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000; // Reset delay on successful connect
        this.onConnect?.();
        this.startHeartbeat();
      };

      this.ws.onmessage = (event: MessageEvent) => {
        try {
          const message: PipelineUpdate = JSON.parse(event.data);
          // Validate sequence number for ordering
          if (message.timestamp) {
            this.onMessage(message);
          }
        } catch (error) {
          console.error('[PipelineWebSocket] Failed to parse message:', error);
        }
      };

      this.ws.onerror = (error: Event) => {
        console.error('[PipelineWebSocket] WebSocket error:', error);
      };

      this.ws.onclose = (event: CloseEvent) => {
        this.stopHeartbeat();
        if (!event.wasClean && this.reconnectAttempts < this.maxReconnectAttempts) {
          // Attempt reconnection with exponential backoff
          setTimeout(() => {
            this.reconnectAttempts++;
            this.connect(sessionId);
          }, this.reconnectDelay);
          this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000); // Cap at 30s
        } else {
          this.onDisconnect?.();
        }
      };
    } catch (error) {
      console.error('[PipelineWebSocket] Failed to create WebSocket:', error);
    }
  }

  disconnect(): void {
    this.stopHeartbeat();
    if (this.ws) {
      // Prevent auto-reconnect by resetting counter
      this.reconnectAttempts = this.maxReconnectAttempts;
      this.ws.close(1000, 'Client disconnecting');
      this.ws = null;
    }
  }

  subscribeToPhase(phase: string): void {
    this.send({ type: 'subscribe', phase });
  }

  unsubscribeFromPhase(phase: string): void {
    this.send({ type: 'unsubscribe', phase });
  }

  private send(data: Record<string, unknown>): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;

    const message = {
      ...data,
      _seq: this.sequenceNumber++,
      _ts: Date.now(),
    };

    try {
      this.ws.send(JSON.stringify(message));
    } catch (error) {
      console.error('[PipelineWebSocket] Failed to send message:', error);
    }
  }

  private startHeartbeat(): void {
    this.heartbeatInterval = setInterval(() => {
      // Send ping
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }));

        // Check for pong response
        this.heartbeatTimeout = setTimeout(() => {
          console.warn('[PipelineWebSocket] Heartbeat timeout — connection may be stale');
        }, 5000);
      }
    }, 30000); // Every 30 seconds
  }

  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
    if (this.heartbeatTimeout) {
      clearTimeout(this.heartbeatTimeout);
      this.heartbeatTimeout = null;
    }
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  getReadyState(): number | null {
    return this.ws?.readyState ?? null;
  }
}

export default PipelineWebSocket;
