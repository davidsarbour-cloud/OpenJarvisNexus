/**
 * Nexus9 - scaffold-brain.js
 *
 * Genere la structure PARA-inspired de la vault BRAIN :
 *   00_Core, 01_Inbox, 02_Daily, 03_Projects, 04_Areas,
 *   05_Resources, 06_Agents, 07_Schemas, 08_Command-Center, 09_Archives
 *
 * Chaque .md cree contient :
 *   - Frontmatter YAML (tags, created)
 *   - Titre H1 avec emoji
 *   - 1-3 wikilinks vers notes du meme groupe (pour densifier le graph)
 *   - Section "Notes" vide a remplir
 *
 * Idempotent : si le .md existe deja, on ne touche pas.
 *
 * Lancement :
 *   node scaffold-brain.js
 */

import fs from 'node:fs';
import path from 'node:path';

const BRAIN_PATH = process.env.BRAIN_PATH
  ?? process.env.VAULT_PATH
  ?? 'C:\\OpenJarvisNexus\\backend\\BRAIN\\BRAIN';

const today = new Date().toISOString().slice(0, 10);

/**
 * Schema de la vault. Pour chaque fichier :
 *   { name, emoji?, tags: string[], links: string[], desc?: string }
 */
const SCHEMA = {
  '00_Core': {
    desc: 'Identite et nord magnetique de tout le systeme.',
    files: [
      { name: 'core-vision', emoji: '🌟', tags: ['core', 'vision'],
        links: ['core-objectifs-2026', 'core-principes', 'core-roadmap'],
        desc: 'LA note maitre. Pourquoi tout existe.' },
      { name: 'core-objectifs-2026', emoji: '🎯', tags: ['core', 'goals'],
        links: ['core-vision', 'core-kpis', 'core-roadmap'],
        desc: 'Objectifs annuels mesurables.' },
      { name: 'core-principes', emoji: '🧭', tags: ['core', 'principles'],
        links: ['core-vision', 'core-mindset', 'core-identité'],
        desc: 'Regles non-negociables, decisions sous contrainte.' },
      { name: 'core-identité', emoji: '👤', tags: ['core', 'identity'],
        links: ['core-vision', 'core-mindset', 'core-principes'],
        desc: 'Qui je suis. Forces, faiblesses, valeurs.' },
      { name: 'core-mindset', emoji: '💪', tags: ['core', 'mindset'],
        links: ['core-identité', 'core-principes', 'core-kpis'],
        desc: 'Mentalite, mantras, daily affirmations.' },
      { name: 'core-kpis', emoji: '📊', tags: ['core', 'metrics'],
        links: ['core-objectifs-2026', 'dashboard-kpis', 'core-roadmap'],
        desc: 'Metriques cles que je track chaque semaine.' },
      { name: 'core-roadmap', emoji: '🗺️', tags: ['core', 'roadmap'],
        links: ['core-vision', 'core-objectifs-2026', 'core-kpis'],
        desc: 'Plan 1 / 3 / 5 ans.' },
    ],
  },

  '01_Inbox': {
    desc: 'Capture brute. Tout ce qui entre passe ici avant tri.',
    files: [],
  },

  '02_Daily': {
    desc: 'Journal quotidien. Une note par jour.',
    files: [
      { name: today, emoji: '📅', tags: ['daily', today.slice(0, 7)],
        links: ['core-objectifs-2026', 'dashboard-main'],
        desc: 'Daily note d\'aujourd\'hui.' },
    ],
  },

  '03_Projects/Dropshipping': {
    desc: 'Projet actif - dropshipping D3Dprintix.',
    files: [
      { name: 'pipeline', emoji: '📌', tags: ['project', 'dropshipping'],
        links: ['produits-test', 'produits-validés', 'fournisseurs'],
        desc: 'Pipeline complet du produit a la vente.' },
      { name: 'produits-test', emoji: '🧪', tags: ['dropshipping', 'tests'],
        links: ['pipeline', 'ads-meta'],
        desc: 'Produits en phase de test.' },
      { name: 'produits-validés', emoji: '✅', tags: ['dropshipping', 'winners'],
        links: ['pipeline', 'tunnels-vente'],
        desc: 'Produits valides avec ROAS positif.' },
      { name: 'fournisseurs', emoji: '🏭', tags: ['dropshipping', 'supply'],
        links: ['pipeline'],
        desc: 'Fournisseurs valides et termes negocies.' },
      { name: 'ads-meta', emoji: '📣', tags: ['dropshipping', 'ads'],
        links: ['produits-test', 'tunnels-vente'],
        desc: 'Campagnes Meta - creatives, audiences, perf.' },
      { name: 'tunnels-vente', emoji: '🔀', tags: ['dropshipping', 'funnels'],
        links: ['ads-meta', 'produits-validés'],
        desc: 'Funnels Shopify, upsells, AOV.' },
    ],
  },

  '03_Projects/Daytrading': {
    desc: 'Projet actif - daytrading.',
    files: [
      { name: 'pipeline', emoji: '📌', tags: ['project', 'trading'],
        links: ['journal-trades', 'setups', 'risk-management'],
        desc: 'Workflow daily de trading.' },
      { name: 'journal-trades', emoji: '📔', tags: ['trading', 'journal'],
        links: ['pipeline', 'post-mortems', 'setups'],
        desc: 'Chaque trade : entry, exit, raison, resultat.' },
      { name: 'setups', emoji: '📐', tags: ['trading', 'setups'],
        links: ['pipeline', 'watchlist'],
        desc: 'Setups valides avec edge demontre.' },
      { name: 'watchlist', emoji: '👀', tags: ['trading', 'watchlist'],
        links: ['setups', 'journal-trades'],
        desc: 'Tickers surveilles, niveaux cles.' },
      { name: 'risk-management', emoji: '🛡️', tags: ['trading', 'risk'],
        links: ['pipeline', 'post-mortems'],
        desc: 'Sizing, stop loss, max drawdown.' },
      { name: 'post-mortems', emoji: '🔬', tags: ['trading', 'learnings'],
        links: ['journal-trades', 'risk-management'],
        desc: 'Trades rates ou notables : qu\'ai-je appris.' },
    ],
  },

  '03_Projects/STL': {
    desc: 'Projet actif - STL / impression 3D (D3Dprintix).',
    files: [
      { name: 'pipeline', emoji: '📌', tags: ['project', 'stl', '3d'],
        links: ['designs', 'machines'],
        desc: 'De l\'idee STL au produit imprime.' },
      { name: 'designs', emoji: '🎨', tags: ['stl', 'designs'],
        links: ['pipeline'],
        desc: 'Catalogue de designs, sources, statuts.' },
      { name: 'machines', emoji: '🖨️', tags: ['stl', 'hardware'],
        links: ['pipeline'],
        desc: 'Imprimantes, filaments, profils.' },
    ],
  },

  '04_Areas/Finance': {
    desc: 'Domaine continu - finance personnelle.',
    files: [
      { name: 'budget', emoji: '💰', tags: ['finance', 'budget'],
        links: ['revenus', 'dépenses', 'patrimoine'],
        desc: 'Budget mensuel reel vs prevu.' },
      { name: 'investissements', emoji: '📈', tags: ['finance', 'invest'],
        links: ['patrimoine', 'revenus'],
        desc: 'Portefeuille, positions, allocations.' },
      { name: 'revenus', emoji: '💵', tags: ['finance', 'income'],
        links: ['budget', 'patrimoine'],
        desc: 'Sources de revenus, evolution.' },
      { name: 'dépenses', emoji: '💸', tags: ['finance', 'expenses'],
        links: ['budget'],
        desc: 'Categories, abonnements, optim.' },
      { name: 'patrimoine', emoji: '🏛️', tags: ['finance', 'wealth'],
        links: ['investissements', 'revenus', 'budget'],
        desc: 'Net worth, evolution, snapshots.' },
    ],
  },

  '04_Areas/Santé': {
    desc: 'Domaine continu - sante.',
    files: [
      { name: 'nutrition', emoji: '🥗', tags: ['santé', 'nutrition'],
        links: ['entraînement', 'bilans'],
        desc: 'Approche nutritionnelle, suppl, plans repas.' },
      { name: 'entraînement', emoji: '🏋️', tags: ['santé', 'training'],
        links: ['nutrition', 'sommeil', 'bilans'],
        desc: 'Programme, PR, progression.' },
      { name: 'sommeil', emoji: '😴', tags: ['santé', 'sleep'],
        links: ['entraînement', 'bilans'],
        desc: 'Routines, suivi qualite, optims.' },
      { name: 'bilans', emoji: '🩺', tags: ['santé', 'bilans'],
        links: ['nutrition', 'entraînement', 'sommeil'],
        desc: 'Analyses sang, mesures, evolution.' },
    ],
  },

  '04_Areas/Business': {
    desc: 'Domaine continu - operations business.',
    files: [
      { name: 'légal', emoji: '⚖️', tags: ['business', 'legal'],
        links: ['comptabilité'],
        desc: 'Structures, contrats, fiscal.' },
      { name: 'comptabilité', emoji: '🧾', tags: ['business', 'accounting'],
        links: ['légal', 'outils-saas'],
        desc: 'Factures, depenses, fournisseurs.' },
      { name: 'outils-saas', emoji: '🧰', tags: ['business', 'saas'],
        links: ['comptabilité'],
        desc: 'Stack SaaS, couts, justifs.' },
    ],
  },

  '05_Resources/Research': {
    desc: 'Recherche - tactiques et frameworks externes.',
    files: [
      { name: 'dropshipping-tactics', emoji: '🛒', tags: ['research', 'dropshipping'],
        links: ['moc-dropshipping', 'pipeline'],
        desc: 'Tactiques validees par d\'autres, sources.' },
      { name: 'trading-strategies', emoji: '📊', tags: ['research', 'trading'],
        links: ['moc-trading', 'setups', 'psychologie-trading'],
        desc: 'Strategies tradeurs reconnus.' },
      { name: 'ia-tools', emoji: '🤖', tags: ['research', 'ia'],
        links: ['moc-ia'],
        desc: 'Tools IA testees, evaluations.' },
      { name: 'marketing-frameworks', emoji: '🎯', tags: ['research', 'marketing'],
        links: ['moc-dropshipping', 'ads-meta'],
        desc: 'AIDA, hook-story-close, AARRR, etc.' },
      { name: 'psychologie-trading', emoji: '🧠', tags: ['research', 'psychology'],
        links: ['moc-trading', 'moc-mindset', 'risk-management'],
        desc: 'Biais cognitifs, discipline, FOMO.' },
    ],
  },

  '05_Resources/MOCs': {
    desc: 'Maps of Content - index des sujets.',
    files: [
      { name: 'moc-finance', emoji: '🗺️', tags: ['moc', 'finance'],
        links: ['budget', 'investissements', 'patrimoine'],
        desc: 'Index de tout ce qui touche finance.' },
      { name: 'moc-trading', emoji: '🗺️', tags: ['moc', 'trading'],
        links: ['pipeline', 'setups', 'trading-strategies', 'psychologie-trading'],
        desc: 'Index trading.' },
      { name: 'moc-dropshipping', emoji: '🗺️', tags: ['moc', 'dropshipping'],
        links: ['pipeline', 'dropshipping-tactics', 'marketing-frameworks'],
        desc: 'Index dropshipping.' },
      { name: 'moc-ia', emoji: '🗺️', tags: ['moc', 'ia'],
        links: ['ia-tools', 'dashboard-agents'],
        desc: 'Index IA, agents, tooling.' },
      { name: 'moc-mindset', emoji: '🗺️', tags: ['moc', 'mindset'],
        links: ['core-mindset', 'psychologie-trading'],
        desc: 'Index mindset, discipline.' },
    ],
  },

  '05_Resources/Templates': {
    desc: 'Templates reutilisables.',
    files: [
      { name: 'template-daily', emoji: '📋', tags: ['template'],
        links: [],
        desc: 'Squelette daily note.' },
      { name: 'template-pipeline', emoji: '📋', tags: ['template'],
        links: [],
        desc: 'Squelette pipeline projet.' },
      { name: 'template-research', emoji: '📋', tags: ['template'],
        links: [],
        desc: 'Squelette note de recherche.' },
      { name: 'template-trade', emoji: '📋', tags: ['template'],
        links: [],
        desc: 'Squelette entry de journal-trades.' },
      { name: 'template-agent', emoji: '📋', tags: ['template'],
        links: [],
        desc: 'Squelette identite d\'agent.' },
      { name: 'template-projet', emoji: '📋', tags: ['template'],
        links: [],
        desc: 'Squelette nouveau projet.' },
    ],
  },

  '06_Agents/_shared': {
    desc: 'Ressources communes a tous les agents.',
    files: [
      { name: 'adn-commun', emoji: '🧬', tags: ['agent', 'shared'],
        links: ['core-vision', 'core-principes', 'shared-tools'],
        desc: 'ADN partage par tous les agents : valeurs, ton, contraintes.' },
      { name: 'shared-tools', emoji: '🧰', tags: ['agent', 'shared'],
        links: ['adn-commun', 'workflows-multi-agents'],
        desc: 'Outils accessibles a tous les agents.' },
      { name: 'shared-memory', emoji: '🧠', tags: ['agent', 'memory'],
        links: ['adn-commun'],
        desc: 'Memoire partagee inter-agents (facts, decisions).' },
      { name: 'workflows-multi-agents', emoji: '🔀', tags: ['agent', 'workflow'],
        links: ['shared-tools', 'shared-memory'],
        desc: 'Comment les agents collaborent (orchestrator JARVIS).' },
    ],
  },

  '06_Agents/ultron': {
    desc: 'ULTRON - Stratege (claude-sonnet-4-6).',
    files: [
      { name: 'identity', emoji: '🦾', tags: ['agent', 'ultron'],
        links: ['adn-commun', 'memory', 'tasks'],
        desc: 'Role : stratege. Model : claude-sonnet-4-6. Trigger : !ultron.' },
      { name: 'memory', emoji: '🧠', tags: ['agent', 'ultron', 'memory'],
        links: ['identity', 'shared-memory'],
        desc: 'Memoire long-terme d\'ULTRON.' },
      { name: 'tasks', emoji: '✅', tags: ['agent', 'ultron'],
        links: ['identity'],
        desc: 'Taches en cours / completees.' },
      { name: 'logs', emoji: '📜', tags: ['agent', 'ultron'],
        links: ['identity'],
        desc: 'Journal des sessions ULTRON.' },
    ],
  },

  '06_Agents/jarvis': {
    desc: 'JARVIS - Master Orchestrator (claude-haiku-4-5).',
    files: [
      { name: 'identity', emoji: '🤖', tags: ['agent', 'jarvis'],
        links: ['adn-commun', 'memory', 'logs'],
        desc: 'Role : master orchestrator. Model : claude-haiku-4-5. Trigger : chaque message.' },
      { name: 'memory', emoji: '🧠', tags: ['agent', 'jarvis', 'memory'],
        links: ['identity', 'shared-memory'],
        desc: 'Memoire d\'orchestration de JARVIS.' },
      { name: 'logs', emoji: '📜', tags: ['agent', 'jarvis'],
        links: ['identity'],
        desc: 'Journal d\'orchestration JARVIS.' },
    ],
  },

  '06_Agents/qwen': {
    desc: 'QWEN - Mass execution / bulk generation (ollama qwen3:14b).',
    files: [
      { name: 'identity', emoji: '🕷️', tags: ['agent', 'qwen'],
        links: ['adn-commun', 'memory', 'ideas-bank'],
        desc: 'Role : mass execution / bulk. Model : ollama qwen3:14b. Trigger : !qwen.' },
      { name: 'memory', emoji: '🧠', tags: ['agent', 'qwen', 'memory'],
        links: ['identity', 'shared-memory'],
        desc: 'Memoire long-terme de QWEN.' },
      { name: 'ideas-bank', emoji: '💡', tags: ['agent', 'qwen', 'ideas'],
        links: ['identity'],
        desc: 'Banque d\'idees creatives.' },
      { name: 'logs', emoji: '📜', tags: ['agent', 'qwen'],
        links: ['identity'],
        desc: 'Journal des sessions QWEN.' },
    ],
  },

  '06_Agents/bruce': {
    desc: 'BRUCE - Analyste autonome (OpenHands).',
    files: [
      { name: 'identity', emoji: '🧪', tags: ['agent', 'bruce'],
        links: ['adn-commun', 'memory', 'research-log'],
        desc: 'Role : analyste autonome. Stack : OpenHands + qwen3:14b. Trigger : !bruce.' },
      { name: 'memory', emoji: '🧠', tags: ['agent', 'bruce', 'memory'],
        links: ['identity', 'shared-memory'],
        desc: 'Memoire long-terme de BRUCE.' },
      { name: 'research-log', emoji: '🔍', tags: ['agent', 'bruce', 'research'],
        links: ['identity'],
        desc: 'Log des analyses et recherches autonomes.' },
      { name: 'logs', emoji: '📜', tags: ['agent', 'bruce'],
        links: ['identity'],
        desc: 'Journal des sessions BRUCE.' },
    ],
  },

  '06_Agents/cortana': {
    desc: 'CORTANA - Assistant code (deepseek-coder:6.7b).',
    files: [
      { name: 'identity', emoji: '💎', tags: ['agent', 'cortana'],
        links: ['adn-commun', 'memory', 'daily-handoff'],
        desc: 'Role : assistant code. Model : deepseek-coder:6.7b. Trigger : !cortana.' },
      { name: 'memory', emoji: '🧠', tags: ['agent', 'cortana', 'memory'],
        links: ['identity', 'shared-memory'],
        desc: 'Memoire long-terme de CORTANA.' },
      { name: 'daily-handoff', emoji: '🤝', tags: ['agent', 'cortana'],
        links: ['identity'],
        desc: 'Handoff quotidien avec les autres agents.' },
      { name: 'logs', emoji: '📜', tags: ['agent', 'cortana'],
        links: ['identity'],
        desc: 'Journal des sessions CORTANA.' },
    ],
  },

  '06_Agents/nova': {
    desc: 'NOVA - Dev complexe (deepseek-r1:7b).',
    files: [
      { name: 'identity', emoji: '💻', tags: ['agent', 'nova'],
        links: ['adn-commun', 'memory', 'projects-code'],
        desc: 'Role : dev complexe / reasoning. Model : deepseek-r1:7b. Trigger : !nova.' },
      { name: 'memory', emoji: '🧠', tags: ['agent', 'nova', 'memory'],
        links: ['identity', 'shared-memory'],
        desc: 'Memoire long-terme de NOVA.' },
      { name: 'projects-code', emoji: '🛠️', tags: ['agent', 'nova', 'code'],
        links: ['identity', 'snippets'],
        desc: 'Projets de code en cours.' },
      { name: 'snippets', emoji: '✂️', tags: ['agent', 'nova', 'code'],
        links: ['projects-code'],
        desc: 'Snippets reutilisables.' },
      { name: 'logs', emoji: '📜', tags: ['agent', 'nova'],
        links: ['identity'],
        desc: 'Journal des sessions NOVA.' },
    ],
  },

  '07_Schemas/system': {
    desc: 'Schemas architecture - canvas Obsidian.',
    files: [
      { name: 'system-overview', emoji: '🌐', tags: ['schema', 'architecture'],
        links: ['agents-map', 'data-flow', 'core-graph'],
        desc: 'Vue globale Nexus9.' },
      { name: 'agents-map', emoji: '🤖', tags: ['schema', 'agents'],
        links: ['system-overview', 'adn-commun'],
        desc: 'Carte des agents et leurs roles.' },
      { name: 'data-flow', emoji: '🔗', tags: ['schema', 'data'],
        links: ['system-overview'],
        desc: 'Flux de donnees inter-services.' },
      { name: 'core-graph', emoji: '🧠', tags: ['schema', 'core'],
        links: ['core-vision', 'system-overview'],
        desc: 'Core etoile : vision -> kpis.' },
    ],
  },

  '07_Schemas/workflows': {
    desc: 'Workflows visuels.',
    files: [
      { name: 'workflow-daily', emoji: '📅', tags: ['workflow', 'daily'],
        links: ['template-daily', 'dashboard-main'],
        desc: 'Flow journee type.' },
      { name: 'workflow-trade', emoji: '📈', tags: ['workflow', 'trading'],
        links: ['pipeline', 'journal-trades'],
        desc: 'Flow d\'un trade.' },
      { name: 'workflow-product-launch', emoji: '📦', tags: ['workflow', 'dropshipping'],
        links: ['pipeline', 'produits-test'],
        desc: 'Flow lancement produit.' },
      { name: 'workflow-research', emoji: '🔬', tags: ['workflow', 'research'],
        links: ['template-research'],
        desc: 'Flow de recherche structuree.' },
      { name: 'workflow-decision', emoji: '🎯', tags: ['workflow', 'decision'],
        links: ['decision-tree', 'first-principles'],
        desc: 'Flow de decision sous contrainte.' },
    ],
  },

  '07_Schemas/mental-models': {
    desc: 'Modeles mentaux.',
    files: [
      { name: 'decision-tree', emoji: '🌳', tags: ['mental-model'],
        links: ['workflow-decision'],
        desc: 'Arbre de decision generique.' },
      { name: 'eisenhower-matrix', emoji: '📐', tags: ['mental-model'],
        links: ['workflow-decision'],
        desc: 'Urgent / important.' },
      { name: 'first-principles', emoji: '🧱', tags: ['mental-model'],
        links: ['workflow-decision'],
        desc: 'Raisonnement par premiers principes.' },
      { name: '80-20-pareto', emoji: '📊', tags: ['mental-model'],
        links: ['core-objectifs-2026'],
        desc: '20% qui produisent 80%.' },
    ],
  },

  '07_Schemas/diagrams': {
    desc: 'Diagrammes techniques.',
    files: [
      { name: 'infra-stack', emoji: '🏗️', tags: ['diagram', 'infra'],
        links: ['system-overview'],
        desc: 'Stack infra Nexus9.' },
      { name: 'api-flows', emoji: '🔌', tags: ['diagram', 'api'],
        links: ['data-flow'],
        desc: 'Flows API entre services.' },
      { name: 'tunnel-vente', emoji: '🌪️', tags: ['diagram', 'sales'],
        links: ['tunnels-vente'],
        desc: 'Tunnel de vente type.' },
    ],
  },

  '08_Command-Center': {
    desc: 'Cockpit - dashboards.',
    files: [
      { name: 'dashboard-main', emoji: '🏠', tags: ['dashboard'],
        links: ['dashboard-finance', 'dashboard-trading', 'dashboard-dropshipping', 'dashboard-kpis'],
        desc: 'Vue principale - point d\'entree.' },
      { name: 'dashboard-finance', emoji: '💰', tags: ['dashboard', 'finance'],
        links: ['budget', 'patrimoine', 'investissements'],
        desc: 'Dashboard finance live.' },
      { name: 'dashboard-trading', emoji: '📈', tags: ['dashboard', 'trading'],
        links: ['pipeline', 'journal-trades'],
        desc: 'Dashboard trading live.' },
      { name: 'dashboard-dropshipping', emoji: '📦', tags: ['dashboard', 'dropshipping'],
        links: ['pipeline', 'produits-validés'],
        desc: 'Dashboard dropshipping live.' },
      { name: 'dashboard-agents', emoji: '🤖', tags: ['dashboard', 'agents'],
        links: ['adn-commun', 'moc-ia'],
        desc: 'Status des agents.' },
      { name: 'dashboard-kpis', emoji: '📊', tags: ['dashboard', 'kpis'],
        links: ['core-kpis'],
        desc: 'Toutes les KPIs en un coup d\'oeil.' },
      { name: 'kanban-board', emoji: '📋', tags: ['dashboard', 'kanban'],
        links: ['dashboard-main'],
        desc: 'Tableau kanban global.' },
    ],
  },

  '09_Archives/Projects-finished': {
    desc: 'Projets termines.',
    files: [],
  },
  '09_Archives/Old-notes': {
    desc: 'Notes anciennes.',
    files: [],
  },
  '09_Archives/Old-research': {
    desc: 'Recherche ancienne.',
    files: [],
  },
};

function renderSeed(folder, file) {
  const tagsLine = file.tags.length
    ? file.tags.map((t) => `#${t}`).join(' ')
    : '';
  const linksList = file.links.length
    ? file.links.map((l) => `- [[${l}]]`).join('\n')
    : '- _aucun pour l\'instant_';
  const emoji = file.emoji ? `${file.emoji} ` : '';
  return `---
created: ${today}
nexus9_scaffold: true
tags: [${file.tags.map((t) => `"${t}"`).join(', ')}]
---

# ${emoji}${file.name}

${file.desc ?? ''}

${tagsLine}

## Notes

_a remplir_

## Liens

${linksList}
`;
}

export function scaffold() {
  console.log(`[scaffold-brain] BRAIN_PATH = ${BRAIN_PATH}`);
  if (!fs.existsSync(BRAIN_PATH)) {
    console.error(`[scaffold-brain] ERROR: BRAIN_PATH does not exist: ${BRAIN_PATH}`);
    return { error: 'BRAIN_PATH missing' };
  }
  let created = 0, skipped = 0, folders = 0;
  for (const [folder, def] of Object.entries(SCHEMA)) {
    const folderPath = path.join(BRAIN_PATH, folder);
    if (!fs.existsSync(folderPath)) {
      fs.mkdirSync(folderPath, { recursive: true });
      folders++;
    }
    for (const file of def.files) {
      const target = path.join(folderPath, `${file.name}.md`);
      if (fs.existsSync(target)) {
        skipped++;
        continue;
      }
      fs.writeFileSync(target, renderSeed(folder, file), 'utf8');
      created++;
    }
  }
  console.log(`[scaffold-brain] DONE - ${folders} folders / ${created} new files / ${skipped} skipped (already existed)`);
  return { folders, created, skipped };
}

const argv1 = process.argv[1];
const isMain = argv1 && import.meta.url.endsWith(argv1.split(path.sep).join('/'));
if (isMain) scaffold();
