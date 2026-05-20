import type { Agent, HubAlert, HubStatus } from '../types';

interface Props {
  agents:    Agent[];
  alerts:    HubAlert[];
  memory:    any;
  hubStatus: HubStatus | null;
}

export function Sidebar({ agents, alerts, memory, hubStatus }: Props) {
  const active  = agents.filter(a => a.enabled && a.status !== 'offline').length;
  const busy    = agents.filter(a => a.status === 'busy').length;
  const totalCost = agents.reduce((s, a) => s + a.cost, 0);

  const facts = memory?.facts ?? {};

  return (
    <aside className="w-64 flex flex-col border-r border-nx-border bg-nx-panel/60 backdrop-blur overflow-y-auto">
      {/* Titre sidebar */}
      <div className="px-4 py-3 border-b border-nx-border">
        <div className="font-hud text-[11px] tracking-[0.3em] text-nx-cyan">CENTRE DE CONTRÔLE</div>
      </div>

      {/* Résumé Hub */}
      <Section title="RÉSUMÉ HUB">
        <Stat label="Agents actifs" value={`${active} / ${agents.length}`} color="#00e5ff" />
        <Stat label="En action"     value={`${busy}`}                        color={busy > 0 ? '#ffcc00' : '#334466'} />
        <Stat label="Backend"       value={hubStatus?.online ? 'OK' : 'KO'}  color={hubStatus?.online ? '#00ff88' : '#ff2244'} />
        <Stat label="Ollama"        value={hubStatus?.ollamaOnline ? 'OK' : 'KO'} color={hubStatus?.ollamaOnline ? '#00ff88' : '#334466'} />
      </Section>

      {/* Mémoire Jarvis */}
      <Section title="MÉMOIRE JARVIS">
        {facts.user_name && (
          <InfoRow icon="👤" label={facts.user_name} />
        )}
        {facts.projects?.slice(0, 2).map((p: string, i: number) => (
          <InfoRow key={i} icon="📁" label={p.slice(0, 30) + '…'} />
        ))}
        {facts.goals?.slice(0, 2).map((g: string, i: number) => (
          <InfoRow key={i} icon="🎯" label={g.slice(0, 30) + '…'} />
        ))}
        {!facts.user_name && (
          <div className="text-nx-dim text-[11px] font-mono italic">Aucune mémoire chargée</div>
        )}
      </Section>

      {/* Statut agents liste */}
      <Section title="STATUT AGENTS">
        {agents.map(a => (
          <div key={a.id} className="flex items-center justify-between py-0.5">
            <div className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full" style={{
                background: a.status === 'busy'    ? '#ffcc00'
                           : a.status === 'idle'   ? '#00ff88'
                           : a.status === 'error'  ? '#ff2244'
                                                   : '#334466',
                boxShadow: a.status === 'busy' ? '0 0 6px #ffcc00' : 'none',
                animation: a.status === 'busy' ? 'pulse 0.6s infinite' : 'none',
              }} />
              <span className="font-mono text-[11px]" style={{ color: a.color + 'cc' }}>{a.name}</span>
            </div>
            <span className="font-mono text-[10px] text-nx-dim uppercase">{a.status}</span>
          </div>
        ))}
      </Section>

      {/* Coûts */}
      <Section title="ÉCONOMIES IA">
        <Stat label="Coût Claude"  value={`$${totalCost.toFixed(3)}`} color="#ffcc00" />
        <Stat label="Économies"    value="~80% local"                  color="#00ff88" />
        <div className="mt-2 text-[10px] font-mono text-nx-dim leading-relaxed">
          Questions simples → Ollama (gratuit)
          <br />Questions complexes → Claude (payant)
        </div>
      </Section>

      {/* Dernières alertes */}
      <Section title="DERNIÈRES ALERTES">
        {alerts.length === 0 ? (
          <div className="text-nx-dim text-[11px] font-mono italic">Aucune alerte</div>
        ) : alerts.slice(0, 5).map(a => (
          <div key={a.id} className="flex gap-2 text-[11px] font-mono py-0.5">
            <span style={{ color: a.level === 'error' ? '#ff2244' : a.level === 'warn' ? '#ffcc00' : '#00e5ff' }}>
              {a.level === 'error' ? '✕' : a.level === 'warn' ? '!' : 'i'}
            </span>
            <span className="text-white/60 truncate">{a.msg}</span>
          </div>
        ))}
      </Section>
    </aside>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="px-4 py-3 border-b border-nx-border/50">
      <div className="font-mono text-[10px] tracking-[0.3em] text-nx-dim mb-2">{title}</div>
      <div className="space-y-1">{children}</div>
    </div>
  );
}

function Stat({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="flex items-center justify-between text-[11px] font-mono">
      <span className="text-nx-dim">{label}</span>
      <span style={{ color }}>{value}</span>
    </div>
  );
}

function InfoRow({ icon, label }: { icon: string; label: string }) {
  return (
    <div className="flex items-center gap-2 text-[11px] font-mono text-white/70">
      <span>{icon}</span><span className="truncate">{label}</span>
    </div>
  );
}