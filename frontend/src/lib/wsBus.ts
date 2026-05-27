/**
 * Nexus9 — Shared WebSocket bus.
 *
 * Singleton wrapper around `/ws/events`. Every subscriber multiplexes
 * over a single underlying socket instead of opening its own connection.
 * This is what makes WebSocket consolidation worth it: 10 cards listening
 * for snapshots = 10 cheap in-memory subscriptions + 1 socket, not 10
 * sockets.
 *
 * Usage:
 *   const unsub = wsBus.subscribe(
 *     (e) => e.source === 'snapshot/agents',
 *     (e) => setData(e.data),
 *   );
 *   // ...
 *   unsub();
 *
 * The bus stays alive for the lifetime of the page; we don't reference-
 * count subscribers because the cost of a quiet idle WS is negligible
 * and reconnect-flapping when one component unmounts would be worse.
 */
import { connectWs, type WsClient, type WsEvent, type WsState } from './ws';

type Predicate = (event: WsEvent) => boolean;
type Listener  = (event: WsEvent) => void;
type StateListener = (state: WsState) => void;

interface Subscription {
  filter:   Predicate;
  callback: Listener;
}

let client: WsClient | null = null;
let currentState: WsState = 'connecting';
const subs:        Set<Subscription>   = new Set();
const stateSubs:   Set<StateListener>  = new Set();

function ensureConnected(): void {
  if (client) return;
  client = connectWs({
    onState: (s) => {
      currentState = s;
      for (const l of stateSubs) l(s);
    },
    onMessage: (msg) => {
      if (msg.type === 'hello') {
        // Replay history so late subscribers get the latest snapshot
        // straight away (saves them waiting for the next push cycle).
        for (const e of msg.history) {
          for (const sub of subs) {
            if (sub.filter(e)) sub.callback(e);
          }
        }
      } else if (msg.type === 'event') {
        for (const sub of subs) {
          if (sub.filter(msg.data)) sub.callback(msg.data);
        }
      }
    },
  });
}

export const wsBus = {
  /**
   * Subscribe to events matching `filter`. Returns an unsubscribe.
   * Callback is invoked synchronously for every matching event,
   * including any in the replay history at connect time.
   */
  subscribe(filter: Predicate, callback: Listener): () => void {
    ensureConnected();
    const sub: Subscription = { filter, callback };
    subs.add(sub);
    return () => { subs.delete(sub); };
  },

  /** Listen to underlying WS state ('connecting' | 'open' | 'closed' | 'error'). */
  onState(listener: StateListener): () => void {
    ensureConnected();
    stateSubs.add(listener);
    // Fire current state immediately so the listener doesn't have to
    // wait for the next transition to know where we are.
    listener(currentState);
    return () => { stateSubs.delete(listener); };
  },

  state(): WsState { return currentState; },
};
