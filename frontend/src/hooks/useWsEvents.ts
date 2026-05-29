import { useEffect, useRef, useState } from 'react';
import { connectWs, type WsEvent, type WsState } from '../lib/ws';

export interface UseWsEventsResult {
  events: WsEvent[];
  state: WsState;
  connected: boolean;
}

/**
 * React hook : connects to `/ws/events` and accumulates incoming events.
 *
 * The hook keeps at most `maxEvents` items (FIFO).
 * `filter`, when given, is applied BEFORE buffering so excluded events never
 * occupy a slot. This matters because high-frequency plumbing events (the
 * `snapshot/*` card-refresh broadcasts, fired every 2-12s) would otherwise
 * flood the FIFO and evict real user-facing events within seconds.
 * `state` reflects the underlying WebSocket lifecycle ('connecting' | 'open' | 'closed' | 'error').
 */
export function useWsEvents(
  maxEvents: number = 50,
  filter?: (e: WsEvent) => boolean,
): UseWsEventsResult {
  const [events, setEvents] = useState<WsEvent[]>([]);
  const [state, setState] = useState<WsState>('connecting');
  const maxRef = useRef(maxEvents);
  const filterRef = useRef(filter);
  // Sync refs via effect so we don't mutate during render (react-hooks/refs).
  useEffect(() => { maxRef.current = maxEvents; });
  useEffect(() => { filterRef.current = filter; });

  useEffect(() => {
    const keep = (e: WsEvent) => (filterRef.current ? filterRef.current(e) : true);

    const append = (e: WsEvent) => {
      if (!keep(e)) return;
      setEvents((prev) => {
        const next = [e, ...prev];
        return next.length > maxRef.current ? next.slice(0, maxRef.current) : next;
      });
    };

    const client = connectWs({
      onState: setState,
      onMessage: (msg) => {
        if (msg.type === 'hello') {
          // Replay history (most recent first)
          const hist = [...msg.history].reverse().filter(keep);
          setEvents(hist.slice(0, maxRef.current));
        } else if (msg.type === 'event') {
          append(msg.data);
        }
        // 'ping' and 'error' are ignored at this layer
      },
    });

    return () => {
      client.close();
    };
  }, []);

  return { events, state, connected: state === 'open' };
}
