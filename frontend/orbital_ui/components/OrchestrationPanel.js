/**
 * OrchestrationPanel — affiche l'intent, les agents, les mémoires Vault,
 * et le plan d'exécution AVANT chaque réponse JARVIS.
 */

const BACKEND = 'http://localhost:8000';

const AGENT_COLORS = {
  JARVIS:  '#00d4ff',
  ULTRON:  '#a855f7',
  FORGE:   '#ff6b35',
  CORTANA: '#ff6b35',
  GWEN:    '#00ff88',
  BRUCE:   '#ff2d55',
};

const INTENT_ICONS = {
  fabrication:  '🔧',
  coding:       '⚙',
  execution:    '🤖',
  memory:       '🔮',
  reasoning:    '◆',
  conversation: '⬡',
};

export class OrchestrationPanel {
  constructor(feed) {
    this.feed = feed; // le #dock-msgs element
    this._el  = null;
  }

  // Affiche le panneau d'orchestration (avant la réponse)
  async show(text) {
    this._remove();

    // 1. Classification rapide locale (avant l'appel backend)
    const el = document.createElement('div');
    el.className = 'orchestration-card';
    el.style.cssText = `
      margin: 4px 0;
      background: rgba(0,212,255,.04);
      border: 1px solid rgba(0,212,255,.15);
      border-radius: 8px;
      padding: 10px 12px;
      font-size: 9px;
      animation: msgin .2s ease;
    `;
    el.innerHTML = `
      <div style="font-size:8px;font-weight:800;letter-spacing:2px;color:#00d4ff;margin-bottom:6px">
        ⬡ JARVIS ORCHESTRATING...
      </div>
      <div id="orch-content" style="display:flex;flex-direction:column;gap:4px">
        <div style="color:rgba(255,255,255,.4)">⏳ Classifying intent...</div>
      </div>
    `;
    this.feed.appendChild(el);
    this.feed.scrollTop = this.feed.scrollHeight;
    this._el = el;

    // 2. Appel backend /v1/orchestrate
    try {
      const r = await fetch(`${BACKEND}/v1/orchestrate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
        signal: AbortSignal.timeout(8000),
      });
      if (r.ok) {
        const d = await r.json();
        this._render(d);
      }
    } catch {
      // Silently fail — l'orchestration est optionnelle
    }
    return this;
  }

  _render(d) {
    if (!this._el) return;
    const content = this._el.querySelector('#orch-content');
    if (!content) return;

    const intent    = d.intent || 'conversation';
    const agents    = d.agents || ['JARVIS'];
    const providers = d.providers || [];
    const memories  = d.memories || [];
    const plan      = d.plan || [];
    const icon      = INTENT_ICONS[intent] || '⬡';

    const agentBadges = agents.map(a => {
      const color = AGENT_COLORS[a] || '#00d4ff';
      return `<span style="padding:1px 6px;border-radius:8px;border:1px solid ${color}44;background:${color}11;color:${color};font-weight:700">${a}</span>`;
    }).join(' ');

    const memHtml = memories.length
      ? memories.slice(0, 2).map(m =>
          `<div style="color:rgba(0,255,204,.7)">◉ [${m.collection || '?'}] ${(m.text || '').slice(0, 80)}</div>`
        ).join('')
      : '<div style="color:rgba(255,255,255,.25)">Aucune mémoire pertinente trouvée</div>';

    const planHtml = plan.slice(0, 4).map((step, i) =>
      `<div style="color:rgba(255,255,255,.5)">${i + 1}. ${step}</div>`
    ).join('');

    content.innerHTML = `
      <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
        <span style="color:rgba(255,255,255,.5)">Intent:</span>
        <span style="color:#00d4ff;font-weight:700">${icon} ${intent.toUpperCase()}</span>
        <span style="color:rgba(255,255,255,.3)">|</span>
        <span style="color:rgba(255,255,255,.5)">Agents:</span>
        ${agentBadges}
      </div>
      ${providers.length ? `<div style="color:rgba(255,255,255,.4)">Providers: ${providers.join(', ')}</div>` : ''}
      <details style="cursor:pointer">
        <summary style="color:rgba(0,212,255,.6);font-size:8px;letter-spacing:1px">
          VAULT MEMORY (${memories.length} retrieved)
        </summary>
        <div style="margin-top:4px;padding:4px 0;border-top:1px solid rgba(255,255,255,.04)">
          ${memHtml}
        </div>
      </details>
      <details style="cursor:pointer">
        <summary style="color:rgba(0,212,255,.6);font-size:8px;letter-spacing:1px">
          EXECUTION PLAN (${plan.length} steps)
        </summary>
        <div style="margin-top:4px;padding:4px 0;border-top:1px solid rgba(255,255,255,.04)">
          ${planHtml}
        </div>
      </details>
    `;
  }

  // Supprime le panneau (après que la réponse arrive)
  _remove() {
    if (this._el) {
      this._el.remove();
      this._el = null;
    }
  }

  // À appeler quand la réponse finale arrive
  collapse() {
    if (!this._el) return;
    // Réduit le panneau au lieu de le supprimer
    this._el.style.opacity = '0.5';
    this._el.style.fontSize = '8px';
    const header = this._el.querySelector('div[style*="ORCHESTRATING"]');
    if (header) {
      const intentEl = this._el.querySelector('[data-intent]');
      header.textContent = '⬡ orchestrated';
    }
  }
}
