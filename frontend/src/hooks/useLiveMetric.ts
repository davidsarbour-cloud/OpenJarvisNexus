import { useEffect, useRef, useState } from 'react';

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
  const { intervalMs = 5000, pauseWhenHidden = true } = options;

  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [age, setAge] = useState(0);
  const lastOkRef = useRef<number>(0);
  const cancelledRef = useRef(false);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

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

    if (intervalMs <= 0) {
      return () => {
        cancelledRef.current = true;
      };
    }

    const poll = setInterval(() => {
      if (pauseWhenHidden && document.hidden) return;
      run();
    }, intervalMs);

    const ageTick = setInterval(() => {
      if (lastOkRef.current) setAge(Date.now() - lastOkRef.current);
    }, 1000);

    return () => {
      cancelledRef.current = true;
      clearInterval(poll);
      clearInterval(ageTick);
    };
  }, [intervalMs, pauseWhenHidden]);

  return { data, error, loading, age };
}
