import { Container, Database } from 'lucide-react';
import { HudCard, CardValue } from './HudCard';

export function DockerCard() {
  return (
    <HudCard title="Docker Infra" subtitle="containers (Phase 4 live)" colorKey="docker" icon={Container} status="demo">
      <CardValue value="—" unit="ctnrs" colorKey="docker" />
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
