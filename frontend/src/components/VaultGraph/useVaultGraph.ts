import { useEffect, useRef, useState } from 'react';

/**
 * Nexus9 — useVaultGraph
 *
 * Hook React qui se connecte au sidecar `services/vault_graph/`
 * (par defaut ws://localhost:8084) et expose le graphe vivant.
 *
 * - Reconnexion automatique avec backoff exponentiel (cap 15s).
 * - StrictMode-safe : on attend `OPEN` avant de close pour eviter
 *   le warning "WebSocket is closed before the connection is established"
 *   (meme pattern que `lib/ws.ts`).
 */

export interface VaultGraphNode {
  id: string;
  group?: string;
}

export interface VaultGraphLink {
  source: string;
  target: string;
  type?: 'wikilink' | 'tag';
}

export interface VaultGraphData {
  nodes: VaultGraphNode[];
  links: VaultGraphLink[];
  stats?: { files: number; links: number; tags: number; orphans: number };
}

export type VaultGraphState = 'connecting' | 'open' | 'closed' | 'error';

interface ServerMessage {
  type: 'vault:graph' | 'vault:refreshing';
  payload: VaultGraphData | boolean;
}

interface UseVaultGraphOptions {
  /** Override de l'URL WebSocket. Default ws://localhost:8084. */
  url?: string;
  /** Active/desactive la connexion (utile pour ne pas ouvrir tant que l'overlay est ferme). */
  enabled?: boolean;
}

export interface UseVaultGraphResult {
  graph: VaultGraphData | null;
  state: VaultGraphState;
  connected: boolean;
  error: string | null;
}

const DEFAULT_URL = 'ws://localhost:8084';
const INITIAL_DELAY_MS = 1000;
const MAX_DELAY_MS = 15_000;

export function useVaultGraph(options: UseVaultGraphOptions = {}): UseVaultGraphResult {
  const { url = DEFAULT_URL, enabled = true } = options;
  const [graph, setGraph] = useState<VaultGraphData | null>(null);
  const [state, setState] = useState<VaultGraphState>('connecting');
  const [error, setError] = useState<string | null>(null);

  const stoppedRef = useRef(false);
  const attemptRef = useRef(0);

  useEffect(() => {
    if (!enabled) {
      setState('closed');
      return;
    }
    stoppedRef.current = false;
    attemptRef.current = 0;
    let socket: WebSocket | null = null;
    let reconnectTimer: number | null = null;

    const open = () => {
      if (stoppedRef.current) return;
      setState('connecting');
      try {
        socket = new WebSocket(url);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
        scheduleReconnect();
        return;
      }

      socket.onopen = () => {
        attemptRef.current = 0;
        setError(null);
        setState('open');
      };

      socket.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data) as ServerMessage;
          if (msg.type === 'vault:graph') {
            setGraph(msg.payload as VaultGraphData);
          }
        } catch {
          /* ignore frames non-JSON */
        }
      };

      socket.onerror = (e) => {
        const msg = (e as ErrorEvent).message || 'WebSocket error';
        setError(msg);
        setState('error');
      };

      socket.onclose = () => {
        setState('closed');
        if (!stoppedRef.current) scheduleReconnect();
      };
    };

    const scheduleReconnect = () => {
      attemptRef.current += 1;
      const delay = Math.min(
        INITIAL_DELAY_MS * Math.pow(1.6, attemptRef.current - 1),
        MAX_DELAY_MS,
      );
      reconnectTimer = window.setTimeout(open, delay);
    };

    open();

    return () => {
      stoppedRef.current = true;
      if (reconnectTimer !== null) window.clearTimeout(reconnectTimer);
      if (!socket) return;
      if (socket.readyState === WebSocket.CONNECTING) {
        // StrictMode-safe : attendre l'open avant de close.
        const s = socket;
        s.addEventListener('open', () => s.close(), { once: true });
      } else {
        socket.close();
      }
    };
  }, [url, enabled]);

  return { graph, state, connected: state === 'open', error };
}
