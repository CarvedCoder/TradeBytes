/**
 * WebSocket Client Manager.
 * 
 * Handles reconnection, authentication, and message routing.
 */

import { useAuthStore } from '@/stores/authStore';

export type WSMessageHandler = (data: Record<string, unknown>) => void;

interface WSConfig {
  url: string;
  onMessage?: WSMessageHandler;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: Event) => void;
  reconnect?: boolean;
  maxRetries?: number;
}

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private config: Required<WSConfig>;
  private retryCount = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(config: WSConfig) {
    this.config = {
      reconnect: true,
      maxRetries: 5,
      onMessage: () => {},
      onOpen: () => {},
      onClose: () => {},
      onError: () => {},
      ...config,
    };
  }

  connect(): void {
    const token = useAuthStore.getState().accessToken;
    if (!token) return;

    const separator = this.config.url.includes('?') ? '&' : '?';
    const wsUrl = `${this.config.url}${separator}token=${token}`;

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      this.retryCount = 0;
      this.config.onOpen();
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.config.onMessage(data);
      } catch {
        console.warn('Failed to parse WS message:', event.data);
      }
    };

    this.ws.onclose = () => {
      this.config.onClose();
      if (this.config.reconnect && this.retryCount < this.config.maxRetries) {
        this.scheduleReconnect();
      }
    };

    this.ws.onerror = (error) => {
      this.config.onError(error);
    };
  }

  send(data: Record<string, unknown>): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  disconnect(): void {
    this.config.reconnect = false;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.ws?.close();
    this.ws = null;
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  private scheduleReconnect(): void {
    const delay = Math.min(1000 * 2 ** this.retryCount, 30_000);
    this.retryCount++;
    this.reconnectTimer = setTimeout(() => this.connect(), delay);
  }
}

// Factory functions for specific WebSocket channels
export function createSimulationWS(sessionId: string, onMessage: WSMessageHandler) {
  return new WebSocketClient({
    url: `/ws/simulation/${sessionId}`,
    onMessage,
  });
}

export function createCommunityWS(channel: string, onMessage: WSMessageHandler) {
  return new WebSocketClient({
    url: `/ws/community/${channel}`,
    onMessage,
  });
}

export function createPriceWS(onMessage: WSMessageHandler) {
  return new WebSocketClient({
    url: '/ws/prices',
    onMessage,
  });
}

export function createNotificationWS(onMessage: WSMessageHandler) {
  return new WebSocketClient({
    url: '/ws/notifications',
    onMessage,
  });
}
