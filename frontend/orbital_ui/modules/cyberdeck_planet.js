/**
 * Cyberdeck Planet — system monitoring terminal.
 * Sections: Ecosystem Health | Agents Status | Quick Smoke Test | System Metrics
 */
const BACKEND = 'http://localhost:8000';

export const CYBERDECK_CONFIG = {
  id: 'cyberdeck', icon: '⌘', name: 'CYBERDECK',
  sub: 'MONITORING SYSTÈME',
  color: 'var(--cyberdeck)', glow: 'rgba(255,45,120,.4)',
  orbitRadius: 380, speed: 0.09, size: 60,
  pollInterval: 5000,
  renderer: {
    startPolling: true,

    async render(body) {
      body.innerHTML = `
        <!-- Section 1 : Ecosystem Health Score -->
        <div class="panel-section-title">ECOSYSTEM HEALTH</div>
        <div id="cd-health-score" style="text-align:center;padding:6px 0 2px">
          <span id="cd-hs-number" style="font-size:2.4rem;font-weight:700;letter-spacing:2px;color:#00ff88">—</span>
          <span id="cd-hs-grade"  style="font-size:1.1rem;font-weight:600;margin-left:8px;color:#ffd700">?</span>
        </div>
        <div id="cd-hs-status" style="text-align:center;font-size:.7rem;color:#3a5870;margin-bottom:4px">Chargement...</div>
        <div style="background:#0d1f2d;border-radius:4px;height:8px;overflow:hidden;margin-bottom:6px">
          <div id="cd-hs-bar" style="height:100%;width:0%;background:#00ff88;transition:width .6s,background .4s"></div>
        </div>

        <!-- Section 2 : Agents Status -->
        <div class="panel-section-title" style="margin-top:4px">AGENTS</div>
        <div id="cd-agents" class="panel-log" style="max-height:120px">Chargement...</div>

        <!-- Section 3 : Quick Smoke Test -->
        <div class="panel-section-title" style="margin-top:4px">SMOKE TEST</div>
        <button class="panel-btn" id="cd-smoke-btn">⚡ QUICK SMOKE TEST</button>
        <div id="cd-smoke-results" class="panel-log" style="max-height:120px"></div>

        <!-- Section 4 : System Metrics -->
        <div class="panel-section-title" style="margin-top:4px">SYSTÈME</div>
        <div id="cd-metrics"></div>

        <div class="panel-section-title" style="margin-top:4px">BUDGET SESSION</div>
        <div id="cd-budget" class="panel-log"></div>`;

      // Bouton smoke test
      const btn = body.querySelector('#cd-smoke-btn');
      if (btn) {
        btn.addEventListener('click', () => cyberdeck_module._runSmokeTest(body));
      }

      await cyberdeck_module.refresh(body);
    },

    async refresh(body) {
      await cyberdeck_module.refresh(body);
    },
  },
};

const cyberdeck_module = {
  async refresh(body) {
    this._pollHealth(body);
    this._pollEcosystemHealth(body);
    this._pollAgents(body);
    this._pollBudget(body);
  },

  // ── Section 1 : Ecosystem Health Score ──────────────────────────────────
  async _pollEcosystemHealth(body) {
    const numEl    = body.querySelector('#cd-hs-number');
    const gradeEl  = body.querySelector('#cd-hs-grade');
    const statusEl = body.querySelector('#cd-hs-status');
    const barEl    = body.querySelector('#cd-hs-bar');
    if (!numEl) return;

    try {
      const r = await fetch(`${BACKEND}/v1/ecosystem/health/quick`, { signal: AbortSignal.timeout(5000) });
      const d = await r.json();

      const score  = d.score  ?? d.health_pct ?? 0;
      const grade  = d.grade  ?? _scoreToGrade(score);
      const status = d.status ?? d.message ?? (score >= 75 ? 'NOMINAL' : score >= 50 ? 'DEGRADED' : 'CRITICAL');

      // Couleur barre selon seuils
      const barColor = score >= 75 ? '#00ff88' : score >= 50 ? '#ffd700' : '#ff2d55';
      const numColor = barColor;

      numEl.textContent    = `${score}%`;
      numEl.style.color    = numColor;
      gradeEl.textContent  = grade;
      gradeEl.style.color  = score >= 75 ? '#00ff88' : score >= 50 ? '#ffd700' : '#ff2d55';
      statusEl.textContent = status;
      statusEl.style.color = score >= 75 ? '#3a8' : score >= 50 ? '#aa8800' : '#c0392b';
      barEl.style.width    = `${Math.min(score, 100)}%`;
      barEl.style.background = barColor;

    } catch {
      if (numEl)    numEl.textContent    = '—';
      if (gradeEl)  gradeEl.textContent  = '?';
      if (statusEl) statusEl.textContent = 'Endpoint indisponible';
      if (barEl)    { barEl.style.width = '0%'; barEl.style.background = '#ff2d55'; }
    }
  },

  // ── Section 2 : Agents Status ───────────────────────────────────────────
  async _pollAgents(body) {
    const el = body.querySelector('#cd-agents');
    if (!el) return;
    try {
      const r = await fetch(`${BACKEND}/v1/agents`, { signal: AbortSignal.timeout(4000) });
      const d = await r.json();
      const agents = d.agents || d || [];
      el.innerHTML = agents.map(a => {
        const st    = (a.status || 'unknown').toLowerCase();
        const color = { active:'#00ff88', running:'#ffd700', idle:'#3a5870', offline:'#ff2d55' }[st] || '#3a5870';
        const model = a.model ? ` <span style="color:#3a5870;font-size:.65rem">[${a.model}]</span>` : '';
        return `<div class="log-line" style="color:${color}">[${(a.id||a.name||'?').toUpperCase()}] ${st.toUpperCase()}${model}</div>`;
      }).join('') || '<div class="log-line warn">Aucun agent</div>';
    } catch {
      if (el) el.innerHTML = '<div class="log-line err">Agents indisponibles</div>';
    }
  },

  // ── Section 3 : Quick Smoke Test ────────────────────────────────────────
  async _runSmokeTest(body) {
    const btn = body.querySelector('#cd-smoke-btn');
    const el  = body.querySelector('#cd-smoke-results');
    if (!el) return;

    if (btn) { btn.disabled = true; btn.textContent = '⏳ Exécution...'; }
    el.innerHTML = '<div class="log-line" style="color:#ffd700">Lancement des tests...</div>';

    try {
      const r = await fetch(`${BACKEND}/v1/smoke-test/quick`, { signal: AbortSignal.timeout(30000) });
      const d = await r.json();

      const results = d.results || [];
      const summary = d.summary || {};
      const health  = d.health_pct ?? 0;

      const headerColor = health >= 75 ? '#00ff88' : health >= 50 ? '#ffd700' : '#ff2d55';
      const headerLine  = `<div class="log-line" style="color:${headerColor};font-weight:600">` +
        `${summary.passed ?? 0}/${summary.total ?? results.length} passed — ${health}%</div>`;

      const lines = results.map(r => {
        const ok    = r.status === 'pass';
        const color = ok ? '#00ff88' : '#ff2d55';
        const icon  = ok ? '✓' : '✗';
        const ms    = r.duration_ms != null ? ` (${r.duration_ms}ms)` : '';
        return `<div class="log-line" style="color:${color}">${icon} ${r.name}: ${r.message}${ms}</div>`;
      });

      el.innerHTML = headerLine + lines.join('');
    } catch (err) {
      el.innerHTML = `<div class="log-line err">Smoke test échoué: ${err.message}</div>`;
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = '⚡ QUICK SMOKE TEST'; }
    }
  },

  // ── Section 4 : System Metrics ──────────────────────────────────────────
  async _pollHealth(body) {
    const el = body.querySelector('#cd-metrics');
    if (!el) return;
    try {
      const r = await fetch(`${BACKEND}/health`, { signal: AbortSignal.timeout(3000) });
      const d = await r.json();
      const items = [
        { l: 'BACKEND',      v: r.ok ? 'ONLINE' : 'OFFLINE',                              c: r.ok ? '#00ff88' : '#ff2d55' },
        { l: 'VERSION',      v: d.version          || '—',                                 c: '#00d4ff' },
        { l: 'CLAUDE MODEL', v: d.claude_model      || '—',                                c: '#ffd700' },
        { l: 'OLLAMA',       v: d.ollama_online ? (d.ollama_model || 'OK') : 'OFFLINE',   c: d.ollama_online ? '#a855f7' : '#ff2d55' },
        { l: 'BUDGET',       v: d.budget?.depense   || '—',                                c: '#00ff88' },
      ];
      el.innerHTML = items.map(i =>
        `<div class="panel-metric">
          <span class="panel-metric-label">${i.l}</span>
          <span class="panel-metric-value" style="color:${i.c}">${i.v}</span>
        </div>`).join('');
    } catch {
      if (el) el.innerHTML = '<div class="panel-metric"><span class="panel-metric-label">BACKEND</span><span class="panel-metric-value" style="color:#ff2d55">OFFLINE</span></div>';
    }
  },

  async _pollBudget(body) {
    const el = body.querySelector('#cd-budget');
    if (!el) return;
    try {
      const r = await fetch(`${BACKEND}/v1/budget`, { signal: AbortSignal.timeout(4000) });
      const d = await r.json();
      el.innerHTML = [
        { l: 'Session',       v: `$${(d.session?.cost_usd || 0).toFixed(4)}` },
        { l: "Aujourd'hui",   v: `$${(d.today?.cost_usd   || 0).toFixed(4)}` },
        { l: 'Limite',        v: `$${d.budget_max || 2}` },
      ].map(i => `<div class="log-line">${i.l}: <span style="color:#ffd700">${i.v}</span></div>`).join('');
    } catch {
      if (el) el.innerHTML = '<div class="log-line warn">Budget indisponible</div>';
    }
  },
};

// ── Helpers ────────────────────────────────────────────────────────────────
function _scoreToGrade(score) {
  if (score >= 90) return 'A';
  if (score >= 75) return 'B';
  if (score >= 50) return 'C';
  return 'D';
}
