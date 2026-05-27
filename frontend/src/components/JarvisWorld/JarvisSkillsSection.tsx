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
type Cadence   = 'daily' | 'weekly';

interface Skill {
  name:        string;
  kind:        SkillKind;
  icon:        LucideIcon;
  description: string;
  example:     string;
  /**
   * Marks a skill that already runs on a recurring APScheduler cron
   * (see daily_tasks.py). When set, the card hides the manual ACTIVATE
   * button — the schedule covers it — and shows an "AUTO · {cadence}"
   * tag instead.
   */
  scheduledAuto?: Cadence;
}

const SKILLS: Skill[] = [
  // ── TOML auto-executables ────────────────────────────────────────────────
  {
    name:          'docker-health',
    kind:          'toml',
    icon:          Container,
    description:   'Vérifie l\'état de tous les containers Docker et signale ceux qui sont down.',
    example:       'check la santé des containers',
    scheduledAuto: 'daily',
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
    name:          'ideation',
    kind:          'protocol',
    icon:          Lightbulb,
    description:   'Génère des idées de projets via contraintes créatives (5W, SCAMPER, etc.).',
    example:       'utilise ideation pour 10 idées STL Etsy',
    scheduledAuto: 'weekly',
  },
  {
    name:        'plan',
    kind:        'protocol',
    icon:        ListChecks,
    description: 'Mode plan : rédige un plan markdown dans `.hermes/plans/` sans exécuter de code.',
    example:     'fais un plan pour le refactor du forge_room',
  },
  {
    name:          'codebase-inspection',
    kind:          'protocol',
    icon:          Code2,
    description:   'Audit un codebase avec pygount : LOC, langues, ratios test/source.',
    example:       'inspecte le codebase Nexus9',
    scheduledAuto: 'weekly',
  },
  {
    name:        'obsidian',
    kind:        'protocol',
    icon:        BookOpen,
    description: 'CRUD sur ton vault Obsidian : lire, chercher, créer, éditer des notes.',
    example:     'cherche dans Obsidian les notes sur le trading',
  },
  {
    name:          'blogwatcher',
    kind:          'protocol',
    icon:          Rss,
    description:   'Monitor des blogs et flux RSS/Atom via blogwatcher-cli.',
    example:       'watch le flux RSS de Hacker News',
    scheduledAuto: 'daily',
  },
  {
    name:          'polymarket',
    kind:          'protocol',
    icon:          TrendingUp,
    description:   'Query Polymarket : marchés, prix, orderbooks, historique.',
    example:       'quels marchés Polymarket sont chauds cette semaine ?',
    scheduledAuto: 'daily',
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

  // Split skills by execution mode for the 2-column layout
  const autoSkills   = SKILLS.filter((s) =>  s.scheduledAuto);
  const manualSkills = SKILLS.filter((s) => !s.scheduledAuto);

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
        JARVIS reçoit le catalogue à chaque tour de chat. Cliquer une card
        ouvre le composer pré-rempli, ou tu peux invoquer par nom dans le chat
        (<em style={{ color: accent }}>"applique humanizer sur X"</em>).
      </div>

      {/* 3-column layout — ACTIVATE left · JARVIS portrait center · SCHEDULED right */}
      <div
        className="grid gap-3"
        style={{
          gridTemplateColumns: 'minmax(260px, 320px) 1fr minmax(260px, 320px)',
          minHeight: 520,
        }}
      >
        <SkillColumn
          label={`ACTIVATE · ${manualSkills.length} ON-DEMAND`}
          accent={accent}
          glow={glow}
          subtle={subtle}
          skills={manualSkills}
          onActivate={(s) => setActiveSkill(s)}
        />

        <JarvisPortrait accent={accent} glow={glow} />

        <SkillColumn
          label={`AUTO · ${autoSkills.length} SCHEDULED`}
          accent={accent}
          glow={glow}
          subtle={subtle}
          skills={autoSkills}
        />
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

/**
 * Centre column of the 3-col JARVIS layout: a hero portrait of the
 * JARVIS image with HUD overlays (low-amplitude CRT scan lines, slow
 * vertical sweep, vignette breath). The image lives in
 * frontend/public/world/ — we try a few candidate names so it works
 * regardless of how the user saved it.
 */
function JarvisPortrait({ accent, glow }: { accent: string; glow: string }) {
  const candidates = [
    '/world/jarvis.png',
    '/world/JARVIS.png',
    '/world/jarvis.jpg',
    '/world/jarvis.webp',
  ];
  const [idx, setIdx]       = useState(0);
  const [failed, setFailed] = useState(false);

  const handleError = () => {
    if (idx + 1 < candidates.length) setIdx(idx + 1);
    else setFailed(true);
  };

  return (
    <div
      className="relative overflow-hidden flex items-center justify-center"
      style={{
        background:   'rgba(2,5,11,0.6)',
        border:       `1px solid ${accent}`,
        borderRadius: 4,
        boxShadow:    `0 0 28px -10px ${glow}, inset 0 0 36px -16px ${glow}`,
      }}
    >
      {!failed ? (
        <>
          {/* Blurred ambient copy — gentle breathing */}
          <img
            src={candidates[idx]}
            alt=""
            aria-hidden="true"
            onError={handleError}
            className="jarvis-ambient"
            style={{
              position: 'absolute',
              inset: 0,
              width:  '100%',
              height: '100%',
              objectFit:     'cover',
              objectPosition: 'center',
              filter:    'blur(36px) saturate(1.15) brightness(0.55)',
              transform: 'scale(1.12)',
              opacity:   0.85,
              display:   'block',
            }}
          />
          {/* Foreground portrait — fits its natural aspect ratio */}
          <img
            src={candidates[idx]}
            alt="JARVIS Core"
            onError={handleError}
            style={{
              position: 'absolute',
              inset: 0,
              width:  '100%',
              height: '100%',
              objectFit:      'contain',
              objectPosition: 'center',
              display:        'block',
            }}
          />
          {/* CRT scan lines — very faint cyan tint */}
          <div
            aria-hidden="true"
            style={{
              position: 'absolute', inset: 0,
              background:
                'repeating-linear-gradient(0deg, transparent 0px, transparent 3px, rgba(0,212,255,0.025) 3px, rgba(0,212,255,0.025) 4px)',
              pointerEvents: 'none',
              mixBlendMode:  'overlay',
            }}
          />
          {/* Slow vertical sweep */}
          <div className="jarvis-sweep" aria-hidden="true" />
          {/* Vignette breath */}
          <div className="jarvis-vignette" aria-hidden="true" />

          <style>{`
            @keyframes jarvis-ambient-breath {
              0%, 100% { opacity: 0.78; }
              50%      { opacity: 0.94; }
            }
            .jarvis-ambient { animation: jarvis-ambient-breath 9s ease-in-out infinite; }

            @keyframes jarvis-sweep {
              0%   { transform: translateY(-15%); opacity: 0;    }
              12%  { opacity: 0.42; }
              88%  { opacity: 0.42; }
              100% { transform: translateY(110%); opacity: 0;    }
            }
            .jarvis-sweep {
              position: absolute;
              left: 0; right: 0; top: 0;
              height: 80px;
              background: linear-gradient(180deg, transparent 0%, rgba(0,212,255,0.10) 50%, transparent 100%);
              pointer-events: none;
              animation: jarvis-sweep 24s linear infinite;
              will-change: transform;
            }
            @keyframes jarvis-vignette {
              0%, 100% { box-shadow: inset 0 0 90px -10px rgba(0,0,0,0.55); }
              50%      { box-shadow: inset 0 0 130px -4px rgba(0,0,0,0.7);  }
            }
            .jarvis-vignette {
              position: absolute;
              inset: 0;
              pointer-events: none;
              animation: jarvis-vignette 11s ease-in-out infinite;
            }
          `}</style>
        </>
      ) : (
        <div className="flex flex-col items-center justify-center gap-3 px-6 text-center"
             style={{ color: 'var(--hud-text-dim)' }}>
          <div className="text-[10px] font-bold tracking-[0.3em]"
               style={{ color: accent }}>
            ◆ JARVIS IMAGE NOT FOUND
          </div>
          <div className="text-[10px] tracking-wider">
            Drop your portrait at one of:
          </div>
          <pre className="text-[9px] p-3"
               style={{
                 background: 'rgba(0,212,255,0.05)',
                 border:     `1px solid ${accent}`,
                 color:      'var(--hud-text)',
                 borderRadius: 3,
               }}>
{`public/world/jarvis.png
public/world/jarvis.jpg
public/world/jarvis.webp`}
          </pre>
          <div className="text-[9px] tracking-wider opacity-70">refresh after</div>
        </div>
      )}
    </div>
  );
}


function SkillColumn({
  label,
  accent,
  glow,
  subtle,
  skills,
  onActivate,
}: {
  label:       string;
  accent:      string;
  glow:        string;
  subtle:      string;
  skills:      Skill[];
  onActivate?: (s: Skill) => void;
}) {
  return (
    <div className="flex flex-col gap-2">
      <div className="text-[8px] font-bold tracking-[0.3em] pb-1"
           style={{ color: 'var(--hud-text-dim)', borderBottom: '1px solid var(--hud-border)' }}>
        {label}
      </div>
      <div className="flex flex-col gap-1.5">
        {skills.map((s) => (
          <SkillCard
            key={s.name}
            skill={s}
            accent={accent}
            glow={glow}
            subtle={subtle}
            onActivate={onActivate ? () => onActivate(s) : undefined}
          />
        ))}
      </div>
    </div>
  );
}

function SkillCard({
  skill,
  accent,
  glow,
  subtle,
  onActivate,
}: {
  skill:       Skill;
  accent:      string;
  glow:        string;
  subtle:      string;
  onActivate?: () => void;
}) {
  const { name, kind, icon: Icon, description, example, scheduledAuto } = skill;
  const isToml    = kind === 'toml';
  const clickable = !scheduledAuto && !!onActivate;

  const wrapperProps = clickable
    ? {
        role:     'button' as const,
        tabIndex: 0,
        onClick:  onActivate,
        onKeyDown: (e: React.KeyboardEvent) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            onActivate?.();
          }
        },
        title:    `Click to open the composer pre-filled with: "${example}"`,
      }
    : { title: `Runs automatically on a ${scheduledAuto} APScheduler cron — see AUTOMATION SCHEDULE.` };

  return (
    <article
      {...wrapperProps}
      className="flex items-center gap-2 px-2 py-1.5 transition-colors"
      style={{
        background: 'rgba(2,5,11,0.5)',
        border:     '1px solid var(--hud-border)',
        borderRadius: 3,
        cursor:     clickable ? 'pointer' : 'default',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = accent;
        e.currentTarget.style.boxShadow   = `inset 0 0 12px -8px ${glow}`;
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = 'var(--hud-border)';
        e.currentTarget.style.boxShadow   = 'none';
      }}
    >
      {/* Icon — small square chip */}
      <span
        className="flex items-center justify-center shrink-0"
        style={{
          width: 22, height: 22,
          background:   subtle,
          color:        accent,
          border:       `1px solid ${accent}`,
          borderRadius: 3,
        }}
      >
        <Icon size={11} strokeWidth={1.8} />
      </span>

      {/* Name + truncated description on one row */}
      <div className="flex flex-col min-w-0 flex-1 leading-tight">
        <span className="text-[10px] font-bold tracking-[0.18em] truncate"
              style={{ color: accent }}>
          {name.toUpperCase()}
        </span>
        <span className="text-[9.5px] truncate"
              style={{ color: 'var(--hud-text-dim)' }}>
          {description}
        </span>
      </div>

      {/* Kind badge (auto-exec / protocol) */}
      <span
        className="shrink-0 px-1 py-px text-[7.5px] tracking-[0.2em]"
        style={{
          color:        isToml ? 'var(--color-docker)' : 'var(--color-vault)',
          border:       `1px solid ${isToml ? 'var(--color-docker)' : 'var(--color-vault)'}`,
          background:   isToml ? 'rgba(0,255,136,0.06)' : 'rgba(168,85,247,0.06)',
          borderRadius: 2,
        }}
      >
        {isToml ? 'TOML' : 'PROTO'}
      </span>

      {/* Trailing tag — either AUTO chip or a tiny zap icon */}
      {scheduledAuto ? (
        <span
          className="shrink-0 px-1 py-px text-[7.5px] tracking-[0.2em]"
          style={{
            color:        'var(--hud-text-dim)',
            border:       '1px dashed var(--hud-border)',
            borderRadius: 2,
          }}
        >
          {scheduledAuto.toUpperCase()}
        </span>
      ) : (
        <span
          className="shrink-0 flex items-center justify-center"
          style={{
            width: 18, height: 18,
            color:      accent,
            borderRadius: 2,
          }}
          aria-hidden
        >
          <Zap size={11} />
        </span>
      )}
    </article>
  );
}
