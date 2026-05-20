/**
 * ChatDock — floating orbital communication panel.
 * Connects to CommHub for all backend calls.
 * Supports: multi-agent, voice, TTS, streaming indicators, forge alerts.
 */

import { AGENTS } from '../modules/comm_hub.js';
import { OrchestrationPanel } from './OrchestrationPanel.js';

const _BACKEND = 'http://localhost:8000';

const AGENT_LIST = [
  { id: 'JARVIS', label: '☀ JARVIS' },
];

export class ChatDock {
  constructor({ commHub, voiceManager, onAgentChange, onPlanetPing }) {
    this.commHub      = commHub;
    this.voice        = voiceManager;
    this.onAgentChange = onAgentChange;
    this.onPlanetPing  = onPlanetPing;

    this.currentAgent = 'JARVIS';
    this.expanded     = false;
    this.ttsOn        = localStorage.getItem('nexus9_tts') !== 'off';
    this._thinkingEl  = null;
    this._destroyed   = false;
    // Référence vers l'interval notifyPlanetActive pour cleanup
    this._activityTimeout = null;
    this._orchPanel   = null;

    this._build();
    this._bindEvents();
    this._initVoice();
    this._addSys('⬡ NEXUS9 ORBITAL — Communication Hub en ligne');
  }

  // ── Build DOM ─────────────────────────────────────────

  _build() {
    // Dock container — commence ouvert
    this.el = document.createElement('div');
    this.el.id = 'comm-dock';
    this.el.className = 'expanded';
    this.expanded = true;

    this.el.innerHTML = `
      <!-- Toolbar (always visible) -->
      <div class="dock-bar" id="dock-bar">
        <div class="dock-icon">🛰</div>
        <div class="dock-label">COMM HUB</div>
        <div class="dock-activity" id="dock-activity">
          <div class="dock-activity-dot"></div>
          <div class="dock-activity-dot"></div>
          <div class="dock-activity-dot"></div>
        </div>
        <div class="dock-agent-badge" id="dock-agent-badge">JARVIS</div>
        <div class="dock-voice-ind" id="dock-voice-ind">
          <div class="dock-vbar"></div><div class="dock-vbar"></div>
          <div class="dock-vbar"></div><div class="dock-vbar"></div>
          <div class="dock-vbar"></div>
        </div>
        <div class="dock-controls">
          <button class="dock-ctrl" id="dock-mic"   title="Microphone">🎤</button>
          <button class="dock-ctrl active tts-on" id="dock-tts" title="TTS ON/OFF">🔊</button>
          <button class="dock-ctrl" id="dock-expand" title="Expand/Collapse">▲</button>
        </div>
      </div>

      <!-- Chat body (visible when expanded) -->
      <div class="dock-body">
        <!-- Agent switcher -->
        <div class="dock-agents" id="dock-agents"></div>

        <!-- Messages -->
        <div id="dock-msgs"></div>

        <!-- Input -->
        <div class="dock-input-row">
          <textarea id="dock-input" rows="1" placeholder="Commande JARVIS..."></textarea>
          <button class="dock-send" id="dock-send">▶</button>
        </div>
      </div>`;

    document.body.appendChild(this.el);
    this._buildAgentTabs();
    this._syncTTSBtn();
    // Bouton expand sync avec état initial
    const expBtn = this.el.querySelector('#dock-expand');
    if (expBtn) expBtn.textContent = '▼';
    // Test backend au démarrage
    this._testBackend();
  }

  _buildAgentTabs() {
    const container = this.el.querySelector('#dock-agents');
    container.innerHTML = AGENT_LIST.map(a => `
      <button class="dock-agent-btn ${a.id === this.currentAgent ? 'active' : ''}"
              id="dag-${a.id}"
              style="--ac:${AGENTS[a.id]?.color || '#00d4ff'}"
              data-agent="${a.id}">${a.label}</button>
    `).join('');
  }

  // ── Events ────────────────────────────────────────────

  _bindEvents() {
    // Agent tabs
    this.el.querySelector('#dock-agents').addEventListener('click', e => {
      const btn = e.target.closest('.dock-agent-btn');
      if (!btn) return;
      this._selectAgent(btn.dataset.agent);
    });

    // Send button
    this.el.querySelector('#dock-send').addEventListener('click', () => this._send());

    // Input — Enter to send, Shift+Enter for newline
    const input = this.el.querySelector('#dock-input');
    input.addEventListener('keydown', e => {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); this._send(); }
      // Auto-resize
      setTimeout(() => {
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 80) + 'px';
      }, 0);
    });

    // Controls
    this.el.querySelector('#dock-mic').addEventListener('click', e => {
      e.stopPropagation();
      this._toggleMic();
    });
    this.el.querySelector('#dock-tts').addEventListener('click', e => {
      e.stopPropagation();
      this._toggleTTS();
    });
    this.el.querySelector('#dock-expand').addEventListener('click', e => {
      e.stopPropagation();
      this._toggle();
    });

    // CommHub events
    this.commHub.onMessage = msg => this._appendMessage(msg);
    this.commHub.onThinking = (agent, active) => {
      if (active) {
        this._showThinking(agent);
      } else {
        this._hideThinking();
        // Collapse le panneau d'orchestration quand la réponse arrive
        if (this._orchPanel?._el) this._orchPanel.collapse();
      }
    };
    this.commHub.onForgeAlert = (mid, status, score) => {
      this._appendMessage({
        role: 'forge', agent: 'FORGE', ts: _ts(),
        text: `⬡ Mission ${mid} — ${status.toUpperCase()}${score ? ' · ' + score + '/100' : ''}`,
      });
      this.onPlanetPing?.('forge', status !== 'running');
    };
    this.commHub.onPlanetActivity = (pid, active) => {
      this.onPlanetPing?.(pid, active);
    };

    // Indicateur de connexion sur le badge agent
    this.commHub.onConnectionChange = (state) => {
      if (this._destroyed) return;
      const badge = this.el?.querySelector('#dock-agent-badge');
      if (!badge) return;
      if (state === 'offline') {
        badge.style.setProperty('--ab-c', '#ff4444');
        badge.title = 'Backend hors ligne';
      } else if (state === 'reconnecting') {
        badge.style.setProperty('--ab-c', '#ffd700');
        badge.title = 'Reconnexion en cours...';
      } else {
        // online — restaure la couleur de l'agent courant
        const color = AGENTS[this.currentAgent]?.color || '#00d4ff';
        badge.style.setProperty('--ab-c', color);
        badge.title = '';
        this._addSys('⬡ Backend reconnecté');
      }
    };
  }

  _initVoice() {
    if (!this.voice) return;
    const micBtn = this.el.querySelector('#dock-mic');
    this.voice.onTranscript = text => {
      const input = this.el.querySelector('#dock-input');
      input.value = text;
      this._send();
    };
    this.voice.onTTSStart = () => {
      this.el.querySelector('#dock-voice-ind')?.classList.add('active');
    };
    this.voice.onTTSEnd = () => {
      this.el.querySelector('#dock-voice-ind')?.classList.remove('active');
    };
    this.voice.onStatus = (status, detail) => {
      switch (status) {
        case 'recording':
          micBtn.className = 'dock-ctrl rec';
          micBtn.textContent = '⏺';
          this.el.querySelector('#dock-activity').classList.add('live');
          break;
        case 'transcribing':
          micBtn.className = 'dock-ctrl active';
          micBtn.textContent = '⏳';
          break;
        case 'idle': case 'nothing_heard': case 'cancelled':
          micBtn.className = 'dock-ctrl';
          micBtn.textContent = '🎤';
          this.el.querySelector('#dock-activity').classList.remove('live');
          break;
        case 'mic_blocked': case 'mic_unavailable':
          micBtn.className = 'dock-ctrl';
          micBtn.textContent = '🚫';
          micBtn.title = 'Microphone non disponible';
          break;
      }
    };
  }

  // ── Actions ───────────────────────────────────────────

  _toggle() {
    this.expanded = !this.expanded;
    this.el.className = this.expanded ? 'expanded' : 'collapsed';
    const btn = this.el.querySelector('#dock-expand');
    btn.textContent = this.expanded ? '▼' : '▲';
    if (this.expanded) {
      const msgs = this.el.querySelector('#dock-msgs');
      msgs.scrollTop = msgs.scrollHeight;
      this.el.querySelector('#dock-input').focus();
    }
  }

  _selectAgent(agentId) {
    this.currentAgent = agentId;
    const color = AGENTS[agentId]?.color || '#00d4ff';

    // Update tabs
    this.el.querySelectorAll('.dock-agent-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.agent === agentId);
    });

    // Update badge
    const badge = this.el.querySelector('#dock-agent-badge');
    badge.textContent = agentId;
    badge.style.setProperty('--ab-c', color);

    this._addSys(`⬡ Agent actif : ${agentId}`);
    this.onAgentChange?.(agentId);
  }

  async _testBackend() {
    const badge = this.el.querySelector('#dock-agent-badge');

    const _setOffline = (reason) => {
      // Message dans le dock
      this._addSys(`⚠ Backend hors ligne — lance 2_BACKEND.bat (${reason})`);
      // Badge rouge OFFLINE dans la toolbar (une seule fois)
      if (!this.el.querySelector('#dock-offline-badge')) {
        const offBadge = document.createElement('span');
        offBadge.id        = 'dock-offline-badge';
        offBadge.textContent = 'OFFLINE';
        offBadge.style.cssText = [
          'padding:2px 7px',
          'border-radius:8px',
          'border:1px solid rgba(255,45,85,.5)',
          'background:rgba(255,45,85,.12)',
          'color:#ff2d55',
          'font-size:7px',
          'font-weight:700',
          'letter-spacing:1.5px',
          'margin-left:4px',
        ].join(';');
        const bar      = this.el.querySelector('#dock-bar');
        const controls = bar?.querySelector('.dock-controls');
        if (controls) bar.insertBefore(offBadge, controls);
      }
      // Retry automatique toutes les 10s (évite les doublons)
      if (!this._backendRetryTimer) {
        this._backendRetryTimer = setInterval(() => this._testBackend(), 10000);
      }
    };

    try {
      const r = await fetch(`${_BACKEND}/health`, { signal: AbortSignal.timeout(3000) });
      if (r.ok) {
        const d = await r.json();
        this._addSys(`⬡ JARVIS CONNECTÉ · ${d.claude_model || 'claude-haiku-4-5'} · Ollama ${d.ollama_online ? 'EN LIGNE' : 'HORS LIGNE'}`);
        if (badge) badge.style.setProperty('--ab-c', 'var(--jarvis, #00d4ff)');
        // Nettoyage badge OFFLINE et timer si reconnexion réussie
        this.el.querySelector('#dock-offline-badge')?.remove();
        if (this._backendRetryTimer) {
          clearInterval(this._backendRetryTimer);
          this._backendRetryTimer = null;
        }
      } else throw new Error('HTTP ' + r.status);
    } catch (e) {
      _setOffline(e.message);
    }
  }

  async _send() {
    const input  = this.el.querySelector('#dock-input');
    const sendBtn = this.el.querySelector('#dock-send');
    const txt    = input.value.trim();
    if (!txt) return;
    if (this.commHub.busy) {
      this._addSys('⬡ Agent occupé — attends la réponse précédente');
      return;
    }

    input.value = '';
    input.style.height = 'auto';
    if (sendBtn) sendBtn.disabled = true;

    let response = '';
    try {
      // Affiche le panneau d'orchestration (pour JARVIS uniquement)
      if (this.currentAgent === 'JARVIS') {
        const feed = this.el.querySelector('#dock-msgs');
        this._orchPanel = new OrchestrationPanel(feed);
        this._orchPanel.show(txt); // non-bloquant
      }

      if (this.currentAgent === 'JARVIS') {
        response = await this.commHub.send(txt);
      } else if (this.currentAgent === 'ULTRON') {
        response = await this.commHub.sendUltron(txt);
      } else if (this.currentAgent === 'CORTANA') {
        response = await this.commHub.sendCortana(txt);
      } else if (this.currentAgent === 'BRUCE') {
        await this.commHub.sendBruce(txt);
        return;
      } else {
        // GWEN et autres
        await this.commHub.sendToAgent(this.currentAgent, txt, txt);
        return;
      }
    } finally {
      if (sendBtn) sendBtn.disabled = false;
    }

    if (response && this.ttsOn) {
      this.voice?.speak(response, this.currentAgent);
    }
  }

  _toggleMic() {
    if (this._destroyed) return;
    if (!this.voice?.available) {
      this._addSys('⬡ Microphone non disponible — accès via http://');
      return;
    }
    if (this.voice.recording) this.voice.stopRecording();
    else this.voice.startRecording();
  }

  _toggleTTS() {
    this.ttsOn = !this.ttsOn;
    this.voice?.setTTS(this.ttsOn);
    this._syncTTSBtn();
    this._addSys(`Voice ${this.ttsOn ? 'ON' : 'OFF'}`);
  }

  _syncTTSBtn() {
    const btn = this.el.querySelector('#dock-tts');
    if (!btn) return;
    btn.className = `dock-ctrl ${this.ttsOn ? 'active tts-on' : ''}`;
    btn.textContent = this.ttsOn ? '🔊' : '🔇';
    btn.title = `Voice ${this.ttsOn ? 'ON — click to mute' : 'OFF — click to unmute'}`;
  }

  // ── Message rendering ─────────────────────────────────

  _appendMessage(msg) {
    if (!this.expanded) this._toggle(); // auto-open on new message

    const feed = this.el.querySelector('#dock-msgs');
    this._hideThinking();

    if (msg.role === 'sys') { this._addSys(msg.text); return; }

    const el  = document.createElement('div');
    const cfg = AGENTS[msg.agent] || { color: '#00d4ff', icon: '⬡' };

    if (msg.role === 'user') {
      el.className = 'dmsg user';
      el.textContent = msg.text;
    } else {
      el.className = `dmsg agent${msg.error ? ' error' : ''}`;
      el.innerHTML = `
        <div class="dmsg-avatar" style="--mc:${cfg.color}">${cfg.icon}</div>
        <div class="dmsg-content">
          <div class="dmsg-header" style="--mc:${cfg.color}">
            ${msg.agent}
            <span class="dmsg-time">${msg.ts || _ts()}</span>
          </div>
          <div class="dmsg-body" style="border-color:${cfg.color}18">
            ${_escapeHtml(msg.text)}
          </div>
        </div>`;
    }

    feed.appendChild(el);

    // Limite le DOM à 100 messages — supprime les 20 premiers si dépassé
    const allMsgs = feed.querySelectorAll('.dmsg:not(.thinking)');
    if (allMsgs.length > 100) {
      for (let i = 0; i < 20; i++) allMsgs[i]?.remove();
    }

    feed.scrollTop = feed.scrollHeight;
  }

  _showThinking(agent) {
    this._hideThinking();
    const feed = this.el.querySelector('#dock-msgs');
    const cfg  = AGENTS[agent] || { color: '#00d4ff', icon: '⬡' };
    const el   = document.createElement('div');
    el.className = 'dmsg agent thinking';
    el.innerHTML = `
      <div class="dmsg-avatar" style="--mc:${cfg.color}">${cfg.icon}</div>
      <div class="dmsg-content">
        <div class="dmsg-header" style="--mc:${cfg.color}">${agent}</div>
        <div class="dmsg-body" style="border-color:${cfg.color}18">
          <div class="think-dots">
            <div class="think-dot" style="background:${cfg.color}"></div>
            <div class="think-dot" style="background:${cfg.color}"></div>
            <div class="think-dot" style="background:${cfg.color}"></div>
          </div>
          <span class="think-status">Processing...</span>
        </div>
      </div>`;
    feed.appendChild(el);
    feed.scrollTop = feed.scrollHeight;
    this._thinkingEl = el;

    // Update activity indicator
    this.el.querySelector('#dock-activity')?.classList.add('live');
  }

  _hideThinking() {
    this._thinkingEl?.remove();
    this._thinkingEl = null;
    this.el.querySelector('#dock-activity')?.classList.remove('live');
  }

  _addSys(text) {
    const feed = this.el.querySelector('#dock-msgs');
    if (!feed) return;
    const el = document.createElement('div');
    el.className = 'dmsg sys';
    el.textContent = text;
    feed.appendChild(el);
    feed.scrollTop = feed.scrollHeight;
  }

  // ── Public API ─────────────────────────────────────────

  // Called by planet clicks to route to specific agent
  routeToAgent(agentId) {
    this._selectAgent(agentId);
    if (!this.expanded) this._toggle();
    this.el.querySelector('#dock-input').focus();
  }

  // Called by planet activity overlay
  notifyPlanetActive(planetId) {
    if (this._destroyed) return;
    clearTimeout(this._activityTimeout);
    this.el.querySelector('#dock-activity')?.classList.add('live');
    this._activityTimeout = setTimeout(() => {
      if (!this._destroyed) this.el.querySelector('#dock-activity')?.classList.remove('live');
    }, 3000);
  }

  destroy() {
    if (this._destroyed) return;
    this._destroyed = true;

    // Arrête l'enregistrement micro si actif — libère le stream
    if (this.voice?.recording) {
      try { this.voice.stopRecording(); } catch {}
    }

    // Annule tout timeout d'activité en attente
    if (this._activityTimeout !== null) {
      clearTimeout(this._activityTimeout);
      this._activityTimeout = null;
    }

    // Déconnecte les callbacks CommHub pour éviter les appels orphelins
    if (this.commHub) {
      this.commHub.onMessage        = null;
      this.commHub.onThinking       = null;
      this.commHub.onForgeAlert     = null;
      this.commHub.onPlanetActivity = null;
    }

    // Retire le DOM
    this.el?.remove();
    this.el = null;
  }
}

function _ts() {
  const n = new Date();
  return [n.getHours(), n.getMinutes()].map(x => String(x).padStart(2, '0')).join(':');
}

function _escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br>');
}
