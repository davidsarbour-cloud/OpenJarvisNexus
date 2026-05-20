import { useState } from 'react';
import type { HubAlert, HubStatus } from '../types';

interface Props {
  hubStatus: HubStatus | null;
  alerts:    HubAlert[];
}

export function HubHeader({ hubStatus, alerts }: Props) {
  const [showAlerts, setShowAlerts] = useState(false);
  const errorCount = alerts.filter(a => a.level === 'error').length;
  const now = new Date().toLocaleTimeString('fr-CA', { hour12: false });

  return (
    <header className="relative z-40 flex items-center justify-between px-6 py-3 border-b border-nx-border bg-nx-panel/90 backdrop-blur">
      {/* Brand */}
      <div className="flex items-center gap-3">
        <div className="relative">
          <div className="w-4 h-4 rotate-45 bg-nx-cyan" style={{ boxShadow:'0 0 16px #00e5ff' }} />
          <div className="absolute inset-0 w-4 h-4 rotate-45 border border-nx-cyan animate-pulse" />
        </div>
        <div>
          <div className="font-hud text-xl font-bold tracking-[0.25em] text-glow-cyan">
            NEXUS<span className="text-white">X9</span>
          </div>
          <div className="text-[10px] tracking-widest text-nx-dim font-mono">
            HUB DE COMMANDEMENT IA
          </div>
        </div>
      </div>

      {/* Centre — statut */}
      <div className="flex items-center gap-6 font-mono text-[11px] tracking-widest">
        <StatusBadge
          label="BACKEND"
          ok={hubStatus?.online ?? false}
          value={hubStatus?.online ? 'EN LIGNE' : 'HORS LIGNE'}
        />
        <StatusBadge
          label="CLAUDE"
          ok={hubStatus?.online ?? false}
          value={hubStatus?.claudeModel ?? '—'}
          color="gold"
        />
        <StatusBadge
          label="OLLAMA"
          ok={hubStatus?.ollamaOnline ?? false}
          value={hubStatus?.ollamaOnline ? hubStatus?.ollamaModel ?? '—' : 'HORS LIGNE'}
          color="blue"
        />
      </div>

      {/* Droite — alertes + heure */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => setShowAlerts(v => !v)}
          className="relative flex items-center gap-2 px-3 py-1.5 rounded border text-[11px] font-mono tracking-widest transition-colors"
          style={{
            borderColor: errorCount > 0 ? '#ff2244' : '#0f1e3d',
            color:       errorCount > 0 ? '#ff2244' : '#334466',
            background:  errorCount > 0 ? '#ff224411' : 'transparent',
          }}
        >
          ⚠ ALERTES
          {errorCount > 0 && (
            <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-nx-red text-white text-[9px] flex items-center justify-center">
              {errorCount}
            </span>
          )}
        </button>
        <div className="text-nx-dim font-mono text-[11px] tracking-widest">{now}</div>
      </div>

      {/* Dropdown alertes */}
      {showAlerts && (
        <div className="absolute top-full right-6 mt-1 w-80 bg-nx-panel border border-nx-border rounded z-50 max-h-64 overflow-y-auto">
          {alerts.length === 0 ? (
            <div className="p-3 text-nx-dim text-[12px] font-mono">Aucune alerte</div>
          ) : alerts.slice(0, 15).map(a => (
            <div key={a.id} className="px-3 py-2 border-b border-nx-border/50 text-[11px] font-mono flex items-start gap-2">
              <span style={{ color: a.level === 'error' ? '#ff2244' : a.level === 'warn' ? '#ffcc00' : '#00e5ff' }}>
                {a.level === 'error' ? '●' : a.level === 'warn' ? '◐' : '○'}
              </span>
              <span className="text-white/80">{a.msg}</span>
            </div>
          ))}
        </div>
      )}
    </header>
  );
}

function StatusBadge({ label, ok, value, color = 'cyan' }: {
  label: string; ok: boolean; value: string; color?: 'cyan'|'gold'|'blue';
}) {
  const colors = { cyan: '#00e5ff', gold: '#ffcc00', blue: '#4488ff' };
  const c = ok ? colors[color] : '#334466';
  return (
    <div className="flex items-center gap-2 px-3 py-1 rounded border"
         style={{ borderColor: `${c}33`, background: `${c}08` }}>
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: c, boxShadow: `0 0 6px ${c}` }} />
      <span className="text-nx-dim">{label}</span>
      <span style={{ color: c }}>{value}</span>
    </div>
  );
}