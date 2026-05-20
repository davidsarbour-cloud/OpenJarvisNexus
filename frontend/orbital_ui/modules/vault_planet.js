/**
 * Vault Planet — Command Center pour la mémoire vectorielle ChromaDB.
 * Endpoints: /v1/vault/stats, /v1/vault/analytics, /v1/vault/search, /v1/vault/memory
 */
const BACKEND = 'http://localhost:8000';

export const VAULT_CONFIG = {
  id: 'vault', icon: '🔮', name: 'VAULT',
  sub: 'CENTRAL INTELLIGENCE HUB',
  color: 'var(--vault)', glow: 'rgba(0,255,204,.4)',
  orbitRadius: 200, speed: 0.22, size: 60,
  pollInterval: 8000,
  renderer: {
    startPolling: true,

    async render(body) {
      body.innerHTML = vault_module.buildSkeleton();
      await vault_module.refresh(body);
      vault_module._bindSearch(body);
    },

    async refresh(body) {
      await vault_module.refresh(body);
    },
  },
};

const vault_module = {
  buildSkeleton() {
    return `
      <!-- Section 1: Analytics Header -->
      <div class="panel-section-title">VAULT INTELLIGENCE HUB</div>
      <div id="vault-stats" style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:8px">
        ${['TOTAL MÉMOIRES','FORGE MISSIONS','SCORE MOYEN','BAMBU READY'].map(l => `
          <div class="panel-metric" style="background:rgba(0,255,204,.04);border:1px solid rgba(0,255,204,.1);border-radius:4px;padding:5px 7px">
            <div style="font-size:7px;color:rgba(255,255,255,.3);letter-spacing:.05em">${l}</div>
            <div style="font-size:13px;font-weight:700;color:#00ffcc;margin-top:2px">—</div>
          </div>`).join('')}
      </div>

      <!-- Section 2: Collections -->
      <div class="panel-section-title">MEMORY COLLECTIONS</div>
      <div id="vault-collections" style="margin-bottom:8px">
        <div style="font-size:9px;color:rgba(255,255,255,.3)">Chargement...</div>
      </div>

      <!-- Section 3: Search RAG -->
      <div class="panel-section-title">RAG MEMORY SEARCH</div>
      <input class="panel-input" id="vault-search" placeholder="Recherche sémantique...">
      <select class="panel-input" id="vault-col-select" style="margin-top:4px">
        <option value="">Toutes collections</option>
        <option value="conversations">Conversations</option>
        <option value="forge_reports">Forge Reports</option>
        <option value="orchestration">Orchestration</option>
        <option value="agent_memory">Agent Memory</option>
        <option value="workflows">Workflows</option>
      </select>
      <button class="panel-btn" id="vault-search-btn" style="margin-top:4px">🔍 SEARCH</button>
      <div id="vault-results" class="panel-log" style="max-height:130px;margin-top:6px"></div>

      <!-- Section 4: Ajouter une mémoire -->
      <div class="panel-section-title" style="margin-top:4px">SAVE MEMORY</div>
      <input class="panel-input" id="vault-mem-text" placeholder="Mémoire à sauvegarder...">
      <select class="panel-input" id="vault-mem-col" style="margin-top:4px">
        <option value="agent_memory">Agent Memory</option>
        <option value="workflows">Workflow</option>
        <option value="architecture">Architecture</option>
        <option value="conversations">Conversation</option>
      </select>
      <button class="panel-btn" id="vault-mem-save" style="margin-top:4px">💾 SAUVEGARDER</button>
    `;
  },

  async refresh(body) {
    try {
      const r = await fetch(`${BACKEND}/v1/vault/analytics`, { signal: AbortSignal.timeout(5000) });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d = await r.json();

      // Mise à jour des 4 métriques
      const metrics = [
        { l: 'TOTAL MÉMOIRES', v: d.total_memories ?? 0,              c: '#00ffcc' },
        { l: 'FORGE MISSIONS', v: d.forge?.completed ?? 0,            c: '#ff6b35' },
        { l: 'SCORE MOYEN',    v: (d.forge?.avg_score ?? 0) + '/100', c: '#ffd700' },
        { l: 'BAMBU READY',   v: d.forge?.bambu_ready ?? 0,           c: '#00ff88' },
      ];

      const statsEl = body.querySelector('#vault-stats');
      if (statsEl) {
        statsEl.innerHTML = metrics.map(m => `
          <div class="panel-metric" style="background:rgba(0,255,204,.04);border:1px solid rgba(0,255,204,.1);border-radius:4px;padding:5px 7px">
            <div style="font-size:7px;color:rgba(255,255,255,.3);letter-spacing:.05em">${m.l}</div>
            <div style="font-size:13px;font-weight:700;color:${m.c};margin-top:2px">${m.v}</div>
          </div>`).join('');
      }

      // Mise à jour des collections
      const collections = d.collections || {};
      const colEl = body.querySelector('#vault-collections');
      if (colEl) {
        const entries = Object.entries(collections).filter(([, count]) => count > 0);
        if (!entries.length) {
          colEl.innerHTML = '<div style="font-size:9px;color:rgba(255,255,255,.3)">Aucune collection active</div>';
        } else {
          const max = Math.max(...entries.map(([, c]) => c), 1);
          colEl.innerHTML = entries.map(([name, count]) => {
            const pct = Math.round((count / max) * 100);
            return `
              <div style="display:flex;justify-content:space-between;align-items:center;padding:3px 0;border-bottom:1px solid rgba(255,255,255,.03)">
                <span style="font-size:9px;color:rgba(255,255,255,.4)">${name}</span>
                <div style="display:flex;align-items:center;gap:6px">
                  <div style="width:60px;height:3px;background:rgba(255,255,255,.06);border-radius:2px">
                    <div style="width:${pct}%;height:100%;background:var(--vault);border-radius:2px"></div>
                  </div>
                  <span style="font-size:9px;color:var(--vault)">${count}</span>
                </div>
              </div>`;
          }).join('');
        }
      }
    } catch (e) {
      console.warn('[vault] refresh failed:', e);
      const statsEl = body.querySelector('#vault-stats');
      if (statsEl) {
        statsEl.innerHTML = `
          <div style="grid-column:1/-1;font-size:9px;color:rgba(255,100,100,.7);padding:4px">
            ⚠ /v1/vault/analytics indisponible
          </div>`;
      }
      const colEl = body.querySelector('#vault-collections');
      if (colEl) colEl.innerHTML = '';
    }
  },

  _bindSearch(body) {
    // Bouton search
    const searchBtn = body.querySelector('#vault-search-btn');
    if (searchBtn) {
      searchBtn.addEventListener('click', async () => {
        const q   = body.querySelector('#vault-search').value.trim();
        const col = body.querySelector('#vault-col-select').value;
        const resultsEl = body.querySelector('#vault-results');
        if (!q) { resultsEl.innerHTML = '<div style="font-size:9px;color:rgba(255,255,255,.3)">Entrez un terme de recherche</div>'; return; }

        resultsEl.innerHTML = '<div style="font-size:9px;color:rgba(255,255,255,.3)">Recherche en cours...</div>';

        try {
          const params = new URLSearchParams({ q, n: 5 });
          if (col) params.set('collection', col);
          const r = await fetch(`${BACKEND}/v1/vault/search?${params}`, { signal: AbortSignal.timeout(6000) });
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          const d = await r.json();
          const results = d.results || [];

          if (!results.length) {
            resultsEl.innerHTML = '<div style="font-size:9px;color:rgba(255,255,255,.3)">Aucun résultat</div>';
            return;
          }

          resultsEl.innerHTML = results.map(res => {
            const score      = typeof res.score === 'number' ? (res.score * 100).toFixed(0) : '?';
            const collection = res.metadata?.collection || res.collection || 'unknown';
            const text       = (res.text || '').slice(0, 150);
            return `
              <div style="padding:5px 0;border-bottom:1px solid rgba(255,255,255,.04)">
                <div style="font-size:7px;color:rgba(0,255,204,.5)">[${collection}] Score: ${score}%</div>
                <div style="font-size:10px;color:#b0c8e8">${text}</div>
              </div>`;
          }).join('');
        } catch (e) {
          resultsEl.innerHTML = `<div style="font-size:9px;color:rgba(255,100,100,.7)">⚠ Erreur search: ${e.message}</div>`;
        }
      });
    }

    // Bouton save memory
    const saveBtn = body.querySelector('#vault-mem-save');
    if (saveBtn) {
      saveBtn.addEventListener('click', async () => {
        const text       = body.querySelector('#vault-mem-text').value.trim();
        const collection = body.querySelector('#vault-mem-col').value;
        if (!text) return;

        saveBtn.textContent = '⏳ SAUVEGARDE...';
        saveBtn.disabled = true;

        try {
          const r = await fetch(`${BACKEND}/v1/vault/memory`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ collection, text, metadata: { source: 'orbital_ui', pinned: false }, pinned: false }),
            signal: AbortSignal.timeout(6000),
          });

          if (!r.ok) throw new Error(`HTTP ${r.status}`);

          body.querySelector('#vault-mem-text').value = '';
          saveBtn.textContent = '✅ SAUVEGARDÉ';

          // Rafraîchir les stats après sauvegarde
          setTimeout(() => {
            saveBtn.textContent = '💾 SAUVEGARDER';
            saveBtn.disabled = false;
          }, 1500);
          await vault_module.refresh(body);
        } catch (e) {
          saveBtn.textContent = '❌ ERREUR';
          console.error('[vault] save memory failed:', e);
          setTimeout(() => {
            saveBtn.textContent = '💾 SAUVEGARDER';
            saveBtn.disabled = false;
          }, 2000);
        }
      });
    }

    // Search déclenché par Enter
    const searchInput = body.querySelector('#vault-search');
    if (searchInput) {
      searchInput.addEventListener('keydown', e => {
        if (e.key === 'Enter') searchBtn?.click();
      });
    }
  },
};
