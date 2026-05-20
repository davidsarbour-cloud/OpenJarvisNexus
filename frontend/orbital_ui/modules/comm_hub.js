/**
 * CommHub — central communication layer for Orbital UI.
 * Connects to the EXACT same backend as legacy Nexus9:
 *   POST /v1/chat/completions  (JARVIS + ULTRON)
 *   POST /task                 (agent routing)
 *   POST /v1/forge/mission     (Forge Room)
 *   POST /v1/speech/transcribe (Whisper STT)
 *   POST /v1/tts               (edge-tts)
 *
 * Zero backend logic duplicated — only HTTP calls.
 */

const BACKEND = 'http://localhost:8000';

// ── Agent definitions (mirrors legacy AGENTS array) ──────

export const AGENTS = {
  JARVIS:  { color: '#00d4ff', icon: '☀', model: 'claude-haiku-4-5',
             system: 'You are JARVIS, orchestrator of Nexus9. Ultra-concise (max 2 sentences). Route tasks. Never ask clarifying questions. Start with ⬡.' },
  ULTRON:  { color: '#a855f7', icon: '◆', model: 'claude-sonnet-4-6',
             system: 'You are ULTRON, strategic reasoning engine of Nexus9. Analytical, precise. Max 3 sentences.' },
  GWEN:    { color: '#00ff88', icon: '◉', route: 'task', agentName: 'QWEN',
             desc: 'Memory Engine — Qwen3:14b local' },
  CORTANA: { color: '#ff6b35', icon: '⚙', route: 'task',
             desc: 'Code Engine — DeepSeek Coder 6.7b' },
  BRUCE:   { color: '#ff2d55', icon: '🤖', route: 'task',
             desc: 'Execution Agent — OpenHands' },
};

// ── Routing detectors (same patterns as legacy) ───────────

const AGENT_TRIGGERS = {
  BRUCE:   /^!?bruce[,:\s]+/i,
  ULTRON:  /^!?ultron[,:\s]+/i,
  GWEN:    /^!?gwen[,:\s]+|^!?qwen[,:\s]+/i,   // !gwen ou !qwen
  CORTANA: /^!?cortana[,:\s]+/i,
};

const STL_RE = [
  // Mots-clés 3D/impression directs
  /\b(stl|low.?poly|figurine|meshy)\b/i,
  /\bfdm\b/i,
  /\bimprimable\b/i,
  /\bimprimer\b/i,
  /\bà\s+imprimer\b/i,
  /\bimprime.?\s+moi\b/i,
  /\b3d\s+print/i,
  // Taille + contexte impression
  /\b\d+\s*cm\b.{0,40}\b(fdm|stl|imprimer|imprimable|3d|figur|model)\b/i,
  /\b(fdm|stl|imprimer|imprimable|3d|figur|model).{0,40}\b\d+\s*cm\b/i,
  // Verbe créer/faire + objet physique
  /\b(fais?|fait|crée|make|generate|génère|fabrique|imprime)\b.{0,40}\b(stl|3d|model|low.?poly|mesh|fdm|imprimable|figurine|statue)\b/i,
  // Animaux + contexte impression (chien, chat, dragon, etc.)
  /\b(chien|chat|dragon|lion|ours|renard|loup|tigre|figurine|statue|buste|robot)\b.{0,60}\b(\d+\s*cm|fdm|stl|imprimer|imprimable|bambu|3d)\b/i,
  /\b(model|mesh|print)\b.{0,30}\b(stl|cm|mm|poly|file|fichier)\b/i,
];

function detectAgent(txt) {
  for (const [agent, re] of Object.entries(AGENT_TRIGGERS)) {
    if (re.test(txt)) return { agent, task: txt.replace(re, '').trim() || txt };
  }
  return null;
}

function detectSTL(txt) { return STL_RE.some(re => re.test(txt)); }

function sanitize(t) {
  if (!t) return '⬡ OK.';
  t = String(t)
    .replace(/<think>[\s\S]*?<\/think>/gi, '')
    .replace(/```[\s\S]*?```/g, '')
    .replace(/`[^`\n]+`/g, '')
    .replace(/^\s*[-*•]\s+/gm, '')
    .replace(/[*_]{1,3}([^*_]+)[*_]{1,3}/g, '$1')
    .replace(/\n{2,}/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  if (!t) return '⬡ OK.';
  const parts = t.split(/(?<=[.!?])\s+/).filter(Boolean);
  if (parts.length > 2) t = parts.slice(0, 2).join(' ');
  return t;
}

// ── CommHub class ─────────────────────────────────────────

export class CommHub {
  constructor({ onMessage, onThinking, onForgeAlert, onPlanetActivity }) {
    this.onMessage          = onMessage;        // fn(msg) → { role, agent, text, ts }
    this.onThinking         = onThinking;       // fn(agent, bool)
    this.onForgeAlert       = onForgeAlert;     // fn(missionId, status)
    this.onPlanetActivity   = onPlanetActivity; // fn(planetId, active)
    this.onConnectionChange = null;             // fn(state) — 'online' | 'offline' | 'reconnecting'
    this.busy               = false;
    this.currentModel       = 'claude-haiku-4-5';

    // ── State machine connexion ───────────────────────────
    this.connectionState    = 'online'; // 'online' | 'offline' | 'reconnecting'

    // ── Poll abort flag ───────────────────────────────────
    this._pollAbort         = false;

    // ── Backoff state — délais successifs: 2s, 5s, 15s (max) ──
    this._backoffDelays     = [2000, 5000, 15000];
    this._backoffIdx        = 0;
    this._reconnectTimer    = null;
  }

  setModel(model) { this.currentModel = model; }

  // ── Connection state machine ──────────────────────────

  _setConnectionState(state) {
    if (this.connectionState === state) return;
    this.connectionState = state;
    this.onConnectionChange?.(state);
  }

  _onFetchSuccess() {
    this._backoffIdx = 0;
    if (this._reconnectTimer !== null) {
      clearTimeout(this._reconnectTimer);
      this._reconnectTimer = null;
    }
    this._setConnectionState('online');
  }

  _onFetchFailure() {
    // Ne déclenche le backoff que si on était online (évite les doubles schedules)
    if (this.connectionState === 'online') {
      this._setConnectionState('offline');
      this._scheduleReconnect();
    }
  }

  _scheduleReconnect() {
    if (this._reconnectTimer !== null) return; // déjà planifié
    const delay = this._backoffDelays[Math.min(this._backoffIdx, this._backoffDelays.length - 1)];
    this._backoffIdx++;
    this._reconnectTimer = setTimeout(async () => {
      this._reconnectTimer = null;
      if (this._pollAbort) return;
      this._setConnectionState('reconnecting');
      try {
        const r = await fetch(`${BACKEND}/health`, { signal: AbortSignal.timeout(3000) });
        if (r.ok) {
          this._onFetchSuccess();
        } else {
          this._setConnectionState('offline');
          this._scheduleReconnect();
        }
      } catch {
        this._setConnectionState('offline');
        this._scheduleReconnect();
      }
    }, delay);
  }

  // ── Poll abort / cleanup ──────────────────────────────

  stopAllPolls() {
    this._pollAbort = true;
    if (this._reconnectTimer !== null) {
      clearTimeout(this._reconnectTimer);
      this._reconnectTimer = null;
    }
  }

  // ── Main send entry point ─────────────────────────────

  async send(text) {
    if (this.busy || !text.trim()) return;

    const agentRoute = detectAgent(text);
    if (agentRoute) return this._sendToAgent(agentRoute.agent, agentRoute.task || text, text);

    if (detectSTL(text)) return this._sendForge(text);

    return this._sendJarvis(text);
  }

  // ── JARVIS via /v1/chat/completions ─────────────────

  async _sendJarvis(text) {
    // Guard offline — évite un fetch inutile et retourne immédiatement
    if (this.connectionState === 'offline') {
      const err = '⬡ Backend hors ligne — en attente de reconnexion';
      this.onMessage?.({ role: 'agent', agent: 'JARVIS', text: err, ts: _ts(), error: true });
      return err;
    }

    this.busy = true;
    this.onMessage?.({ role: 'user', agent: 'YOU', text, ts: _ts() });
    this.onThinking?.('JARVIS', true);
    this.onPlanetActivity?.('jarvis', true);

    try {
      const r = await fetch(`${BACKEND}/v1/chat/completions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          stream: false,
          system: AGENTS.JARVIS.system,
          model: this.currentModel,
        }),
        signal: AbortSignal.timeout(60000),
      });

      let response = '';
      if (r.ok) {
        this._onFetchSuccess();
        const d = await r.json();
        const msg = d.choices?.[0]?.message;
        response = typeof msg === 'string' ? msg : (msg?.content || d.response || d.content || '');
      } else {
        this._onFetchFailure();
        const e = await r.json().catch(() => ({}));
        response = '⬡ Error: ' + (e.detail || 'HTTP ' + r.status);
      }

      response = sanitize(response);
      if (!response.startsWith('⬡')) response = '⬡ ' + response;
      this.onMessage?.({ role: 'agent', agent: 'JARVIS', text: response, ts: _ts() });
      return response;

    } catch (e) {
      this._onFetchFailure();
      const err = '⬡ Error: ' + e.message;
      this.onMessage?.({ role: 'agent', agent: 'JARVIS', text: err, ts: _ts() });
      return err;
    } finally {
      this.busy = false;
      this.onThinking?.('JARVIS', false);
      this.onPlanetActivity?.('jarvis', false);
    }
  }

  // ── ULTRON via /v1/chat/completions (Sonnet) ─────────

  async sendUltron(text) {
    this.busy = true;
    this.onMessage?.({ role: 'user', agent: 'YOU', text, ts: _ts() });
    this.onThinking?.('ULTRON', true);
    this.onPlanetActivity?.('ultron', true);

    try {
      const r = await fetch(`${BACKEND}/v1/chat/completions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          stream: false,
          system: AGENTS.ULTRON.system,
          model: 'claude-sonnet-4-6',
        }),
        signal: AbortSignal.timeout(60000),
      });

      let response = '';
      if (r.ok) {
        this._onFetchSuccess();
        const d = await r.json();
        const msg = d.choices?.[0]?.message;
        response = typeof msg === 'string' ? msg : (msg?.content || d.response || '');
      } else {
        this._onFetchFailure();
        response = '◆ Error: HTTP ' + r.status;
      }

      this.onMessage?.({ role: 'agent', agent: 'ULTRON', text: response, ts: _ts() });
      return response;

    } catch (e) {
      this._onFetchFailure();
      const err = '◆ Error: ' + e.message;
      this.onMessage?.({ role: 'agent', agent: 'ULTRON', text: err, ts: _ts() });
      return err;
    } finally {
      this.busy = false;
      this.onThinking?.('ULTRON', false);
      this.onPlanetActivity?.('ultron', false);
    }
  }

  // ── Agent routing via /task ───────────────────────────
  // Public alias for ChatDock
  async sendToAgent(agent, task, originalText) {
    return this._sendToAgent(agent, task, originalText);
  }

  async _sendToAgent(agent, task, originalText) {
    this.busy = true;
    // GWEN est l'alias frontend de QWEN — le backend ne connaît que QWEN
    const backendAgent = agent === 'GWEN' ? 'QWEN' : agent;
    const pid = _agentToPlanet(agent);
    this.onMessage?.({ role: 'user', agent: 'YOU', text: originalText, ts: _ts() });
    this.onThinking?.(agent, true);
    if (pid) this.onPlanetActivity?.(pid, true);

    try {
      const r = await fetch(`${BACKEND}/task`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent: backendAgent, task }),
        signal: AbortSignal.timeout(180000),
      });

      let result = '';
      if (r.ok) {
        this._onFetchSuccess();
        const d = await r.json();
        result = d.result || d.response || '⬡ Done.';
      } else {
        this._onFetchFailure();
        const e = await r.json().catch(() => ({}));
        result = (e.detail || 'HTTP ' + r.status);
      }

      this.onMessage?.({ role: 'agent', agent, text: result, ts: _ts() });
      return result;

    } catch (e) {
      this._onFetchFailure();
      const msg = e.message.includes('timeout')
        ? `Timeout — ${agent} a mis trop de temps (>3min)` : e.message;
      this.onMessage?.({ role: 'agent', agent, text: msg, ts: _ts(), error: true });
    } finally {
      this.busy = false;
      this.onThinking?.(agent, false);
      if (pid) this.onPlanetActivity?.(pid, false);
    }
  }

  // ── CORTANA via /task (DeepSeek Coder) ───────────────

  async sendCortana(text) {
    this.busy = true;
    this.onMessage?.({ role: 'user', agent: 'YOU', text, ts: _ts() });
    this.onThinking?.('CORTANA', true);
    this.onPlanetActivity?.('cortana', true);
    try {
      const r = await fetch(`${BACKEND}/task`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent: 'CORTANA', task: text }),
        signal: AbortSignal.timeout(180000),
      });
      let result = r.ok ? (await r.json()).result || '⚙ Done.' : 'Error HTTP ' + r.status;
      this.onMessage?.({ role: 'agent', agent: 'CORTANA', text: result, ts: _ts() });
      return result;
    } finally {
      this.busy = false;
      this.onThinking?.('CORTANA', false);
      this.onPlanetActivity?.('cortana', false);
    }
  }

  // ── BRUCE via /task (OpenHands) ───────────────────────

  async sendBruce(text) {
    return this._sendToAgent('BRUCE', text, text);
  }

  // ── Forge Room via /v1/forge/mission ─────────────────

  async _sendForge(text) {
    // Guard offline — évite un fetch inutile
    if (this.connectionState === 'offline') {
      const err = '⬡ Backend hors ligne — impossible de lancer une mission Forge';
      this.onMessage?.({ role: 'agent', agent: 'FORGE', text: err, ts: _ts(), error: true });
      return err;
    }

    this.busy = true;
    this.onMessage?.({ role: 'user', agent: 'YOU', text, ts: _ts() });
    this.onMessage?.({ role: 'sys', text: '⬡ THE FORGE ROOM — pipeline démarré', ts: _ts() });
    this.onPlanetActivity?.('forge', true);

    try {
      const r = await fetch(`${BACKEND}/v1/forge/mission`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: text }),
        signal: AbortSignal.timeout(30000),
      });

      if (r.ok) {
        this._onFetchSuccess();
      } else {
        this._onFetchFailure();
      }

      const d = await r.json();
      const mid = d.mission_id || '?';
      this.onMessage?.({
        role: 'forge', agent: 'FORGE', ts: _ts(),
        text: `⬡ Mission ${mid} — pipeline en cours\nSuivi: /v1/forge/mission/${mid}`,
        missionId: mid,
      });
      this.onForgeAlert?.(mid, 'running');
      this._pollForge(mid);

    } catch (e) {
      this._onFetchFailure();
      this.onMessage?.({ role: 'agent', agent: 'FORGE', text: '⬡ Forge error: ' + e.message, ts: _ts(), error: true });
      this.onPlanetActivity?.('forge', false);
    } finally {
      this.busy = false;
    }
  }

  async _pollForge(mid) {
    let errors = 0;
    for (let i = 0; i < 180; i++) {
      await new Promise(r => setTimeout(r, 3000));
      // Stop demandé via stopAllPolls()
      if (this._pollAbort) break;
      try {
        const r = await fetch(`${BACKEND}/v1/forge/mission/${mid}`, { signal: AbortSignal.timeout(8000) });
        // Vérif stop après le await réseau
        if (this._pollAbort) break;
        if (!r.ok) { errors++; if (errors > 5) break; continue; }
        errors = 0;
        const d = await r.json();
        const status = d.status || 'running';
        this.onForgeAlert?.(mid, status, d.report?.printability_score);

        if (status === 'completed') {
          const report = d.report || {};
          const score  = report.printability_score ?? '?';
          const grade  = report.printability_grade ?? '?';
          const ready  = report.bambu_ready;

          // Message de complétion dans le chat
          this.onMessage?.({
            role: 'forge', agent: 'FORGE', ts: _ts(),
            text: `✓ Mission ${mid} COMPLÈTE\nScore: ${score}/100  Grade: ${grade}  ${ready ? '✓ BAMBU READY' : '⚠ Non prêt'}\nParois: ${report.wall_thickness_min_mm ?? '?'}mm | Matière: ${report.estimated_material_g ?? '?'}g | Temps: ${report.estimated_print_time_str ?? '?'}`,
          });

          this.onPlanetActivity?.('forge', false);

          // ── Ouverture automatique Bambu Studio ──────────
          // Ouvre toujours Bambu — même si score < 75, l'utilisateur slice manuellement
          if (!this._pollAbort) {
            try {
              const br = await fetch(`${BACKEND}/v1/forge/bambu/${mid}`, {
                method: 'POST',
                signal: AbortSignal.timeout(8000),
              });
              if (br.ok) {
                const bd = await br.json();
                this.onMessage?.({
                  role: 'sys', ts: _ts(),
                  text: `▶ Bambu Studio ouvert — ${bd.file}`,
                });
              } else {
                const be = await br.json().catch(() => ({}));
                this.onMessage?.({
                  role: 'sys', ts: _ts(),
                  text: `⚠ Bambu Studio: ${be.detail || 'HTTP ' + br.status} — STL dispo via /v1/forge/download/${mid}`,
                });
              }
            } catch (be) {
              this.onMessage?.({
                role: 'sys', ts: _ts(),
                text: `⚠ Bambu Studio non accessible: ${be.message}`,
              });
            }
          }
          return;
        }

        if (status === 'failed') {
          this.onMessage?.({
            role: 'agent', agent: 'FORGE', ts: _ts(),
            text: `✗ Mission ${mid} échouée: ${d.error || 'erreur pipeline'}`,
            error: true,
          });
          this.onPlanetActivity?.('forge', false);
          return;
        }
      } catch (e) { errors++; if (errors > 5) break; }
    }
    this.onPlanetActivity?.('forge', false);
  }
}

// ── Helpers ───────────────────────────────────────────────

function _ts() {
  const n = new Date();
  return [n.getHours(), n.getMinutes()].map(x => String(x).padStart(2, '0')).join(':');
}

function _agentToPlanet(agent) {
  const m = { ULTRON: 'ultron', QWEN: 'qwen', GWEN: 'qwen', CORTANA: 'cyberdeck', BRUCE: 'missions' };
  return m[agent?.toUpperCase()] ?? null;
}
