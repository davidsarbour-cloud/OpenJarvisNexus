/**
 * Nexus9 — WorldPage.
 *
 * Generic page for the WORLD sidebar entries (JARVIS, Forge, Commerce,
 * Cyberdeck, Vault, Docker). One component, one route per world, routed
 * in App.tsx via `/world/<key>`.
 *
 * Layout (per world):
 *   ┌────────────────────────────────────────────────────────┐
 *   │  Hero header — icon + name + tagline + live pulse dot  │
 *   ├────────────────────────────────────────────────────────┤
 *   │  LIVE TELEMETRY — pre-wired CommandCenter cards        │
 *   │    (subset of SYSTEM OVERVIEW filtered by world)       │
 *   ├────────────────────────────────────────────────────────┤
 *   │  CUSTOM SLOTS — dashed empty cells, room for future    │
 *   │    world-specific cards + charts.                      │
 *   └────────────────────────────────────────────────────────┘
 */
import type { ComponentType, ReactNode } from 'react';
import {
  Cpu, Hammer, ShoppingBag, Eye, Lock, Container,
  type LucideIcon,
} from 'lucide-react';
import { cssVar, moduleColor, type ModuleKey } from '../lib/colors';
import { CardSlot } from '../systems/CardSlot';
import { SystemHealthCard }   from '../components/CommandCenter/SystemHealthCard';
import { AgentActivityCard }  from '../components/CommandCenter/AgentActivityCard';
import { OllamaStatusCard }   from '../components/CommandCenter/OllamaStatusCard';
import { BudgetCard }         from '../components/CommandCenter/BudgetCard';
import { ForgePipelinesCard } from '../components/CommandCenter/ForgePipelinesCard';
import { DockerLiveCard }     from '../components/CommandCenter/DockerLiveCard';
import { ChromaDbLiveCard }   from '../components/CommandCenter/ChromaDbLiveCard';
import { SonarqubeLiveCard }  from '../components/CommandCenter/SonarqubeLiveCard';
import { ResourceMonitorCard } from '../components/CommandCenter/ResourceMonitorCard';

// ── World metadata ────────────────────────────────────────────────────────────

interface WorldMeta {
  icon:    LucideIcon;
  tagline: string;
}

const WORLD_META: Record<ModuleKey, WorldMeta | null> = {
  jarvis:    { icon: Cpu,         tagline: 'Orchestrator — Claude routing, agents, budget' },
  forge:     { icon: Hammer,      tagline: 'Fabrication — Meshy AI · STL · Bambu pipeline' },
  commerce:  { icon: ShoppingBag, tagline: 'Marketplace — Etsy, scrapers, trend hunting' },
  cyberdeck: { icon: Eye,         tagline: 'Security — code quality, scans, alerts' },
  vault:     { icon: Lock,        tagline: 'Knowledge — Obsidian brain, ChromaDB, memory' },
  docker:    { icon: Container,   tagline: 'Containers — services, stack health, monitoring' },
  // ModuleKey union also lists cortex + security, but those have no sidebar
  // entry and no dedicated page — guard with null so the wiring is explicit.
  cortex:   null,
  security: null,
};

/**
 * Live cards already implemented in CommandCenter that fit naturally under
 * each world. Pure subset of SYSTEM OVERVIEW, regrouped — the same card
 * may be relevant in multiple worlds.
 *
 * `serviceId` mirrors what CommandCenterPage uses so the CardSlot focus
 * animation (orbital → card scroll) keeps working from anywhere.
 */
interface LiveCardEntry {
  serviceId: string;
  Card:      ComponentType;
}

const WORLD_LIVE_CARDS: Record<ModuleKey, LiveCardEntry[]> = {
  jarvis: [
    { serviceId: 'backend',   Card: SystemHealthCard },
    { serviceId: 'bruce',     Card: AgentActivityCard },
    { serviceId: 'ollama',    Card: OllamaStatusCard },
    { serviceId: 'backend',   Card: BudgetCard },
  ],
  forge: [
    { serviceId: 'forge',     Card: ForgePipelinesCard },
  ],
  commerce: [
    // No commerce live card yet — leave empty; placeholder slots show below.
  ],
  cyberdeck: [
    { serviceId: 'sonarqube', Card: SonarqubeLiveCard },
    { serviceId: 'backend',   Card: ResourceMonitorCard },
  ],
  vault: [
    { serviceId: 'chromadb',  Card: ChromaDbLiveCard },
  ],
  docker: [
    { serviceId: 'docker',    Card: DockerLiveCard },
  ],
  cortex:   [],
  security: [],
};

// ── Page component ────────────────────────────────────────────────────────────

interface WorldPageProps {
  worldKey: ModuleKey;
  /** Optional override; defaults to MODULE_COLORS[worldKey].label */
  title?: string;
}

export function WorldPage({ worldKey, title }: WorldPageProps) {
  const meta   = WORLD_META[worldKey];
  const color  = moduleColor(worldKey);
  const accent = cssVar(worldKey);
  const displayTitle = (title ?? color.label).toUpperCase();
  const liveCards = WORLD_LIVE_CARDS[worldKey];

  if (!meta) {
    // Defensive: ModuleKey covers worlds without dedicated pages (cortex,
    // security). The router shouldn't reach here, but render a clean fallback.
    return (
      <div className="flex-1 flex items-center justify-center text-[11px] tracking-[0.22em]"
           style={{ color: 'var(--hud-text-dim)' }}>
        WORLD NOT CONFIGURED · {displayTitle}
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-5">
      <Hero
        Icon={meta.icon}
        title={displayTitle}
        tagline={meta.tagline}
        accent={accent}
        glow={color.glow}
        subtle={color.subtle}
      />

      {liveCards.length > 0 && (
        <Section label="LIVE TELEMETRY" accent={accent}>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 xl:grid-cols-6 2xl:grid-cols-10 gap-3">
            {liveCards.map((entry, i) => {
              const { Card } = entry;
              return (
                <CardSlot key={i} serviceId={entry.serviceId}>
                  <Card />
                </CardSlot>
              );
            })}
          </div>
        </Section>
      )}

      <Section label="CUSTOM SLOTS — drop new cards here" accent={accent}>
        <PlaceholderGrid accent={accent} count={liveCards.length > 0 ? 5 : 10} />
      </Section>
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

interface HeroProps {
  Icon:    LucideIcon;
  title:   string;
  tagline: string;
  accent:  string;
  glow:    string;
  subtle:  string;
}
function Hero({ Icon, title, tagline, accent, glow, subtle }: HeroProps) {
  return (
    <header
      className="relative flex items-center gap-4 px-5 py-4"
      style={{
        border:     `1px solid ${accent}`,
        background: `linear-gradient(135deg, ${subtle} 0%, transparent 60%)`,
        boxShadow:  `0 0 24px -8px ${glow}, inset 0 0 32px -16px ${glow}`,
        borderRadius: 4,
      }}
    >
      <div
        className="flex items-center justify-center"
        style={{
          width: 44, height: 44,
          background: subtle,
          border:     `1px solid ${accent}`,
          color:      accent,
          borderRadius: 4,
        }}
      >
        <Icon size={22} />
      </div>
      <div className="flex flex-col flex-1 gap-1">
        <div className="text-base font-bold tracking-[0.3em]" style={{ color: accent, textShadow: `0 0 12px ${glow}` }}>
          {title}
        </div>
        <div className="text-[10px] tracking-[0.18em]" style={{ color: 'var(--hud-text-dim)' }}>
          {tagline}
        </div>
      </div>
      <PulseDot accent={accent} glow={glow} />
    </header>
  );
}

function PulseDot({ accent, glow }: { accent: string; glow: string }) {
  return (
    <span className="relative flex items-center justify-center" style={{ width: 14, height: 14 }}>
      <span
        className="absolute inset-0 rounded-full"
        style={{ background: glow, animation: 'world-pulse 2.4s ease-out infinite' }}
      />
      <span
        className="rounded-full"
        style={{ width: 7, height: 7, background: accent, boxShadow: `0 0 8px ${accent}` }}
      />
      <style>{`
        @keyframes world-pulse {
          0%   { transform: scale(0.6); opacity: 0.7; }
          80%  { transform: scale(1.8); opacity: 0;   }
          100% { transform: scale(1.8); opacity: 0;   }
        }
      `}</style>
    </span>
  );
}

function Section({
  label,
  accent,
  children,
}: {
  label:    string;
  accent:   string;
  children: ReactNode;
}) {
  return (
    <section className="flex flex-col gap-2">
      <div className="flex items-center gap-3 text-[9px] font-bold tracking-[0.3em]"
           style={{ color: 'var(--hud-text-dim)' }}>
        <span style={{ color: accent }}>◆</span>
        {label}
        <span className="flex-1" style={{ height: 1, background: 'var(--hud-border)' }} />
      </div>
      {children}
    </section>
  );
}

function PlaceholderGrid({ accent, count }: { accent: string; count: number }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 xl:grid-cols-6 2xl:grid-cols-10 gap-3">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="aspect-[5/4] flex items-center justify-center text-[8px] tracking-[0.25em]"
          style={{
            border: `1px dashed ${accent}`,
            background: 'rgba(255,255,255,0.012)',
            color: 'var(--hud-text-dim)',
            borderRadius: 4,
            opacity: 0.55,
          }}
        >
          + SLOT
        </div>
      ))}
    </div>
  );
}
