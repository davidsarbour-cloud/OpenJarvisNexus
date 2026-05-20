/**
 * Commerce Planet — Commerce Hub : pipeline produit, approbations, statut Etsy.
 * Connecté à /v1/commerce/* et /v1/etsy/status sur le backend existant.
 */
const BACKEND = 'http://localhost:8000';

const STATUS_COLORS = {
  'pending':     '#3a5870',
  'concept':     '#a855f7',
  'fabrication': '#ff6b35',
  'validation':  '#ffd700',
  'metadata':    '#00d4ff',
  'approval':    '#ffd700',
  'publishing':  '#00ff88',
  'published':   '#00ff88',
  'rejected':    '#ff2d55',
  'error':       '#ff2d55',
};

function _statusBadge(status) {
  const color = STATUS_COLORS[status] || '#aaa';
  return `<span style="color:${color};font-weight:bold;font-size:9px;text-transform:uppercase">${status}</span>`;
}

export const COMMERCE_CONFIG = {
  id: 'missions', icon: '🏪', name: 'COMMERCE HUB',
  sub: 'AI PRODUCT FACTORY',
  color: 'var(--missions)', glow: 'rgba(255,210,0,.4)',
  orbitRadius: 420, speed: -0.11, size: 64,
  pollInterval: 5000,
  renderer: {
    startPolling: true,

    async render(body) {
      body.innerHTML = `
        <!-- Section 1 — New Product Pipeline -->
        <div class="panel-section-title">NEW PRODUCT PIPELINE</div>
        <input class="panel-input" id="commerce-idea"
          placeholder="Product idea (dragon figurine, gear, etc.)">
        <button class="panel-btn" id="commerce-launch" style="margin-top:6px">
          🏪 GENERATE PRODUCT
        </button>
        <div id="commerce-status"
          style="font-size:9px;min-height:14px;margin-top:4px;color:rgba(255,210,0,.7)"></div>

        <!-- Section 2 — Approval Queue -->
        <div class="panel-section-title" style="margin-top:4px">
          APPROVAL QUEUE
          <span id="approval-count" style="color:#ffd700;margin-left:4px">0</span>
        </div>
        <div id="commerce-approvals" class="panel-log"
          style="max-height:140px">Chargement...</div>

        <!-- Section 3 — Recent Pipelines -->
        <div class="panel-section-title" style="margin-top:4px">PIPELINES RÉCENTS</div>
        <div id="commerce-pipelines" class="panel-log" style="max-height:120px"></div>

        <!-- Section 4 — Etsy Status -->
        <div class="panel-section-title" style="margin-top:4px">ETSY STATUS</div>
        <div id="etsy-status"></div>`;

      commerce_module._bindGenerate(body);
      await commerce_module._refresh(body);
    },

    async refresh(body) {
      await commerce_module._refresh(body);
    },
  },
};

const commerce_module = {
  // ── Lier le bouton GENERATE PRODUCT ──────────────────────
  _bindGenerate(body) {
    const btn    = body.querySelector('#commerce-launch');
    const input  = body.querySelector('#commerce-idea');
    const status = body.querySelector('#commerce-status');

    btn.addEventListener('click', async () => {
      const idea = input.value.trim();
      if (!idea) return;
      btn.disabled = true;
      status.textContent = 'Lancement pipeline...';
      try {
        const r = await fetch(`${BACKEND}/v1/commerce/pipeline`, {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          body:    JSON.stringify({ idea }),
          signal:  AbortSignal.timeout(30000),
        });
        const d = await r.json();
        const pid = d.pipeline_id || d.id || '?';
        const st  = d.status || 'started';
        status.textContent = `Pipeline ${pid} — ${st}`;
        input.value = '';
        // Rafraîchit la liste après création
        await commerce_module._refresh(body);
      } catch (e) {
        status.textContent = 'Erreur: ' + e.message;
      } finally {
        btn.disabled = false;
      }
    });
  },

  // ── Rafraîchit les 3 sections dynamiques ─────────────────
  async _refresh(body) {
    await Promise.allSettled([
      commerce_module._loadApprovals(body),
      commerce_module._loadPipelines(body),
      commerce_module._loadEtsyStatus(body),
    ]);
  },

  // ── Section 2 — Approval Queue ───────────────────────────
  async _loadApprovals(body) {
    const container = body.querySelector('#commerce-approvals');
    const countEl   = body.querySelector('#approval-count');
    if (!container) return;
    try {
      const r = await fetch(`${BACKEND}/v1/commerce/approval/pending`,
        { signal: AbortSignal.timeout(8000) });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const items = await r.json();
      const list  = Array.isArray(items) ? items : (items.items || []);
      countEl.textContent = list.length;

      if (list.length === 0) {
        container.innerHTML = '<div class="log-line" style="opacity:.4">Aucun produit en attente</div>';
        return;
      }

      container.innerHTML = list.map(item => {
        const id    = item.id || item.pipeline_id || '?';
        const title = item.title || item.name || item.idea || id;
        const price = item.price ? `$${item.price}` : '';
        return `
          <div style="border-bottom:1px solid rgba(255,255,255,.08);padding:4px 0;display:flex;align-items:center;gap:4px;flex-wrap:wrap">
            <span style="flex:1;font-size:10px;color:#e0e0e0">${title}</span>
            ${price ? `<span style="font-size:9px;color:#ffd700">${price}</span>` : ''}
            <button class="panel-btn approve-btn" data-id="${id}"
              style="background:rgba(0,255,136,.15);color:#00ff88;border-color:#00ff88;padding:2px 6px;font-size:8px">
              ✓ APPROVE
            </button>
            <button class="panel-btn reject-btn" data-id="${id}"
              style="background:rgba(255,45,85,.15);color:#ff2d55;border-color:#ff2d55;padding:2px 6px;font-size:8px">
              ✗ REJECT
            </button>
          </div>`;
      }).join('');

      // Lier les boutons APPROVE
      container.querySelectorAll('.approve-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
          const id = btn.dataset.id;
          btn.disabled = true;
          try {
            await fetch(`${BACKEND}/v1/commerce/approval/${id}/approve`,
              { method: 'POST', signal: AbortSignal.timeout(10000) });
            await commerce_module._loadApprovals(body);
          } catch (e) {
            btn.disabled = false;
          }
        });
      });

      // Lier les boutons REJECT
      container.querySelectorAll('.reject-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
          const id     = btn.dataset.id;
          const reason = window.prompt('Raison du rejet:', '');
          if (reason === null) return; // annulé
          btn.disabled = true;
          try {
            await fetch(`${BACKEND}/v1/commerce/approval/${id}/reject`, {
              method:  'POST',
              headers: { 'Content-Type': 'application/json' },
              body:    JSON.stringify({ reason }),
              signal:  AbortSignal.timeout(10000),
            });
            await commerce_module._loadApprovals(body);
          } catch (e) {
            btn.disabled = false;
          }
        });
      });

    } catch (e) {
      container.innerHTML = `<div class="log-line err">Approval queue: ${e.message}</div>`;
    }
  },

  // ── Section 3 — Recent Pipelines ─────────────────────────
  async _loadPipelines(body) {
    const container = body.querySelector('#commerce-pipelines');
    if (!container) return;
    try {
      const r = await fetch(`${BACKEND}/v1/commerce/pipelines`,
        { signal: AbortSignal.timeout(8000) });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      const list = Array.isArray(data) ? data : (data.pipelines || data.items || []);

      if (list.length === 0) {
        container.innerHTML = '<div class="log-line" style="opacity:.4">Aucun pipeline récent</div>';
        return;
      }

      // Afficher les 8 plus récents
      container.innerHTML = list.slice(0, 8).map(p => {
        const id     = p.id || p.pipeline_id || '?';
        const title  = p.title || p.name || p.idea || id;
        const status = p.status || 'unknown';
        const badge  = _statusBadge(status);
        return `
          <div class="log-line" style="display:flex;align-items:center;gap:6px;padding:2px 0">
            <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:9px">
              ${title.slice(0, 40)}
            </span>
            ${badge}
          </div>`;
      }).join('');

    } catch (e) {
      container.innerHTML = `<div class="log-line err">Pipelines: ${e.message}</div>`;
    }
  },

  // ── Section 4 — Etsy Status ───────────────────────────────
  async _loadEtsyStatus(body) {
    const container = body.querySelector('#etsy-status');
    if (!container) return;
    try {
      const r = await fetch(`${BACKEND}/v1/etsy/status`,
        { signal: AbortSignal.timeout(8000) });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d = await r.json();

      // Affichage flexible selon la forme de la réponse
      const connected = d.connected ?? d.ok ?? (d.status === 'online');
      const shop      = d.shop_name || d.shop || '';
      const listings  = d.active_listings ?? d.listings ?? '';
      const color     = connected ? '#00ff88' : '#ff2d55';
      const label     = connected ? 'CONNECTÉ' : 'HORS-LIGNE';

      container.innerHTML = `
        <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
          <span style="color:${color};font-size:10px;font-weight:bold">⬡ ${label}</span>
          ${shop      ? `<span style="font-size:9px;opacity:.7">${shop}</span>` : ''}
          ${listings !== '' ? `<span style="font-size:9px;color:#ffd700">${listings} listing(s)</span>` : ''}
        </div>`;

    } catch (e) {
      container.innerHTML = `<div class="log-line err">Etsy: ${e.message}</div>`;
    }
  },
};
