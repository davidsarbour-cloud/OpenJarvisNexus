/**
 * orbital_ui_main.js — Nexus9 Orbital UI entry point.
 *
 * This is ONLY a visual navigation layer.
 * All logic lives in the existing Nexus9 backend (localhost:8000).
 * No backend logic is duplicated here.
 */

import { GalaxyBackground }    from './components/GalaxyBackground.js';
import { StarCore }             from './components/StarCore.js';
import { OrbitSystem }          from './components/OrbitSystem.js';
import { PlanetNode }           from './components/PlanetNode.js';
import { ModulePanel }          from './components/ModulePanel.js';
import { AgentActivityOverlay } from './components/AgentActivityOverlay.js';
import { VoiceManager }         from './components/VoiceManager.js';
import { ChatDock }             from './components/ChatDock.js';
import { PipelineHub }          from './components/PipelineHub.js';
import { ForgeHub }             from './components/ForgeHub.js';
import { CommHub }              from './modules/comm_hub.js';

import { FORGE_CONFIG }    from './modules/forge_room_planet.js';
import { ULTRON_CONFIG }   from './modules/ultron_planet.js';
import { VAULT_CONFIG }    from './modules/vault_planet.js';
import { CYBERDECK_CONFIG } from './modules/cyberdeck_planet.js';
import { MISSIONS_CONFIG } from './modules/missions_planet.js';
import { COMMERCE_CONFIG } from './modules/commerce_planet.js';
import { BRUCE_CONFIG }    from './modules/bruce_planet.js';
import { CORTANA_CONFIG }  from './modules/cortana_planet.js';

const BACKEND = 'http://localhost:8000';

// ── Handlers globaux d'erreurs (Task 7.2) ──────────────
window.onerror = (msg, src, line, col, err) => {
  console.error('[Nexus9] Uncaught error:', msg, src, line);
  // Ne pas crasher, juste logger
};
window.onunhandledrejection = (e) => {
  console.error('[Nexus9] Unhandled promise:', e.reason);
};

// ── Planet definitions ──────────────────────────────────

const PLANET_DEFS = [
  // ── Inner orbit (200px) : ULTRON, FORGE, VAULT ──────────
  { ...ULTRON_CONFIG,  orbitRadius: 200 },
  { ...FORGE_CONFIG,   orbitRadius: 200 },
  { ...VAULT_CONFIG,   orbitRadius: 200 },

  // ── Middle orbit (310px) : GWEN (ex-QWEN), CORTANA ──────
  {
    id: 'qwen', icon: '◑', name: 'GWEN',
    sub: 'GWEN — Memory Engine · qwen3:14b',
    color: 'var(--qwen)', glow: 'rgba(0,255,136,.4)',
    orbitRadius: 310, speed: 0.07, size: 60,
    renderer: _simpleRenderer('GWEN — qwen3:14b local (ex-QWEN)', 'qwen'),
  },
  { ...CORTANA_CONFIG },   // orbitRadius: 310 défini dans cortana_planet.js

  // ── Outer orbit (420px) : BRUCE, CYBERDECK, MISSIONS ────
  { ...BRUCE_CONFIG },     // orbitRadius: 420 défini dans bruce_planet.js
  { ...CYBERDECK_CONFIG, orbitRadius: 420, speed: 0.09 },
  { ...COMMERCE_CONFIG,  orbitRadius: 420, speed: -0.11 },
];

function _simpleRenderer(info, agent) {
  return {
    startPolling: false,
    async render(body) {
      body.innerHTML = `
        <div class="log-line ok">${info}</div>
        <div class="log-line" style="opacity:.4;margin-top:8px">Connecté au backend existant</div>
        <div style="margin-top:12px">
          <textarea class="panel-input" id="sr-input" rows="2" placeholder="Mission rapide..."></textarea>
          <button class="panel-btn" id="sr-btn" style="margin-top:6px">▶ ENVOYER À ${agent.toUpperCase()}</button>
          <div id="sr-result" class="panel-log" style="margin-top:8px;max-height:120px"></div>
        </div>`;

      const btn = body.querySelector('#sr-btn');
      const inp = body.querySelector('#sr-input');
      const res = body.querySelector('#sr-result');

      btn.addEventListener('click', async () => {
        const txt = inp.value.trim();
        if (!txt) return;
        btn.disabled = true;
        res.innerHTML = '<div class="log-line" style="opacity:.4">En cours...</div>';
        try {
          const r = await fetch(`${BACKEND}/task`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ agent: agent.toUpperCase(), task: txt }),
            signal: AbortSignal.timeout(60000),
          });
          const d = await r.json();
          res.innerHTML = `<div class="log-line ok">${(d.result || d.response || 'Done').slice(0, 300)}</div>`;
          inp.value = '';
        } catch (e) {
          res.innerHTML = `<div class="log-line err">${e.message}</div>`;
        } finally {
          btn.disabled = false;
        }
      });
    },
    async refresh() {},
  };
}

// ── Clock ────────────────────────────────────────────────

function startClock() {
  const el = document.getElementById('hud-clock');
  const update = () => {
    const n = new Date();
    el.textContent = [n.getHours(), n.getMinutes(), n.getSeconds()]
      .map(x => String(x).padStart(2, '0')).join(':');
  };
  update();
  setInterval(update, 1000);
}

// ── Backend status ────────────────────────────────────────

async function pollBackendStatus() {
  const pill = document.getElementById('hud-backend');
  try {
    const r = await fetch(`${BACKEND}/health`, { signal: AbortSignal.timeout(3000) });
    if (r.ok) {
      pill.textContent = '⬡ BACKEND ONLINE';
      pill.className = 'hud-pill online';
    } else throw new Error();
  } catch {
    pill.textContent = '⬡ BACKEND OFFLINE';
    pill.className = 'hud-pill offline';
  }
}

// ── Init ─────────────────────────────────────────────────

async function init() {
  // ── Initialisation avec try/catch indépendants (Task 7.1) ──

  // Galaxy background (canvas)
  let galaxy;
  try {
    const galaxyCanvas = document.getElementById('galaxy-canvas');
    galaxy = new GalaxyBackground(galaxyCanvas);
  } catch (e) { console.error('[Galaxy] init failed:', e); }

  // Orbital stage
  const stage = document.getElementById('orbital-stage');
  let orbitSystem;
  try {
    const orbitCanvas = document.getElementById('orbit-canvas');
    orbitSystem = new OrbitSystem(orbitCanvas, stage);
  } catch (e) { console.error('[Orbit] init failed:', e); }

  // Panel
  let panel;
  try {
    panel = new ModulePanel();
  } catch (e) { console.error('[Panel] init failed:', e); }

  // ── Communication Hub (legacy backend layer) ──────────
  let commHub;
  try {
    commHub = new CommHub({
      onMessage:        () => {},    // overridden by ChatDock
      onThinking:       () => {},
      onForgeAlert:     () => {},
      onPlanetActivity: () => {},
    });
  } catch (e) { console.error('[CommHub] init failed:', e); }

  let voiceManager;
  try {
    voiceManager = new VoiceManager({
      onTranscript: () => {},        // overridden by ChatDock
      onTTSStart:   () => {},
      onTTSEnd:     () => {},
      onStatus:     () => {},
    });
  } catch (e) { console.error('[VoiceManager] init failed:', e); }

  // Forward ref pour éviter la référence avant déclaration
  const overlayRef = {};

  let chatDock;
  try {
    chatDock = new ChatDock({
      commHub,
      voiceManager,
      onAgentChange: (agentId) => {
        // Pulse matching planet when agent switches
        const pid = agentId.toLowerCase();
        planetMap.get(pid)?.setActive(true);
        setTimeout(() => planetMap.get(pid)?.setActive(false), 1500);
      },
      onPlanetPing: (pid, highlight) => {
        const planet = planetMap.get(pid);
        if (planet) {
          planet.setStatus(highlight ? 'busy' : 'online');
          if (!highlight) setTimeout(() => overlayRef._poll?.(), 2000);
        }
        // Quand la Forge démarre depuis le chat → ouvrir le panel Forge automatiquement
        if (pid === 'forge' && highlight) {
          const forgeDef = PLANET_DEFS.find(d => d.id === 'forge');
          if (forgeDef && panel && !panel.isOpen('forge')) {
            for (const p of planetMap.values()) p.setActive(false);
            planetMap.get('forge')?.setActive(true);
            panel.open({ ...forgeDef, renderer: forgeDef.renderer });
            panel.setStatus('busy', 'Mission Forge en cours...');
          }
        }
      },
    });
  } catch (e) { console.error('[ChatDock] init failed:', e); }

  // Pipeline Hub (barre top — juste sous NEXUS9 ORBITAL INTERFACE)
  try {
    new PipelineHub();
  } catch (e) { console.error('[PipelineHub] init failed:', e); }

  // Forge Hub (panneau bas-droit — STL / Forge Room)
  try {
    new ForgeHub();
  } catch (e) { console.error('[ForgeHub] init failed:', e); }


  // JARVIS star → open comm hub
  try {
    new StarCore(stage, () => {
      chatDock?.routeToAgent('JARVIS');
    });
  } catch (e) { console.error('[StarCore] init failed:', e); }

  // Build planets
  const planetMap = new Map();

  for (const def of PLANET_DEFS) {
    try {
      const planet = new PlanetNode({
        id:          def.id,
        icon:        def.icon,
        label:       def.name.split(' ')[0],
        color:       def.color,
        glow:        def.glow,
        orbitRadius: def.orbitRadius,
        speed:       def.speed,
        size:        def.size || 64,
        onActivate: (id) => {
          // Deactivate all planets
          for (const p of planetMap.values()) p.setActive(false);
          planet.setActive(true);

          // Map planet → agent for ChatDock routing
          const planetToAgent = {
            jarvis:    'JARVIS',
            ultron:    'ULTRON',
            qwen:      'QWEN',       // GWEN — garde id 'qwen' pour compatibilité backend
            cortana:   'CORTANA',
            bruce:     'BRUCE',
            cyberdeck: 'CORTANA',
            missions:  'BRUCE',
            forge:     'JARVIS',
            vault:     'JARVIS',
          };
          const agent = planetToAgent[id];
          if (agent) chatDock?.routeToAgent(agent);

          // Also open module panel (secondary)
          if (panel?.isOpen(id)) { panel.close(); return; }
          if (def.renderer) {
            panel?.open({ ...def, renderer: def.renderer });
            panel?.setStatus('online', 'Connexion backend...');
          }
        },
      });

      planet.appendTo(stage);
      orbitSystem?.addPlanet(planet);
      planetMap.set(def.id, planet);
    } catch (e) { console.error(`[Planet:${def.id}] init failed:`, e); }
  }

  try { orbitSystem?.start(); } catch (e) { console.error('[Orbit] start failed:', e); }

  // Agent activity overlay
  let overlay;
  try {
    overlay = new AgentActivityOverlay(BACKEND, planetMap);
    overlayRef._poll = () => overlay._poll();
    overlay.start(6000);
  } catch (e) { console.error('[AgentOverlay] init failed:', e); }

  // HUD
  try { startClock(); } catch (e) { console.error('[Clock] init failed:', e); }

  pollBackendStatus();
  setInterval(pollBackendStatus, 10000);

  // Keyboard: Escape closes panel
  // Dé-registre tout handler précédent pour éviter la duplication si init est rappelée
  if (window._nexusEscHandler) {
    document.removeEventListener('keydown', window._nexusEscHandler);
  }
  window._nexusEscHandler = e => { if (e.key === 'Escape') panel?.close(); };
  document.addEventListener('keydown', window._nexusEscHandler);

  console.log('[OrbitalUI] Initialized — connected to', BACKEND);
}

document.addEventListener('DOMContentLoaded', init);
