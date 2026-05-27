/**
 * Tests for useLiveMetric — verify the HTTP poll AND the optional
 * WebSocket push channel both update `data`, and that the HTTP poll
 * interval is correctly relaxed when a wsTopic is provided.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';
import type { WsEvent } from '../lib/ws';

// Capture the bus subscribe so tests can drive it directly. Listeners
// are reset before every test so cross-test bleed is impossible.
type Listener  = (e: WsEvent) => void;
type Predicate = (e: WsEvent) => boolean;
let activeListeners: Array<{ filter: Predicate; cb: Listener }> = [];

vi.mock('../lib/wsBus', () => ({
  wsBus: {
    subscribe: (filter: Predicate, cb: Listener) => {
      const entry = { filter, cb };
      activeListeners.push(entry);
      return () => { activeListeners = activeListeners.filter((e) => e !== entry); };
    },
    onState: () => () => undefined,
    state: () => 'open' as const,
  },
}));

function pushEvent(e: WsEvent) {
  for (const l of activeListeners) {
    if (l.filter(e)) l.cb(e);
  }
}

import { useLiveMetric } from './useLiveMetric';

describe('useLiveMetric', () => {
  beforeEach(() => { activeListeners = []; });
  afterEach(()  => { vi.restoreAllMocks(); });

  it('fetches once on mount and surfaces the result', async () => {
    const fetcher = vi.fn().mockResolvedValue({ ok: true });
    const { result } = renderHook(() => useLiveMetric(fetcher, { intervalMs: 0 }));
    await waitFor(() => expect(result.current.data).toEqual({ ok: true }));
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it('captures fetch errors without throwing', async () => {
    const fetcher = vi.fn().mockRejectedValue(new Error('boom'));
    const { result } = renderHook(() => useLiveMetric(fetcher, { intervalMs: 0 }));
    await waitFor(() => expect(result.current.error).toBe('boom'));
    expect(result.current.data).toBeNull();
  });

  it('replaces data when a matching WS event arrives', async () => {
    const fetcher = vi.fn().mockResolvedValue({ source: 'http' });
    const { result } = renderHook(() =>
      useLiveMetric(fetcher, { intervalMs: 0, wsTopic: 'snapshot/agents' }),
    );
    await waitFor(() => expect(result.current.data).toEqual({ source: 'http' }));

    act(() => {
      pushEvent({ source: 'snapshot/agents', msg: 'snapshot', data: { source: 'ws' } });
    });
    expect(result.current.data).toEqual({ source: 'ws' });
  });

  it('ignores WS events whose source does not match the topic', async () => {
    const fetcher = vi.fn().mockResolvedValue({ from: 'http' });
    const { result } = renderHook(() =>
      useLiveMetric(fetcher, { intervalMs: 0, wsTopic: 'snapshot/agents' }),
    );
    await waitFor(() => expect(result.current.data).toEqual({ from: 'http' }));

    act(() => {
      pushEvent({ source: 'snapshot/jobs', msg: 'snapshot', data: { from: 'wrong' } });
    });
    expect(result.current.data).toEqual({ from: 'http' });
  });

  it('does not register any WS listener when wsTopic is omitted', () => {
    const fetcher = vi.fn().mockResolvedValue({});
    renderHook(() => useLiveMetric(fetcher, { intervalMs: 0 }));
    expect(activeListeners).toHaveLength(0);
  });

  it('registers exactly one WS listener when wsTopic is set', async () => {
    const fetcher = vi.fn().mockResolvedValue({});
    renderHook(() => useLiveMetric(fetcher, { intervalMs: 0, wsTopic: 'snapshot/x' }));
    await waitFor(() => expect(activeListeners).toHaveLength(1));
  });

  it('relaxes the HTTP poll to >= 60s when wsTopic is set', async () => {
    // Use shouldAdvanceTime so waitFor still polls (its internal setTimeout
    // is dispatched by the same fake clock as `vi.advanceTimersByTime`).
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      const fetcher = vi.fn().mockResolvedValue({ v: 0 });
      renderHook(() => useLiveMetric(fetcher, { intervalMs: 2000, wsTopic: 'snapshot/x' }));
      await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1));
      // Run 5 seconds — at the original 2000ms cadence the fetcher would
      // have been called twice more. With wsTopic, the effective poll
      // interval is floored at 60s so no additional calls fire.
      act(() => { vi.advanceTimersByTime(5000); });
      expect(fetcher).toHaveBeenCalledTimes(1);
    } finally {
      vi.useRealTimers();
    }
  });

  it('unsubscribes from the bus on unmount', async () => {
    const fetcher = vi.fn().mockResolvedValue({});
    const { unmount } = renderHook(() =>
      useLiveMetric(fetcher, { intervalMs: 0, wsTopic: 'snapshot/x' }),
    );
    await waitFor(() => expect(activeListeners).toHaveLength(1));
    unmount();
    expect(activeListeners).toHaveLength(0);
  });
});
