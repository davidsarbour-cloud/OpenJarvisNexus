/**
 * CORTANA Planet — DeepSeek Coder 6.7b via Ollama.
 * Génération de code, debug, refactor via POST /task {agent:"CORTANA"}.
 * Vérifie la disponibilité de deepseek-coder:6.7b via GET localhost:11434/api/tags.
 */
const BACKEND     = 'http://localhost:8000';
const OLLAMA_HOST = 'http://localhost:11434';
const CODER_MODEL = 'deepseek-coder:6.7b';

export const CORTANA_CONFIG = {
  id: 'cortana', icon: '⚙', name: 'CORTANA',
  sub: 'CODE ENGINE — DeepSeek Coder',
  color: '#ff6b35', glow: 'rgba(255,107,53,.5)',
  orbitRadius: 310, speed: -0.10, size: 62,
  pollInterval: 0,
  renderer: {
    startPolling: false,

    async render(body) {
      body.innerHTML = `
        <div class="panel-section-title">CORTANA — DeepSeek Coder 6.7b</div>
        <div id="cortana-status" class="panel-log" style="max-height:40px">Vérification modèle...</div>

        <div class="panel-section-title" style="margin-top:10px">REQUÊTE CODE</div>
        <textarea class="panel-input" id="cortana-input" rows="4"
          placeholder="Génère un script Python, debug, refactor...&#10;&#10;Ex: Écris une API FastAPI avec endpoint /health et /users"></textarea>
        <button class="panel-btn" id="cortana-send" style="margin-top:6px;border-color:rgba(255,107,53,.5);color:#ff6b35">
          ⚙ CODER
        </button>
        <div id="cortana-exec-status" style="font-size:9px;color:rgba(255,107,53,.6);min-height:14px;margin-top:4px"></div>

        <div class="panel-section-title" style="margin-top:4px">OUTPUT</div>
        <div id="cortana-log" class="panel-log" style="max-height:200px;font-family:'Courier New',monospace;font-size:9px"></div>`;

      await cortana_module._checkModel(body);
      cortana_module._bindCoder(body);
    },

    async refresh(body) {
      await cortana_module._checkModel(body);
    },
  },
};

const cortana_module = {
  async _checkModel(body) {
    const el = body.querySelector('#cortana-status');
    if (!el) return;
    try {
      const r = await fetch(`${OLLAMA_HOST}/api/tags`,
        { signal: AbortSignal.timeout(3000) });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d = await r.json();
      const models = (d.models || []).map(m => m.name || '');
      const found  = models.some(m => m.startsWith('deepseek-coder'));
      if (found) {
        el.innerHTML = `<div class="log-line ok">⬡ ${CODER_MODEL} — ONLINE</div>`;
      } else {
        el.innerHTML = `
          <div class="log-line warn">⚠ deepseek-coder non trouvé dans Ollama</div>
          <div class="log-line" style="opacity:.4;font-size:8px">ollama pull ${CODER_MODEL}</div>`;
      }
    } catch {
      el.innerHTML = `
        <div class="log-line err">⬡ OLLAMA OFFLINE</div>
        <div class="log-line" style="opacity:.4;font-size:8px">Lance 1_OLLAMA.bat pour démarrer Ollama</div>`;
    }
  },

  _bindCoder(body) {
    const btn    = body.querySelector('#cortana-send');
    const inp    = body.querySelector('#cortana-input');
    const status = body.querySelector('#cortana-exec-status');
    const log    = body.querySelector('#cortana-log');

    btn.addEventListener('click', async () => {
      const txt = inp.value.trim();
      if (!txt) return;
      btn.disabled = true;
      status.textContent = 'DeepSeek Coder en cours...';
      log.innerHTML = '<div class="log-line" style="opacity:.4">Génération code...</div>';

      const start = Date.now();
      try {
        const r = await fetch(`${BACKEND}/task`, {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          body:    JSON.stringify({ agent: 'CORTANA', task: txt }),
          signal:  AbortSignal.timeout(120000),   // 2 min max
        });
        const d  = await r.json();
        const ms = Date.now() - start;
        const res = d.result || d.response || '⬡ Done.';
        status.textContent = `Complété en ${(ms / 1000).toFixed(1)}s`;

        // Coloration code : détecte les blocs ```
        log.innerHTML = _renderCodeOutput(res.slice(0, 2000));
        inp.value = '';
      } catch (e) {
        status.textContent = 'Erreur: ' + e.message;
        log.innerHTML = `<div class="log-line err">${_escHtml(e.message)}</div>`;
      } finally {
        btn.disabled = false;
        log.scrollTop = log.scrollHeight;
      }
    });
  },
};

/** Rend la sortie code avec coloration simple des blocs ``` */
function _renderCodeOutput(text) {
  const parts = text.split(/(```[\s\S]*?```)/g);
  return parts.map(part => {
    if (part.startsWith('```')) {
      const lines = part.replace(/^```\w*\n?/, '').replace(/```$/, '');
      return `<pre style="background:rgba(255,107,53,.07);border:1px solid rgba(255,107,53,.2);
        border-radius:4px;padding:6px;margin:4px 0;white-space:pre-wrap;color:#ffd700;
        font-family:'Courier New',monospace;font-size:8px">${_escHtml(lines)}</pre>`;
    }
    // Texte normal — chaque ligne devient une div
    return part.split('\n')
      .filter(l => l.trim())
      .map(l => `<div class="log-line">${_escHtml(l)}</div>`)
      .join('');
  }).join('');
}

function _escHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}
