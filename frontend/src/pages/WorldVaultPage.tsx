/**
 * Nexus9 — World · Vault.
 *
 * Thin wrapper around <WorldShell>. Pre-seeds CHROMADB (left) +
 * EVENT LOGGER (right) on first visit. Existing users get the same
 * seeds injected once, gated by LAYOUT_VERSION to avoid duplicate
 * re-injection on every load.
 */
import {
  BookOpen, CalendarClock, CloudUpload, Database, FileText, Layers,
  Network, Sun, Unlink,
} from 'lucide-react';
import { AgentActivityCard } from '../components/CommandCenter/AgentActivityCard';
import { ChromaDbLiveCard } from '../components/CommandCenter/ChromaDbLiveCard';
import { ScheduledTasksCard } from '../components/CommandCenter/ScheduledTasksCard';
import { NamedSatellite, LiveSatellite } from '../components/CommandCenter/FunctionalSatellites';
import { WorldShell, type CardDef, type PlacedCard } from '../components/WorldShell/WorldShell';

const EventLoggerVault = () => <NamedSatellite title="EVENT LOGGER"  colorKey="vault" />;
const BackupVault      = () => <NamedSatellite title="BACKUP"         colorKey="vault" />;
const CacheRelayVault  = () => <NamedSatellite title="CACHE RELAY"    colorKey="vault" />;
const VaultGrowth      = () => <LiveSatellite  title="VAULT GROWTH"   colorKey="vault" snapshotKey="vault_growth"  />;
const OrphanAlert      = () => <LiveSatellite  title="ORPHAN ALERT"   colorKey="vault" snapshotKey="orphan_alert"  />;
const MorningBrief     = () => <LiveSatellite  title="MORNING BRIEF"  colorKey="vault" snapshotKey="morning_brief" />;

type CardType =
  | 'chromadb' | 'eventlogger' | 'agents' | 'backup' | 'cache'
  | 'scheduled' | 'growth' | 'orphans' | 'morningbrief';

const CARD_REGISTRY: Record<CardType, CardDef> = {
  chromadb:     { label: 'CHROMADB',      sub: 'Vector store',             icon: Database,       Card: ChromaDbLiveCard  },
  eventlogger:  { label: 'EVENT LOGGER',  sub: 'Action log capture',       icon: FileText,       Card: EventLoggerVault  },
  agents:       { label: 'AGENTS LINK',   sub: 'Memory consumers',         icon: Network,        Card: AgentActivityCard },
  backup:       { label: 'BACKUP',        sub: 'File / pipeline backups',  icon: CloudUpload,    Card: BackupVault       },
  cache:        { label: 'CACHE RELAY',   sub: 'Hot asset shortcuts',      icon: Layers,         Card: CacheRelayVault   },
  scheduled:    { label: 'SCHEDULED',     sub: 'APScheduler jobs',         icon: CalendarClock,  Card: ScheduledTasksCard },
  growth:       { label: 'VAULT GROWTH',  sub: 'Notes today / total',      icon: BookOpen,       Card: VaultGrowth       },
  orphans:      { label: 'ORPHAN ALERT',  sub: 'Notes without backlinks',  icon: Unlink,         Card: OrphanAlert       },
  morningbrief: { label: 'MORNING BRIEF', sub: 'Daily brief 07:30',        icon: Sun,            Card: MorningBrief      },
};

const STORAGE_KEY = 'nexus9.world-vault.layout';
const VERSION_KEY = `${STORAGE_KEY}.version`;
const LAYOUT_VERSION = 'v2';

const DEFAULT_SEEDS: PlacedCard<CardType>[] = [
  { id: 'chromadb-default',    type: 'chromadb',    side: 'left',  height: 240 },
  { id: 'eventlogger-default', type: 'eventlogger', side: 'right', height: 240 },
];

// One-time migration: if the user has already visited the Vault page on
// an older version, inject any missing seed cards before WorldShell
// mounts. Runs at module load (lazy import = first navigation here).
(function migrateLayout() {
  try {
    const currentVersion = localStorage.getItem(VERSION_KEY);
    if (currentVersion === LAYOUT_VERSION) return;
    const raw = localStorage.getItem(STORAGE_KEY);
    let cards: PlacedCard<CardType>[] = [];
    if (raw !== null) {
      try {
        const parsed = JSON.parse(raw) as unknown;
        if (Array.isArray(parsed)) cards = parsed as PlacedCard<CardType>[];
      } catch { /* corrupted — fall through to fresh seeds */ }
    }
    let changed = raw === null;
    for (const seed of DEFAULT_SEEDS) {
      if (!cards.some((c) => c?.type === seed.type)) {
        cards.push(seed);
        changed = true;
      }
    }
    if (changed) localStorage.setItem(STORAGE_KEY, JSON.stringify(cards));
    localStorage.setItem(VERSION_KEY, LAYOUT_VERSION);
  } catch { /* private mode / quota — accept the loss, defaults will still seed on first visit */ }
})();

export function WorldVaultPage() {
  return (
    <WorldShell
      colorKey="vault"
      imageCandidates={['/world/vault.webp', '/world/vault.png', '/world/vault.jpg']}
      imageAlt="Vault — Knowledge Repository"
      storageKey={STORAGE_KEY}
      cardRegistry={CARD_REGISTRY}
      defaultSeeds={DEFAULT_SEEDS}
      worldLabel="Vault"
    />
  );
}
