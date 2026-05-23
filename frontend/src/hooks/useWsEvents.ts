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
 * `state` reflects the underlying WebSocket lifecycle ('connecting' | 'open' | 'closed' | 'error').
 */
export function useWsEvents(maxEvents: number = 50): UseWsEventsResult {
  const [events, setEvents] = useState<WsEvent[]>([]);
  const [state, setState] = useState<WsState>('connecting');
  const maxRef = useRef(maxEvents);
  maxRef.current = maxEvents;

  useEffect(() => {
    const append = (e: WsEvent) => {
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
          const hist = [...msg.history].reverse();
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
