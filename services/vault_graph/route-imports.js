/**
 * Nexus9 - route-imports.js
 *
 * Apres sync-brain, dispatch les fichiers de BRAIN/imported/ vers les bons
 * dossiers PARA (00_Core, 03_Projects, 06_Agents, etc.).
 *
 * Strategie :
 *  - COPIE puis CLEANUP des sources (option B v2) :
 *    apres avoir route un fichier avec succes, on supprime la source d'imported/
 *    UNIQUEMENT si la destination existe toujours sur disque (garde-fou).
 *    Si tu as deplace/supprime la destination, on garde la source comme backup.
 *  - LEDGER (option B v1) : .nexus9-routed-lock.json memorise ce qui a deja
 *    ete route. On ne re-route JAMAIS un fichier ledge -> moves manuels OK.
 *  - Idempotent : si la destination existe avec le meme body, on skip.
 *
 * Utilisation :
 *   node route-imports.js                              -> route + cleanup
 *   node route-imports.js --no-cleanup                 -> route sans supprimer
 *   node route-imports.js --cleanup-only               -> juste nettoyer imported/
 *   node route-imports.js --dry-run                    -> plan sans rien ecrire
 *   node route-imports.js --unlock imported/skills/x.md  -> retirer du ledger
 *   node route-imports.js --reset-ledger               -> vider ledger
 *
 * Env :
 *   BRAIN_PATH (default = C:\OpenJarvisNexus\backend\BRAIN\BRAIN)
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const BRAIN_PATH = process.env.BRAIN_PATH
  ?? process.env.VAULT_PATH
  ?? 'C:\\OpenJarvisNexus\\backend\\BRAIN\\BRAIN';

const IMPORTED_DIR = path.join(BRAIN_PATH, 'imported');
const LEDGER_PATH  = path.join(BRAIN_PATH, '.nexus9-routed-lock.json');

const FILE_MAP = {
  'skills/agents.md':           '06_Agents/_shared/agents.md',
  'skills/architecture.md':     '07_Schemas/system/architecture.md',
  'skills/design.md':           '07_Schemas/system/design.md',
  'skills/routing.md':          '07_Schemas/workflows/routing.md',
  'skills/session-protocol.md': '06_Agents/_shared/session-protocol.md',
  'skills/session-history.md':  '02_Daily/session-history.md',
  'skills/stl-pipeline.md':     '03_Projects/STL/stl-pipeline.md',
  'skills/superpowers.md':      '05_Resources/Research/superpowers.md',
  'skills/obsidian-skills.md':  '05_Resources/Research/obsidian-skills.md',
  'skills/vault-graph.md':      '05_Resources/Research/vault-graph.md',
};

const DIR_MAP = [
  { from: 'sessions/',                   to: '02_Daily/sessions/' },
  { from: 'backend-vault/claude-mem/',   to: '05_Resources/Research/claude-mem/' },
  { from: 'backend-vault/ragtime/',      to: '05_Resources/Research/ragtime/' },
  { from: 'ragtime/',                    to: '05_Resources/Research/ragtime/' },
  { from: 'backend-vault/',              to: '01_Inbox/backend-vault/' },
];

const FM_RE = /^---\n([\s\S]*?)\n---\n/;

function withRoutedFrontmatter(originalContent, fromRel) {
  const now = new Date().toISOString();
  const slashRel = fromRel.split(path.sep).join('/');
  const m = originalContent.match(FM_RE);
  if (m) {
    const body = originalContent.slice(m[0].length);
    return `---\n${m[1]}\nnexus9_routed_from: imported/${slashRel}\nnexus9_routed_at: ${now}\n---\n\n${body}`;
  }
  return `---\nnexus9_routed_from: imported/${slashRel}\nnexus9_routed_at: ${now}\n---\n\n${originalContent}`;
}

function stripFrontmatter(s) { return s.replace(FM_RE, ''); }

function walkAll(dir, baseDir, out = []) {
  let entries;
  try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch { return out; }
  for (const e of entries) {
    const full = path.join(dir, e.name);
    if (e.isDirectory()) walkAll(full, baseDir, out);
    else if (e.isFile() && e.name.toLowerCase().endsWith('.md')) {
      out.push({ full, rel: path.relative(baseDir, full) });
    }
  }
  return out;
}

function resolveDestination(relFromImported) {
  const slash = relFromImported.split(path.sep).join('/');
  if (FILE_MAP[slash]) return FILE_MAP[slash];
  const sorted = [...DIR_MAP].sort((a, b) => b.from.length - a.from.length);
  for (const rule of sorted) {
    if (slash.startsWith(rule.from)) {
      const tail = slash.slice(rule.from.length);
      return rule.to + tail;
    }
  }
  return null;
}

/* ====== LEDGER ====== */

function readLedger() {
  if (!fs.existsSync(LEDGER_PATH)) return {};
  try { return JSON.parse(fs.readFileSync(LEDGER_PATH, 'utf8')); }
  catch (err) {
    console.warn('[route-imports] ledger corrupted, starting fresh:', err.message);
    return {};
  }
}
function writeLedger(ledger) {
  fs.writeFileSync(LEDGER_PATH, JSON.stringify(ledger, null, 2), 'utf8');
}

/* ====== CLEANUP (option B v2) ====== */

/**
 * Pour chaque entree du ledger :
 *  - si la source dans imported/ existe ET la destination existe -> supprimer la source
 *  - si la destination est manquante (user a delete/move) -> garder la source comme backup
 *  - si la source n'existe deja plus -> noop
 */
function cleanupRoutedSources(ledger) {
  let deleted = 0, preserved = 0, alreadyGone = 0;
  for (const [sourceKey, entry] of Object.entries(ledger)) {
    // sourceKey est de la forme "imported/skills/agents.md"
    const srcAbs = path.join(BRAIN_PATH, sourceKey.replace(/\//g, path.sep));
    if (!fs.existsSync(srcAbs)) { alreadyGone++; continue; }

    const destAbs = path.join(BRAIN_PATH, entry.routedTo.replace(/\//g, path.sep));
    if (!fs.existsSync(destAbs)) {
      preserved++;
      continue;
    }
    try {
      fs.unlinkSync(srcAbs);
      deleted++;
    } catch (err) {
      console.warn(`[route-imports] could not delete ${srcAbs}:`, err.message);
      preserved++;
    }
  }
  return { deleted, preserved, alreadyGone };
}

/** Supprime les dossiers vides recursivement (sauf IMPORTED_DIR lui-meme). */
function removeEmptyDirs(dir) {
  if (!fs.existsSync(dir) || !fs.statSync(dir).isDirectory()) return;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.isDirectory()) removeEmptyDirs(path.join(dir, entry.name));
  }
  if (dir !== IMPORTED_DIR && fs.readdirSync(dir).length === 0) {
    try { fs.rmdirSync(dir); } catch { /* noop */ }
  }
}

/* ====== Main ====== */

export function routeImports({ dryRun = false, cleanup = true } = {}) {
  if (!fs.existsSync(IMPORTED_DIR)) {
    console.log(`[route-imports] no imported/ at ${IMPORTED_DIR}, nothing to do`);
    return { copied: 0, updated: 0, skipped: 0, unmapped: 0, lockedSkipped: 0, cleaned: 0, preserved: 0 };
  }
  const ledger = readLedger();
  const ledgerWas = Object.keys(ledger).length;
  const files = walkAll(IMPORTED_DIR, IMPORTED_DIR);
  let copied = 0, updated = 0, skipped = 0, unmapped = 0, lockedSkipped = 0;
  const unmappedFiles = [];

  for (const f of files) {
    const slashRel = f.rel.split(path.sep).join('/');
    const sourceKey = `imported/${slashRel}`;

    if (ledger[sourceKey]) {
      lockedSkipped++;
      continue;
    }

    const destRel = resolveDestination(f.rel);
    if (!destRel) {
      unmapped++;
      unmappedFiles.push(slashRel);
      continue;
    }
    const destAbs = path.join(BRAIN_PATH, destRel);
    const source  = fs.readFileSync(f.full, 'utf8');
    const wrapped = withRoutedFrontmatter(source, f.rel);

    if (dryRun) {
      const tag = fs.existsSync(destAbs) ? 'update?' : 'create ';
      console.log(`[route-imports] [DRY] ${tag} ${sourceKey}  ->  ${destRel}`);
      continue;
    }

    fs.mkdirSync(path.dirname(destAbs), { recursive: true });
    if (fs.existsSync(destAbs)) {
      const existing = fs.readFileSync(destAbs, 'utf8');
      if (stripFrontmatter(existing) === stripFrontmatter(wrapped)) {
        skipped++;
        ledger[sourceKey] = { routedTo: destRel, at: new Date().toISOString(), state: 'unchanged' };
        continue;
      }
      fs.writeFileSync(destAbs, wrapped, 'utf8');
      updated++;
      ledger[sourceKey] = { routedTo: destRel, at: new Date().toISOString(), state: 'updated' };
    } else {
      fs.writeFileSync(destAbs, wrapped, 'utf8');
      copied++;
      ledger[sourceKey] = { routedTo: destRel, at: new Date().toISOString(), state: 'new' };
    }
  }

  if (!dryRun) writeLedger(ledger);

  // === CLEANUP step ===
  let cleanStats = { deleted: 0, preserved: 0, alreadyGone: 0 };
  if (cleanup && !dryRun) {
    cleanStats = cleanupRoutedSources(ledger);
    removeEmptyDirs(IMPORTED_DIR);
  }

  console.log(
    `[route-imports]${dryRun ? ' [DRY]' : ''} done: +${copied} new / ~${updated} updated / =${skipped} unchanged / [LOCK]${lockedSkipped} locked / ?${unmapped} unmapped (total ${files.length})`,
  );
  console.log(
    `[route-imports] ledger: ${ledgerWas} -> ${Object.keys(ledger).length} entries`,
  );
  if (cleanup && !dryRun) {
    console.log(
      `[route-imports] cleanup: -${cleanStats.deleted} deleted from imported/ | =${cleanStats.alreadyGone} already gone | [GUARD]${cleanStats.preserved} preserved (destination missing)`,
    );
  }
  if (unmappedFiles.length && unmappedFiles.length <= 30) {
    console.log('[route-imports] unmapped files (left in imported/):');
    for (const u of unmappedFiles) console.log(`  - imported/${u}`);
  } else if (unmappedFiles.length) {
    console.log(`[route-imports] ${unmappedFiles.length} unmapped files - too many to list`);
  }

  return {
    copied, updated, skipped, unmapped, lockedSkipped, total: files.length,
    cleaned: cleanStats.deleted, preserved: cleanStats.preserved,
  };
}

export function cleanupOnly() {
  const ledger = readLedger();
  const stats = cleanupRoutedSources(ledger);
  removeEmptyDirs(IMPORTED_DIR);
  console.log(`[route-imports] cleanup-only: -${stats.deleted} deleted | =${stats.alreadyGone} already gone | [GUARD]${stats.preserved} preserved`);
  return stats;
}

export function unlockEntry(sourceKey) {
  const ledger = readLedger();
  if (!ledger[sourceKey]) {
    console.log(`[route-imports] no ledger entry for ${sourceKey}`);
    return false;
  }
  delete ledger[sourceKey];
  writeLedger(ledger);
  console.log(`[route-imports] unlocked ${sourceKey} - will be re-routed on next sync`);
  return true;
}

export function resetLedger() {
  if (fs.existsSync(LEDGER_PATH)) fs.unlinkSync(LEDGER_PATH);
  console.log('[route-imports] ledger reset');
}

/* ====== CLI ====== */

const argv1 = process.argv[1];
const isMain = argv1 && import.meta.url.endsWith(argv1.split(path.sep).join('/'));
if (isMain) {
  if (process.argv.includes('--reset-ledger')) {
    resetLedger();
    process.exit(0);
  }
  if (process.argv.includes('--cleanup-only')) {
    cleanupOnly();
    process.exit(0);
  }
  const unlockIdx = process.argv.indexOf('--unlock');
  if (unlockIdx !== -1 && process.argv[unlockIdx + 1]) {
    unlockEntry(process.argv[unlockIdx + 1]);
    process.exit(0);
  }
  const dryRun  = process.argv.includes('--dry-run');
  const cleanup = !process.argv.includes('--no-cleanup');
  routeImports({ dryRun, cleanup });
}
