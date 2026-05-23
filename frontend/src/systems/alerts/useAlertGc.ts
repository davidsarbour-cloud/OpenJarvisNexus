/**
 * Nexus9 — Alert garbage collector.
 *
 * Mounted ONCE near the root (App.tsx or HudLayout). Prunes acknowledged
 * alerts older than the TTL defined in nexusStore.pruneExpiredAlerts.
 */
import { useEffect } from 'react';
import { useNexusStore } from '../nexusStore';

export function useAlertGc(intervalMs = 30_000): void {
  const prune = useNexusStore((s) => s.pruneExpiredAlerts);
  useEffect(() => {
    const t = setInterval(prune, intervalMs);
    return () => clearInterval(t);
  }, [prune, intervalMs]);
}
