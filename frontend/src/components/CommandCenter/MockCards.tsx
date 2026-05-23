import { Container, LineChart, BarChart3, Bug, Database } from 'lucide-react';
import { HudCard, CardValue } from './HudCard';

export function DockerCard() {
  return (
    <HudCard title="Docker Infra" subtitle="containers (Phase 4 live)" colorKey="docker" icon={Container} status="demo">
      <CardValue value="—" unit="ctnrs" colorKey="docker" />
      <a
        href="http://localhost:8888"
        target="_blank"
        rel="noopener noreferrer"
        className="text-[9px] tracking-[0.18em] mt-2 underline"
        style={{ color: 'var(--color-docker)' }}
      >
        cAdvisor :8888 →
      </a>
    </HudCard>
  );
}

export function PrometheusCard() {
  return (
    <HudCard title="Prometheus" subtitle="scrape jobs" colorKey="forge" icon={LineChart} status="demo">
      <CardValue value="2" unit="jobs" colorKey="forge" />
      <a
        href="http://localhost:9090"
        target="_blank"
        rel="noopener noreferrer"
        className="text-[9px] tracking-[0.18em] mt-2 underline"
        style={{ color: 'var(--color-forge)' }}
      >
        Open :9090 →
      </a>
    </HudCard>
  );
}

export function GrafanaCard() {
  return (
    <HudCard title="Grafana" subtitle="observability" colorKey="security" icon={BarChart3} status="demo">
      <CardValue value="—" unit="dashboards" colorKey="security" />
      <a
        href="http://localhost:3001"
        target="_blank"
        rel="noopener noreferrer"
        className="text-[9px] tracking-[0.18em] mt-2 underline"
        style={{ color: 'var(--color-security)' }}
      >
        Open :3001 →
      </a>
    </HudCard>
  );
}

export function SonarqubeCard() {
  return (
    <HudCard title="SonarQube" subtitle="code quality / security" colorKey="cyberdeck" icon={Bug} status="demo">
      <CardValue value="—" unit="issues" colorKey="cyberdeck" />
      <a
        href="http://localhost:9000"
        target="_blank"
        rel="noopener noreferrer"
        className="text-[9px] tracking-[0.18em] mt-2 underline"
        style={{ color: 'var(--color-cyberdeck)' }}
      >
        Open :9000 →
      </a>
    </HudCard>
  );
}

export function ChromaDbCard() {
  return (
    <HudCard title="ChromaDB" subtitle="vector store stats" colorKey="vault" icon={Database} status="demo">
      <CardValue value="—" unit="collections" colorKey="vault" />
      <a
        href="http://localhost:8001/api/v1/heartbeat"
        target="_blank"
        rel="noopener noreferrer"
        className="text-[9px] tracking-[0.18em] mt-2 underline"
        style={{ color: 'var(--color-vault)' }}
      >
        Heartbeat :8001 →
      </a>
    </HudCard>
  );
}
