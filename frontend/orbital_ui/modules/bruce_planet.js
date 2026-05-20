/**
 * BRUCE Planet — OpenHands autonomous execution agent.
 * Envoie des missions autonomes via POST /task {agent:"BRUCE"}.
 * Vérifie la disponibilité d'OpenHands via GET localhost:3000/api/options/models.
 */
const BACKEND       = 'http://localhost:8000';
const OPENHANDS_URL = 'http://localhost:3000';

export const BRUCE_CONFIG = {
  id: 'bruce', icon: '🤖', name: 'BRUCE',
  sub: 'OPENHANDS EXECUTION AGENT',
  color: '#ff2d55', glow: 'rgba(255,45,85,.5)',
  orbitRadius: 420, speed: 0.06, size: 64,
  pollInterval: 0,
  renderer: {
    startPolling: false,

    async render(body) {
      body.innerHTML = `
        <div class="panel-section-title">OPENHANDS STATUS</div>
        <div id="bruce-status" class="panel-log" style="max-height:48px">Vérification...</div>
        <div style="margin-top:6px">
          <a id="bruce-monitor-link" href="${OPENHANDS_URL}" target="_blank"
             style="display:inline-block;font-size:9px;letter-spacing:1px;color:#ff2d55;
                    border:1px solid rgba(255,45,85,.35);border-radius:4px;padding:4px 10px;
                    text-decoration:none;transition:background .15s"
             onmouseover="this.style.background='rgba(255,45,85,.12)'"
             onmouseout="this.style.background='transparent'">
            → MONITOR BRUCE :3000
          </a>
        </div>

        <div class="panel-section-title" style="margin-top:10px">MISSION AUTONOME</div>
        <textarea class="panel-input" id="bruce-task" rows="3"
          placeholder="Ex: Crée un fichier hello.py, installe flask, lance un serveur..."></textarea>
        <button class="panel-btn" id="bruce-exec" style="margin-top:6px;border-color:rgba(255,45,85,.5);color:#ff2d55">
          ⚙ EXÉCUTER
        </button>
        <div id="bruce-exec-status" style="font-size:9px;color:rgba(255,45,85,.6);min-height:14px;margin-top:4px"></div>

        <div class="panel-section-title" style="margin-top:4px">LOG EXÉCUTION</div>
        <div id="bruce-log" class="panel-log" style="max-height:160px"></div>`;

      await bruce_module._checkStatus(body);
      bruce_module._bindExec(body);
    },

    async refresh(body) {
      await bruce_module._checkStatus(body);
    },
  },
};

const bruce_module = {
  async _checkStatus(body) {
    const el = body.querySelector('#bruce-status');
    if (!el) return;
    try {
      const r = await fetch(`${OPENHANDS_URL}/api/options/models`,
        { signal: AbortSignal.timeout(3000) });
      if (r.ok) {
        el.innerHTML = '<div class="log-line ok">⬡ OPENHANDS ONLINE — Qwen3:14b prêt</div>';
      } else {
        el.innerHTML = `<div class="log-line warn">⚠ OpenHands HTTP ${r.status}</div>`;
      }
    } catch {
      el.innerHTML = `
        <div class="log-line err">⬡ OPENHANDS OFFLINE</div>
        <div class="log-line" style="opacity:.4;font-size:8px">Démarre avec : docker compose --profile bruce up bruce</div>`;
    }

    // Statut backend aussi (fallback /task)
    try {
      const rb = await fetch(`${BACKEND}/health`, { signal: AbortSignal.timeout(3000) });
      if (rb.ok) {
        el.innerHTML += '<div class="log-line ok" style="opacity:.6">⬡ BACKEND ONLINE</div>';
      }
    } catch { /* silencieux */ }
  },

  _bindExec(body) {
    const btn    = body.querySelector('#bruce-exec');
    const inp    = body.querySelector('#bruce-task');
    const status = body.querySelector('#bruce-exec-status');
    const log    = body.querySelector('#bruce-log');

    btn.addEventListener('click', async () => {
      const txt = inp.value.trim();
      if (!txt) return;
      btn.disabled = true;
      status.textContent = 'Envoi à BRUCE...';
      log.innerHTML = '<div class="log-line" style="opacity:.4">Mission en cours — peut prendre plusieurs minutes...</div>';

      const start = Date.now();
      try {
        const r = await fetch(`${BACKEND}/task`, {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          body:    JSON.stringify({ agent: 'BRUCE', task: txt }),
          signal:  AbortSignal.timeout(300000),   // 5 min max
        });
        const d  = await r.json();
        const ms = Date.now() - start;
        const res = d.result || d.response || '⬡ Mission terminée.';
        status.textContent = `Complété en ${(ms / 1000).toFixed(1)}s`;
        log.innerHTML = `<div class="log-line ok">${_escHtml(res.slice(0, 600))}</div>`;
        inp.value = '';
      } catch (e) {
        status.textContent = 'Erreur: ' + e.message;
        log.innerHTML = `<div class="log-line err">${_escHtml(e.message)}</div>`;
      } finally {
        btn.disabled = false;
      }
    });
  },
};

function _escHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}
