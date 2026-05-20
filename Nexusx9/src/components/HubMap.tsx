import { AgentRoom } from './AgentRoom';
import type { Agent } from '../types';

interface Props {
  agents:   Agent[];
  selected: Agent | null;
  onSelect: (a: Agent) => void;
  onToggle: (id: string) => void;
  onTrigger:(id: string, action: string) => void;
}

export function HubMap({ agents, selected, onSelect, onToggle, onTrigger }: Props) {
  return (
    <main className="flex-1 overflow-auto p-6 relative">
      {/* Titre carte */}
      <div className="flex items-center gap-3 mb-6">
        <div className="h-px flex-1 bg-gradient-to-r from-transparent to-nx-cyan/30" />
        <div className="font-mono text-[11px] tracking-[0.4em] text-nx-cyan/70">
          ◈ HUB DE COMMANDE — {agents.filter(a => a.enabled).length} AGENTS ACTIFS
        </div>
        <div className="h-px flex-1 bg-gradient-to-l from-transparent to-nx-cyan/30" />
      </div>

      {/* Grille de rooms */}
      <div className="grid grid-cols-4 gap-4 max-w-4xl mx-auto">
        {/* Rangée 1 — top */}
        <div />
        <AgentRoom
          agent={agents.find(a => a.id === 'claude') ?? agents[1]}
          selected={selected?.id === 'claude'}
          onSelect={() => onSelect(agents.find(a => a.id === 'claude') ?? agents[1])}
          onToggle={() => onToggle('claude')}
          onTrigger={(action) => onTrigger('claude', action)}
        />
        <AgentRoom
          agent={agents.find(a => a.id === 'missions') ?? agents[7]}
          selected={selected?.id === 'missions'}
          onSelect={() => onSelect(agents.find(a => a.id === 'missions') ?? agents[7])}
          onToggle={() => onToggle('missions')}
          onTrigger={(action) => onTrigger('missions', action)}
        />
        <div />

        {/* Rangée 2 — milieu gauche + centre + droite */}
        <AgentRoom
          agent={agents.find(a => a.id === 'researcher') ?? agents[2]}
          selected={selected?.id === 'researcher'}
          onSelect={() => onSelect(agents.find(a => a.id === 'researcher') ?? agents[2])}
          onToggle={() => onToggle('researcher')}
          onTrigger={(action) => onTrigger('researcher', action)}
        />

        {/* Architecte — pièce centrale */}
        <div className="col-span-2 relative">
          <div className="absolute inset-0 rounded-xl border border-nx-cyan/20"
               style={{ boxShadow: '0 0 40px #00e5ff11' }} />
          <AgentRoom
            agent={agents.find(a => a.id === 'architect') ?? agents[0]}
            selected={selected?.id === 'architect'}
            onSelect={() => onSelect(agents.find(a => a.id === 'architect') ?? agents[0])}
            onToggle={() => onToggle('architect')}
            onTrigger={(action) => onTrigger('architect', action)}
          />
        </div>

        <AgentRoom
          agent={agents.find(a => a.id === 'memory') ?? agents[3]}
          selected={selected?.id === 'memory'}
          onSelect={() => onSelect(agents.find(a => a.id === 'memory') ?? agents[3])}
          onToggle={() => onToggle('memory')}
          onTrigger={(action) => onTrigger('memory', action)}
        />

        {/* Rangée 3 — bas */}
        <AgentRoom
          agent={agents.find(a => a.id === 'ollama') ?? agents[4]}
          selected={selected?.id === 'ollama'}
          onSelect={() => onSelect(agents.find(a => a.id === 'ollama') ?? agents[4])}
          onToggle={() => onToggle('ollama')}
          onTrigger={(action) => onTrigger('ollama', action)}
        />
        <AgentRoom
          agent={agents.find(a => a.id === 'observer') ?? agents[6]}
          selected={selected?.id === 'observer'}
          onSelect={() => onSelect(agents.find(a => a.id === 'observer') ?? agents[6])}
          onToggle={() => onToggle('observer')}
          onTrigger={(action) => onTrigger('observer', action)}
        />
        <AgentRoom
          agent={agents.find(a => a.id === 'coder') ?? agents[5]}
          selected={selected?.id === 'coder'}
          onSelect={() => onSelect(agents.find(a => a.id === 'coder') ?? agents[5])}
          onToggle={() => onToggle('coder')}
          onTrigger={(action) => onTrigger('coder', action)}
        />
        <div />
      </div>

      {/* Légende */}
      <div className="flex items-center justify-center gap-6 mt-8 font-mono text-[10px]">
        {[
          { color:'#ffcc00', label:'Claude API' },
          { color:'#4488ff', label:'Ollama Local' },
          { color:'#00ff88', label:'Système' },
          { color:'#334466', label:'Hors ligne' },
        ].map(({ color, label }) => (
          <div key={label} className="flex items-center gap-2 text-nx-dim">
            <div className="w-2 h-2 rounded-full" style={{ background: color }} />
            {label}
          </div>
        ))}
      </div>
    </main>
  );
}