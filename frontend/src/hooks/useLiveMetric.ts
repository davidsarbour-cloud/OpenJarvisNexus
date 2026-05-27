import { useEffect, useRef, useState } from 'react';
import { wsBus } from '../lib/wsBus';

export interface LiveMetricState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  /** ms since last successful fetch */
  age: number;
}

export interface LiveMetricOptions {
  /** Poll interval in ms (default 5000). Set 0 to fetch once. */
  intervalMs?: number;
  /** Pause polling while tab hidden. Default true. */
  pauseWhenHidden?: boolean;
  /**
   * Optional WebSocket topic to listen for. When provided, the hook
   * subscribes to the shared wsBus and replaces `data` whenever an
   * event whose `source` matches the topic arrives. The event must
   * carry the payload under a `data` key. The HTTP poll continues as
   * a fallback but at a relaxed cadence (at least 60s) because the
   * WS push is the primary update channel; the poll just covers the
   * "WS disconnected for a while" gap and the initial paint.
   */
  wsTopic?: string;
}

/**
 * Generic polling hook with cleanup and staleness tracking.
 *
 *   const { data, error, loading } = useLiveMetric(fetchHealth, { intervalMs: 4000 });
 *
 * The fetcher is called once on mount, then every `intervalMs` ms.
 * Errors are captured and exposed without crashing the component.
 */
export function useLiveMetric<T>(
  fetcher: () => Promise<T>,
  options: LiveMetricOptions = {},
): LiveMetricState<T> {
  const { intervalMs = 5000, pauseWhenHidden = true, wsTopic } = options;
  // When a WS topic is provided, the HTTP poll is a safety net only —
  // relax it to at least 60s so we don't double-pay for data we are
  // already getting pushed in real time.
  const effectiveInterval = wsTopic ? Math.max(intervalMs, 60_000) : intervalMs;

  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [age, setAge] = useState(0);
  const lastOkRef = useRef<number>(0);
  const cancelledRef = useRef(false);
  const fetcherRef = useRef(fetcher);
  // Keep a latest-value ref so the polling effect always calls the
  // current fetcher closure without restarting on every render.
  useEffect(() => { fetcherRef.current = fetcher; });

  useEffect(() => {
    cancelledRef.current = false;

    const run = async () => {
      try {
        const res = await fetcherRef.current();
        if (cancelledRef.current) return;
        setData(res);
        setError(null);
        lastOkRef.current = Date.now();
      } catch (e) {
        if (cancelledRef.current) return;
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        if (!cancelledRef.current) setLoading(false);
      }
    };

    run();

    // WebSocket subscription — when a matching snapshot arrives, replace
    // `data` from the event payload without making an HTTP call. The
    // backend tags snapshots with `source: "snapshot/<topic>"` so the
    // filter is a strict equality match.
    let unsubWs: (() => void) | null = null;
    if (wsTopic) {
      unsubWs = wsBus.subscribe(
        (e) => e.source === wsTopic,
        (e) => {
          const payload = (e as { data?: unknown }).data;
          if (cancelledRef.current || payload === undefined) return;
          setData(payload as T);
          setError(null);
          setLoading(false);
          lastOkRef.current = Date.now();
        },
      );
    }

    if (effectiveInterval <= 0) {
      return () => {
        cancelledRef.current = true;
        unsubWs?.();
      };
    }

    const poll = setInterval(() => {
      if (pauseWhenHidden && document.hidden) return;
      run();
    }, effectiveInterval);

    const ageTick = setInterval(() => {
      if (lastOkRef.current) setAge(Date.now() - lastOkRef.current);
    }, 1000);

    return () => {
      cancelledRef.current = true;
      clearInterval(poll);
      clearInterval(ageTick);
      unsubWs?.();
    };
  }, [effectiveInterval, pauseWhenHidden, wsTopic]);

  return { data, error, loading, age };
}
