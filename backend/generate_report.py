"""
Génère un rapport PDF de la session NexusX9.
Lance : python generate_report.py
Ouvre : rapport_nexusx9.html → Ctrl+P → Enregistrer en PDF
"""

from pathlib import Path

HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>NexusX9 — Rapport de Session</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

  * { margin:0; padding:0; box-sizing:border-box; }

  body {
    background: #04060f;
    color: #c8d8ff;
    font-family: 'Rajdhani', sans-serif;
    padding: 40px;
    max-width: 900px;
    margin: 0 auto;
  }

  /* ─── Page de titre ─── */
  .cover {
    text-align: center;
    padding: 60px 0 40px;
    border-bottom: 2px solid #00e5ff33;
    margin-bottom: 40px;
  }
  .cover .sigil {
    font-size: 60px;
    color: #00e5ff;
    text-shadow: 0 0 30px #00e5ff;
    margin-bottom: 16px;
  }
  .cover h1 {
    font-size: 48px;
    font-weight: 700;
    letter-spacing: 0.3em;
    color: #00e5ff;
    text-shadow: 0 0 20px #00e5ff44;
  }
  .cover h1 span { color: white; }
  .cover .subtitle {
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    letter-spacing: 0.4em;
    color: #334466;
    margin-top: 8px;
  }
  .cover .date {
    font-family: 'JetBrains Mono', monospace;
    font-size: 14px;
    color: #00e5ff88;
    margin-top: 20px;
    border: 1px solid #00e5ff22;
    display: inline-block;
    padding: 6px 20px;
    border-radius: 4px;
  }
  .cover .owner {
    font-size: 18px;
    color: #b44dff;
    margin-top: 12px;
    letter-spacing: 0.15em;
  }

  /* ─── Sections ─── */
  .section {
    margin-bottom: 36px;
    break-inside: avoid;
  }
  .section-title {
    font-size: 13px;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 0.4em;
    color: #00e5ff;
    border-left: 3px solid #00e5ff;
    padding-left: 12px;
    margin-bottom: 16px;
  }

  /* ─── Cards ─── */
  .card {
    background: #070d1f;
    border: 1px solid #0f1e3d;
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 12px;
  }
  .card.cyan   { border-color: #00e5ff33; }
  .card.purple { border-color: #b44dff33; }
  .card.gold   { border-color: #ffcc0033; }
  .card.green  { border-color: #00ff8833; }
  .card.orange { border-color: #ff660033; }

  /* ─── Items ─── */
  .item {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    margin-bottom: 8px;
    font-size: 15px;
    line-height: 1.5;
  }
  .item .icon { flex-shrink: 0; font-size: 16px; }
  .item .text { color: #c8d8ff; }
  .item .text strong { color: #00e5ff; }
  .item.done  .icon { color: #00ff88; }
  .item.warn  .icon { color: #ffcc00; }
  .item.plan  .icon { color: #b44dff; }
  .item.info  .icon { color: #4488ff; }

  /* ─── Grid 2 cols ─── */
  .grid-2 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }

  /* ─── Stats ─── */
  .stats-row {
    display: flex;
    gap: 12px;
    margin-bottom: 20px;
    flex-wrap: wrap;
  }
  .stat-badge {
    flex: 1; min-width: 120px;
    background: #070d1f;
    border-radius: 8px;
    padding: 14px 16px;
    text-align: center;
  }
  .stat-badge.cyan   { border: 1px solid #00e5ff33; }
  .stat-badge.purple { border: 1px solid #b44dff33; }
  .stat-badge.gold   { border: 1px solid #ffcc0033; }
  .stat-badge.green  { border: 1px solid #00ff8833; }
  .stat-badge .val {
    font-size: 28px;
    font-weight: 700;
    display: block;
    text-shadow: 0 0 10px currentColor;
  }
  .stat-badge.cyan   .val { color: #00e5ff; }
  .stat-badge.purple .val { color: #b44dff; }
  .stat-badge.gold   .val { color: #ffcc00; }
  .stat-badge.green  .val { color: #00ff88; }
  .stat-badge .lbl {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    letter-spacing: 0.3em;
    color: #334466;
    margin-top: 4px;
  }

  /* ─── Timeline ─── */
  .timeline { position: relative; padding-left: 24px; }
  .timeline::before {
    content: '';
    position: absolute;
    left: 8px; top: 0; bottom: 0;
    width: 1px;
    background: linear-gradient(to bottom, #00e5ff, #b44dff, #00e5ff);
    opacity: 0.3;
  }
  .tl-item {
    position: relative;
    margin-bottom: 16px;
    padding: 12px 16px;
    background: #070d1f;
    border-radius: 6px;
    border: 1px solid #0f1e3d;
  }
  .tl-item::before {
    content: '';
    position: absolute;
    left: -20px; top: 16px;
    width: 8px; height: 8px;
    border-radius: 50%;
    background: #00e5ff;
    box-shadow: 0 0 8px #00e5ff;
  }
  .tl-item .tl-title {
    font-weight: 700;
    color: #00e5ff;
    font-size: 15px;
    margin-bottom: 4px;
  }
  .tl-item .tl-desc {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: #334466;
    line-height: 1.6;
  }

  /* ─── Stack table ─── */
  .stack-table {
    width: 100%;
    border-collapse: collapse;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
  }
  .stack-table th {
    text-align: left;
    color: #334466;
    letter-spacing: 0.3em;
    font-size: 10px;
    padding: 8px 12px;
    border-bottom: 1px solid #0f1e3d;
  }
  .stack-table td {
    padding: 8px 12px;
    border-bottom: 1px solid #0f1e3d08;
    color: #c8d8ff;
  }
  .stack-table tr:hover td { background: #0f1e3d22; }
  .badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 10px;
    letter-spacing: 0.2em;
  }
  .badge.done { background:#00ff8822; color:#00ff88; border:1px solid #00ff8844; }
  .badge.plan { background:#b44dff22; color:#b44dff; border:1px solid #b44dff44; }
  .badge.next { background:#ffcc0022; color:#ffcc00; border:1px solid #ffcc0044; }

  /* ─── Footer ─── */
  footer {
    margin-top: 60px;
    padding-top: 20px;
    border-top: 1px solid #0f1e3d;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: #334466;
  }
  footer .brand { color: #00e5ff; letter-spacing: 0.3em; }

  /* ─── Print ─── */
  @media print {
    body { background: #04060f !important; -webkit-print-color-adjust: exact; }
    .section { break-inside: avoid; }
  }
</style>
</head>
<body>

<!-- ═══ PAGE DE TITRE ═══ -->
<div class="cover">
  <div class="sigil">◈</div>
  <h1>NEXUS<span>X9</span></h1>
  <div class="subtitle">HUB DE COMMANDEMENT IA — RAPPORT DE SESSION</div>
  <div class="owner">David Arbour</div>
  <div class="date">SESSION DU 13-14 MAI 2026 · 00H19</div>
</div>


<!-- ═══ STATS GLOBALES ═══ -->
<div class="section">
  <div class="section-title">VUE D'ENSEMBLE</div>
  <div class="stats-row">
    <div class="stat-badge cyan">
      <span class="val">8</span>
      <div class="lbl">AGENTS IA</div>
    </div>
    <div class="stat-badge purple">
      <span class="val">7</span>
      <div class="lbl">PHASES LIVRÉES</div>
    </div>
    <div class="stat-badge gold">
      <span class="val">4</span>
      <div class="lbl">INTERFACES</div>
    </div>
    <div class="stat-badge green">
      <span class="val">~80%</span>
      <div class="lbl">COÛT ÉCONOMISÉ</div>
    </div>
  </div>
</div>


<!-- ═══ TIMELINE AUJOURD'HUI ═══ -->
<div class="section">
  <div class="section-title">CE QU'ON A CONSTRUIT AUJOURD'HUI</div>
  <div class="timeline">

    <div class="tl-item">
      <div class="tl-title">🏗️ Phase 1 — Backend FastAPI</div>
      <div class="tl-desc">
        API Python fonctionnelle · Port 8000 · CORS configuré<br>
        Claude Sonnet 4-6 connecté (workspace Nexus9 · $61 crédits)
      </div>
    </div>

    <div class="tl-item">
      <div class="tl-title">🐛 Phase 2 — Débogage intensif</div>
      <div class="tl-desc">
        ✓ httpx/anthropic conflict → versions pinnées<br>
        ✓ 3 clés API testées → bonne clé trouvée<br>
        ✓ Format modèle: claude-sonnet-4-6 (sans date)<br>
        ✓ CORS 400 → port 5173 ajouté<br>
        ✓ "No response" → streaming SSE ajouté<br>
        ✓ PowerShell curl bug → Python pour tous appels
      </div>
    </div>

    <div class="tl-item">
      <div class="tl-title">🧠 Phase 3 — Mémoire Persistante</div>
      <div class="tl-desc">
        memory.py · sessions.json · memory.json<br>
        Jarvis te connaît et survit aux redémarrages
      </div>
    </div>

    <div class="tl-item">
      <div class="tl-title">🎭 Phase 4 — Personnalisation Française</div>
      <div class="tl-desc">
        config.json · personnalité co-fondateur cyberpunk<br>
        Parle toujours en français · Règles et expertise configurées
      </div>
    </div>

    <div class="tl-item">
      <div class="tl-title">💻 Phase 5 — Ollama Local Gratuit</div>
      <div class="tl-desc">
        ollama_client.py · qwen3:14b · deepseek-coder<br>
        Routing intelligent: local 80% du temps → 0$ pour questions simples
      </div>
    </div>

    <div class="tl-item">
      <div class="tl-title">👥 Phase 6 — CrewAI Multi-Agents</div>
      <div class="tl-desc">
        crew_agents.py · crew_factory.py<br>
        Architecte (Claude) · Chercheur (Ollama) · Développeur (Ollama)
      </div>
    </div>

    <div class="tl-item">
      <div class="tl-title">📱 Phase 7 — Telegram Bot</div>
      <div class="tl-desc">
        telegram_bot.py v2 · Monitoring proactif toutes les 5 min<br>
        /start /status /diag /memory /hub /crew /clear<br>
        Alertes automatiques si backend tombe
      </div>
    </div>

    <div class="tl-item">
      <div class="tl-title">🌌 Phase 8 — NexusX9 Hub Cyberpunk UI</div>
      <div class="tl-desc">
        React + TypeScript + Tailwind · Port 5174<br>
        8 pièces agents RPG avec toggle ON/OFF<br>
        Sidebar gauche · Panel central · Panel droit<br>
        Chat Jarvis + Missions CrewAI intégrés
      </div>
    </div>

  </div>
</div>


<!-- ═══ ARCHITECTURE FINALE ═══ -->
<div class="section">
  <div class="section-title">ARCHITECTURE NEXUSX9</div>
  <div class="card cyan">
    <table class="stack-table">
      <thead>
        <tr>
          <th>SERVICE</th>
          <th>URL</th>
          <th>TECHNOLOGIE</th>
          <th>STATUT</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>🌌 NexusX9 Hub</td>
          <td>localhost:5174</td>
          <td>React + TypeScript + Tailwind</td>
          <td><span class="badge done">LIVRÉ</span></td>
        </tr>
        <tr>
          <td>💬 OpenJarvis Chat</td>
          <td>localhost:5173</td>
          <td>Vite + React (open-source)</td>
          <td><span class="badge done">ACTIF</span></td>
        </tr>
        <tr>
          <td>⚡ Backend FastAPI</td>
          <td>localhost:8000</td>
          <td>Python + FastAPI + Anthropic</td>
          <td><span class="badge done">ACTIF</span></td>
        </tr>
        <tr>
          <td>🤖 Ollama Local</td>
          <td>localhost:11434</td>
          <td>qwen3:14b + deepseek-coder</td>
          <td><span class="badge done">ACTIF</span></td>
        </tr>
        <tr>
          <td>📱 Telegram Bot</td>
          <td>@ton_bot_telegram</td>
          <td>python-telegram-bot v21</td>
          <td><span class="badge done">ACTIF</span></td>
        </tr>
      </tbody>
    </table>
  </div>
</div>


<!-- ═══ 8 AGENTS ═══ -->
<div class="section">
  <div class="section-title">LES 8 AGENTS NEXUSX9</div>
  <div class="grid-2">
    <div class="card cyan">
      <div class="item done"><span class="icon">◈</span>
        <div class="text"><strong>Architecte</strong> — Claude<br>
          <span style="font-size:12px;color:#334466;">Planification · Orchestration · Décisions</span></div>
      </div>
    </div>
    <div class="card gold">
      <div class="item done"><span class="icon">☼</span>
        <div class="text"><strong>Tour Claude</strong> — Claude<br>
          <span style="font-size:12px;color:#334466;">Raisonnement complexe · Escalade</span></div>
      </div>
    </div>
    <div class="card purple">
      <div class="item done"><span class="icon">✺</span>
        <div class="text"><strong>Laboratoire</strong> — Ollama<br>
          <span style="font-size:12px;color:#334466;">Recherche · Analyse · Résumés</span></div>
      </div>
    </div>
    <div class="card" style="border-color:#ff00cc33">
      <div class="item done"><span class="icon">▤</span>
        <div class="text"><strong>Coffre Mémoire</strong> — Système<br>
          <span style="font-size:12px;color:#334466;">Stockage persistant · Rappels</span></div>
      </div>
    </div>
    <div class="card" style="border-color:#4488ff33">
      <div class="item done"><span class="icon">◐</span>
        <div class="text"><strong>Zone Locale</strong> — Ollama<br>
          <span style="font-size:12px;color:#334466;">IA gratuite · qwen3:14b local</span></div>
      </div>
    </div>
    <div class="card orange">
      <div class="item done"><span class="icon">⚙</span>
        <div class="text"><strong>Atelier Code</strong> — Ollama<br>
          <span style="font-size:12px;color:#334466;">Code · Scripts · deepseek-coder</span></div>
      </div>
    </div>
    <div class="card green">
      <div class="item done"><span class="icon">◉</span>
        <div class="text"><strong>Surveillance</strong> — Système<br>
          <span style="font-size:12px;color:#334466;">Logs · Alertes · Monitoring</span></div>
      </div>
    </div>
    <div class="card" style="border-color:#c8d8ff33">
      <div class="item done"><span class="icon">✦</span>
        <div class="text"><strong>Tableau Missions</strong> — Système<br>
          <span style="font-size:12px;color:#334466;">Queue · Scheduler · CrewAI jobs</span></div>
      </div>
    </div>
  </div>
</div>


<!-- ═══ PLAN DEMAIN ═══ -->
<div class="section">
  <div class="section-title">PLAN POUR DEMAIN</div>

  <div class="card purple" style="margin-bottom:16px;">
    <div style="font-family:'JetBrains Mono',monospace;font-size:11px;color:#b44dff;
                letter-spacing:0.3em;margin-bottom:12px;">MATIN — STABILITÉ</div>
    <div class="item plan"><span class="icon">1️⃣</span>
      <div class="text"><strong>Smoke Tests complets</strong><br>
        <span style="font-size:12px;color:#334466;">Script automatique · Vérifier tous les services · 30 min</span></div>
    </div>
    <div class="item plan"><span class="icon">2️⃣</span>
      <div class="text"><strong>Fix bugs TypeScript NexusX9</strong><br>
        <span style="font-size:12px;color:#334466;">53 erreurs à corriger · Interface propre · 1h</span></div>
    </div>
    <div class="item plan"><span class="icon">3️⃣</span>
      <div class="text"><strong>Dashboard logs agents</strong><br>
        <span style="font-size:12px;color:#334466;">Voir en temps réel ce que les agents font · 30 min</span></div>
    </div>
    <div class="item plan"><span class="icon">4️⃣</span>
      <div class="text"><strong>NVIDIA CUDA Toolkit</strong><br>
        <span style="font-size:12px;color:#334466;">Ollama 5-10x plus rapide sur GPU · 20 min</span></div>
    </div>
  </div>

  <div class="card gold">
    <div style="font-family:'JetBrains Mono',monospace;font-size:11px;color:#ffcc00;
                letter-spacing:0.3em;margin-bottom:12px;">APRÈS-MIDI — EXPANSION</div>
    <div class="item plan"><span class="icon">5️⃣</span>
      <div class="text"><strong>N8N + CrewAI Automation</strong><br>
        <span style="font-size:12px;color:#334466;">Automatisation visuelle · Workflows multi-agents · 2h</span></div>
    </div>
    <div class="item plan"><span class="icon">6️⃣</span>
      <div class="text"><strong>Shopify → Jarvis</strong><br>
        <span style="font-size:12px;color:#334466;">API Shopify · Jarvis répond questions produits/stocks · 1h</span></div>
    </div>
    <div class="item plan"><span class="icon">7️⃣</span>
      <div class="text"><strong>Boutique Etsy + Jarvis</strong><br>
        <span style="font-size:12px;color:#334466;">Créer boutique · API Etsy · Link avec Jarvis · 1h</span></div>
    </div>
    <div class="item plan"><span class="icon">8️⃣</span>
      <div class="text"><strong>NVIDIA Morpheus Sécurité</strong><br>
        <span style="font-size:12px;color:#334466;">Cybersécurité IA · Monitore accès NexusX9 · Alertes Telegram · 1h</span></div>
    </div>
  </div>
</div>


<!-- ═══ ROADMAP LONG TERME ═══ -->
<div class="section">
  <div class="section-title">ROADMAP LONG TERME</div>
  <table class="stack-table">
    <thead>
      <tr><th>SEMAINE</th><th>OBJECTIF</th><th>PRIORITÉ</th></tr>
    </thead>
    <tbody>
      <tr>
        <td>Demain</td>
        <td>Fix UI · GPU · Shopify · Etsy · N8N</td>
        <td><span class="badge done">CRITIQUE</span></td>
      </tr>
      <tr>
        <td>Semaine 2</td>
        <td>NVIDIA NIM (remplace Ollama) · Vector DB mémoire infinie</td>
        <td><span class="badge next">HAUTE</span></td>
      </tr>
      <tr>
        <td>Semaine 3</td>
        <td>Docker pour tout packager · Déploiement serveur</td>
        <td><span class="badge plan">MOYENNE</span></td>
      </tr>
      <tr>
        <td>Semaine 4</td>
        <td>NexusX9 v2 · PixiJS isométrique 3D · Animations agents</td>
        <td><span class="badge plan">BONUS</span></td>
      </tr>
      <tr>
        <td>Mois 2</td>
        <td>Multi-utilisateurs · API publique · Marketplace agents</td>
        <td><span class="badge plan">FUTUR</span></td>
      </tr>
    </tbody>
  </table>
</div>


<!-- ═══ NOTES IMPORTANTES ═══ -->
<div class="section">
  <div class="section-title">NOTES & RAPPELS TECHNIQUES</div>
  <div class="card" style="border-color:#0f1e3d">
    <div class="item info"><span class="icon">📌</span>
      <div class="text">Utiliser <strong>Python</strong> au lieu de curl dans PowerShell (évite le bug des crochets [])</div>
    </div>
    <div class="item info"><span class="icon">📌</span>
      <div class="text">Workspace Anthropic = <strong>Nexus9</strong> · Format modèle: <strong>claude-sonnet-4-6</strong> (sans date)</div>
    </div>
    <div class="item info"><span class="icon">📌</span>
      <div class="text">Frontend: port <strong>5173</strong> · NexusX9: port <strong>5174</strong> · Backend: port <strong>8000</strong> · Ollama: port <strong>11434</strong></div>
    </div>
    <div class="item info"><span class="icon">📌</span>
      <div class="text">Toujours lancer avec <strong>load_dotenv(override=True)</strong> — évite les variables OS qui écrasent .env</div>
    </div>
    <div class="item info"><span class="icon">📌</span>
      <div class="text">Clé API dans <strong>backend/.env</strong> — ignorer root .env et frontend .env.local</div>
    </div>
    <div class="item warn"><span class="icon">⚠️</span>
      <div class="text">Crédits Anthropic: <strong>$61</strong> restants · Activer auto-reload dans les settings</div>
    </div>
    <div class="item warn"><span class="icon">⚠️</span>
      <div class="text">NexusX9 Hub a <strong>53 erreurs TypeScript</strong> à corriger demain matin en priorité</div>
    </div>
  </div>
</div>


<!-- ═══ FOOTER ═══ -->
<footer>
  <div class="brand">◈ NEXUSX9</div>
  <div>Hub de Commandement IA · David Arbour · 2026</div>
  <div style="color:#00e5ff44">Confidentiel</div>
</footer>

</body>
</html>"""

output = Path("rapport_nexusx9.html")
output.write_text(HTML, encoding="utf-8")
print(f"✅ Rapport généré : {output.absolute()}")
print()
print("📄 Pour créer le PDF :")
print("  1. Ouvre rapport_nexusx9.html dans Chrome")
print("  2. Ctrl + P")
print("  3. Destination : Enregistrer en PDF")
print("  4. Format : A4, Marges : Aucune, Cocher 'Graphiques d'arrière-plan'")
print("  → PDF noir cyberpunk parfait ✅")

if __name__ == "__main__":
    pass