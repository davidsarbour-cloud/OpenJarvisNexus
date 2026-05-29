import { useNavigate } from 'react-router';
import { HeartPulse, Gauge, ChevronRight, type LucideIcon } from 'lucide-react';

/**
 * Compact launcher tiles for the Command Center docks — click to open the
 * full Health Checks / Benchmark views. Deliberately NO data fetch here:
 * /v1/health/all runs live Claude/Meshy pings (cost + latency), so we don't
 * poll it from the always-visible home; the live check runs on /diagnostics.
 */
function Shortcut({
  icon: Icon, accent, label, sub, to,
}: {
  icon: LucideIcon;
  accent: string;
  label: string;
  sub: string;
  to: string;
}) {
  const navigate = useNavigate();
  const go = () => navigate(to);
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={go}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(); } }}
      className="flex items-center gap-2.5 p-3 cursor-pointer"
      style={{
        background: 'var(--hud-bg-elev)',
        border: '1px solid var(--hud-border)',
        borderLeft: `2px solid ${accent}`,
        transition: 'background 0.15s, box-shadow 0.15s',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = 'rgba(0,212,255,0.05)';
        e.currentTarget.style.boxShadow = `0 0 16px -6px ${accent}`;
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = 'var(--hud-bg-elev)';
        e.currentTarget.style.boxShadow = 'none';
      }}
    >
      <Icon size={16} style={{ color: accent }} />
      <div className="flex flex-col min-w-0 flex-1">
        <span className="text-[10px] font-bold tracking-[0.2em]" style={{ color: accent }}>{label}</span>
        <span className="text-[9px] truncate" style={{ color: 'var(--hud-text-dim)' }}>{sub}</span>
      </div>
      <ChevronRight size={13} style={{ color: 'var(--hud-text-dim)' }} />
    </div>
  );
}

export function HealthShortcutCard() {
  return (
    <Shortcut
      icon={HeartPulse}
      accent="var(--color-docker)"
      label="HEALTH CHECKS"
      sub="services + system status"
      to="/diagnostics"
    />
  );
}

export function BenchmarkShortcutCard() {
  return (
    <Shortcut
      icon={Gauge}
      accent="var(--color-security)"
      label="BENCHMARK"
      sub="API latency test"
      to="/benchmark"
    />
  );
}
