# PLAN NEXUS9 — Audit + Roadmap UI/Écosystème

**Auteur** : Claude (Cowork) pour David Arbour
**Date** : 2026-05-20
**Statut** : Proposition — à valider avant exécution

---

## 1. État actuel — Cartographie

### 1.1 Backend (FastAPI, port 8000)

`backend/main.py` est l'unique point d'entrée. Il agrège :

- **8 routers inclus** : `stl_router`, `research_router`, `forge_router`, `vault_router`, `files_router`, `commerce_router`, `etsy_oauth_router`, `crew_factory`
- **~50 routes REST déjà exposées** : `/v1/agents`, `/v1/chat/completions`, `/v1/crew/*`, `/v1/memory/*`, `/v1/budget`, `/v1/health/deep`, `/v1/savings`, `/v1/models`, `/v1/business/stats`, `/v1/reports/*`, `/v1/orchestrate`, `/v1/smoke-test`, etc.
- **Logger d'erreurs** correctement configuré sur `backend/error_logs/errors.log`
- **Apscheduler** branché pour les tâches journalières
- **CORS** : `localhost:5173,3000,8080` — déjà prêt pour le dev React

**Routes UI actuellement servies par FastAPI** :
- `GET /` → renvoie `Nexus9.html` (monolithique, 132 KB, vanilla)
- `GET /orbital` → renvoie `frontend/orbital_ui/orbital.html` (vanilla JS + canvas)
- `GET /callback` → page HTML inline pour OAuth Etsy

### 1.2 Frontend React (Vite + TS, port dev 5173)

Stack **installée mais 0% utilisée** dans `frontend/src/` :

| Lib installée | Utilisée ? |
|---|---|
| `@arwes/react` | ❌ Aucun import |
| `@react-three/fiber` + `@react-three/drei` + `three` | ❌ Aucun import |
| `@xyflow/react` (React Flow) | ❌ Aucun import |
| `motion` (Framer Motion) | ❌ Aucun import |
| `recharts` | ❌ Aucun import |
| `shadcn/ui` | ⚠️ Setup présent (`components.json`, dossier `ui/`) |
| `zustand` | ✅ Utilisé (`lib/store.ts`) |
| `react-router` v7 | ✅ Utilisé |

**Routes React actuelles** (`App.tsx`) :
```
/             → ChatPage
/dashboard    → DashboardPage  (Energy + CostComparison + TraceDebugger)
/data-sources → DataSourcesPage
/agents       → AgentsPage     (174 KB — gros fichier)
/logs         → LogsPage
/settings     → SettingsPage
/get-started  → GetStartedPage
```

**Sidebar actuelle** (`Sidebar.tsx`) : liste plate `Chat / Dashboard / Data Sources / Agents / Logs / Settings / Get Started`. Aucune organisation par sections AI ENTITIES / SYSTEMS / TOOLS comme le brief le demande.

### 1.3 Orbital UI (`frontend/orbital_ui/`)

Implémentation **vanilla JS** (pas React), à parité fonctionnelle avancée :

- 13 composants JS : `Planet3DScene`, `OrbitSystem`, `GalaxyBackground`, `StarCore`, `PlanetNode`, `SpaceshipNode`, `ModulePanel`, `AgentActivityOverlay`, `VoiceManager`, `ChatDock`, `PipelineHub`, `ForgeHub`, `OrchestrationPanel`
- 9 modules planètes : `forge_room`, `ultron`, `vault`, `cyberdeck`, `missions`, `commerce`, `bruce`, `cortana`, `comm_hub`
- 6 feuilles CSS : `galaxy`, `orbit`, `planets`, `comm`, `pipeline`, `forge_hub`

**Problème** : ce module fait double emploi avec ce qu'on devrait construire en React + R3F dans `frontend/src/`.

### 1.4 Docker (état actuel `docker-compose.yml`)

Services en place :

| Service | Port | Statut |
|---|---|---|
| `ollama` | 11434 | OK (GPU NVIDIA) |
| `backend` (FastAPI) | 8000 | OK |
| `frontend` (nginx Vite build) | 5173→80 | OK |
| `telegram` | — | OK |
| `bruce` (OpenHands) | 3000 | OK |
| **ChromaDB** | — | ❌ **MANQUANT** malgré référence dans CLAUDE.md et le brief |

---

## 2. Bugs et points faibles identifiés

### 2.1 Bugs « hygiène » (rapides à corriger)

1. **Fichiers Python vides à la racine** :
   - `security_monitor.py` (0 byte) — orphelin, jamais importé → à supprimer ou implémenter
   - `shopify_integration.py` (0 byte) — orphelin → à supprimer ou implémenter
2. **Doublons** :
   - `prometheus.yaml` + `prometheus.yml/` (dossier) + `prometheus_1.yml` + `prometheus/` (dossier) → 4 sources de configuration Prometheus en conflit
   - `docker-compose.yml` + `docker-compose.yml.backup` → backup à archiver
   - `backend/index_skills.py` + `backend/index_skills_enriched.py` → dédupliquer
3. **Dossier au nom suspect** : `OpenJarvisNexusservicescrush_ai/` (probablement créé par erreur, à inspecter puis renommer/supprimer)
4. **Tests `__init__.py` vides partout** sous `tests/*/` — normal en Python, à laisser

### 2.2 Bugs « architecture » (vrai travail)

5. **UI principale dispersée sur 3 codebases** : Nexus9.html monolithique (132 KB), orbital_ui vanilla JS, app React inutilisée → impossible à maintenir
6. **App React = coquille vide** : stack ARWES + Three + R3F + React Flow installée mais aucun fichier ne l'importe — dette d'installation
7. **Pas de Command Center** : la `DashboardPage` actuelle est minimaliste (Energy + Cost + Trace), ne correspond pas du tout au brief « tactical command bridge »
8. **Pas de switch routing** entre Command Center et Orbital View dans la nav React
9. **Aucun widget de monitoring live** pour Prometheus / Grafana / SonarQube / Docker / ChromaDB
10. **Pas d'identité couleur** par module/planète (Forge orange, Commerce teal, etc.)

### 2.3 Bugs backend potentiels (à vérifier en Phase 0)

11. Vérifier que tous les `from xxx import router` au démarrage de `main.py` n'échouent pas (8 imports de routers, si un seul casse → backend KO)
12. `index_skills_enriched.py` peut-être un fix non-mergé de `index_skills.py`
13. ChromaDB manquant dans Docker → toute route qui tente d'y parler échoue silencieusement

---

## 3. Architecture cible

### 3.1 Principe de consolidation

**Une seule UI** servie par FastAPI à `/`, basée sur l'app React existante.

```
http://localhost:8000/          → React Command Center      (NOUVEAU)
http://localhost:8000/orbital   → React Orbital View        (port du vanilla actuel)
http://localhost:8000/chat      → ChatPage                  (déjà existant)
http://localhost:8000/agents    → AgentsPage                (déjà existant)
http://localhost:8000/v1/*      → API REST (inchangé)

http://localhost:5173/          → Vite dev server (proxy /v1 → :8000) pour le dev
```

`Nexus9.html` est archivé dans `legacy/` et conservé en lecture seule.
`frontend/orbital_ui/` est archivé dans `legacy/orbital_ui_vanilla/` puis supprimé du serving.

### 3.2 Structure cible `frontend/src/`

```
frontend/src/
├── App.tsx                          (router)
├── components/
│   ├── Layout/
│   │   ├── HudLayout.tsx            (top bar + sidebar + center + right + bottom)
│   │   ├── TopBar.tsx               (logo Nexus9 + switch CC/Orbital + clock + status pills)
│   │   ├── HudSidebar.tsx           (3 sections : AI ENTITIES / SYSTEMS / TOOLS)
│   │   ├── RightPanel.tsx           (alerts + logs + events feed)
│   │   └── BottomPanel.tsx          (graphs Recharts)
│   ├── CommandCenter/
│   │   ├── SystemHealthCard.tsx     (CPU/RAM/GPU — live /v1/health/deep)
│   │   ├── AgentActivityCard.tsx    (live /v1/agents)
│   │   ├── DockerContainersCard.tsx (live /v1/docker/containers — NEW route)
│   │   ├── OllamaStatusCard.tsx     (live /v1/models)
│   │   ├── ForgePipelinesCard.tsx   (live /v1/crew/jobs)
│   │   ├── MemoryCard.tsx           (ChromaDB — mock d'abord)
│   │   ├── PrometheusCard.tsx       (iframe embed + mock summary)
│   │   ├── GrafanaCard.tsx          (iframe embed)
│   │   ├── SonarqubeCard.tsx        (mock + iframe)
│   │   └── SecurityCard.tsx         (mock)
│   ├── Orbital/
│   │   ├── OrbitalScene.tsx         (R3F Canvas)
│   │   ├── JarvisCore.tsx           (sun central, cyan)
│   │   ├── Planet.tsx               (générique, props: color, orbit, label, onClick)
│   │   ├── OrbitRing.tsx
│   │   ├── Starfield.tsx
│   │   ├── ModulePanel.tsx          (shadcn Dialog au click planète)
│   │   └── planets.config.ts        (Forge orange / Vault purple / Cyberdeck red / Commerce teal / Docker green)
│   ├── ui/                          (shadcn — déjà là)
│   └── arwes/                       (wrappers Frame/Animator au-dessus de ARWES)
├── pages/
│   ├── CommandCenterPage.tsx        (NOUVEAU — page /)
│   ├── OrbitalPage.tsx              (NOUVEAU — page /orbital)
│   ├── ChatPage.tsx                 (existant, garder)
│   ├── AgentsPage.tsx               (existant, garder)
│   ├── DashboardPage.tsx            (existant, garder ou fusionner dans CommandCenter)
│   ├── LogsPage.tsx                 (existant)
│   ├── SettingsPage.tsx             (existant)
│   ├── DataSourcesPage.tsx          (existant)
│   └── GetStartedPage.tsx           (existant)
├── lib/
│   ├── api.ts                       (existant, étendre avec nouveaux endpoints)
│   ├── store.ts                     (existant Zustand)
│   ├── colors.ts                    (NOUVEAU — palette par module)
│   └── ws.ts                        (NOUVEAU — WebSocket client pour /ws/events)
└── hooks/
    ├── useLiveMetric.ts             (NOUVEAU — polling générique)
    └── useWsEvents.ts               (NOUVEAU)
```

### 3.3 Palette d'identité (`lib/colors.ts`)

| Module | Couleur principale | Hex | Usage |
|---|---|---|---|
| JARVIS Core | cyan | `#00d4ff` | sun, accents globaux |
| Forge | orange | `#ff8a00` | planète, badges, headers Forge |
| Commerce | teal | `#00d4a8` | Etsy, Shopify |
| Cyberdeck | red | `#ff2d55` | sécurité, alertes |
| Vault | purple | `#a855f7` | memory, knowledge |
| Docker | green | `#00ff88` | containers, infra |

Exposé via CSS custom properties (`--color-forge`, etc.) dans `index.css`.

### 3.4 Switch Command Center ↔ Orbital

Bouton dans `TopBar` :
- `[ COMMAND CENTER ]` (actif) / `[ ORBITAL VIEW ]`
- Click → `navigate('/')` ou `navigate('/orbital')`
- Style ARWES `Frame` + Framer Motion transition

### 3.5 Backend — nouveaux endpoints (Phase 4)

Endpoint | Source | Mode
---|---|---
`GET /v1/docker/containers` | `docker ps` ou socket | Live
`GET /v1/prometheus/query?q=...` | Proxy vers `:9090/api/v1/query` | Live
`GET /v1/grafana/dashboards` | Proxy vers `:3001/api/search` | Live
`GET /v1/sonarqube/issues` | Proxy auth vers `:9000/api/issues/search` | Hybride (mock si KO)
`GET /v1/chromadb/stats` | Proxy vers ChromaDB (`:8001`) | Hybride
`WS  /ws/events` | EventBus interne → push alerts/logs | Live

Tous codés dans `backend/routers/monitoring.py` (NEW), inclus comme nouveau router.

---

## 4. Roadmap par phases

Phases courtes, chacune **mergeable indépendamment**, chacune doit laisser le système en état marchant.

### Phase 0 — Hygiène (≈ 1 session courte)

- [ ] Supprimer `security_monitor.py` (0 byte) et `shopify_integration.py` (0 byte) à la racine
- [ ] Déplacer `docker-compose.yml.backup` → `legacy/`
- [ ] Consolider les 4 sources Prometheus en **un seul** `prometheus.yml` à la racine
- [ ] Inspecter `OpenJarvisNexusservicescrush_ai/` → renommer ou supprimer
- [ ] Ajouter le service **ChromaDB** au `docker-compose.yml` (image `chromadb/chroma`, port 8001)
- [ ] Décider du sort de `index_skills.py` vs `index_skills_enriched.py`
- [ ] Lancer un smoke test : `python -m uvicorn backend.main:app` pour vérifier qu'aucun import ne casse

**Critère de sortie** : `docker compose up` démarre tous les services sans erreur, FastAPI répond `200` sur `/health`.

### Phase 1 — Squelette UI React (≈ 2-3 sessions)

- [ ] Créer `components/Layout/HudLayout.tsx` (grid 5 zones : top / left / center / right / bottom)
- [ ] Créer `components/Layout/TopBar.tsx` avec switch CC/Orbital + clock + status pills
- [ ] Refondre `Sidebar.tsx` en 3 sections (AI ENTITIES / SYSTEMS / TOOLS) — items pour l'instant cliquables vers placeholders
- [ ] Créer `pages/CommandCenterPage.tsx` (route `/`, layout HUD + cards placeholders)
- [ ] Créer `pages/OrbitalPage.tsx` (route `/orbital`, scène R3F vide avec starfield)
- [ ] Mettre à jour `App.tsx` : nouvelle route `/` = CommandCenter, `/chat` = ancienne ChatPage
- [ ] Ajouter `lib/colors.ts` + CSS variables
- [ ] Ajouter premiers composants ARWES (`Animator`, `Frame`) en wrappers

**Critère de sortie** : `npm run dev` → `localhost:5173/` affiche le HUD Command Center vide, `localhost:5173/orbital` affiche un starfield Three.js.

### Phase 2 — Widgets Command Center hybrides (≈ 3-4 sessions)

Pour chaque widget : composant React + endpoint live (ou mock) + Recharts si série temporelle.

- [ ] `SystemHealthCard` (live `/v1/health/deep` + Recharts area)
- [ ] `OllamaStatusCard` (live `/v1/models` — liste modèles + activité)
- [ ] `AgentActivityCard` (live `/v1/agents` — JARVIS / ULTRON / QWEN / CORTANA / BRUCE / NOVA / FORGE)
- [ ] `ForgePipelinesCard` (live `/v1/crew/jobs`)
- [ ] `MemoryCard` (mock — placeholder ChromaDB)
- [ ] `DockerContainersCard` (mock d'abord, endpoint live en Phase 4)
- [ ] `PrometheusCard` (mock + bouton « Open Grafana » → `:3001`)
- [ ] `GrafanaCard` (iframe embed minimal)
- [ ] `SonarqubeCard` (mock)
- [ ] `RightPanel` : feed live `/v1/logs`
- [ ] `BottomPanel` : 2-3 graphs Recharts (load, savings, energy)

**Critère de sortie** : Command Center affiche 10 cards, 5 sont live, 5 sont mock visiblement étiquetées `DEMO`.

### Phase 3 — Orbital View React (≈ 3-4 sessions)

Port du vanilla JS vers React + R3F. Réutiliser la **logique mathématique** (`OrbitSystem.js` Lissajous) en TS.

- [ ] `OrbitalScene` : Canvas R3F + lights + ambient
- [ ] `Starfield` : 2000 particules instanced
- [ ] `JarvisCore` : sphère cyan émissive au centre + halo bloom
- [ ] `Planet` générique : sphère + ring + label + click handler
- [ ] `planets.config.ts` : 5 planètes (Forge / Vault / Cyberdeck / Commerce / Docker)
- [ ] Animation orbites (useFrame) + Lissajous pour Spaceships (Ultron, Qwen, Cortana, Bruce)
- [ ] `ModulePanel` (shadcn Dialog) — overlay au click planète, contenu spécifique par planète
- [ ] Camera : `OrbitControls` + zoom-on-click Framer Motion
- [ ] HUD overlay (réutilisable depuis CommandCenter)

**Critère de sortie** : `/orbital` affiche un vrai système solaire interactif, clic sur Forge ouvre le ModulePanel orange.

### Phase 4 — Backend endpoints live (≈ 2 sessions)

- [ ] Créer `backend/routers/monitoring.py`
- [ ] `GET /v1/docker/containers` (via `docker` SDK Python ou `subprocess`)
- [ ] `GET /v1/prometheus/query` (proxy auth)
- [ ] `GET /v1/grafana/dashboards`
- [ ] `GET /v1/sonarqube/issues`
- [ ] `GET /v1/chromadb/stats`
- [ ] `WS /ws/events` — pub/sub interne (logs FastAPI + events Forge + alertes)
- [ ] Brancher widgets CommandCenter au live (remplacer les mocks)

**Critère de sortie** : tous les widgets Command Center sont live (sauf ceux qu'on a choisi explicitement de laisser en demo).

### Phase 5 — Servir React via FastAPI (≈ 1 session)

- [ ] `npm run build` → `frontend/dist/`
- [ ] Dans `main.py`, route `/` → `FileResponse('frontend/dist/index.html')` (au lieu de Nexus9.html)
- [ ] `app.mount('/assets', StaticFiles(directory='frontend/dist/assets'))`
- [ ] Catch-all SPA : route `{full_path:path}` → `dist/index.html` pour react-router
- [ ] Archiver `Nexus9.html` → `legacy/Nexus9.html`
- [ ] Archiver `frontend/orbital_ui/` → `legacy/orbital_ui_vanilla/`
- [ ] Mettre à jour `docker-compose.yml` frontend → build une fois et serve via FastAPI (option : supprimer le service nginx séparé)

**Critère de sortie** : `http://localhost:8000/` (sans Vite) affiche le Command Center React.

### Phase 6 — Polish (≈ 2 sessions)

- [ ] Animations Framer Motion (pulse alertes, expansion panels, transitions de route)
- [ ] Sound effects ARWES (opt-in dans Settings)
- [ ] Tests fumée Playwright sur `/` et `/orbital`
- [ ] Page Settings : toggle dev/demo, toggle sons, choix thème
- [ ] CHANGELOG.md mis à jour
- [ ] README.md mis à jour avec captures

---

## 5. Ordre d'exécution recommandé

Strictement séquentiel pour ne pas casser un état marchant :

```
Phase 0  (hygiène)
   ↓
Phase 1  (squelette UI)
   ↓
Phase 2  (widgets — mock OK)        ←──┐
   ↓                                    │
Phase 3  (orbital R3F)                 │  Phase 4 peut commencer en
   ↓                                    │  parallèle de Phase 3
Phase 4  (endpoints live) ─────────────┘
   ↓
Phase 5  (servir React via FastAPI)
   ↓
Phase 6  (polish)
```

---

## 6. Décisions à valider (avant code)

1. **OK pour archiver `Nexus9.html`** (132 KB monolithique) après Phase 5 ?
2. **OK pour archiver le `orbital_ui` vanilla JS** une fois la version React livrée ?
3. **OK pour servir l'UI React via FastAPI à `/`** (et utiliser Vite dev server uniquement pendant le dev) ?
4. **OK pour le set de 5 planètes Forge/Vault/Cyberdeck/Commerce/Docker** ? (Le brief mentionne ces 5, mais le code actuel a 9 modules incluant Ultron, Bruce, Cortana, Missions — on les garde comme **spaceships en orbite** autour de JARVIS, pas comme planètes)
5. **OK pour ajouter ChromaDB au docker-compose** ?
6. **OK pour supprimer `security_monitor.py` et `shopify_integration.py` vides** ?

---

## 7. Premier livrable concret (si tu valides ce plan)

Je commencerai par **Phase 0 (hygiène)** en une seule passe, puis je m'arrêterai pour te montrer l'état avant d'attaquer Phase 1. Tu valides à chaque fin de phase.

---

**Prochaine action attendue** : ta validation (oui/modifications) sur les questions de la section 6, puis je démarre Phase 0.
