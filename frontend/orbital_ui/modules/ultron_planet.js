/**
 * ULTRON Planet — connects to existing claude-sonnet-4-6 via /v1/chat/completions.
 * Strategic intelligence interface.
 */
const BACKEND = 'http://localhost:8000';

export const ULTRON_CONFIG = {
  id: 'ultron', icon: '◆', name: 'ULTRON',
  sub: 'INTELLIGENCE STRATÉGIQUE',
  color: 'var(--ultron)', glow: 'rgba(168,85,247,.5)',
  orbitRadius: 220, speed: -0.14, size: 64,
  pollInterval: 0,
  renderer: {
    startPolling: false,

    async render(body) {
      body.innerHTML = `
        <div class="panel-section-title">ANALYSE STRATÉGIQUE</div>
        <div id="ultron-msgs" class="panel-log" style="max-height:200px">
          <div class="log-line" style="opacity:.4">ULTRON en ligne — Sonnet 4-6</div>
        </div>
        <textarea class="panel-input" id="ultron-input" rows="2"
          placeholder="Analyse / planification / décision..."></textarea>
        <button class="panel-btn" id="ultron-send">◆ ANALYSER</button>`;

      const btn   = body.querySelector('#ultron-send');
      const input = body.querySelector('#ultron-input');
      const msgs  = body.querySelector('#ultron-msgs');

      btn.addEventListener('click', async () => {
        const txt = input.value.trim();
        if (!txt) return;
        btn.disabled = true;
        input.value = '';
        msgs.innerHTML += `<div class="log-line" style="color:rgba(168,85,247,.6)">[USER] ${txt}</div>`;

        try {
          const r = await fetch(`${BACKEND}/v1/chat/completions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              message: txt, stream: false,
              model: 'claude-sonnet-4-6',
              system: 'You are ULTRON, strategic intelligence of Nexus9. Be precise, analytical, futuristic. Max 3 sentences.',
            }),
          });
          const d = await r.json();
          const msg = d.choices?.[0]?.message;
          const text = typeof msg === 'string' ? msg : msg?.content || d.response || '—';
          msgs.innerHTML += `<div class="log-line ok">[ULTRON] ${text}</div>`;
        } catch (e) {
          msgs.innerHTML += `<div class="log-line err">[ERROR] ${e.message}</div>`;
        } finally {
          btn.disabled = false;
          msgs.scrollTop = msgs.scrollHeight;
        }
      });
    },

    async refresh() {},
  },
};
