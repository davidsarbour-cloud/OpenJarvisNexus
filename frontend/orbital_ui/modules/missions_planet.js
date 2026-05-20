/**
 * Missions Planet — task routing + agent orchestration interface.
 * Connects to existing /task and /v1/agents endpoints.
 */
const BACKEND = 'http://localhost:8000';

export const MISSIONS_CONFIG = {
  id: 'missions', icon: '🛰️', name: 'MISSIONS',
  sub: 'ORCHESTRATION & ROUTING',
  color: 'var(--missions)', glow: 'rgba(255,210,0,.4)',
  orbitRadius: 380, speed: -0.11, size: 60,
  pollInterval: 5000,
  renderer: {
    startPolling: true,

    async render(body) {
      body.innerHTML = `
        <div class="panel-section-title">ENVOYER UNE MISSION</div>
        <select class="panel-input" id="mission-agent" style="margin-bottom:6px">
          <option value="JARVIS">JARVIS — Orchestrateur</option>
          <option value="ULTRON">ULTRON — Stratégie</option>
          <option value="QWEN">QWEN — Masse locale</option>
          <option value="CORTANA">CORTANA — Code</option>
          <option value="BRUCE">BRUCE — Autonome</option>
        </select>
        <textarea class="panel-input" id="mission-task" rows="2"
          placeholder="Décris la mission..."></textarea>
        <button class="panel-btn" id="mission-send" style="margin-top:6px">🛰️ DÉPLOYER</button>
        <div id="mission-status" style="font-size:9px;color:rgba(255,210,0,.6);min-height:14px;margin-top:4px"></div>

        <div class="panel-section-title" style="margin-top:4px">RÉSULTAT</div>
        <div id="mission-result" class="panel-log" style="max-height:140px"></div>`;

      missions_module._bind(body);
    },

    async refresh(body) {},
  },
};

const missions_module = {
  _bind(body) {
    const btn    = body.querySelector('#mission-send');
    const agent  = body.querySelector('#mission-agent');
    const task   = body.querySelector('#mission-task');
    const status = body.querySelector('#mission-status');
    const result = body.querySelector('#mission-result');

    btn.addEventListener('click', async () => {
      const txt = task.value.trim();
      if (!txt) return;
      btn.disabled = true;
      status.textContent = `Routing vers ${agent.value}...`;
      result.innerHTML   = '<div class="log-line" style="opacity:.4">Attente réponse...</div>';

      const start = Date.now();
      try {
        const r = await fetch(`${BACKEND}/task`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ agent: agent.value, task: txt }),
          signal: AbortSignal.timeout(180000),
        });
        const d  = await r.json();
        const ms = Date.now() - start;
        const res = d.result || d.response || '⬡ Done.';
        status.textContent = `Complété en ${(ms/1000).toFixed(1)}s`;
        result.innerHTML   = `<div class="log-line ok">${res.slice(0, 400)}</div>`;
        task.value = '';
      } catch (e) {
        status.textContent = 'Erreur: ' + e.message;
        result.innerHTML   = `<div class="log-line err">${e.message}</div>`;
      } finally {
        btn.disabled = false;
      }
    });
  },
};
