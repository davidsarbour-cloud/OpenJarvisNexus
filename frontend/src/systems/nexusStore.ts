/**
 * Nexus9 — Cross-module shared state (Phase 4 · Step 7)
 *
 * SEPARATE from the existing `lib/store.ts` (which is the chat / settings
 * app store) — this one is dedicated to the orbital/command-center sync
 * layer, alerts and live service status.
 */
import { useMemo } from 'react';
import { create } from 'zustand';
import type { ServiceStatus } from './serviceRegistry';
import type { Alert } from './alerts/types';

interface NexusState {
  // ── Selection / focus ───────────────────────────────────
  focusedServiceId: string | null;
  setFocusedService: (id: string | null) => void;

  selectedPlanet: string | null;
  setSelectedPlanet: (id: string | null) => void;

  // ── Service status snapshot ─────────────────────────────
  serviceStatus: Record<string, ServiceStatus>;
  setServiceStatus: (id: string, status: ServiceStatus) => void;

  // ── Alerts ──────────────────────────────────────────────
  alerts: Alert[];
  pushAlert: (alert: Omit<Alert, 'id' | 'createdAt' | 'acknowledged'>) => void;
  acknowledgeAlert: (id: string) => void;
  clearAlerts: () => void;
  pruneExpiredAlerts: () => void;
}

let _alertCounter = 0;
const nextAlertId = () => `a-${Date.now()}-${++_alertCounter}`;

export const useNexusStore = create<NexusState>((set, get) => ({
  focusedServiceId: null,
  setFocusedService: (id) => {
    set({ focusedServiceId: id });
    if (id) {
      import('./serviceRegistry').then(({ getService }) => {
        const svc = getService(id);
        if (svc?.orbitalRelation) {
          set({ selectedPlanet: svc.orbitalRelation });
        }
      });
    }
  },

  selectedPlanet: null,
  setSelectedPlanet: (id) => set({ selectedPlanet: id }),

  serviceStatus: {},
  setServiceStatus: (id, status) =>
    set((s) => {
      if (s.serviceStatus[id] === status) return s;
      return { serviceStatus: { ...s.serviceStatus, [id]: status } };
    }),

  alerts: [],
  pushAlert: (a) => {
    const alert: Alert = {
      ...a,
      id: nextAlertId(),
      createdAt: Date.now(),
      acknowledged: false,
    };
    set((s) => ({ alerts: [alert, ...s.alerts].slice(0, 100) }));
  },
  acknowledgeAlert: (id) =>
    set((s) => ({
      alerts: s.alerts.map((a) =>
        a.id === id ? { ...a, acknowledged: true } : a,
      ),
    })),
  clearAlerts: () => set({ alerts: [] }),
  pruneExpiredAlerts: () => {
    const now = Date.now();
    const TTL = 5 * 60 * 1000;
    const fresh = get().alerts.filter(
      (a) => !a.acknowledged || now - a.createdAt < TTL,
    );
    if (fresh.length !== get().alerts.length) set({ alerts: fresh });
  },
}));

// ── Selector helpers ─────────────────────────────────────
// IMPORTANT: returning a NEW reference (.filter / .map / .slice) from a
// Zustand v5 selector triggers an infinite re-render loop with React 19.
// We split the work in two: subscribe to the raw array (stable ref),
// then derive the filtered list with useMemo (recomputed only when alerts
// itself changes).

export const useFocusedService = () =>
  useNexusStore((s) => s.focusedServiceId);

export const useActiveAlerts = () => {
  const alerts = useNexusStore((s) => s.alerts);
  return useMemo(
    () => alerts.filter((a) => !a.acknowledged),
    [alerts],
  );
};

export const useServiceStatus = (id: string) =>
  useNexusStore((s) => s.serviceStatus[id] ?? 'loading');
