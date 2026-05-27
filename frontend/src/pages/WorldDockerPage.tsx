/**
 * Nexus9 — World · Docker.
 *
 * Thin wrapper around <WorldShell>. Pre-seeds the CONTAINERS card on
 * the left dock on first visit (still customisable afterwards).
 */
import { Container, HardDrive, Heart, Terminal, Wrench } from 'lucide-react';
import { DockerLiveCard } from '../components/CommandCenter/DockerLiveCard';
import { SystemHealthCard } from '../components/CommandCenter/SystemHealthCard';
import { NamedSatellite, LiveSatellite } from '../components/CommandCenter/FunctionalSatellites';
import { WorldShell, type CardDef, type PlacedCard } from '../components/WorldShell/WorldShell';

const MaintenanceDrone = () => <NamedSatellite title="MAINTENANCE DRONE" colorKey="docker" />;
const DiskUsage        = () => <LiveSatellite  title="DISK USAGE"        colorKey="docker" snapshotKey="disk_usage"     />;
const ContainerLogs    = () => <LiveSatellite  title="CONTAINER LOGS"    colorKey="docker" snapshotKey="container_logs" />;

type CardType = 'containers' | 'health' | 'maintenance' | 'disk' | 'logs';

const CARD_REGISTRY: Record<CardType, CardDef> = {
  containers:  { label: 'CONTAINERS',        sub: 'Stack roster',               icon: Container,  Card: DockerLiveCard   },
  health:      { label: 'SYSTEM HEALTH',     sub: 'Services deep-check',        icon: Heart,      Card: SystemHealthCard },
  maintenance: { label: 'MAINTENANCE DRONE', sub: 'Health / resource / errors', icon: Wrench,     Card: MaintenanceDrone },
  disk:        { label: 'DISK USAGE',        sub: 'C: free + folder sizes',     icon: HardDrive,  Card: DiskUsage        },
  logs:        { label: 'CONTAINER LOGS',    sub: 'Live tail (last N lines)',   icon: Terminal,   Card: ContainerLogs    },
};

const DEFAULT_SEEDS: PlacedCard<CardType>[] = [
  { id: 'docker-infra-default', type: 'containers', side: 'left', height: 240 },
];

export function WorldDockerPage() {
  return (
    <WorldShell
      colorKey="docker"
      imageCandidates={['/world/docker.webp', '/world/docker.png', '/world/docker.jpg']}
      imageAlt="Docker — Container Orchestration"
      storageKey="nexus9.world-docker.layout"
      cardRegistry={CARD_REGISTRY}
      defaultSeeds={DEFAULT_SEEDS}
      worldLabel="Docker"
    />
  );
}
