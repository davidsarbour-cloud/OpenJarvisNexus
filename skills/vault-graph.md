# vault-graph.md — Vault Graph Sync

Pipeline live : Obsidian (.md) -> WebSocket -> UI Nexus9 planete VAULT.

---

## ROLE

Quand l'utilisateur clique sur la planete VAULT dans l'OrbitalScene,
ouvrir un overlay plein-ecran qui visualise le vault Obsidian comme un
graphe de notes (nodes = .md, edges = [[wikilinks]]). Le graphe est
live : tout edit dans le vault rafraichit l'UI en moins d'une seconde.

---

## ARCHITECTURE

```
Obsidian Vault (.md)
   |
   v
chokidar watcher  (services/vault_graph/server.js)
   |
   v
vaultParser.js  -> { nodes, links, stats }
   |
   v
WebSocket :8084  ----> useVaultGraph (frontend hook)
                          |
                          v
                       VaultGraphOverlay (d3 (force, zoom 100x, drag))
                          |
                       click planet VAULT
                          ^
                       OrbitalScene.tsx
```

---

## FICHIERS

| Cote | Path | Role |
|------|------|------|
| Backend | `services/vault_graph/package.json` | deps : chokidar, ws |
| Backend | `services/vault_graph/vaultParser.js` | walk .md + extract wikilinks |
| Backend | `services/vault_graph/server.js` | watcher + WebSocket port 8084 |
| Backend | `services/vault_graph/.env.example` | template VAULT_PATH |
| Frontend | `frontend/src/stores/vaultGraph.ts` | store Zustand (source unique) |
| Frontend | `frontend/src/components/VaultGraph/useVaultGraphSocket.ts` | hook WS -> store |
| Frontend | `frontend/src/components/VaultGraph/VaultGraphOverlay.tsx` | overlay d3 + slider 100x |
| Frontend | `frontend/src/components/VaultGraph/index.ts` | barrel export |
| Frontend | `frontend/src/components/Orbital/OrbitalScene.tsx` | wire planet click |

---

## LANCEMENT

```bash
# 1. install (une fois)
cd services/vault_graph
npm install

# 2. demarrage (a chaque session)
# Windows PowerShell :
$env:VAULT_PATH = "C:\OpenJarvisNexus\backend\BRAIN\BRAIN"
npm start

# Linux/macOS :
VAULT_PATH=~/Documents/ObsidianVault npm start
```

Puis demarrer le frontend (`3_FRONTEND.bat` ou `cd frontend && npm run dev`),
naviguer vers `/orbital`, cliquer sur la planete VAULT.

---

## PROTOCOLE WEBSOCKET

`ws://localhost:8084`

Server -> client :
```json
{
  "type": "vault:graph",
  "payload": {
    "nodes": [{ "id": "Note A", "group": "projects" }, ...],
    "links": [{ "source": "Note A", "target": "Note B" }, ...],
    "stats": { "files": 42, "links": 87 }
  }
}
```

Le serveur envoie un snapshot a la connexion, puis re-broadcast
le graphe complet a chaque save .md (debounce 250ms).

---

## CONVENTIONS

- `group = '_orphan'` : note referencee via [[...]] mais .md absent
- `group = '_root'` : note a la racine du vault
- `group = '<dossier>'` : dossier de premier niveau (sert au coloriage UI)
- Wikilinks geres : `[[Note]]`, `[[Note|Alias]]`, `[[Note#anchor]]`

---

## EXTENSIONS POSSIBLES

- Filtrage par dossier (cf. Tip "Performance" du cheat sheet — vault > 500 notes)
- Tags Obsidian (#tag) comme noeuds secondaires
- Highlight d'une note depuis JARVIS (orchestrator -> ws message ciblant un id)
- Mode "search" dans l'overlay (Ctrl+F focus + filtre live)
