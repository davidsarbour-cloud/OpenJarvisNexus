/**
 * Nexus9 — World · Cyberdeck.
 *
 * Thin wrapper around <WorldShell>. The cyberdeck red/pink accent and
 * the security / observability card mix is declared here; the
 * dashboard mechanics live in the shell.
 */
import {
  AlertTriangle, Bell, Brain, Cpu, Gauge, GitFork, Megaphone, MessageSquare,
  Radio, Thermometer,
} from 'lucide-react';
import { OllamaStatusCard } from '../components/CommandCenter/OllamaStatusCard';
import { ResourceMonitorCard } from '../components/CommandCenter/ResourceMonitorCard';
import { NamedSatellite, LiveSatellite } from '../components/CommandCenter/FunctionalSatellites';
import { WorldShell, type CardDef } from '../components/WorldShell/WorldShell';

const NotificationBeacon    = () => <NamedSatellite title="NOTIFICATION BEACON"    colorKey="cyberdeck" />;
const NotificationAmplifier = () => <NamedSatellite title="NOTIFICATION AMPLIFIER" colorKey="cyberdeck" />;
const AiResearchProbe       = () => <NamedSatellite title="AI RESEARCH PROBE"      colorKey="cyberdeck" />;
const GpuTemp               = () => <LiveSatellite  title="GPU TEMP"               colorKey="cyberdeck" snapshotKey="gpu_temp" />;
const ErrorLogTail          = () => <LiveSatellite  title="ERROR LOG TAIL"         colorKey="cyberdeck" snapshotKey="error_log" />;
const ApiRateLimits         = () => <NamedSatellite title="API RATE LIMITS"        colorKey="cyberdeck" />;
const TelegramActivity      = () => <LiveSatellite  title="TELEGRAM ACTIVITY"      colorKey="cyberdeck" snapshotKey="telegram_activity" />;
const ModelRouting          = () => <LiveSatellite  title="MODEL ROUTING"          colorKey="cyberdeck" snapshotKey="model_routing"     />;

type CardType =
  | 'signal' | 'load' | 'beacon' | 'amplifier' | 'airesearch'
  | 'gpu' | 'errorlog' | 'ratelimits' | 'telegram' | 'routing';

const CARD_REGISTRY: Record<CardType, CardDef> = {
  signal:     { label: 'SIGNAL FEED',            sub: 'Ollama heartbeat',          icon: Radio,          Card: OllamaStatusCard      },
  load:       { label: 'COMPUTE LOAD',           sub: 'CPU / RAM / VRAM',          icon: Cpu,            Card: ResourceMonitorCard   },
  beacon:     { label: 'NOTIFICATION BEACON',    sub: 'Alerts / system messages',  icon: Bell,           Card: NotificationBeacon    },
  amplifier:  { label: 'NOTIFICATION AMPLIFIER', sub: 'Priority alerts filter',    icon: Megaphone,      Card: NotificationAmplifier },
  airesearch: { label: 'AI RESEARCH PROBE',      sub: 'Suggestions for agents',    icon: Brain,          Card: AiResearchProbe       },
  gpu:        { label: 'GPU TEMP',               sub: 'RTX 4070 Super temp/util',  icon: Thermometer,    Card: GpuTemp               },
  errorlog:   { label: 'ERROR LOG TAIL',         sub: 'Recent backend errors',     icon: AlertTriangle,  Card: ErrorLogTail          },
  ratelimits: { label: 'API RATE LIMITS',        sub: 'Anthropic · Meshy · Etsy',  icon: Gauge,          Card: ApiRateLimits         },
  telegram:   { label: 'TELEGRAM ACTIVITY',      sub: 'David ↔ JARVIS messages',   icon: MessageSquare,  Card: TelegramActivity      },
  routing:    { label: 'MODEL ROUTING',          sub: 'Agents routed today',       icon: GitFork,        Card: ModelRouting          },
};

export function WorldCyberdeckPage() {
  return (
    <WorldShell
      colorKey="cyberdeck"
      imageCandidates={['/world/cyberdeck.webp', '/world/cyberdeck.png', '/world/cyberdeck.jpg']}
      imageAlt="Cyberdeck — Security & Observability"
      storageKey="nexus9.world-cyberdeck.layout"
      cardRegistry={CARD_REGISTRY}
      worldLabel="Cyberdeck"
    />
  );
}
