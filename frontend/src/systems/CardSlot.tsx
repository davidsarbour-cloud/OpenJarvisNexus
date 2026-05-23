/**
 * Nexus9 — CardSlot
 *
 * Thin wrapper that connects any Command Center card to the shared store.
 * Behavior:
 *   - tags the DOM node with data-service-id (useful for tests & shortcuts)
 *   - scrolls itself into view + pulses a brief glow when focusedServiceId
 *     matches its id (triggered by an Orbital planet click)
 *
 * Usage:
 *   <CardSlot serviceId="ollama"><OllamaStatusCard /></CardSlot>
 */
import { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { useFocusedService, useNexusStore } from './nexusStore';
import { getService } from './serviceRegistry';
import { MODULE_COLORS } from '../lib/colors';

interface CardSlotProps {
  serviceId: string;
  children: React.ReactNode;
}

export function CardSlot({ serviceId, children }: CardSlotProps) {
  const ref = useRef<HTMLDivElement>(null);
  const focused = useFocusedService();
  const isFocused = focused === serviceId;
  const setFocused = useNexusStore((s) => s.setFocusedService);

  const svc = getService(serviceId);
  const glow = svc ? MODULE_COLORS[svc.colorKey].glow : 'rgba(0,212,255,0.45)';

  useEffect(() => {
    if (!isFocused || !ref.current) return;
    ref.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    // Auto-unfocus after a few seconds so the next click works fresh.
    const t = setTimeout(() => setFocused(null), 2400);
    return () => clearTimeout(t);
  }, [isFocused, setFocused]);

  return (
    <div ref={ref} data-service-id={serviceId} className="relative">
      <AnimatePresence>
        {isFocused && (
          <motion.span
            key="halo"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="pointer-events-none absolute -inset-1 z-0"
            style={{
              boxShadow: `0 0 28px -2px ${glow}, inset 0 0 18px -6px ${glow}`,
              border: `1px solid ${glow}`,
              borderRadius: 2,
            }}
          />
        )}
      </AnimatePresence>
      <div className="relative z-10">{children}</div>
    </div>
  );
}
