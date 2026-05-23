import { useEffect } from 'react';
import { useNavigate } from 'react-router';
import { X, ExternalLink, ArrowRight } from 'lucide-react';
import type { PlanetDef, SpaceshipDef, JarvisDef } from './planets.config';

type Selection =
  | { kind: 'planet'; def: PlanetDef }
  | { kind: 'ship';   def: SpaceshipDef }
  | { kind: 'jarvis'; def: JarvisDef };

interface Props {
  selection: Selection;
  onClose: () => void;
}

export function ModulePanel({ selection, onClose }: Props) {
  const navigate = useNavigate();
  const def = selection.def;
  const color = def.color;
  const glow  = def.glow;

  const subtitle =
    selection.kind === 'planet' ? 'PLANET'
    : selection.kind === 'ship' ? 'AI DRONE'
    :                              'ORCHESTRATOR CORE';

  useEffect(() => {
    const k = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', k);
    return () => window.removeEventListener('keydown', k);
  }, [onClose]);

  return (
    <div
      className="absolute top-0 right-0 h-full flex flex-col"
      style={{
        width: 340,
        background: 'rgba(2,5,11,0.92)',
        borderLeft: `1px solid ${color}`,
        boxShadow: `-12px 0 40px -10px ${glow}`,
        backdropFilter: 'blur(6px)',
        animation: 'slideIn 220ms cubic-bezier(.22,.61,.36,1)',
        pointerEvents: 'auto',
      }}
    >
      <div
        className="flex items-center justify-between px-4 py-3"
        style={{ borderBottom: `1px solid ${color}`, background: 'rgba(0,0,0,0.4)' }}
      >
        <div className="flex flex-col leading-none">
          <span className="text-[9px] tracking-[0.3em]" style={{ color: 'var(--hud-text-dim)' }}>
            {subtitle}
          </span>
          <span
            className="text-[14px] font-bold tracking-[0.22em] mt-1"
            style={{ color, textShadow: `0 0 12px ${glow}` }}
          >
            {def.label}
          </span>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 transition-colors cursor-pointer"
          style={{ color: 'var(--hud-text-dim)' }}
          onMouseEnter={(e) => (e.currentTarget.style.color = color)}
          onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--hud-text-dim)')}
          title="Close (Esc)"
        >
          <X size={16} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-4">
        <Section title="DESCRIPTION">
          <p className="text-[12px] leading-relaxed" style={{ color: 'var(--hud-text)' }}>
            {def.description}
          </p>
        </Section>

        {selection.kind === 'planet' && (
          <Section title="ORBITAL PARAMETERS">
            <KV k="orbit radius"     v={`${selection.def.orbit.toFixed(1)} u`} color={color} />
            <KV k="planet radius"    v={`${selection.def.radius.toFixed(2)} u`} color={color} />
            <KV k="angular velocity" v={`${selection.def.speed.toFixed(3)} rad/s`} color={color} />
            <KV k="tilt"             v={`${(selection.def.tilt ?? 0).toFixed(3)} rad`} color={color} />
          </Section>
        )}

        {selection.kind === 'ship' && (
          <Section title="MISSION PROFILE">
            <KV k="mission"  v={selection.def.mission}                       color={color} />
            <KV k="pattern"  v={selection.def.pattern.toUpperCase()}         color={color} />
            <KV k="orbit"    v={`${selection.def.scale.toFixed(1)} u`}       color={color} />
            <KV k="speed"    v={`${selection.def.speed.toFixed(3)} rad/s`}   color={color} />
            <KV k="phase"    v={selection.def.phase.toFixed(2)}              color={color} />
            <KV k="status"   v="ACTIVE"                                       color={color} />
          </Section>
        )}

        {selection.kind === 'jarvis' && (
          <Section title="REACTOR STATUS">
            <KV k="role"   v={selection.def.role}  color={color} />
            <KV k="model"  v={selection.def.model} color={color} />
            <KV k="scope"  v={selection.def.scope} color={color} />
            <KV k="status" v="ONLINE"              color={color} />
          </Section>
        )}

        <Section title="ACTIONS">
          <div className="flex flex-col gap-2">
            {selection.kind === 'planet' && selection.def.route && (
              <ActionRow
                color={color}
                icon={<ArrowRight size={12} />}
                label={`Open ${def.label} page`}
                onClick={() => { onClose(); navigate(selection.def.route!); }}
              />
            )}
            {selection.kind === 'planet' && selection.def.external && (
              <ActionRow
                color={color}
                icon={<ExternalLink size={12} />}
                label={selection.def.external}
                onClick={() => window.open(selection.def.external!, '_blank', 'noopener')}
              />
            )}
            <ActionRow
              color={color}
              icon={<ArrowRight size={12} />}
              label="Back to Command Center"
              onClick={() => { onClose(); navigate('/'); }}
            />
          </div>
        </Section>
      </div>

      <style>{`
        @keyframes slideIn {
          from { transform: translateX(100%); opacity: 0; }
          to   { transform: translateX(0);    opacity: 1; }
        }
      `}</style>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <div
        className="text-[9px] font-bold tracking-[0.3em] pb-1"
        style={{ color: 'var(--hud-text-dim)', borderBottom: '1px solid var(--hud-border)' }}
      >
        -- {title}
      </div>
      <div className="flex flex-col gap-1">{children}</div>
    </div>
  );
}

function KV({ k, v, color }: { k: string; v: string; color: string }) {
  return (
    <div className="flex items-baseline justify-between text-[10px] gap-3">
      <span style={{ color: 'var(--hud-text-dim)', letterSpacing: '0.15em' }}>{k.toUpperCase()}</span>
      <span className="tabular-nums text-right" style={{ color }}>{v}</span>
    </div>
  );
}

function ActionRow({ color, icon, label, onClick }: { color: string; icon: React.ReactNode; label: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-2 px-2 py-1.5 text-[10px] tracking-wider cursor-pointer transition-all text-left"
      style={{
        color: 'var(--hud-text)',
        border: `1px solid ${color}`,
        background: 'rgba(0,0,0,0.25)',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = 'rgba(0,212,255,0.05)';
        e.currentTarget.style.boxShadow = `inset 0 0 12px ${color}`;
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = 'rgba(0,0,0,0.25)';
        e.currentTarget.style.boxShadow = 'none';
      }}
    >
      <span style={{ color }}>{icon}</span>
      <span className="flex-1 truncate">{label}</span>
    </button>
  );
}
