/**
 * Nexus9 — Vault Graph store
 *
 * Source unique de verite pour le graphe du vault Obsidian. Tous les
 * consommateurs (overlay d3, Command Center, vues Agent, etc.) doivent
 * passer par ce store — pas de fetch parallele ailleurs.
 *
 * Cycle :
 *   sidecar `services/vault_graph/server.js`  (ws://localhost:8084)
 *      |  vault:graph / vault:refreshing
 *      v
 *   `useVaultGraphSocket` (un seul hook actif a la fois est suffisant)
 *      |  setGraph / setRefreshing
 *      v
 *   ce store  <----- lu par n'importe quel composant
 */

import { create } from 'zustand';

export interface VNode {
  /** ID stable (== nom de fichier sans .md, ou `#tag` pour les tags). */
  id: string;
  /** Label affiche (pour les tags : sans le `#`). */
  label: string;
  /** Chemin absolu du .md (undefined pour les tags et les orphans). */
  path?: string;
  /** Tags trouves dans le contenu de la note. */
  tags?: string[];
  /** True quand le node represente un tag. */
  isTag?: boolean;
  /** True quand la note est referencee mais n'existe pas. */
  isOrphan?: boolean;
  /** Dossier de premier niveau, utile pour le coloriage. */
  group?: string;
  /** Nombre de liens entrants+sortants (degre). */
  connections?: number;
}

export interface VLink {
  source: string;
  target: string;
  type: 'wikilink' | 'tag' | 'embed';
}

interface State {
  nodes: VNode[];
  links: VLink[];
  /** Timestamp ms du dernier setGraph. 0 = jamais. */
  lastUpdate: number;
  /** True pendant qu'un scan tourne cote serveur. */
  isRefreshing: boolean;
  setGraph: (nodes: VNode[], links: VLink[]) => void;
  setRefreshing: (v: boolean) => void;
}

export const useVaultGraph = create<State>((set) => ({
  nodes: [],
  links: [],
  lastUpdate: 0,
  isRefreshing: false,
  setGraph: (nodes, links) =>
    set({ nodes, links, lastUpdate: Date.now(), isRefreshing: false }),
  setRefreshing: (v) => set({ isRefreshing: v }),
}));

/* ─── Helpers hors-React reutilisables par les agents ─── */

export const vaultGraph = {
  /** Snapshot hors-React. */
  get: () => useVaultGraph.getState(),

  /** Voisins directs d'un node (source ou target). */
  neighbors: (id: string): VNode[] => {
    const { nodes, links } = useVaultGraph.getState();
    const ids = new Set<string>();
    for (const l of links) {
      const s = typeof l.source === 'string' ? l.source : (l.source as { id: string }).id;
      const t = typeof l.target === 'string' ? l.target : (l.target as { id: string }).id;
      if (s === id) ids.add(t);
      if (t === id) ids.add(s);
    }
    return nodes.filter((n) => ids.has(n.id));
  },

  /** Recherche fuzzy basique sur label. */
  find: (q: string): VNode | undefined => {
    const needle = q.toLowerCase();
    return useVaultGraph.getState().nodes.find(
      (n) => n.label.toLowerCase().includes(needle),
    );
  },

  /** Top N hubs (par nombre de connexions). */
  hubs: (n = 10): VNode[] => {
    return [...useVaultGraph.getState().nodes]
      .sort((a, b) => (b.connections ?? 0) - (a.connections ?? 0))
      .slice(0, n);
  },
};
