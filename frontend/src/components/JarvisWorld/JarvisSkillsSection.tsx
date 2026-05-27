/**
 * Nexus9 — JARVIS Skills section.
 *
 * Rendered only on the `/world/jarvis` page, right under the JARVIS Core
 * hero header. Lists the 13 skills JARVIS currently exposes, grouped by
 * type (auto-executable TOML vs Hermes markdown protocols) with an
 * example invocation per skill.
 *
 * Wiring reference:
 *   - Skill loader:  backend/tools/skill_tools.py
 *   - Tools defs:    SKILL_TOOL_DEFS exposed via Claude tool_use
 *   - Chat router:   backend/chat_router.py:412 injects the compact
 *                    catalog into the system prompt at every chat turn,
 *                    so JARVIS always knows these exist.
 */
import { useState } from 'react';
import { type LucideIcon, Container, FileText, Activity, RefreshCw,
         Rss, Code2, Image, Eraser, Lightbulb, BookOpen,
         ListChecks, TrendingUp, Bug, Zap } from 'lucide-react';
import { SkillActivator } from './SkillActivator';

type SkillKind = 'toml' | 'protocol';

interface Skill {
  name:        string;
  kind:        SkillKind;
  icon:        LucideIcon;
  description: string;
  example:     string;
}

const SKILLS: Skill[] = [
  // ── TOML auto-executables ────────────────────────────────────────────────
  {
    name:        'docker-health',
    kind:        'toml',
    icon:        Container,
    description: 'Vérifie l\'état de tous les containers Docker et signale ceux qui sont down.',
    example:     'check la santé des containers',
  },
  {
    name:        'docker-logs-check',
    kind:        'toml',
    icon:        FileText,
    description: 'Récupère les logs récents d\'un container pour diagnostiquer une erreur.',
    example:     'donne-moi les logs de chromadb',
  },
  {
    name:        'docker-stats',
    kind:        'toml',
    icon:        Activity,
    description: 'Affiche la consommation CPU et mémoire de tous les containers.',
    example:     'consommation CPU des containers',
  },
  {
    name:        'docker-restart-container',
    kind:        'toml',
    icon:        RefreshCw,
    description: 'Redémarre un container Docker spécifique sans toucher au reste de la stack.',
    example:     'redémarre le container ollama',
  },

  // ── Hermes markdown protocols ────────────────────────────────────────────
  {
    name:        'systematic-debugging',
    kind:        'protocol',
    icon:        Bug,
    description: 'Protocole de debug en 4 phases : comprendre le bug avant de tenter un fix.',
    example:     'j\'ai un bug bizarre dans Forge, applique systematic-debugging',
  },
  {
    name:        'humanizer',
    kind:        'protocol',
    icon:        Eraser,
    description: 'Nettoie un texte généré par IA — supprime les tics ("furthermore", "leverage", "synergies") et restitue une voix humaine.',
    example:     'applique humanizer sur ce paragraphe',
  },
  {
    name:        'ideation',
    kind:        'protocol',
    icon:        Lightbulb,
    description: 'Génère des idées de projets via contraintes créatives (5W, SCAMPER, etc.).',
    example:     'utilise ideation pour 10 idées STL Etsy',
  },
  {
    name:        'plan',
    kind:        'protocol',
    icon:        ListChecks,
    description: 'Mode plan : rédige un plan markdown dans `.hermes/plans/` sans exécuter de code.',
    example:     'fais un plan pour le refactor du forge_room',
  },
  {
    name:        'codebase-inspection',
    kind:        'protocol',
    icon:        Code2,
    description: 'Audit un codebase avec pygount : LOC, langues, ratios test/source.',
    example:     'inspecte le codebase Nexus9',
  },
  {
    name:        'obsidian',
    kind:        'protocol',
    icon:        BookOpen,
    description: 'CRUD sur ton vault Obsidian : lire, chercher, créer, éditer des notes.',
    example:     'cherche dans Obsidian les notes sur le trading',
  },
  {
    name:        'blogwatcher',
    kind:        'protocol',
    icon:        Rss,
    description: 'Monitor des blogs et flux RSS/Atom via blogwatcher-cli.',
    example:     'watch le flux RSS de Hacker News',
  },
  {
    name:        'polymarket',
    kind:        'protocol',
    icon:        TrendingUp,
    description: 'Query Polymarket : marchés, prix, orderbooks, historique.',
    example:     'quels marchés Polymarket sont chauds cette semaine ?',
  },
  {
    name:        'comfyui',
    kind:        'protocol',
    icon:        Image,
    description: 'Génère images, vidéo, audio avec ComfyUI — install, launch, run workflows.',
    example:     'génère 5 visuels pour ma listing Etsy avec ComfyUI',
  },
];

interface Props {
  accent: string;
  glow:   string;
  subtle: string;
}

export function JarvisSkillsSection({ accent, glow, subtle }: Props) {
  // Which skill (if any) has its ACTIVATE modal open
  const [activeSkill, setActiveSkill] = useState<Skill | null>(null);

  return (
    <section className="flex flex-col gap-3">
      {/* Section header */}
      <div className="flex items-center gap-3 text-[9px] font-bold tracking-[0.3em]"
           style={{ color: 'var(--hud-text-dim)' }}>
        <span style={{ color: accent }}>◆</span>
        SKILLS &mdash; {SKILLS.length} INSTALLED
        <span className="flex-1" style={{ height: 1, background: 'var(--hud-border)' }} />
        <span style={{ color: 'var(--hud-text-dim)' }}>
          chat-invocable · auto-injected in system prompt
        </span>
      </div>

      {/* Intro card */}
      <div
        className="px-4 py-3 text-[11px] leading-relaxed"
        style={{
          color:      'var(--hud-text-dim)',
          background: 'rgba(255,255,255,0.018)',
          border:     '1px solid var(--hud-border)',
          borderLeft: `2px solid ${accent}`,
          borderRadius: 4,
        }}
      >
        JARVIS reçoit le catalogue ci-dessous à chaque tour de chat. Tu peux invoquer
        une skill par son nom (<em style={{ color: accent }}>"applique humanizer sur X"</em>),
        décrire ton intent (<em style={{ color: accent }}>"ce texte sonne trop IA"</em>),
        ou cliquer <strong style={{ color: accent }}>ACTIVATE</strong> sur une card
        ci-dessous pour ouvrir le composer pré-rempli.
      </div>

      {/* Skill grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
        {SKILLS.map((s) => (
          <SkillCard
            key={s.name}
            skill={s}
            accent={accent}
            glow={glow}
            subtle={subtle}
            onActivate={() => setActiveSkill(s)}
          />
        ))}
      </div>

      {/* Activator modal */}
      {activeSkill && (
        <SkillActivator
          skillName={activeSkill.name}
          description={activeSkill.description}
          exampleText={activeSkill.example}
          accent={accent}
          glow={glow}
          subtle={subtle}
          onClose={() => setActiveSkill(null)}
        />
      )}
    </section>
  );
}

function SkillCard({
  skill,
  accent,
  glow,
  subtle,
  onActivate,
}: {
  skill:      Skill;
  accent:     string;
  glow:       string;
  subtle:     string;
  onActivate: () => void;
}) {
  const { name, kind, icon: Icon, description, example } = skill;
  const isToml = kind === 'toml';

  return (
    <article
      className="flex flex-col gap-2 px-4 py-3 transition-colors"
      style={{
        background: 'rgba(2,5,11,0.5)',
        border:     '1px solid var(--hud-border)',
        borderRadius: 4,
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = accent;
        e.currentTarget.style.boxShadow   = `inset 0 0 16px -10px ${glow}`;
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = 'var(--hud-border)';
        e.currentTarget.style.boxShadow   = 'none';
      }}
    >
      {/* Header: icon + name + kind badge */}
      <header className="flex items-center gap-2">
        <span
          className="flex items-center justify-center"
          style={{
            width: 28, height: 28,
            background: subtle,
            color:      accent,
            border:     `1px solid ${accent}`,
            borderRadius: 4,
          }}
        >
          <Icon size={14} strokeWidth={1.7} />
        </span>
        <span className="text-[11px] font-bold tracking-[0.18em] flex-1"
              style={{ color: accent, textShadow: `0 0 6px ${glow}` }}>
          {name.toUpperCase()}
        </span>
        <span
          className="px-1.5 py-0.5 text-[8px] tracking-[0.2em]"
          style={{
            color:      isToml ? 'var(--color-docker)' : 'var(--color-vault)',
            border:     `1px solid ${isToml ? 'var(--color-docker)' : 'var(--color-vault)'}`,
            background: isToml ? 'rgba(0,255,136,0.06)' : 'rgba(168,85,247,0.06)',
            borderRadius: 2,
          }}
        >
          {isToml ? 'AUTO-EXEC' : 'PROTOCOL'}
        </span>
      </header>

      {/* Description */}
      <div className="text-[10.5px] leading-relaxed" style={{ color: 'var(--hud-text)' }}>
        {description}
      </div>

      {/* Example invocation */}
      <div
        className="px-2 py-1 text-[10px] tracking-wide italic flex items-center gap-2"
        style={{
          background: 'rgba(0,0,0,0.4)',
          color:      'var(--hud-text-dim)',
          borderLeft: `2px solid ${accent}`,
          borderRadius: 2,
        }}
      >
        <span style={{ color: accent }}>›</span>
        <span>"{example}"</span>
      </div>

      {/* Activate button — opens the modal pre-filled with the example */}
      <button
        type="button"
        onClick={onActivate}
        aria-label={`Activate ${name}`}
        className="self-end flex items-center gap-2 px-3 py-1 text-[9px] font-bold tracking-[0.22em] transition-colors"
        style={{
          color:        accent,
          background:   'transparent',
          border:       `1px solid ${accent}`,
          borderRadius: 3,
          cursor:       'pointer',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = subtle;
          e.currentTarget.style.boxShadow  = `0 0 12px -4px ${glow}`;
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = 'transparent';
          e.currentTarget.style.boxShadow  = 'none';
        }}
      >
        <Zap size={10} />
        ACTIVATE
      </button>
    </article>
  );
}
