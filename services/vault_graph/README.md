# Nexus9 — Vault Graph Sync

Sidecar Node.js qui parse un vault Obsidian et broadcast le graphe
(`{nodes, links}`) vers la UI Nexus9 via WebSocket.

Pipeline : Obsidian (.md) -> chokidar -> parser wikilinks -> WebSocket -> planete VAULT.

## Ports

- `8084` (WebSocket) -- choisi pour ne pas entrer en collision avec
  Obsidian Skills (8081) et Superpowers (8082) deja documentes dans
  `skills/architecture.md`.

## Install

```bash
cd services/vault_graph
npm install
```

## Run

```bash
# Windows PowerShell
$env:VAULT_PATH = "C:\OpenJarvisNexus\backend\BRAIN\BRAIN"
npm start
```

```bash
# Linux/macOS
VAULT_PATH=~/Documents/ObsidianVault npm start
```

Variables d'env :

| Variable | Default | Role |
|----------|---------|------|
| `VAULT_PATH` | `../../backend/BRAIN/BRAIN` | Chemin absolu du vault Obsidian |
| `VAULT_GRAPH_PORT` | `8084` | Port WebSocket |
| `VAULT_DEBOUNCE_MS` | `250` | Fenetre de debounce du re-parse |

## Protocole WebSocket

Connexion : `ws://localhost:8084`

Messages serveur -> client :

```json
{ "type": "vault:graph", "payload": { "nodes": [...], "links": [...], "stats": {...} } }
```

- `nodes[i]` : `{ id: string, group?: string }`
  - `group = '_orphan'` quand la note est referencee mais n'existe pas
  - `group = '_root'` quand la note est a la racine du vault
- `links[i]` : `{ source: string, target: string }`

Le serveur envoie un snapshot initial des l'ouverture du socket, puis
re-broadcast a chaque changement de fichier .md.

## Smoke test

```bash
npm run check   # syntaxe Node
node -e "import('./vaultParser.js').then(m => console.log(m.parseVault(process.env.VAULT_PATH ?? '.')))"
```
