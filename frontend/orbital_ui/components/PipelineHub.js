/**
 * PipelineHub — barre top (juste sous NEXUS9 ORBITAL INTERFACE), pleine largeur.
 * Contient : CHEAT_CODE (gold) · SERVICES · PIPELINES · TÂCHES · LOG
 */

const BACKEND = 'http://localhost:8000';

const SERVICES = [
  { id: 'backend',  label: 'Backend'  },
  { id: 'ollama',   label: 'Ollama'   },
  { id: 'claude',   label: 'Claude'   },
  { id: 'meshy',    label: 'Meshy'    },
  { id: 'bruce',    label: 'BRUCE'    },
  { id: 'telegram', label: 'Telegram' },
];


export class PipelineHub {
  constructor() {
    this._expanded  = true;
    this._destroyed = false;
    this._pollTimer = null;
    this._build();
    this._bindEvents();
    this._poll();
  }

  // ── Build DOM ──────────────────────────────────────────────

  _build() {
    this.el = document.createElement('div');
    this.el.id = 'pipeline-hub';
    this.el.className = 'expanded';

    this.el.innerHTML = `
      <div class="ph-bar" id="ph-bar">
        <div class="ph-icon">⚡</div>
        <div class="ph-label">PIPELINE HUB</div>
        <div class="ph-activity" id="ph-activity">
          <div class="ph-adot"></div><div class="ph-adot"></div><div class="ph-adot"></div>
        </div>
        <div class="ph-score" id="ph-score">—</div>
        <button class="ph-ctrl" id="ph-expand" title="Réduire/Agrandir">▼</button>
      </div>

      <div class="ph-body">

        <!-- SERVICES — en haut -->
        <div class="ph-section">
          <div class="ph-hdr">SERVICES</div>
          <div class="ph-services" id="ph-services"></div>
        </div>

        <!-- ♛ CHEAT_CODE — GOLD VIP -->
        <div class="ph-section ph-vip-section">
          <button class="ph-vip-btn" id="ph-cheat-btn"
                  data-tip="Sync agents · Ecosystem score 0-100 · 12 daily tasks · Vault update · Notification vocale">
            <span class="ph-vip-crown">♛</span>
            <span class="ph-vip-name">CHEAT_CODE</span>
            <span class="ph-vip-sub">SYNC ALL · VAULT · NOTIFY</span>
          </button>
        </div>

        <!-- ⬡ STL_PIPELINE — SILVER VIP -->
        <div class="ph-section ph-silver-vip-section">
          <button class="ph-silver-btn" id="ph-stl-btn"
                  data-tip="Génère un STL imprimable : décris l'objet → Meshy AI → trimesh repair → validation → Bambu Studio">
            <span class="ph-silver-icon">⬡</span>
            <span class="ph-silver-name">STL_PIPELINE</span>
            <span class="ph-silver-sub">MESHY AI · TRIMESH · BAMBU</span>
          </button>
          <div id="ph-stl-wrap" style="display:none">
            <textarea id="ph-stl-prompt" class="ph-stl-textarea" rows="2"
              placeholder="dragon low-poly 15cm · boitier · engrenage..."></textarea>
            <div class="ph-stl-row">
              <button id="ph-stl-go">▶ LANCER</button>
              <button id="ph-stl-cancel">✕</button>
            </div>
            <div id="ph-stl-status" class="ph-forge-status"></div>
          </div>
        </div>

        <!-- ◑ DAILY RESEARCH — mauve -->
        <div class="ph-section ph-solo-section">
          <div class="ph-daily-wrap">
            <button class="ph-action-btn ph-action-mauve" id="phpb-daily"
                    data-tip="8 tâches masterlist via QWEN + NOVA local — Code, STL, IA, Outils, Projets…">
              <span class="ph-action-icon">◑</span>
              <span class="ph-action-name">DAILY RESEARCH</span>
              <span class="ph-action-sub">QWEN · NOVA · 8 TASKS</span>
            </button>
            <div class="ph-daily-status" id="ph-daily-status" style="display:none">
              <span class="ph-daily-spinner">⏳</span>
              <span class="ph-daily-progress" id="ph-daily-progress">0/8</span>
              <span class="ph-daily-task" id="ph-daily-task"></span>
            </div>
          </div>
        </div>

        <!-- ▣ RAPPORT — bleu -->
        <div class="ph-section ph-solo-section">
          <button class="ph-action-btn ph-action-blue" id="phpb-report"
                  data-tip="Génère un rapport HTML Nexus9 complet — missions, agents, budget, analytics">
            <span class="ph-action-icon">▣</span>
            <span class="ph-action-name">RAPPORT</span>
            <span class="ph-action-sub">HTML · AGENTS · ANALYTICS</span>
          </button>
        </div>

        <!-- ▶ START ALL — rose -->
        <div class="ph-section ph-solo-section">
          <button class="ph-action-btn ph-action-rose" id="phpb-start-all"
                  data-tip="Lance START_ALL.bat — démarre Ollama, Backend, Telegram, BRUCE, Crush AI + Morning Routine">
            <span class="ph-action-icon">▶</span>
            <span class="ph-action-name">START ALL</span>
            <span class="ph-action-sub">OLLAMA · BACKEND · BRUCE · CRUSH</span>
          </button>
        </div>

        <!-- LOG -->
        <div class="ph-section ph-section-last">
          <div class="ph-hdr">LOG</div>
          <div class="ph-log" id="ph-log"></div>
        </div>

      </div>`;

    document.body.appendChild(this.el);
    this._buildServices();
    this._initTooltips();
  }

  _initTooltips() {
    // Tooltip JS injecté dans body — échappe à overflow:hidden du panel
    const tip = document.createElement('div');
    tip.id = 'ph-tooltip';
    tip.style.cssText = [
      'position:fixed', 'z-index:9999', 'pointer-events:none',
      'max-width:240px', 'padding:9px 13px',
      'background:rgba(2,6,20,.97)',
      'border:1px solid rgba(0,212,255,.3)', 'border-radius:8px',
      'color:rgba(176,200,232,.9)', 'font:10px/1.55 "Share Tech Mono",monospace',
      'letter-spacing:.4px', 'white-space:normal',
      'box-shadow:0 4px 20px rgba(0,0,0,.7)',
      'opacity:0', 'transition:opacity .15s ease',
      'display:none',
    ].join(';');
    document.body.appendChild(tip);

    this.el.querySelectorAll('[data-tip]').forEach(btn => {
      btn.addEventListener('mouseenter', e => {
        tip.textContent  = btn.dataset.tip;
        tip.style.display = 'block';
        requestAnimationFrame(() => {
          const r  = btn.getBoundingClientRect();
          const tw = tip.offsetWidth;
          const th = tip.offsetHeight;
          let left = r.left + r.width / 2 - tw / 2;
          let top  = r.bottom + 8;
          // Si ça dépasse à droite
          if (left + tw > window.innerWidth - 8) left = window.innerWidth - tw - 8;
          if (left < 8) left = 8;
          // Si ça sort en bas, afficher au-dessus
          if (top + th > window.innerHeight - 8) top = r.top - th - 8;
          tip.style.left    = left + 'px';
          tip.style.top     = top  + 'px';
          tip.style.opacity = '1';
          // Couleur bordure selon le bouton
          const color = btn.classList.contains('ph-vip-btn')    ? 'rgba(255,215,0,.5)'     :
                        btn.classList.contains('ph-silver-btn') ? 'rgba(192,200,216,.4)'  :
                        btn.classList.contains('ph-action-red') ? 'rgba(255,45,85,.4)'    :
                        btn.classList.contains('ph-action-mauve') ? 'rgba(168,85,247,.4)' :
                        btn.classList.contains('ph-action-blue')  ? 'rgba(0,180,255,.4)'  :
                        btn.classList.contains('ph-action-rose')  ? 'rgba(255,105,180,.4)': 'rgba(0,212,255,.3)';
          tip.style.borderColor = color;
        });
      });
      btn.addEventListener('mouseleave', () => {
        tip.style.opacity = '0';
        setTimeout(() => { tip.style.display = 'none'; }, 150);
      });
    });
  }

  _buildServices() {
    this.el.querySelector('#ph-services').innerHTML = SERVICES.map(s => `
      <div class="ph-svc" id="phs-${s.id}">
        <div class="ph-svc-dot offline" id="phd-${s.id}"></div>
        <span>${s.label}</span>
      </div>`).join('');
  }


  // ── Events ─────────────────────────────────────────────────

  _bindEvents() {
    this.el.querySelector('#ph-expand').addEventListener('click', () => this._toggle());

    // CHEAT_CODE
    this.el.querySelector('#ph-cheat-btn').addEventListener('click', () => {
      if (!this.el.querySelector('#ph-cheat-btn').disabled) this._runCheatCode();
    });

    // STL_PIPELINE
    this.el.querySelector('#ph-stl-btn').addEventListener('click', () => {
      if (!this.el.querySelector('#ph-stl-btn').disabled) this._toggleSTLPrompt();
    });
    this.el.querySelector('#ph-stl-go').addEventListener('click', () => this._launchSTL());
    this.el.querySelector('#ph-stl-cancel').addEventListener('click', () => this._hideSTLPrompt());
    this.el.querySelector('#ph-stl-prompt').addEventListener('keydown', e => {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); this._launchSTL(); }
    });

    // Action buttons
    this.el.querySelector('#phpb-daily').addEventListener('click', () => {
      if (!this.el.querySelector('#phpb-daily').disabled) this._runDailyResearch();
    });
    this.el.querySelector('#phpb-report').addEventListener('click', () => {
      if (!this.el.querySelector('#phpb-report').disabled) this._runReport();
    });
    this.el.querySelector('#phpb-start-all').addEventListener('click', () => {
      if (!this.el.querySelector('#phpb-start-all').disabled) this._runStartAll();
    });
  }

  _toggle() {
    this._expanded = !this._expanded;
    this.el.className = this._expanded ? 'expanded' : 'collapsed';
    this.el.querySelector('#ph-expand').textContent = this._expanded ? '▼' : '▲';
  }

  // ── STL_PIPELINE ───────────────────────────────────────────

  _toggleSTLPrompt() {
    const wrap = this.el.querySelector('#ph-stl-wrap');
    if (wrap.style.display === 'none') {
      wrap.style.display = 'block';
      this.el.querySelector('#ph-stl-prompt').focus();
    } else {
      this._hideSTLPrompt();
    }
  }

  _hideSTLPrompt() {
    this.el.querySelector('#ph-stl-wrap').style.display = 'none';
    this.el.querySelector('#ph-stl-prompt').value = '';
    this.el.querySelector('#ph-stl-status').textContent = '';
  }

  async _launchSTL() {
    const prompt  = this.el.querySelector('#ph-stl-prompt').value.trim();
    if (!prompt) return;
    const statusEl = this.el.querySelector('#ph-stl-status');
    const stlBtn   = this.el.querySelector('#ph-stl-btn');
    stlBtn.disabled = true;
    stlBtn.classList.add('running');
    statusEl.textContent = 'Lancement...';
    this._log(`⬡ STL — "${prompt.slice(0, 45)}"`);
    try {
      const r = await fetch(`${BACKEND}/v1/forge/mission`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt }),
        signal: AbortSignal.timeout(30000),
      });
      const d   = await r.json();
      const mid = d.mission_id || '?';
      statusEl.textContent = `⬡ Mission ${mid} démarrée — suivi dans Forge Hub ↓`;
      this._log(`⬡ Mission ${mid} démarrée · résultat dans Forge Hub`);
      this.el.querySelector('#ph-stl-prompt').value = '';
    } catch (e) {
      statusEl.textContent = 'Erreur: ' + e.message;
      this._log(`✗ STL: ${e.message}`, 'err');
    } finally {
      stlBtn.disabled = false;
      stlBtn.classList.remove('running');
    }
  }

  // ── Polling (services health + daily tasks) ────────────────

  async _poll() {
    if (this._destroyed) return;
    await Promise.allSettled([this._fetchHealth(), this._fetchDailyTasks()]);
    if (!this._destroyed) this._pollTimer = setTimeout(() => this._poll(), 30000);
  }

  async _fetchHealth() {
    try {
      const r = await fetch(`${BACKEND}/health`, { signal: AbortSignal.timeout(5000) });
      if (!r.ok) throw new Error();
      const d = await r.json();
      this._setSvc('backend', true);
      this._setSvc('ollama',  d.ollama_online !== false);
      this._setSvc('claude',  !!d.claude_model);
      this._fetchDeepHealth();
    } catch { this._setSvc('backend', false); }
  }

  async _fetchDeepHealth() {
    try {
      const r = await fetch(`${BACKEND}/v1/health/deep`, { signal: AbortSignal.timeout(10000) });
      if (!r.ok) return;
      const d = await r.json();
      this._setSvc('meshy',    d.meshy?.ok    === true);
      this._setSvc('bruce',    d.bruce?.ok    === true || d.openhands?.ok === true);
      this._setSvc('telegram', d.telegram?.ok === true);
      this._setSvc('claude',   d.claude?.ok   !== false);
      const score = d.score ?? d.health_score;
      if (score !== undefined) this._setScore(Math.round(score));
    } catch {}
  }

  async _fetchDailyTasks() {
    try {
      const r = await fetch(`${BACKEND}/v1/daily/status`, { signal: AbortSignal.timeout(5000) });
      if (!r.ok) return;
      this._renderTasks(await r.json());
    } catch {
      const el = this.el.querySelector('#ph-tasks');
      if (el) el.innerHTML = '<div class="ph-muted ph-placeholder">Non disponible</div>';
    }
  }

  _renderTasks(d) {
    const jobs = d.jobs || [];
    const cnt  = this.el.querySelector('#ph-task-count');
    if (cnt) cnt.textContent = `(${jobs.length})`;
    const container = this.el.querySelector('#ph-tasks');
    if (!jobs.length) {
      container.innerHTML = '<div class="ph-muted ph-placeholder">Aucune tâche planifiée</div>';
      return;
    }
    container.innerHTML = jobs.map(j => {
      const next = j.next_run
        ? new Date(j.next_run).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
        : '—';
      const cls = j.last_status === 'ok' || j.last_status === 'completed' ? 'ok' : j.last_status ? 'warn' : '';
      return `<div class="ph-task">
        <div class="ph-task-dot ${cls}"></div>
        <div>
          <div class="ph-task-name">${j.id || j.name || 'task'}</div>
          <div class="ph-task-next ph-muted">next: ${next}</div>
        </div>
      </div>`;
    }).join('');
  }

  _setSvc(id, online) {
    const dot = this.el.querySelector(`#phd-${id}`);
    if (dot) dot.className = `ph-svc-dot ${online ? 'online' : 'offline'}`;
  }

  _setScore(score) {
    const el = this.el.querySelector('#ph-score');
    if (!el) return;
    el.textContent = score + '%';
    el.style.color = score > 75 ? '#00ff88' : score > 50 ? '#ffd700' : '#ff2d55';
  }

  // ── Regular pipelines ──────────────────────────────────────

  async _runStartAll() {
    this._log('▶ START ALL...');
    this._busy('start-all', true);
    try {
      const r = await fetch(`${BACKEND}/v1/pipeline/start-all`, { method: 'POST', signal: AbortSignal.timeout(10000) });
      const d = await r.json();
      this._log(`⬡ ${d.message || 'Lancé'}`);
    } catch { this._log('⬡ Lance START_ALL.bat depuis ton terminal', 'warn'); }
    finally { this._busy('start-all', false); }
  }

  async _runDailyResearch() {
    const btn = this.el.querySelector('#phpb-daily');
    if (btn.disabled) return;
    btn.disabled = true;

    // Lance en background
    try {
      const r = await fetch(`${BACKEND}/v1/pipeline/daily/start`, {
        method: 'POST', signal: AbortSignal.timeout(8000),
      });
      const d = await r.json();
      if (!d.ok) { this._log(`✗ Daily: ${d.message}`, 'warn'); btn.disabled = false; return; }
      this._log(`◑ DAILY RESEARCH lancé — ${d.total || 8} tâches en cours…`);
    } catch (e) { this._log(`✗ Daily start: ${e.message}`, 'err'); btn.disabled = false; return; }

    // Afficher la barre de progression
    const statusEl   = this.el.querySelector('#ph-daily-status');
    const progressEl = this.el.querySelector('#ph-daily-progress');
    const taskEl     = this.el.querySelector('#ph-daily-task');
    const spinnerEl  = this.el.querySelector('.ph-daily-spinner');
    statusEl.style.display = 'flex';

    // Polling toutes les 5 secondes
    this._dailyPollTimer = setInterval(async () => {
      try {
        const r = await fetch(`${BACKEND}/v1/pipeline/daily/status`, { signal: AbortSignal.timeout(4000) });
        const s = await r.json();

        const cur   = s.current  ?? 0;
        const total = s.total    ?? 8;
        progressEl.textContent = `${cur}/${total}`;
        taskEl.textContent     = s.current_task ? s.current_task.slice(0, 45) : '';

        if (s.status === 'done') {
          clearInterval(this._dailyPollTimer);
          spinnerEl.textContent = '✅';
          const passed = (s.results || []).filter(t => t.ok).length;
          progressEl.textContent = `${passed}/${total} OK`;
          taskEl.textContent     = s.folder ? `→ ${s.folder.split('\\').pop()}` : '';
          this._log(`✅ Daily Research terminé — ${passed}/${total} tâches · ${s.folder || ''}`);
          btn.disabled = false;
          setTimeout(() => { statusEl.style.display = 'none'; spinnerEl.textContent = '⏳'; }, 8000);

        } else if (s.status === 'error') {
          clearInterval(this._dailyPollTimer);
          spinnerEl.textContent = '❌';
          progressEl.textContent = 'Erreur';
          taskEl.textContent = s.current_task || '';
          this._log(`✗ Daily Research: ${s.current_task || 'erreur'}`, 'err');
          btn.disabled = false;
        }
      } catch {}
    }, 5000);
  }

  async _runReport() {
    this._log('▶ RAPPORT...');
    this._busy('report', true);
    try {
      const r = await fetch(`${BACKEND}/v1/reports/generate`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: 'Nexus9 Daily Report', agent: 'JARVIS' }),
        signal: AbortSignal.timeout(30000),
      });
      const d = await r.json();
      this._log(`▣ Rapport: ${d.filename || 'généré'}`);
      this._saveToFolder('reports', d);
    } catch (e) { this._log(`✗ Rapport: ${e.message}`, 'err'); }
    finally { this._busy('report', false); }
  }

  async _runCheatCode() {
    const btn = this.el.querySelector('#ph-cheat-btn');
    btn.disabled = true;
    btn.classList.add('running');
    this._log('♛ CHEAT_CODE — synchronisation Nexus9...');
    try {
      const r = await fetch(`${BACKEND}/v1/cheat-code?voice=true`, { method: 'POST', signal: AbortSignal.timeout(60000) });
      const d      = await r.json();
      const online = d.agents?.online ?? 0;
      const total  = d.agents?.total  ?? 0;
      const mems   = d.vault?.total_memories ?? 0;
      const saved  = d.vault_id ? '✅' : '⚠';
      const eco   = d.ecosystem?.score != null ? `${d.ecosystem.score}/100 ${d.ecosystem.grade ?? ''}` : '—';
      this._log(`♛ ${(d.status ?? '').toUpperCase()} — ${online}/${total} agents · Ecosystem ${eco} · ${mems} mémoires ${saved}`);
      d.agents?.details?.forEach(a => this._log(`  ${a.ok ? '✓' : '✗'} ${a.agent}`, a.ok ? '' : 'warn'));
      if (d.daily_tasks) {
        const p = d.daily_tasks.passed ?? 0, t = d.daily_tasks.total ?? 0;
        this._log(`  ⚙ Daily tasks: ${p}/${t} OK`, p < t ? 'warn' : '');
      }
    } catch (e) { this._log(`✗ CHEAT_CODE: ${e.message}`, 'err'); }
    finally { btn.disabled = false; btn.classList.remove('running'); }
  }

  // ── Helpers ────────────────────────────────────────────────

  _busy(id, on) {
    const btn = this.el.querySelector(`#phpb-${id}`);
    if (!btn) return;
    btn.disabled = on;
    btn.classList.toggle('running', on);
  }

  async _saveToFolder(type, data) {
    try {
      await fetch(`${BACKEND}/v1/report/save`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type, data }), signal: AbortSignal.timeout(5000),
      });
    } catch {}
  }

  _log(text, type = '') {
    const log = this.el.querySelector('#ph-log');
    if (!log) return;
    const n  = new Date();
    const ts = [n.getHours(), n.getMinutes()].map(x => String(x).padStart(2, '0')).join(':');
    const el = document.createElement('div');
    el.className = `ph-log-line${type ? ' ' + type : ''}`;
    el.innerHTML = `<span class="ph-log-ts">${ts}</span> ${_esc(text)}`;
    log.appendChild(el);
    const lines = log.querySelectorAll('.ph-log-line');
    if (lines.length > 40) lines[0].remove();
    log.scrollTop = log.scrollHeight;
    const act = this.el.querySelector('#ph-activity');
    act?.classList.add('live');
    setTimeout(() => act?.classList.remove('live'), 1500);
  }

  destroy() {
    if (this._destroyed) return;
    this._destroyed = true;
    if (this._pollTimer) clearTimeout(this._pollTimer);
    this.el?.remove();
    this.el = null;
  }
}

function _esc(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
