import { useState } from 'react';
import { ChatBox } from './ChatBox';
import type { Agent } from '../types';

interface Props {
  selected:    Agent | null;
  agents:      Agent[];
  onAgentBusy:(id: string, action?: string) => void;
  addAlert:   (level: 'info'|'warn'|'error', msg: string) => void;
}

type Tab = 'chat' | 'agent' | 'missions';

export function RightPanel({ selected, agents, onAgentBusy, addAlert }: Props) {
  const [tab, setTab] = useState<Tab>('chat');

  return (
    <aside className="w-80 flex flex-col border-l border-nx-border bg-nx-panel/60 backdrop-blur">
      {/* Tabs */}
      <div className="flex border-b border-nx-border">
        {([['chat','💬 CHAT'],['agent','🤖 AGENT'],['missions','⚡ MISSIONS']] as const).map(([t,label]) => (
          <button key={t} onClick={() => setTab(t as Tab)}
                  className="flex-1 py-2.5 font-mono text-[10px] tracking-widest transition-all border-b-2"
                  style={{
                    borderColor: tab === t ? '#00e5ff' : 'transparent',
                    color:       tab === t ? '#00e5ff' : '#334466',
                    background:  tab === t ? '#00e5ff08' : 'transparent',
                  }}>
            {label}
          </button>
        ))}
      </div>

      {/* Contenu */}
      <div className="flex-1 overflow-hidden flex flex-col">
        {tab === 'chat' && <ChatBox addAlert={addAlert} onAgentBusy={onAgentBusy} />}
        {tab === 'agent' && <AgentDetail agent={selected} />}
        {tab === 'missions' && <MissionsPanel agents={agents} />}
      </div>
    </aside>
  );
}

function AgentDetail({ agent }: { agent: Agent | null }) {
  if (!agent) return (
    <div className="p-4 text-nx-dim font-mono text-[12px] italic">
      Clique sur une pièce pour voir les détails
    </div>
  );
  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center gap-3">
        <span className="text-4xl" style={{ color: agent.color, textShadow:`0 0 16px ${agent.color}` }}>
          {agent.sigil}
        </span>
        <div>
          <div className="font-hud font-bold tracking-wider" style={{ color: agent.color }}>{agent.name}</div>
          <div className="font-mono text-[11px] text-nx-dim">{agent.role}</div>
        </div>
      </div>
      <div className="space-y-2 font-mono text-[11px]">
        <Row k="Statut"      v={agent.status}      c={agent.status==='busy' ? '#ffcc00' : '#00ff88'} />
        <Row k="Provider"    v={agent.provider}     c={agent.color} />
        <Row k="Modèle"      v={agent.model}        c="#c8d8ff" />
        <Row k="Actions"     v={String(agent.actionCount)} c="#c8d8ff" />
        {agent.lastAction && <Row k="Dernière action" v={agent.lastAction} c="#b44dff" />}
      </div>
      <div className="text-[11px] text-nx-dim font-mono leading-relaxed border border-nx-border rounded p-2">
        {agent.description}
      </div>
    </div>
  );
}

function Row({ k, v, c }: { k: string; v: string; c: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-nx-dim">{k}</span>
      <span style={{ color: c }}>{v}</span>
    </div>
  );
}

function MissionsPanel({ agents }: { agents: Agent[] }) {
  const activeAgents = agents.filter(a => a.enabled && a.status !== 'offline');
  return (
    <div className="p-4 space-y-3">
      <div className="font-mono text-[10px] tracking-[0.3em] text-nx-cyan">AGENTS DISPONIBLES</div>
      {activeAgents.map(a => (
        <div key={a.id} className="flex items-center gap-3 px-3 py-2 rounded border"
             style={{ borderColor:`${a.color}33`, background:`${a.color}08` }}>
          <span style={{ color:a.color }}>{a.sigil}</span>
          <div>
            <div className="font-hud text-[12px] font-bold" style={{ color:a.color }}>{a.name}</div>
            <div className="font-mono text-[10px] text-nx-dim">{a.role}</div>
          </div>
          <div className="ml-auto w-2 h-2 rounded-full"
               style={{ background: a.status==='busy' ? '#ffcc00' : '#00ff88' }} />
        </div>
      ))}
      <div className="font-mono text-[10px] tracking-[0.3em] text-nx-cyan mt-4">MISSIONS CREW</div>
      <div className="text-[11px] font-mono text-nx-dim italic">
        Utilise le tab CHAT → mode 👥 CREW pour lancer une mission multi-agents
      </div>
    </div>
  );
}