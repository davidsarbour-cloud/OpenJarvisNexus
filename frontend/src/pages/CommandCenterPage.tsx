import { SystemHealthCard }    from '../components/CommandCenter/SystemHealthCard';
import { AgentActivityCard }   from '../components/CommandCenter/AgentActivityCard';
import { OllamaStatusCard }    from '../components/CommandCenter/OllamaStatusCard';
import { ForgePipelinesCard }  from '../components/CommandCenter/ForgePipelinesCard';
import { BudgetCard }          from '../components/CommandCenter/BudgetCard';
import { DockerLiveCard }      from '../components/CommandCenter/DockerLiveCard';
import { PrometheusLiveCard }  from '../components/CommandCenter/PrometheusLiveCard';
import { ChromaDbLiveCard }    from '../components/CommandCenter/ChromaDbLiveCard';
import { SonarqubeLiveCard }   from '../components/CommandCenter/SonarqubeLiveCard';
import { GrafanaLiveCard }     from '../components/CommandCenter/GrafanaLiveCard';
import { ScheduledTasksCard }  from '../components/CommandCenter/ScheduledTasksCard';
import { SatelliteCards } from '../components/CommandCenter/FunctionalSatellites';
import { CardSlot }           from '../systems/CardSlot';

/**
 * CommandCenterPage — route `/`.
 * Shows the 10 live service cards grid only.
 */
export function CommandCenterPage() {
  return (
    <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
      <SectionTitle text="AUTOMATION" />
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 xl:grid-cols-6 2xl:grid-cols-10 gap-3">
        <div className="col-span-2 sm:col-span-3 lg:col-span-5 xl:col-span-6 2xl:col-span-10">
          <ScheduledTasksCard />
        </div>
      </div>

      <SectionTitle text="SYSTEM OVERVIEW" />
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 xl:grid-cols-6 2xl:grid-cols-10 gap-3">
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
        <SatelliteCards />
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
