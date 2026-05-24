/**
 * Nexus9 - sync-brain.js
 *
 * Importe / synchronise du contenu vers la vault Obsidian BRAIN.
 *
 * Sources :
 *  - `backend/vault`        -> BRAIN/imported/backend-vault/
 *  - `skills`               -> BRAIN/imported/skills/
 *  - `session_logs`         -> BRAIN/imported/sessions/
 *
 * Strategie :
 *  - Idempotent : si le body est identique, on ne reecrit pas.
 *  - Frontmatter YAML ajoute (nexus9_source, nexus9_synced) pour tracabilite.
 *
 * Utilisation :
 *   node sync-brain.js
 *
 * Env :
 *   BRAIN_PATH       — destination (default = VAULT_PATH du sidecar)
 *   NEXUS9_ROOT      — racine du projet (default = ../../)
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const BRAIN_PATH  = process.env.BRAIN_PATH
  ?? process.env.VAULT_PATH
  ?? 'C:\\OpenJarvisNexus\\backend\\BRAIN\\BRAIN';
const NEXUS9_ROOT = process.env.NEXUS9_ROOT
  ?? path.resolve(__dirname, '..', '..');

const SOURCES = [
  {
    label: 'backend-vault',
    src:   path.join(NEXUS9_ROOT, 'backend', 'vault'),
    dest:  path.join(BRAIN_PATH, 'imported', 'backend-vault'),
  },
  {
    label: 'skills',
    src:   path.join(NEXUS9_ROOT, 'skills'),
    dest:  path.join(BRAIN_PATH, 'imported', 'skills'),
  },
  {
    label: 'session_logs',
    src:   path.join(NEXUS9_ROOT, 'session_logs'),
    dest:  path.join(BRAIN_PATH, 'imported', 'sessions'),
  },
];

const IGNORED_DIRS = new Set([
  '.git', '.obsidian', '.trash', 'node_modules', '.DS_Store',
  '__pycache__', '.pytest_cache', 'dist', 'build',
  'claude-mem',  // docs vendor du submodule — ne pas importer dans le vault
]);

function walkMd(dir, baseDir, out = []) {
  let entries;
  try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch { return out; }
  for (const entry of entries) {
    if (IGNORED_DIRS.has(entry.name)) continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walkMd(full, baseDir, out);
    } else if (entry.isFile() && entry.name.toLowerCase().endsWith('.md')) {
      out.push({ full, rel: path.relative(baseDir, full) });
    }
  }
  return out;
}

const FM_RE = /^---\n([\s\S]*?)\n---\n/;

function withFrontmatter(originalContent, sourcePath) {
  const now = new Date().toISOString();
  const srcSlash = sourcePath.split(path.sep).join('/');
  const existing = originalContent.match(FM_RE);
  if (existing) {
    // Remplace les clés nexus9 existantes au lieu de les dupliquer.
    let fm = existing[1]
      .replace(/^nexus9_source:.*$/m, '')
      .replace(/^nexus9_synced:.*$/m, '')
      .replace(/\n{2,}/g, '\n')
      .trim();
    if (fm) fm += '\n';
    const body = originalContent.slice(existing[0].length);
    return `---\n${fm}nexus9_source: ${srcSlash}\nnexus9_synced: ${now}\n---\n\n${body}`;
  }
  return `---\nnexus9_source: ${srcSlash}\nnexus9_synced: ${now}\n---\n\n${originalContent}`;
}

function stripFrontmatter(content) {
  return content.replace(FM_RE, '');
}

function syncSource({ label, src, dest }) {
  if (!fs.existsSync(src)) {
    console.log(`[sync-brain] skip ${label}: source absente (${src})`);
    return { copied: 0, skipped: 0, updated: 0 };
  }
  fs.mkdirSync(dest, { recursive: true });
  const files = walkMd(src, src);
  let copied = 0, skipped = 0, updated = 0;
  for (const f of files) {
    const target = path.join(dest, f.rel);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    const sourceContent = fs.readFileSync(f.full, 'utf8');
    const wrapped = withFrontmatter(sourceContent, path.relative(NEXUS9_ROOT, f.full));
    if (fs.existsSync(target)) {
      const existing = fs.readFileSync(target, 'utf8');
      if (stripFrontmatter(existing) === stripFrontmatter(wrapped)) {
        skipped++;
        continue;
      }
      fs.writeFileSync(target, wrapped, 'utf8');
      updated++;
    } else {
      fs.writeFileSync(target, wrapped, 'utf8');
      copied++;
    }
  }
  console.log(`[sync-brain] ${label}: +${copied} new / ~${updated} updated / =${skipped} unchanged (total ${files.length})`);
  return { copied, skipped, updated };
}

export function syncAll() {
  console.log(`[sync-brain] BRAIN_PATH  = ${BRAIN_PATH}`);
  console.log(`[sync-brain] NEXUS9_ROOT = ${NEXUS9_ROOT}`);
  if (!fs.existsSync(BRAIN_PATH)) {
    console.error(`[sync-brain] ERROR: BRAIN_PATH does not exist: ${BRAIN_PATH}`);
    return { error: 'BRAIN_PATH missing' };
  }
  const start = Date.now();
  const results = {};
  for (const s of SOURCES) {
    results[s.label] = syncSource(s);
  }
  const elapsed = Date.now() - start;
  const totals = Object.values(results).reduce(
    (acc, r) => ({
      copied:  acc.copied  + (r.copied  ?? 0),
      updated: acc.updated + (r.updated ?? 0),
      skipped: acc.skipped + (r.skipped ?? 0),
    }),
    { copied: 0, updated: 0, skipped: 0 },
  );
  console.log(`[sync-brain] DONE in ${elapsed}ms - total +${totals.copied} new / ~${totals.updated} updated / =${totals.skipped} unchanged`);
  return { ...results, totals, elapsed };
}

// CLI direct : node sync-brain.js
const isMain = process.argv[1] && import.meta.url.endsWith(process.argv[1].split(path.sep).join('/'));
if (isMain) syncAll();
