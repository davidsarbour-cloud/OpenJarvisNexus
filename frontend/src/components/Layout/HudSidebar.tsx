import { useNavigate, useLocation } from 'react-router';
import {
  Cpu, Hammer, Lock, Eye, ShoppingBag,
  Database, Container,
  Workflow,
  Network, Share2, Waypoints, X,
} from 'lucide-react';
import { cssVar, type ModuleKey } from '../../lib/colors';

type Entry = {
  label: string;
  icon: React.ComponentType<{ size?: number; style?: React.CSSProperties }>;
  colorKey?: ModuleKey;
  route?: string;
  external?: string;
  status?: 'on' | 'off' | 'warn';
  /** Show X close-button when this entry is the active route (escapes back to /). */
  escapable?: boolean;
};

type Section = {
  title: string;
  entries: Entry[];
};

const SECTIONS: Section[] = [
  {
    title: 'VIEWS',
    entries: [
      { label: 'Agent Network',  icon: Network,        colorKey: 'cortex',   route: '/agent-network', status: 'on', escapable: true },
      { label: 'Brain Hub',      icon: Share2,         colorKey: 'vault',    route: '/brain',         status: 'on' },
      { label: 'Pipeline Hub',   icon: Waypoints,      colorKey: 'security', route: '/pipeline-hub',  status: 'on' },
    ],
  },
  {
    title: 'WORLD',
    entries: [
      { label: 'JARVIS',    icon: Cpu,         colorKey: 'jarvis',    route: '/world/jarvis',    status: 'on', escapable: true },
      { label: 'Forge',     icon: Hammer,      colorKey: 'forge',     route: '/world/forge',     status: 'on', escapable: true },
      { label: 'Commerce',  icon: ShoppingBag, colorKey: 'commerce',  route: '/world/commerce',  status: 'on', escapable: true },
      { label: 'Cyberdeck', icon: Eye,         colorKey: 'cyberdeck', route: '/world/cyberdeck', status: 'on', escapable: true },
      { label: 'Vault',     icon: Lock,        colorKey: 'vault',     route: '/world/vault',     status: 'on', escapable: true },
      { label: 'Docker',    icon: Container,   colorKey: 'docker',    route: '/world/docker',    status: 'on', escapable: true },
    ],
  },
  {
    title: 'SYSTEM',
    entries: [
      { label: 'ChromaDB',  icon: Database,  colorKey: 'vault',     status: 'on' },
      { label: 'OpenHands', icon: Workflow,  colorKey: 'commerce',  external: 'http://localhost:3000', status: 'on' },
    ],
  },
];

/**
 * HudSidebar - left tactical nav, fixed width 240px.
 * Sections: VIEWS / ENTITIES / SYSTEM.
 * External entries open in new tab; route entries navigate inside React.
 * Entries flagged `escapable` show an X close-button when active (returns to /).
 */
export function HudSidebar() {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <aside
      className="flex flex-col shrink-0 overflow-y-auto"
      style={{
        width: 240,
        background: 'var(--hud-bg-elev)',
        borderRight: '1px solid var(--hud-border)',
      }}
    >
      {SECTIONS.map((section) => (
        <div key={section.title} className="px-3 pt-4 pb-2">
          <div
            className="px-1 pb-2 text-[9px] font-bold tracking-[0.25em]"
            style={{
              color: 'var(--hud-text-dim)',
              borderBottom: '1px solid var(--hud-border)',
            }}
          >
            -- {section.title}
          </div>

          <div className="flex flex-col gap-0.5 mt-2">
            {section.entries.map((entry) => {
              const color = entry.colorKey ? cssVar(entry.colorKey) : 'var(--hud-text)';
              const isActive = !!(entry.route && location.pathname === entry.route);
              const handleClick = () => {
                if (entry.external) {
                  window.open(entry.external, '_blank', 'noopener,noreferrer');
                } else if (entry.route) {
                  navigate(entry.route);
                }
              };
              const handleEscape = (e: React.MouseEvent) => {
                e.stopPropagation();
                navigate('/');
              };
              return (
                <button
                  key={entry.label}
                  onClick={handleClick}
                  className="flex items-center gap-2.5 px-2 py-1.5 text-[11px] tracking-wider transition-colors cursor-pointer text-left"
                  style={{
                    color: isActive ? color : 'var(--hud-text)',
                    background: isActive ? 'rgba(0,212,255,0.06)' : 'transparent',
                    borderLeft: isActive
                      ? `2px solid ${color}`
                      : '2px solid transparent',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'rgba(0,212,255,0.04)';
                    e.currentTarget.style.color = color;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = isActive ? 'rgba(0,212,255,0.06)' : 'transparent';
                    e.currentTarget.style.color = isActive ? color : 'var(--hud-text)';
                  }}
                >
                  <entry.icon size={13} style={{ color }} />
                  <span className="flex-1">{entry.label}</span>
                  {entry.escapable && isActive ? (
                    <span
                      role="button"
                      tabIndex={0}
                      aria-label={`Fermer ${entry.label}`}
                      onClick={handleEscape}
                      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') handleEscape(e as unknown as React.MouseEvent); }}
                      className="flex items-center justify-center rounded transition-colors"
                      style={{
                        width: 14,
                        height: 14,
                        color: 'var(--hud-text-dim)',
                        background: 'transparent',
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = 'rgba(255,45,85,0.15)';
                        e.currentTarget.style.color = 'var(--color-cyberdeck)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'transparent';
                        e.currentTarget.style.color = 'var(--hud-text-dim)';
                      }}
                    >
                      <X size={11} />
                    </span>
                  ) : (
                    <StatusDot state={entry.status} />
                  )}
                </button>
              );
            })}
          </div>
        </div>
      ))}
    </aside>
  );
}

function StatusDot({ state }: { state?: 'on' | 'off' | 'warn' }) {
  const map = {
    on:   { c: 'var(--color-docker)',    glow: 'var(--color-docker-glow)' },
    warn: { c: 'var(--color-security)',  glow: 'var(--color-security-glow)' },
    off:  { c: 'var(--color-cyberdeck)', glow: 'var(--color-cyberdeck-glow)' },
  } as const;
  const s = state ? map[state] : map.off;
  return (
    <span
      className="w-1.5 h-1.5 rounded-full"
      style={{ background: s.c, boxShadow: `0 0 4px ${s.glow}` }}
    />
  );
}
