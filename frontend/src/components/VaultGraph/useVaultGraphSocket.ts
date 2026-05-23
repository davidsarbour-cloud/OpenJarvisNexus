import { useCallback, useEffect, useRef, useState } from 'react';
import { useVaultGraph, type VNode, type VLink } from '../../stores/vaultGraph';

/**
 * Nexus9 — useVaultGraphSocket
 *
 * Hook React qui se connecte au sidecar `services/vault_graph/`
 * (par defaut ws://localhost:8084) et **ecrit** les snapshots de graph
 * dans le store partage `useVaultGraph` (Zustand).
 *
 * Le hook lui-meme retourne :
 *   - state           : etat du WebSocket
 *   - error           : message d'erreur eventuel
 *   - requestRefresh  : envoie `vault:refresh` au serveur (trigger manuel)
 *
 * Pour lire les nodes/links, importer `useVaultGraph` depuis le store.
 *
 * Reconnect exponentiel (cap 15s), StrictMode-safe (le close attend l'open
 * avant de se declencher si le socket est encore en CONNECTING).
 */

export type VaultSocketState = 'connecting' | 'open' | 'closed' | 'error';

interface ServerMessage {
  type: 'vault:graph' | 'vault:refreshing';
  payload: unknown;
}

interface GraphPayload {
  nodes: VNode[];
  links: VLink[];
  stats?: { files: number; links: number; tags: number; orphans: number };
}

interface UseVaultGraphSocketOptions {
  /** Override URL. Default ws://localhost:8084. */
  url?: string;
  /** Active/desactive la connexion. */
  enabled?: boolean;
}

export interface UseVaultGraphSocketResult {
  state: VaultSocketState;
  connected: boolean;
  error: string | null;
  requestRefresh: () => void;
}

const DEFAULT_URL = 'ws://localhost:8084';
const INITIAL_DELAY_MS = 1000;
const MAX_DELAY_MS = 15_000;

export function useVaultGraphSocket(
  options: UseVaultGraphSocketOptions = {},
): UseVaultGraphSocketResult {
  const { url = DEFAULT_URL, enabled = true } = options;
  const [state, setState] = useState<VaultSocketState>('connecting');
  const [error, setError] = useState<string | null>(null);
  const socketRef = useRef<WebSocket | null>(null);

  const setGraph = useVaultGraph((s) => s.setGraph);
  const setRefreshing = useVaultGraph((s) => s.setRefreshing);

  useEffect(() => {
    if (!enabled) {
      setState('closed');
      return;
    }
    let stopped = false;
    let attempt = 0;
    let reconnectTimer: number | null = null;
    let socket: WebSocket | null = null;

    const open = () => {
      if (stopped) return;
      setState('connecting');
      try {
        socket = new WebSocket(url);
        socketRef.current = socket;
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
        scheduleReconnect();
        return;
      }

      socket.onopen = () => {
        attempt = 0;
        setError(null);
        setState('open');
      };

      socket.onmessage = (e) => {
        let msg: ServerMessage;
        try {
          msg = JSON.parse(e.data) as ServerMessage;
        } catch {
          return;
        }
        if (msg.type === 'vault:graph') {
          const p = msg.payload as GraphPayload;
          if (p && Array.isArray(p.nodes) && Array.isArray(p.links)) {
            setGraph(p.nodes, p.links);
          }
        } else if (msg.type === 'vault:refreshing') {
          setRefreshing(Boolean(msg.payload));
        }
      };

      socket.onerror = () => setState('error');

      socket.onclose = () => {
        setState('closed');
        if (!stopped) scheduleReconnect();
      };
    };

    const scheduleReconnect = () => {
      attempt += 1;
      const delay = Math.min(
        INITIAL_DELAY_MS * Math.pow(1.6, attempt - 1),
        MAX_DELAY_MS,
      );
      reconnectTimer = window.setTimeout(open, delay);
    };

    open();

    return () => {
      stopped = true;
      if (reconnectTimer !== null) window.clearTimeout(reconnectTimer);
      if (!socket) return;
      if (socket.readyState === WebSocket.CONNECTING) {
        const s = socket;
        s.addEventListener('open', () => s.close(), { once: true });
      } else {
        socket.close();
      }
      socketRef.current = null;
    };
  }, [url, enabled, setGraph, setRefreshing]);

  const requestRefresh = useCallback(() => {
    const s = socketRef.current;
    if (s && s.readyState === WebSocket.OPEN) {
      try {
        s.send(JSON.stringify({ type: 'vault:refresh' }));
      } catch {
        /* ignore */
      }
    }
  }, []);

  return { state, connected: state === 'open', error, requestRefresh };
}
