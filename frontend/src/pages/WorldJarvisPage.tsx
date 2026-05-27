/**
 * Nexus9 — World · JARVIS.
 *
 * Same shell as the Forge page: 3-column pinned layout, big image in the
 * center, skills docked to the borders.
 *   ┌────────────┬──────────────────────────┬────────────┐
 *   │ ACTIVATE   │   JARVIS Core image      │  AUTO      │
 *   │ on-demand  │   (cinematic + subtle    │ scheduled  │
 *   │  skills    │    sci-fi overlays)      │  skills    │
 *   └────────────┴──────────────────────────┴────────────┘
 *
 * No "SKILLS · N INSTALLED" header, no intro card — just the skills and
 * the picture in the frame. Manual skills open a SkillActivator modal on
 * click; scheduled ones are read-only (covered by APScheduler).
 */
import { useState } from 'react';
import type { LucideIcon } from 'lucide-react';
import {
  Container, FileText, Activity, RefreshCw,
  Rss, Code2, Image as ImageIcon, Eraser, Lightbulb, BookOpen,
  ListChecks, TrendingUp, Bug, Zap,
} from 'lucide-react';
import { SkillActivator } from '../components/JarvisWorld/SkillActivator';

const CANDIDATES = ['/world/jarvis.png', '/world/jarvis.jpg', '/world/jarvis.webp'];
const DOCK_WIDTH = 300;

type SkillKind = 'toml' | 'protocol';
type Cadence   = 'daily' | 'weekly';

interface Skill {
  name:           string;
  kind:           SkillKind;
  icon:           LucideIcon;
  description:    string;
  example:        string;
  scheduledAuto?: Cadence;
}

const SKILLS: Skill[] = [
  { name: 'docker-health',            kind: 'toml',     icon: Container,   description: "Vérifie l'état de tous les containers Docker et signale ceux qui sont down.", example: 'check la santé des containers', scheduledAuto: 'daily' },
  { name: 'docker-logs-check',        kind: 'toml',     icon: FileText,    description: "Récupère les logs récents d'un container pour diagnostiquer une erreur.",     example: 'donne-moi les logs de chromadb' },
  { name: 'docker-stats',             kind: 'toml',     icon: Activity,    description: 'Affiche la consommation CPU et mémoire de tous les containers.',              example: 'consommation CPU des containers' },
  { name: 'docker-restart-container', kind: 'toml',     icon: RefreshCw,   description: 'Redémarre un container Docker spécifique sans toucher au reste de la stack.', example: 'redémarre le container ollama' },
  { name: 'systematic-debugging',     kind: 'protocol', icon: Bug,         description: 'Protocole de debug en 4 phases : comprendre le bug avant de tenter un fix.',  example: "applique systematic-debugging sur ce bug" },
  { name: 'humanizer',                kind: 'protocol', icon: Eraser,      description: 'Nettoie un texte généré par IA — supprime les tics et restitue une voix humaine.', example: 'applique humanizer sur ce paragraphe' },
  { name: 'ideation',                 kind: 'protocol', icon: Lightbulb,   description: 'Génère des idées de projets via contraintes créatives (5W, SCAMPER, etc.).',  example: 'utilise ideation pour 10 idées STL Etsy',  scheduledAuto: 'weekly' },
  { name: 'plan',                     kind: 'protocol', icon: ListChecks,  description: 'Mode plan : rédige un plan markdown sans exécuter de code.',                   example: 'fais un plan pour le refactor du forge_room' },
  { name: 'codebase-inspection',      kind: 'protocol', icon: Code2,       description: 'Audit un codebase avec pygount : LOC, langues, ratios test/source.',          example: 'inspecte le codebase Nexus9',              scheduledAuto: 'weekly' },
  { name: 'obsidian',                 kind: 'protocol', icon: BookOpen,    description: 'CRUD sur ton vault Obsidian : lire, chercher, créer, éditer des notes.',      example: 'cherche dans Obsidian les notes sur le trading' },
  { name: 'blogwatcher',              kind: 'protocol', icon: Rss,         description: 'Monitor des blogs et flux RSS/Atom via blogwatcher-cli.',                     example: 'watch le flux RSS de Hacker News',         scheduledAuto: 'daily'  },
  { name: 'polymarket',               kind: 'protocol', icon: TrendingUp,  description: 'Query Polymarket : marchés, prix, orderbooks, historique.',                   example: 'quels marchés Polymarket sont chauds ?',   scheduledAuto: 'daily'  },
  { name: 'comfyui',                  kind: 'protocol', icon: ImageIcon,   description: 'Génère images, vidéo, audio avec ComfyUI — install, launch, run workflows.', example: 'génère 5 visuels Etsy avec ComfyUI' },
];

// ── Page component ──────────────────────────────────────────────────────────

export function WorldJarvisPage() {
  const [idx, setIdx] = useState(0);
  const [allFailed, setAllFailed] = useState(false);
  const [activeSkill, setActiveSkill] = useState<Skill | null>(null);

  const handleImgError = () => {
    if (idx + 1 < CANDIDATES.length) setIdx(idx + 1);
    else setAllFailed(true);
  };

  const manualSkills = SKILLS.filter((s) => !s.scheduledAuto);
  const autoSkills   = SKILLS.filter((s) =>  s.scheduledAuto);

  return (
    <div
      className="flex-1 flex flex-row overflow-hidden min-h-0"
      style={{ background: 'var(--hud-bg)' }}
    >
      {!allFailed ? (
        <>
          {/* LEFT — manual ACTIVATE skills */}
          <SkillDock
            side="left"
            label={`ACTIVATE · ${manualSkills.length} ON-DEMAND`}
            skills={manualSkills}
            onActivate={(s) => setActiveSkill(s)}
          />

          {/* CENTER — big JARVIS image */}
          <ImageArea src={CANDIDATES[idx]} onError={handleImgError} />

          {/* RIGHT — AUTO scheduled skills */}
          <SkillDock
            side="right"
            label={`AUTO · ${autoSkills.length} SCHEDULED`}
            skills={autoSkills}
          />
        </>
      ) : (
        <NotFoundOverlay />
      )}

      {/* Activator modal for clickable skills */}
      {activeSkill && (
        <SkillActivator
          skillName={activeSkill.name}
          description={activeSkill.description}
          exampleText={activeSkill.example}
          accent="var(--color-jarvis)"
          glow="var(--color-jarvis-glow)"
          subtle="rgba(0, 212, 255, 0.10)"
          onClose={() => setActiveSkill(null)}
        />
      )}
    </div>
  );
}

// ── Image area (center column with low sci-fi overlays, cyan tint) ──────────

function ImageArea({ src, onError }: { src: string; onError: () => void }) {
  return (
    <div
      className="flex-1 relative overflow-hidden flex items-center justify-center"
      style={{ background: 'var(--hud-bg)' }}
    >
      {/* Main image — fills the column edge-to-edge with `cover` so it
          reaches the skill docks on both sides (no empty gap). */}
      <img
        src={src}
        alt="JARVIS Core"
        onError={onError}
        style={{
          position: 'absolute',
          inset: 0,
          width:  '100%',
          height: '100%',
          objectFit:      'cover',
          objectPosition: 'center',
          display:        'block',
        }}
      />

      {/* CRT scan lines — cyan tint, very faint */}
      <div
        aria-hidden="true"
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'repeating-linear-gradient(0deg, transparent 0px, transparent 3px, rgba(0,212,255,0.025) 3px, rgba(0,212,255,0.025) 4px)',
          pointerEvents: 'none',
          mixBlendMode:  'overlay',
        }}
      />

      {/* Vignette breath */}
      <div className="jarvis-vignette" aria-hidden="true" />

      <style>{`
        @keyframes jarvis-vignette {
          0%, 100% { box-shadow: inset 0 0 90px -10px rgba(0,0,0,0.55); }
          50%       { box-shadow: inset 0 0 130px -4px rgba(0,0,0,0.7);  }
        }
        .jarvis-vignette {
          position: absolute;
          inset: 0;
          pointer-events: none;
          animation: jarvis-vignette 11s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
}

// ── Skill dock (left or right) ──────────────────────────────────────────────

interface SkillDockProps {
  side:        'left' | 'right';
  label:       string;
  skills:      Skill[];
  onActivate?: (s: Skill) => void;
}

function SkillDock({ side, label, skills, onActivate }: SkillDockProps) {
  return (
    <div
      style={{
        width: DOCK_WIDTH,
        flexShrink: 0,
        display: 'flex',
        flexDirection: 'column',
        gap: 6,
        padding: 10,
        overflowY: 'auto',
        background: 'rgba(2,4,12,0.55)',
        borderLeft:  side === 'right' ? '1px solid var(--hud-border)' : 'none',
        borderRight: side === 'left'  ? '1px solid var(--hud-border)' : 'none',
        fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
      }}
    >
      <div
        className="text-[8px] font-bold tracking-[0.3em] pb-1.5"
        style={{
          color: 'var(--hud-text-dim)',
          borderBottom: '1px solid var(--hud-border)',
        }}
      >
        {label}
      </div>

      <div className="flex flex-col gap-1.5 mt-1">
        {skills.map((s) => (
          <SkillCard
            key={s.name}
            skill={s}
            onActivate={onActivate ? () => onActivate(s) : undefined}
          />
        ))}
      </div>
    </div>
  );
}

// ── Skill card ──────────────────────────────────────────────────────────────

function SkillCard({
  skill, onActivate,
}: { skill: Skill; onActivate?: () => void }) {
  const { name, kind, icon: Icon, description, example, scheduledAuto } = skill;
  const accent  = 'var(--color-jarvis)';
  const glow    = 'var(--color-jarvis-glow)';
  const subtle  = 'rgba(0, 212, 255, 0.10)';
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
        title: `Click to open the composer pre-filled with: "${example}"`,
      }
    : { title: `Runs automatically on a ${scheduledAuto} cron — see AUTOMATION SCHEDULE.` };

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

      <div className="flex flex-col min-w-0 flex-1 leading-tight">
        <span className="text-[10px] font-bold tracking-[0.18em] truncate" style={{ color: accent }}>
          {name.toUpperCase()}
        </span>
        <span className="text-[9.5px] truncate" style={{ color: 'var(--hud-text-dim)' }}>
          {description}
        </span>
      </div>

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

      {scheduledAuto ? (
        <span
          className="shrink-0 px-1 py-px text-[7.5px] tracking-[0.2em]"
          style={{
            color: 'var(--hud-text-dim)',
            border: '1px dashed var(--hud-border)',
            borderRadius: 2,
          }}
        >
          {scheduledAuto.toUpperCase()}
        </span>
      ) : (
        <span
          className="shrink-0 flex items-center justify-center"
          style={{ width: 18, height: 18, color: accent, borderRadius: 2 }}
          aria-hidden
        >
          <Zap size={11} />
        </span>
      )}
    </article>
  );
}

// ── Not-found overlay (image asset missing) ─────────────────────────────────

function NotFoundOverlay() {
  return (
    <div
      className="flex-1 flex flex-col items-center justify-center gap-3 text-center px-6"
      style={{
        color: 'var(--hud-text-dim)',
        fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
      }}
    >
      <div className="text-[10px] tracking-[0.3em] font-bold" style={{ color: 'var(--color-jarvis)' }}>
        ◆ JARVIS IMAGE NOT FOUND
      </div>
      <div className="text-[11px] tracking-wider max-w-md">Save your image as one of:</div>
      <pre
        className="text-[10px] p-3"
        style={{
          background: 'rgba(0,212,255,0.06)',
          border: '1px solid rgba(0,212,255,0.3)',
          color: 'var(--hud-text)',
        }}
      >
{`C:\\OpenJarvisNexus\\frontend\\public\\world\\jarvis.png
C:\\OpenJarvisNexus\\frontend\\public\\world\\jarvis.jpg
C:\\OpenJarvisNexus\\frontend\\public\\world\\jarvis.webp`}
      </pre>
      <div className="text-[9px] tracking-wider opacity-70 max-w-md">then refresh this page</div>
    </div>
  );
}
