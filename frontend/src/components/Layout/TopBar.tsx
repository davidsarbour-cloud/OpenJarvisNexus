import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router';
import { Hexagon, Orbit, LayoutDashboard, Activity, Share2, MessageSquare } from 'lucide-react';

type Pill = {
  label: string;
  state: 'online' | 'warning' | 'offline';
};

/**
 * TopBar — fixed top HUD strip.
 *  • Left  : Nexus9 logo + subtitle
 *  • Mid   : COMMAND CENTER ↔ ORBITAL VIEW switch
 *  • Right : status pills + live clock
 */
export function TopBar() {
  const navigate = useNavigate();
  const location = useLocation();
  const isOrbital = location.pathname.startsWith('/orbital');
  const path = location.pathname;

  const [now, setNow] = useState<string>(() => formatClock(new Date()));
  useEffect(() => {
    const t = setInterval(() => setNow(formatClock(new Date())), 1000);
    return () => clearInterval(t);
  }, []);

  // Placeholder pills — Phase 2 will wire these to real backend health.
  const pills: Pill[] = [
    { label: 'BACKEND', state: 'warning' },
    { label: 'OLLAMA', state: 'online' },
    { label: 'JARVIS', state: 'online' },
  ];

  return (
    <header
      className="flex items-center shrink-0 px-4"
      style={{
        height: 48,
        background: 'var(--hud-bg-elev)',
        borderBottom: '1px solid var(--hud-border)',
        boxShadow: '0 1px 0 0 var(--hud-border)',
      }}
    >
      {/* LEFT — brand */}
      <div className="flex items-center gap-3 min-w-0 flex-1">
        <Hexagon
          size={20}
          style={{
            color: 'var(--color-jarvis)',
            filter: 'drop-shadow(0 0 6px var(--color-jarvis-glow))',
          }}
        />
        <div className="flex flex-col leading-none">
          <span
            className="text-[13px] font-bold tracking-[0.18em]"
            style={{ color: 'var(--hud-text-hot)' }}
          >
            NEXUS9
          </span>
          <span
            className="text-[9px] tracking-[0.22em] mt-0.5"
            style={{ color: 'var(--hud-text-dim)' }}
          >
            {isOrbital ? 'ORBITAL INTERFACE' : 'COMMAND CENTER'}
          </span>
        </div>
      </div>

      {/* MID — view nav (boutons uniformes) */}
      <div
        className="flex items-stretch rounded-sm overflow-hidden shrink-0"
        style={{ border: '1px solid var(--hud-border)' }}
      >
        <ViewButton active={path.startsWith('/chat')}         icon={<MessageSquare size={13} />}   label="CHAT"           onClick={() => navigate('/chat')} />
        <ViewButton active={path === '/'}                     icon={<LayoutDashboard size={13} />} label="COMMAND CENTER" onClick={() => navigate('/')} />
        <ViewButton active={path.startsWith('/orbital')}      icon={<Orbit size={13} />}           label="ORBITAL"        onClick={() => navigate('/orbital')} />
        <ViewButton active={false}                             icon={<Share2 size={13} />}          label="BRAIN"          onClick={() => window.open('obsidian://open?vault=BRAIN', '_blank')} />
      </div>

      {/* RIGHT — pills + clock */}
      <div className="flex items-center gap-2 flex-1 justify-end">
        {pills.map((p) => (
          <StatusPill key={p.label} pill={p} />
        ))}
        <div
          className="px-2 py-1 text-[11px] font-mono tracking-wider tabular-nums"
          style={{
            color: 'var(--hud-text-hot)',
            background: 'rgba(0,212,255,0.06)',
            border: '1px solid var(--hud-border)',
            borderRadius: 2,
            minWidth: 84,
            textAlign: 'center',
          }}
        >
          {now}
        </div>
      </div>
    </header>
  );
}

function ViewButton({
  active,
  icon,
  label,
  onClick,
}: {
  active: boolean;
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-2 px-3 text-[10px] font-bold tracking-[0.18em] transition-colors cursor-pointer"
      style={{
        color: active ? 'var(--hud-bg)' : 'var(--hud-text)',
        background: active ? 'var(--color-jarvis)' : 'transparent',
        boxShadow: active ? '0 0 12px var(--color-jarvis-glow)' : 'none',
        minWidth: 130,
        justifyContent: 'center',
      }}
      onMouseEnter={(e) => {
        if (!active) e.currentTarget.style.background = 'rgba(0,212,255,0.08)';
      }}
      onMouseLeave={(e) => {
        if (!active) e.currentTarget.style.background = 'transparent';
      }}
    >
      {icon}
      {label}
    </button>
  );
}

function StatusPill({ pill }: { pill: Pill }) {
  const colorMap = {
    online: 'var(--color-docker)',
    warning: 'var(--color-security)',
    offline: 'var(--color-cyberdeck)',
  } as const;
  const c = colorMap[pill.state];
  return (
    <div
      className="flex items-center gap-1.5 px-2 py-1 rounded-sm text-[9px] font-bold tracking-[0.18em]"
      style={{
        color: c,
        background: 'rgba(255,255,255,0.02)',
        border: `1px solid ${c}`,
        boxShadow: `0 0 6px ${c}`,
      }}
    >
      <Activity size={9} />
      {pill.label}
    </div>
  );
}

function formatClock(d: Date): string {
  return d.toISOString().slice(11, 19);
}
