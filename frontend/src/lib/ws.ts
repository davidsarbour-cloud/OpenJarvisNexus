/**
 * Nexus9 — WebSocket client utilities.
 *
 * Auto-reconnect with exponential backoff. Re-emits replay history on connect.
 *
 * The URL defaults to the SAME ORIGIN as the page:
 *   - Page on http://localhost:8000  → ws://localhost:8000/ws/events
 *   - Page on http://localhost:5173  → ws://localhost:5173/ws/events
 *     (handled by Vite proxy `ws: true` to FastAPI :8000)
 */

export type WsEventLevel = 'info' | 'warn' | 'alert';

export interface WsEvent {
  ts?: string;
  level?: WsEventLevel | string;
  source?: string;
  msg?: string;
  [k: string]: unknown;
}

export type WsMessage =
  | { type: 'hello'; subscribers: number; history: WsEvent[] }
  | { type: 'event'; data: WsEvent }
  | { type: 'ping'; ts: number }
  | { type: 'error'; msg: string };

export interface WsClientOptions {
  /** Path on the same origin (default '/ws/events'). */
  path?: string;
  /** Initial reconnect delay in ms (default 1000). */
  reconnectDelayMs?: number;
  /** Cap on backoff (default 15000). */
  maxReconnectDelayMs?: number;
  /** Called on every incoming message. */
  onMessage?: (msg: WsMessage) => void;
  /** Called when socket transitions state. */
  onState?: (state: WsState) => void;
}

export type WsState = 'connecting' | 'open' | 'closed' | 'error';

export interface WsClient {
  close: () => void;
  state: () => WsState;
}

function buildWsUrl(path: string): string {
  if (typeof window === 'undefined') return path;
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${window.location.host}${path}`;
}

/**
 * Open a long-lived WebSocket with auto-reconnect.
 * Returns a handle with `close()` to stop reconnecting.
 */
export function connectWs(options: WsClientOptions = {}): WsClient {
  const {
    path = '/ws/events',
    reconnectDelayMs = 1000,
    maxReconnectDelayMs = 15000,
    onMessage,
    onState,
  } = options;

  let socket: WebSocket | null = null;
  let stopped = false;
  let attempt = 0;
  let state: WsState = 'connecting';

  const setState = (s: WsState) => {
    if (s !== state) {
      state = s;
      onState?.(s);
    }
  };

  const open = () => {
    if (stopped) return;
    setState('connecting');
    const url = buildWsUrl(path);
    try {
      socket = new WebSocket(url);
    } catch {
      scheduleReconnect();
      return;
    }

    socket.onopen = () => {
      attempt = 0;
      setState('open');
    };

    socket.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data) as WsMessage;
        onMessage?.(msg);
      } catch {
        /* ignore non-JSON frames */
      }
    };

    socket.onerror = () => {
      setState('error');
    };

    socket.onclose = () => {
      setState('closed');
      if (!stopped) scheduleReconnect();
    };
  };

  const scheduleReconnect = () => {
    attempt += 1;
    const delay = Math.min(
      reconnectDelayMs * Math.pow(1.6, attempt - 1),
      maxReconnectDelayMs,
    );
    setTimeout(open, delay);
  };

  open();

  return {
    close: () => {
      stopped = true;
      if (!socket) return;
      if (socket.readyState === WebSocket.CONNECTING) {
        // Avoid the "WebSocket is closed before the connection is established"
        // dev warning (triggered by React 18 StrictMode double-mount): wait for
        // the handshake to finish, then close cleanly.
        socket.addEventListener('open', () => socket?.close(), { once: true });
      } else {
        socket.close();
      }
    },
    state: () => state,
  };
}
