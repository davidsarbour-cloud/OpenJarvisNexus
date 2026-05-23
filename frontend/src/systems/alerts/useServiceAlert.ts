/**
 * Nexus9 — useServiceAlert
 *
 * Convenience hook: cards call this when their poll resolves so they push
 * an alert only when the status *changes* to a problem state. Avoids spam.
 *
 *   useServiceAlert('ollama', error ? 'down' : 'live', 'Ollama unreachable');
 */
import { useEffect, useRef } from 'react';
import { useNexusStore } from '../nexusStore';
import type { ServiceStatus } from '../serviceRegistry';
import type { AlertLevel } from './types';

const LEVEL_FROM_STATUS: Partial<Record<ServiceStatus, AlertLevel>> = {
  warn: 'warning',
  down: 'critical',
};

export function useServiceAlert(
  source: string,
  status: ServiceStatus,
  title: string,
  detail?: string,
): void {
  const pushAlert = useNexusStore((s) => s.pushAlert);
  const setStatus = useNexusStore((s) => s.setServiceStatus);
  const prev = useRef<ServiceStatus | null>(null);

  useEffect(() => {
    setStatus(source, status);
    const level = LEVEL_FROM_STATUS[status];
    // Only push when *transitioning* into a problem state — not on every poll.
    if (level && prev.current !== status) {
      pushAlert({ level, source, title, detail });
    }
    prev.current = status;
  }, [source, status, title, detail, pushAlert, setStatus]);
}
