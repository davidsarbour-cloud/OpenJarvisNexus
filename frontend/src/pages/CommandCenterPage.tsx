import { SystemHealthCard }   from '../components/CommandCenter/SystemHealthCard';
import { AgentActivityCard }  from '../components/CommandCenter/AgentActivityCard';
import { OllamaStatusCard }   from '../components/CommandCenter/OllamaStatusCard';
import { ForgePipelinesCard } from '../components/CommandCenter/ForgePipelinesCard';
import { BudgetCard }         from '../components/CommandCenter/BudgetCard';
import { DockerLiveCard }     from '../components/CommandCenter/DockerLiveCard';
import { PrometheusLiveCard } from '../components/CommandCenter/PrometheusLiveCard';
import { ChromaDbLiveCard }   from '../components/CommandCenter/ChromaDbLiveCard';
import { SonarqubeLiveCard }  from '../components/CommandCenter/SonarqubeLiveCard';
import { GrafanaLiveCard }    from '../components/CommandCenter/GrafanaLiveCard';
import { SystemHealthGauge }  from '../components/CommandCenter/SystemHealthGauge';
import { ResourceMonitorCard } from '../components/CommandCenter/ResourceMonitorCard';
import { CardSlot }           from '../systems/CardSlot';

/**
 * CommandCenterPage — route `/`.
 *
 * Phase 4 milestone: 10 cards LIVE (Grafana migré vers GrafanaLiveCard).
 * Each card is wrapped in <CardSlot serviceId="..."> so that clicking a
 * planet in /orbital scrolls + pulses the matching card.
 */
export function CommandCenterPage() {
  return (
    <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
      <SectionTitle text="SYSTEM OVERVIEW" />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-5 gap-3">
        <CardSlot serviceId="backend"><SystemHealthCard /></CardSlot>
        <CardSlot serviceId="bruce"><AgentActivityCard /></CardSlot>
        <CardSlot serviceId="ollama"><OllamaStatusCard /></CardSlot>
        <CardSlot serviceId="forge"><ForgePipelinesCard /></CardSlot>
        <CardSlot serviceId="backend"><BudgetCard /></CardSlot>
        <CardSlot serviceId="docker"><DockerLiveCard /></CardSlot>
        <CardSlot serviceId="prometheus"><PrometheusLiveCard /></CardSlot>
        <CardSlot serviceId="chromadb"><ChromaDbLiveCard /></CardSlot>
        <CardSlot serviceId="sonarqube"><SonarqubeLiveCard /></CardSlot>
        <CardSlot serviceId="grafana"><GrafanaLiveCard /></CardSlot>
      </div>

      <SectionTitle text="HARDWARE" />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <CardSlot serviceId="backend"><SystemHealthGauge /></CardSlot>
        <CardSlot serviceId="backend"><ResourceMonitorCard /></CardSlot>
      </div>

    </div>
  );
}

function SectionTitle({ text }: { text: string }) {
  return (
    <div
      className="flex items-center gap-3 text-[10px] font-bold tracking-[0.3em]"
      style={{ color: 'var(--hud-text-dim)' }}
    >
      <span style={{ color: 'var(--color-jarvis)' }}>◆</span>
      {text}
      <span className="flex-1" style={{ height: 1, background: 'var(--hud-border)' }} />
    </div>
  );
}
