import type { Agent } from '../types';

interface Props {
  agent:    Agent;
  selected: boolean;
  onSelect: () => void;
  onToggle: () => void;
  onTrigger:(action: string) => void;
}

export function AgentRoom({ agent, selected, onSelect, onToggle, onTrigger }: Props) {
  const { color, sigil, name, role, status, enabled, provider, model, actionCount } = agent;

  const borderColor = enabled
    ? status === 'busy'    ? color
    : status === 'offline' ? '#334466'
    : `${color}66`
    : '#0f1e3d';

  const bgColor = selected
    ? `${color}18`
    : enabled ? `${color}08` : '#070d1f';

  const glowStyle = enabled && status !== 'offline'
    ? { boxShadow: `0 0 20px ${color}33, inset 0 0 20px ${color}08` }
    : {};

  const animClass = !enabled ? ''
    : status === 'busy'    ? 'room-busy'
    : status === 'idle'    ? 'room-active'
    : '';

  return (
    <div
      className={`relative rounded-lg border cursor-pointer transition-all duration-300 ${animClass}`}
      style={{ borderColor, background: bgColor, ...glowStyle }}
      onClick={onSelect}
    >
      {/* Coin déco top-left */}
      <div className="absolute top-0 left-0 w-3 h-3 border-t border-l rounded-tl"
           style={{ borderColor: color + '88' }} />
      <div className="absolute top-0 right-0 w-3 h-3 border-t border-r rounded-tr"
           style={{ borderColor: color + '88' }} />

      <div className="p-3">
        {/* Header room */}
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-2">
            {/* Sigil */}
            <div className="text-2xl font-hud font-bold leading-none"
                 style={{ color, textShadow: `0 0 12px ${color}` }}>
              {sigil}
            </div>
            {/* Status LED */}
            <div className="flex flex-col gap-0.5">
              <div className="w-2 h-2 rounded-full"
                   style={{
                     background:  status === 'busy'    ? '#ffcc00'
                                : status === 'idle'    ? color
                                : status === 'error'   ? '#ff2244'
                                                       : '#334466',
                     boxShadow:   status === 'busy'    ? '0 0 8px #ffcc00'
                                : status === 'idle'    ? `0 0 6px ${color}`
                                                       : 'none',
                     animation:   status === 'busy'    ? 'pulse 0.6s infinite' : 'none',
                   }} />
            </div>
          </div>

          {/* Toggle ON/OFF */}
          <div
            className={`toggle-track ${enabled ? 'toggle-on' : ''}`}
            style={{ background: enabled ? color + '88' : '#0f1e3d' }}
            onClick={e => { e.stopPropagation(); onToggle(); }}
          >
            <div className="toggle-thumb" style={{ background: enabled ? 'white' : '#334466' }} />
          </div>
        </div>

        {/* Nom + rôle */}
        <div className="font-hud font-bold text-sm tracking-wider mb-0.5"
             style={{ color: enabled ? color : '#334466' }}>
          {name}
        </div>
        <div className="font-mono text-[10px] text-nx-dim mb-2 leading-tight">{role}</div>

        {/* Provider badge */}
        <div className="flex items-center justify-between">
          <span className="font-mono text-[10px] px-1.5 py-0.5 rounded border"
                style={{
                  borderColor: `${color}33`,
                  color:       provider === 'claude' ? '#ffcc00'
                             : provider === 'ollama' ? '#4488ff'
                                                     : '#00ff88',
                  background:  `${color}08`,
                }}>
            {provider.toUpperCase()}
          </span>
          <span className="font-mono text-[10px] text-nx-dim">{actionCount} acts</span>
        </div>

        {/* Action status */}
        {status === 'busy' && agent.lastAction && (
          <div className="mt-2 text-[10px] font-mono animate-pulse"
               style={{ color: '#ffcc00' }}>
            ⚡ {agent.lastAction}
          </div>
        )}

        {/* Bouton activer si sélectionné */}
        {selected && enabled && (
          <button
            className="mt-2 w-full py-1 rounded text-[11px] font-hud font-semibold tracking-widest border transition-all hover:opacity-80"
            style={{ borderColor: color, color, background: `${color}18` }}
            onClick={e => { e.stopPropagation(); onTrigger(`Action ${name}`); }}
          >
            ▶ ACTIVER
          </button>
        )}
      </div>

      {/* Bottom corner déco */}
      <div className="absolute bottom-0 left-0 w-3 h-3 border-b border-l rounded-bl"
           style={{ borderColor: color + '44' }} />
      <div className="absolute bottom-0 right-0 w-3 h-3 border-b border-r rounded-br"
           style={{ borderColor: color + '44' }} />
    </div>
  );
}