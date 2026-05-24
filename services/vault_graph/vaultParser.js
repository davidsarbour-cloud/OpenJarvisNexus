/**
 * Nexus9 — vaultParser.js
 *
 * Parcourt recursivement un vault Obsidian et produit :
 *   - 1 node par .md (group = dossier de 1er niveau, _root, ou _orphan)
 *   - 1 node par #tag rencontre (id = `#nom`, isTag: true)
 *   - 1 link 'wikilink'/'tag' pour chaque [[ref]] ou #tag
 *
 * Conventions :
 *   [[Note]], [[Note|Alias]], [[Note#anchor]] tous resolvent vers 'Note'
 *   #foo, #foo/bar  -> tag node `#foo/bar`
 *
 * Code-blocks et inline code sont strippes avant extraction pour eviter
 * les faux positifs (bash [[:space:]], regex copy/paste, etc.).
 *
 * Retourne { nodes, links, stats } — format direct pour le store Nexus9
 * (compatible avec react-force-graph-2d et d3-force).
 */

import fs from 'node:fs';
import path from 'node:path';

const IGNORED_DIRS = new Set([
  '.git',
  '.obsidian',
  '.trash',
  'node_modules',
  '.DS_Store',
  // Third-party documentation imported as library — pollue le graph d'orphelins
  'claude-mem',
  'ragtime',
]);

/** @param {string} dir @returns {string[]} */
function getAllMdFiles(dir) {
  const out = [];
  let entries;
  try {
    entries = fs.readdirSync(dir, { withFileTypes: true });
  } catch {
    return out;
  }
  for (const entry of entries) {
    if (IGNORED_DIRS.has(entry.name)) continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      out.push(...getAllMdFiles(full));
    } else if (entry.isFile() && entry.name.toLowerCase().endsWith('.md')) {
      out.push(full);
    }
  }
  return out;
}

const WIKILINK_RE = /\[\[([^\]]+)\]\]/g;
// Tag : precede d'un debut ou whitespace, puis # puis [\w\-/]+
// On capture aussi le contexte pour s'assurer du whitespace devant.
const TAG_RE = /(?:^|\s)#([\w\-/]+)/g;

function stripCode(content) {
  return content
    .replace(/```[\s\S]*?```/g, '')
    .replace(/`[^`\n]*`/g, '');
}

function looksLikeNoteTitle(target) {
  if (!target || target.length === 0 || target.length > 120) return false;
  if (/[`$="]/.test(target)) return false;
  if (/^:[a-z]+:$/.test(target)) return false;
  return true;
}

/**
 * Parse un vault complet.
 * @param {string} vaultPath
 * @returns {{ nodes: Array<object>, links: Array<object>, stats: object }}
 */
export function parseVault(vaultPath) {
  /** @type {Map<string, object>} */
  const nodes = new Map();
  /** @type {Array<{source: string, target: string, type: string}>} */
  const links = [];

  if (!fs.existsSync(vaultPath)) {
    return {
      nodes: [],
      links: [],
      stats: { files: 0, links: 0, tags: 0, orphans: 0 },
    };
  }

  const files = getAllMdFiles(vaultPath);

  // --- Pass 1 : enregistre tous les fichiers reels avec leur group ---
  // Detecte les doublons de nom pour eviter la collision silencieuse.
  const nameCount = new Map();
  for (const file of files) {
    const base = path.basename(file, '.md');
    nameCount.set(base, (nameCount.get(base) ?? 0) + 1);
  }
  for (const file of files) {
    const base = path.basename(file, '.md');
    const rel  = path.relative(vaultPath, path.dirname(file));
    const group = rel === '' ? '_root' : rel.split(path.sep)[0];
    // Si doublon : on prefixe avec le 1er sous-dossier pour un ID unique.
    const id = nameCount.get(base) > 1
      ? (rel === '' ? base : `${rel.split(path.sep)[0]}/${base}`)
      : base;
    if (!nodes.has(id)) {
      nodes.set(id, {
        id,
        label: base,   // label reste le nom court
        path: file,
        group,
        tags: [],
      });
    }
  }

  // --- Pass 2 : extrait wikilinks, tags + cree orphans/tag-nodes ---
  for (const file of files) {
    const id = path.basename(file, '.md');
    let content;
    try {
      content = fs.readFileSync(file, 'utf8');
    } catch {
      continue;
    }
    const cleaned = stripCode(content);

    // Wikilinks
    for (const [, raw] of cleaned.matchAll(WIKILINK_RE)) {
      const target = raw.split('|')[0].split('#')[0].trim();
      if (!target) continue;
      if (!looksLikeNoteTitle(target)) continue;
      if (!nodes.has(target)) {
        nodes.set(target, {
          id: target,
          label: target,
          group: '_orphan',
          isOrphan: true,
          tags: [],
        });
      }
      if (target !== id) links.push({ source: id, target, type: 'wikilink' });
    }

    // Tags
    const noteTags = new Set();
    for (const [, t] of cleaned.matchAll(TAG_RE)) {
      noteTags.add(t);
    }
    const node = nodes.get(id);
    if (node) node.tags = [...noteTags];
    for (const t of noteTags) {
      const tagId = `#${t}`;
      if (!nodes.has(tagId)) {
        nodes.set(tagId, {
          id: tagId,
          label: t,
          isTag: true,
          group: '_tag',
        });
      }
      links.push({ source: id, target: tagId, type: 'tag' });
    }
  }

  // --- Pass 3 : comptage des connexions (degre) ---
  const degree = new Map();
  for (const l of links) {
    degree.set(l.source, (degree.get(l.source) ?? 0) + 1);
    degree.set(l.target, (degree.get(l.target) ?? 0) + 1);
  }
  for (const [id, c] of degree) {
    const n = nodes.get(id);
    if (n) n.connections = c;
  }

  const nodeArr = [...nodes.values()];
  return {
    nodes: nodeArr,
    links,
    stats: {
      files: files.length,
      links: links.length,
      tags: nodeArr.filter((n) => n.isTag).length,
      orphans: nodeArr.filter((n) => n.isOrphan).length,
    },
  };
}
