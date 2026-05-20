/**
 * ForgeHub — panneau rétractable BOTTOM-RIGHT pour toutes les opérations STL/Forge.
 * Fusion de l'ancien ForgeHub + logique complète de forge_room_planet.js.
 * Nexus9 · D3Dprintix · KAIZEN pipeline.
 */

const BACKEND = 'http://localhost:8000';

// ── Constantes pipeline ──────────────────────────────────────────────────────

const FORGE_STEPS = [
  { key: 'routing',          label: 'JARVIS Routing',   icon: '⬡' },
  { key: 'planning',         label: 'ULTRON Planning',  icon: '◆' },
  { key: 'code_generation',  label: 'DeepSeek Codegen', icon: '◈' },
  { key: 'mesh_generation',  label: 'Mesh Generation',  icon: '◫' },
  { key: 'validation_raw',   label: 'Raw Validation',   icon: '⬟' },
  { key: 'repair',           label: 'Auto Repair',      icon: '⚙' },
  { key: 'orientation',      label: 'FDM Orientation',  icon: '↻' },
  { key: 'support_analysis', label: 'Support Analysis', icon: '△' },
  { key: 'validation_final', label: 'Final Validation', icon: '✓' },
  { key: 'export',           label: 'STL Export',       icon: '↓' },
  { key: 'report',           label: 'Mfg Report',       icon: '📊' },
];

const FORGE_PIPELINES = [
  { id: 'forge-analytics', label: 'FORGE ANALYTICS', icon: '◆' },
  { id: 'stl-sync',        label: 'STL SYNC',        icon: '⬢' },
  { id: 'forge-report',    label: 'FORGE REPORT',    icon: '▣' },
  { id: 'stl-research',    label: 'STL RESEARCH',    icon: '◑' },
];

// ── Helpers standalone ───────────────────────────────────────────────────────

function _fhEsc(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function _scoreGrade(score) {
  if (score == null || score === '—') return '—';
  const n = Number(score);
  if (n >= 90) return 'A';
  if (n >= 75) return 'B';
  if (n >= 60) return 'C';
  return 'D';
}

function _gradeColor(grade) {
  if (grade === 'A') return '#00ff88';
  if (grade === 'B') return '#00d4ff';
  if (grade === 'C') return '#ffd700';
  return '#ff4444';
}

// ── CSS injecté une seule fois ───────────────────────────────────────────────

const FH_STYLE_ID = 'fhub-style';

function _injectStyle() {
  if (document.getElementById(FH_STYLE_ID)) return;
  const s = document.createElement('style');
  s.id = FH_STYLE_ID;
  s.textContent = `
/* ══════════════════════════════════════════════════════════
   FORGE HUB — panneau bottom-right rétractable
   Palette steel/silver : #c0c8d8 / rgba(192,200,216,...)
   ══════════════════════════════════════════════════════════ */

#fhub {
  position: fixed;
  bottom: 16px;
  right: 16px;
  width: 310px;
  background: rgba(8, 12, 22, 0.96);
  border: 1px solid rgba(192, 200, 216, 0.22);
  border-radius: 10px;
  box-shadow: 0 0 24px rgba(192, 200, 216, 0.08), 0 4px 40px rgba(0,0,0,.7);
  font-family: 'Orbitron', 'Share Tech Mono', monospace;
  font-size: 9px;
  letter-spacing: .6px;
  color: #c0c8d8;
  z-index: 9000;
  transition: height .25s ease, opacity .2s;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  max-height: 90vh;
}

#fhub.collapsed .fh-body {
  display: none;
}

/* ── Header bar ──────────────────────────────────────────── */

.fh-bar {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 8px 10px 7px;
  border-bottom: 1px solid rgba(192, 200, 216, 0.12);
  background: rgba(192, 200, 216, 0.04);
  cursor: pointer;
  flex-shrink: 0;
  user-select: none;
}

.fh-icon {
  font-size: 13px;
  color: #c0c8d8;
  line-height: 1;
  flex-shrink: 0;
}

.fh-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1.8px;
  color: #c0c8d8;
  flex: 1;
}

.fh-activity {
  display: flex;
  gap: 3px;
  align-items: center;
}

.fh-adot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: rgba(192, 200, 216, 0.25);
  transition: background .3s;
}

.fh-activity.live .fh-adot {
  background: #c0c8d8;
  box-shadow: 0 0 4px #c0c8d8;
}

.fh-activity.live .fh-adot:nth-child(2) {
  animation: fh-pulse 1s infinite .2s;
}

.fh-activity.live .fh-adot:nth-child(3) {
  animation: fh-pulse 1s infinite .4s;
}

@keyframes fh-pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: .3; }
}

.fh-score {
  font-size: 9px;
  color: rgba(192, 200, 216, 0.55);
  letter-spacing: .5px;
  min-width: 24px;
  text-align: right;
}

.fh-ctrl {
  background: none;
  border: 1px solid rgba(192, 200, 216, 0.2);
  border-radius: 3px;
  color: #c0c8d8;
  font-family: inherit;
  font-size: 8px;
  padding: 2px 5px;
  cursor: pointer;
  transition: border-color .2s, background .2s;
  flex-shrink: 0;
}

.fh-ctrl:hover {
  border-color: rgba(192, 200, 216, 0.5);
  background: rgba(192, 200, 216, 0.07);
}

/* ── Body (scrollable) ───────────────────────────────────── */

.fh-body {
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: 0;
  scrollbar-width: thin;
  scrollbar-color: rgba(192,200,216,.2) transparent;
}

.fh-body::-webkit-scrollbar { width: 4px; }
.fh-body::-webkit-scrollbar-thumb { background: rgba(192,200,216,.2); border-radius: 2px; }

/* ── Section ─────────────────────────────────────────────── */

.fh-section {
  padding: 8px 10px;
  border-bottom: 1px solid rgba(192, 200, 216, 0.07);
}

.fh-section-last {
  border-bottom: none;
}

.fh-hdr {
  font-size: 8px;
  letter-spacing: 2px;
  color: rgba(192, 200, 216, 0.45);
  margin-bottom: 6px;
  font-weight: 600;
}

/* ── VIP STL button ──────────────────────────────────────── */

.fh-vip-section {
  background: rgba(192, 200, 216, 0.03);
}

.fh-vip-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  background: linear-gradient(135deg, rgba(192,200,216,.1), rgba(192,200,216,.05));
  border: 1px solid rgba(192,200,216,.28);
  border-radius: 6px;
  padding: 8px 10px;
  cursor: pointer;
  font-family: inherit;
  color: #c0c8d8;
  transition: border-color .2s, background .2s, box-shadow .2s;
}

.fh-vip-btn:hover:not(:disabled) {
  border-color: rgba(192,200,216,.55);
  background: linear-gradient(135deg, rgba(192,200,216,.16), rgba(192,200,216,.08));
  box-shadow: 0 0 12px rgba(192,200,216,.12);
}

.fh-vip-btn:disabled {
  opacity: .5;
  cursor: not-allowed;
}

.fh-vip-btn.running {
  border-color: rgba(192,200,216,.6);
  animation: fh-vip-run 1.8s infinite;
}

@keyframes fh-vip-run {
  0%, 100% { box-shadow: 0 0 8px rgba(192,200,216,.15); }
  50%       { box-shadow: 0 0 18px rgba(192,200,216,.35); }
}

.fh-vip-icon {
  font-size: 20px;
  line-height: 1;
  flex-shrink: 0;
}

.fh-vip-text {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
}

.fh-vip-name {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1.6px;
  color: #c0c8d8;
}

.fh-vip-sub {
  font-size: 7.5px;
  letter-spacing: 1px;
  color: rgba(192,200,216,.55);
}

/* ── STL prompt area ─────────────────────────────────────── */

.fh-stl-wrap {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.fh-stl-wrap textarea {
  width: 100%;
  box-sizing: border-box;
  background: rgba(0,0,0,.4);
  border: 1px solid rgba(192,200,216,.22);
  border-radius: 5px;
  color: #c0c8d8;
  font-family: inherit;
  font-size: 9px;
  letter-spacing: .5px;
  padding: 6px 8px;
  resize: none;
  outline: none;
  transition: border-color .2s;
}

.fh-stl-wrap textarea:focus {
  border-color: rgba(192,200,216,.5);
}

.fh-stl-wrap textarea::placeholder {
  color: rgba(192,200,216,.3);
}

.fh-stl-row {
  display: flex;
  gap: 5px;
}

.fh-stl-row button {
  background: rgba(192,200,216,.08);
  border: 1px solid rgba(192,200,216,.3);
  border-radius: 4px;
  color: #c0c8d8;
  font-family: inherit;
  font-size: 8.5px;
  letter-spacing: .8px;
  padding: 4px 10px;
  cursor: pointer;
  transition: background .2s, border-color .2s;
  flex: 1;
}

.fh-stl-row button:hover {
  background: rgba(192,200,216,.16);
  border-color: rgba(192,200,216,.5);
}

.fh-stl-row button:last-child {
  flex: 0 0 auto;
  padding: 4px 8px;
  color: rgba(192,200,216,.55);
}

.fh-stl-status {
  font-size: 8px;
  color: rgba(192,200,216,.5);
  min-height: 12px;
  letter-spacing: .5px;
}

/* ── Pipeline grid ───────────────────────────────────────── */

.fh-pipelines {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 5px;
}

.fh-pipe-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  background: rgba(192,200,216,.05);
  border: 1px solid rgba(192,200,216,.18);
  border-radius: 5px;
  padding: 6px 7px;
  cursor: pointer;
  font-family: inherit;
  font-size: 8px;
  letter-spacing: .8px;
  color: rgba(192,200,216,.75);
  transition: background .2s, border-color .2s, color .2s;
  white-space: nowrap;
  overflow: hidden;
}

.fh-pipe-btn:hover:not(:disabled) {
  background: rgba(192,200,216,.12);
  border-color: rgba(192,200,216,.4);
  color: #c0c8d8;
}

.fh-pipe-btn:disabled {
  opacity: .45;
  cursor: not-allowed;
}

.fh-pipe-btn.running {
  border-color: rgba(192,200,216,.5);
  color: #c0c8d8;
  animation: fh-pipe-run 1.4s infinite;
}

@keyframes fh-pipe-run {
  0%, 100% { background: rgba(192,200,216,.05); }
  50%       { background: rgba(192,200,216,.14); }
}

.fh-pipe-ico {
  font-size: 11px;
  flex-shrink: 0;
}

/* ── Pipeline steps ──────────────────────────────────────── */

.fh-steps {
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-height: 170px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(192,200,216,.15) transparent;
}

.fh-fstep {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 2px 4px;
  border-radius: 3px;
  font-size: 8px;
  letter-spacing: .5px;
  color: rgba(192,200,216,.25);
  transition: color .3s, background .3s;
}

.fh-fstep-ico {
  width: 12px;
  text-align: center;
  flex-shrink: 0;
}

.fh-fstep-label {
  flex: 1;
}

.fh-fstep-badge {
  font-size: 7.5px;
  letter-spacing: .8px;
  opacity: .7;
}

/* ── Metrics panel ───────────────────────────────────────── */

#fh-forge-metrics {
  display: none;
  gap: 7px;
  flex-wrap: wrap;
  margin-top: 4px;
}

#fh-forge-metrics.visible {
  display: flex;
}

.fhm-score-box {
  flex: 1;
  background: rgba(0,0,0,.3);
  border: 1px solid rgba(192,200,216,.1);
  border-radius: 6px;
  padding: 8px;
  text-align: center;
  min-width: 70px;
}

#fh-score-val {
  font-size: 20px;
  font-weight: 900;
  color: #ffd700;
  font-family: 'Orbitron', monospace;
  line-height: 1;
}

#fh-grade {
  font-size: 8px;
  letter-spacing: 2px;
  color: rgba(192,200,216,.4);
  margin-top: 3px;
}

.fhm-meta-box {
  flex: 1;
  background: rgba(0,0,0,.3);
  border: 1px solid rgba(192,200,216,.1);
  border-radius: 6px;
  padding: 8px;
  min-width: 90px;
}

.fhm-row {
  display: flex;
  justify-content: space-between;
  padding: 1.5px 0;
  font-size: 7.5px;
  color: rgba(192,200,216,.55);
}

.fhm-val {
  color: #c0c8d8;
  font-weight: 600;
}

#fh-bambu {
  display: none;
  width: 100%;
  margin-top: 6px;
  background: rgba(0,255,136,.06);
  border: 1px solid rgba(0,255,136,.35);
  border-radius: 5px;
  color: #00ff88;
  font-family: inherit;
  font-size: 8.5px;
  letter-spacing: 1px;
  padding: 5px;
  cursor: pointer;
  transition: background .2s, box-shadow .2s;
}

#fh-bambu:hover:not(:disabled) {
  background: rgba(0,255,136,.12);
  box-shadow: 0 0 10px rgba(0,255,136,.2);
}

#fh-bambu:disabled {
  opacity: .5;
  cursor: not-allowed;
}

/* ── Missions récentes ───────────────────────────────────── */

#fh-missions {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.fh-mission-item {
  background: rgba(192,200,216,.04);
  border: 1px solid rgba(192,200,216,.1);
  border-radius: 4px;
  padding: 5px 7px;
}

.fh-mission-id {
  font-size: 7.5px;
  color: rgba(192,200,216,.4);
  letter-spacing: .5px;
}

.fh-mission-prompt {
  font-size: 8px;
  color: rgba(192,200,216,.75);
  margin: 1px 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.fh-mission-score {
  font-size: 7.5px;
  letter-spacing: .5px;
}

.fh-mission-score.score-ok  { color: #00ff88; }
.fh-mission-score.score-err { color: #ff4444; }
.fh-mission-score.score-run { color: #ffd700; }

/* ── Logs ────────────────────────────────────────────────── */

#fh-live-log {
  max-height: 80px;
  overflow-y: auto;
  font-size: 7.5px;
  color: rgba(192,200,216,.55);
  scrollbar-width: thin;
  scrollbar-color: rgba(192,200,216,.15) transparent;
}

#fh-log {
  max-height: 70px;
  overflow-y: auto;
  font-size: 7.5px;
  color: rgba(192,200,216,.55);
  scrollbar-width: thin;
  scrollbar-color: rgba(192,200,216,.15) transparent;
}

.fh-log-line {
  padding: 1px 0;
  line-height: 1.4;
}

.fh-log-line.ok   { color: #00ff88; }
.fh-log-line.err  { color: #ff4444; }
.fh-log-line.warn { color: #ffd700; }

.fh-log-ts {
  color: rgba(192,200,216,.3);
  margin-right: 4px;
  font-size: 7px;
}
`;
  document.head.appendChild(s);
}

// ════════════════════════════════════════════════════════════════════════════
// ForgeHub class
// ════════════════════════════════════════════════════════════════════════════

export class ForgeHub {
  constructor() {
    this._expanded       = true;
    this._destroyed      = false;
    this._lastMissionId  = null;
    this._stopPoll       = false;
    this._polling        = false;   // true quand _pollForgeMission tourne activement
    this._watchTimer     = null;

    _injectStyle();
    this._build();
    this._bindEvents();
    // Auto-reprend une mission en cours au démarrage
    this._autoResumeMission();
    // Surveille les nouvelles missions lancées depuis Pipeline HUB ou chat
    this._startMissionWatch();
  }

  // ── Build DOM ──────────────────────────────────────────────────────────────

  _build() {
    this.el = document.createElement('div');
    this.el.id        = 'fhub';
    this.el.className = 'expanded';

    // Génère le HTML des 11 étapes pipeline
    const stepsHtml = FORGE_STEPS.map(s => `
      <div id="fh-fstep-${s.key}" class="fh-fstep">
        <span class="fh-fstep-ico">${s.icon}</span>
        <span class="fh-fstep-label">${s.label}</span>
        <span class="fh-fstep-badge">PENDING</span>
      </div>`).join('');

    // Génère le HTML de la grille pipelines
    const pipelinesHtml = FORGE_PIPELINES.map(p => `
      <button class="fh-pipe-btn" id="fhb-${p.id}" data-id="${p.id}">
        <span class="fh-pipe-ico">${p.icon}</span>
        <span>${p.label}</span>
      </button>`).join('');

    this.el.innerHTML = `
      <!-- Header -->
      <div class="fh-bar" id="fh-bar">
        <div class="fh-icon">⬡</div>
        <div class="fh-label">FORGE HUB</div>
        <div class="fh-activity" id="fh-activity">
          <div class="fh-adot"></div>
          <div class="fh-adot"></div>
          <div class="fh-adot"></div>
        </div>
        <div class="fh-score" id="fh-score">—</div>
        <button class="fh-ctrl" id="fh-expand" title="Réduire/Agrandir">▼</button>
      </div>

      <!-- Body -->
      <div class="fh-body">

        <!-- 1. VIP STL_PIPELINE button -->
        <div class="fh-section fh-vip-section">
          <button class="fh-vip-btn" id="fh-stl-btn">
            <span class="fh-vip-icon">⬡</span>
            <div class="fh-vip-text">
              <span class="fh-vip-name">STL_PIPELINE</span>
              <span class="fh-vip-sub">MESHY AI · TRIMESH · BAMBU</span>
            </div>
          </button>
          <div class="fh-stl-wrap" id="fh-stl-wrap" style="display:none">
            <textarea id="fh-stl-prompt" rows="2"
              placeholder="dragon low-poly 15cm · boitier · engrenage..."></textarea>
            <div class="fh-stl-row">
              <button id="fh-stl-go">▶ LANCER</button>
              <button id="fh-stl-cancel">✕</button>
            </div>
            <div class="fh-stl-status" id="fh-stl-status"></div>
          </div>
        </div>

        <!-- 2. FORGE PIPELINES grid -->
        <div class="fh-section">
          <div class="fh-hdr">FORGE PIPELINES</div>
          <div class="fh-pipelines" id="fh-pipelines">
            ${pipelinesHtml}
          </div>
        </div>

        <!-- 3. PIPELINE STATUS — 11 étapes -->
        <div class="fh-section">
          <div class="fh-hdr">PIPELINE STATUS</div>
          <div class="fh-steps" id="fh-steps">
            ${stepsHtml}
          </div>
        </div>

        <!-- 4. METRICS (masqué jusqu'à mission complète) -->
        <div class="fh-section">
          <div id="fh-forge-metrics">
            <div class="fhm-score-box">
              <div id="fh-score-val">—</div>
              <div id="fh-grade">SCORE</div>
            </div>
            <div class="fhm-meta-box">
              <div class="fhm-row"><span>PAROIS</span>    <span class="fhm-val" id="fhm-wall">—</span></div>
              <div class="fhm-row"><span>SURPLOMBS</span> <span class="fhm-val" id="fhm-oh">—</span></div>
              <div class="fhm-row"><span>MATIÈRE</span>   <span class="fhm-val" id="fhm-mat">—</span></div>
              <div class="fhm-row"><span>TEMPS EST.</span><span class="fhm-val" id="fhm-time">—</span></div>
            </div>
            <button id="fh-bambu" title="Ouvrir dans Bambu Studio">▶ BAMBU STUDIO</button>
          </div>
        </div>

        <!-- 5. MISSIONS RÉCENTES -->
        <div class="fh-section">
          <div class="fh-hdr">MISSIONS RÉCENTES</div>
          <div id="fh-missions">
            <div class="fh-log-line" style="opacity:.4">Chargement...</div>
          </div>
        </div>

        <!-- 6. LOG FORGE live (poll) -->
        <div class="fh-section">
          <div class="fh-hdr">LOG FORGE</div>
          <div id="fh-live-log"></div>
        </div>

        <!-- 7. LOG général actions -->
        <div class="fh-section fh-section-last">
          <div class="fh-hdr">LOG</div>
          <div id="fh-log"></div>
        </div>

      </div>`;

    document.body.appendChild(this.el);
  }

  // ── Events ─────────────────────────────────────────────────────────────────

  _bindEvents() {
    // Toggle collapse
    this.el.querySelector('#fh-expand').addEventListener('click', e => {
      e.stopPropagation();
      this._toggle();
    });
    // Clic sur la bar aussi toggle
    this.el.querySelector('#fh-bar').addEventListener('click', () => this._toggle());

    // VIP STL button
    this.el.querySelector('#fh-stl-btn').addEventListener('click', e => {
      e.stopPropagation();
      if (!this.el.querySelector('#fh-stl-btn').disabled) this._toggleSTLPrompt();
    });

    // STL Go / Cancel
    this.el.querySelector('#fh-stl-go').addEventListener('click', () => this._launchSTL());
    this.el.querySelector('#fh-stl-cancel').addEventListener('click', () => this._hideSTLPrompt());
    this.el.querySelector('#fh-stl-prompt').addEventListener('keydown', e => {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); this._launchSTL(); }
    });

    // Pipeline grid
    this.el.querySelector('#fh-pipelines').addEventListener('click', e => {
      const btn = e.target.closest('.fh-pipe-btn');
      if (!btn || btn.disabled) return;
      const id = btn.dataset.id;
      const map = {
        'forge-analytics': () => this._runForgeAnalytics(),
        'stl-sync':        () => this._runSTLSync(),
        'forge-report':    () => this._runForgeReport(),
        'stl-research':    () => this._runSTLResearch(),
      };
      map[id]?.();
    });

    // Bambu button
    this.el.querySelector('#fh-bambu').addEventListener('click', () => this._openBambu());
  }

  // ── Toggle panel ────────────────────────────────────────────────────────────

  _toggle() {
    this._expanded = !this._expanded;
    this.el.className = this._expanded ? 'expanded' : 'collapsed';
    this.el.querySelector('#fh-expand').textContent = this._expanded ? '▼' : '▲';
  }

  // ── STL Prompt helpers ──────────────────────────────────────────────────────

  _toggleSTLPrompt() {
    const wrap = this.el.querySelector('#fh-stl-wrap');
    const visible = wrap.style.display !== 'none';
    if (visible) {
      this._hideSTLPrompt();
    } else {
      wrap.style.display = 'flex';
      wrap.style.flexDirection = 'column';
      this.el.querySelector('#fh-stl-prompt').focus();
    }
  }

  _hideSTLPrompt() {
    const wrap = this.el.querySelector('#fh-stl-wrap');
    wrap.style.display = 'none';
    this.el.querySelector('#fh-stl-prompt').value = '';
    this._q('#fh-stl-status').textContent = '';
  }

  // ── STL Launch ──────────────────────────────────────────────────────────────

  async _launchSTL() {
    const prompt = this.el.querySelector('#fh-stl-prompt').value.trim();
    if (!prompt) return;

    const statusEl = this._q('#fh-stl-status');
    const btn      = this._q('#fh-stl-btn');

    btn.disabled = true;
    btn.classList.add('running');
    statusEl.textContent = 'Lancement...';
    statusEl.style.color = 'rgba(192,200,216,.5)';

    // Réinitialise pipeline visuel
    this._resetForgeSteps();
    const metricsEl = this._q('#fh-forge-metrics');
    if (metricsEl) metricsEl.classList.remove('visible');
    const bambuBtn = this._q('#fh-bambu');
    if (bambuBtn) bambuBtn.style.display = 'none';

    this._log(`⬡ STL — "${prompt.slice(0, 50)}"`);

    try {
      const r = await fetch(`${BACKEND}/v1/forge/mission`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt }),
        signal: AbortSignal.timeout(30000),
      });

      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d = await r.json();
      const mid = d.mission_id || '?';
      this._lastMissionId = mid;

      // Arrête tout poll précédent
      this._stopPoll = true;
      await new Promise(res => setTimeout(res, 50));
      this._stopPoll = false;

      statusEl.textContent = `Mission ${mid} démarrée`;
      this._q('#fh-stl-prompt').value = '';

      // Lance le polling — save uniquement à la FIN dans _showForgeMetrics
      const liveLog = this._q('#fh-live-log');
      this._pollForgeMission(mid, liveLog, statusEl);
    } catch (e) {
      statusEl.textContent = `✗ Erreur: ${e.message}`;
      statusEl.style.color = '#ff4444';
      this._log(`✗ STL: ${e.message}`, 'err');
      btn.disabled = false;
      btn.classList.remove('running');
    }
  }

  // ── Pipeline steps ──────────────────────────────────────────────────────────

  _resetForgeSteps() {
    FORGE_STEPS.forEach(s => {
      const el = this._q(`#fh-fstep-${s.key}`);
      if (!el) return;
      el.style.color      = 'rgba(192,200,216,.25)';
      el.style.background = 'transparent';
      const badge = el.querySelector('.fh-fstep-badge');
      if (badge) badge.textContent = 'PENDING';
    });
  }

  _updateForgeStep(key, status) {
    const el = this._q(`#fh-fstep-${key}`);
    if (!el) return;
    const badge = el.querySelector('.fh-fstep-badge');

    if (status === 'running') {
      el.style.color      = '#ffd700';
      el.style.background = 'rgba(255,215,0,.07)';
      if (badge) badge.textContent = '▶ RUN';
    } else if (status === 'done' || status === 'completed') {
      el.style.color      = '#00ff88';
      el.style.background = 'rgba(0,255,136,.04)';
      if (badge) badge.textContent = '✓ DONE';
    } else if (status === 'failed') {
      el.style.color      = '#ff4444';
      el.style.background = 'rgba(255,68,68,.07)';
      if (badge) badge.textContent = '✗ FAIL';
    } else {
      el.style.color      = 'rgba(192,200,216,.25)';
      el.style.background = 'transparent';
      if (badge) badge.textContent = 'PENDING';
    }
  }

  // ── Metrics ─────────────────────────────────────────────────────────────────

  _showForgeMetrics(d) {
    const report = d.report || {};
    const score  = report.printability_score ?? null;
    const grade  = report.printability_grade ?? _scoreGrade(score);
    const color  = _gradeColor(grade);
    const ready  = report.bambu_ready;

    // Score box
    const scoreEl = this._q('#fh-score-val');
    const gradeEl = this._q('#fh-grade');
    if (scoreEl) { scoreEl.textContent = score != null ? `${score}/100` : '—'; scoreEl.style.color = color; }
    if (gradeEl) { gradeEl.textContent = `GRADE ${grade}`; gradeEl.style.color = color; }

    // Header score
    const hScore = this._q('#fh-score');
    if (hScore) { hScore.textContent = score != null ? `${score}` : '—'; hScore.style.color = color; }

    // Meta
    const set = (id, val) => { const e = this._q(id); if (e) e.textContent = val ?? '—'; };
    set('#fhm-wall', report.wall_thickness_min_mm  != null ? `${report.wall_thickness_min_mm}mm` : '—');
    set('#fhm-oh',   report.overhang_pct            != null ? `${report.overhang_pct}%`           : '—');
    set('#fhm-mat',  report.estimated_material_g    != null ? `${report.estimated_material_g}g`   : '—');
    set('#fhm-time', report.estimated_print_time_str ?? '—');

    // Affiche metrics
    const metricsEl = this._q('#fh-forge-metrics');
    if (metricsEl) metricsEl.classList.add('visible');

    // Bambu button
    const bambuBtn = this._q('#fh-bambu');
    if (bambuBtn && ready) { bambuBtn.style.display = 'block'; }

    // Log live — résumé
    const liveLog = this._q('#fh-live-log');
    if (liveLog) {
      const readyTxt = ready ? '✓ BAMBU READY' : '⚠ Non prêt';
      liveLog.innerHTML += `
        <div class="fh-log-line ok" style="font-weight:700;margin-top:3px">
          ⬡ MISSION COMPLETE — ${score ?? '?'}/100 Grade: ${grade} — ${readyTxt}
        </div>
        <div class="fh-log-line" style="opacity:.65">
          Parois: ${report.wall_thickness_min_mm ?? '?'}mm | OH: ${report.overhang_pct ?? '?'}% | ${report.estimated_material_g ?? '?'}g | ${report.estimated_print_time_str ?? '?'}
        </div>`;
      liveLog.scrollTop = liveLog.scrollHeight;
    }

    // ── 1 seule save à la fin — rapport complet avec score + métriques
    this._saveToFolder('stl_completed', {
      mission_id:  this._lastMissionId,
      completed_at: new Date().toISOString(),
      score, grade,
      bambu_ready: ready,
      wall_mm:     report.wall_thickness_min_mm,
      overhang_pct: report.overhang_pct,
      material_g:  report.estimated_material_g,
      print_time:  report.estimated_print_time_str,
    });
  }

  // ── Missions list ────────────────────────────────────────────────────────────

  _renderMissions(missions) {
    const el = this._q('#fh-missions');
    if (!el) return;
    if (!missions.length) {
      el.innerHTML = '<div class="fh-log-line" style="opacity:.4">Aucune mission</div>';
      return;
    }
    el.innerHTML = missions.slice(0, 5).map(m => {
      const score  = m.score ?? null;
      const grade  = _scoreGrade(score);
      const gColor = _gradeColor(grade);
      const cls    = m.status === 'completed' ? 'score-ok' : m.status === 'failed' ? 'score-err' : 'score-run';
      const gradeTag = score != null
        ? `<span style="font-size:10px;font-weight:900;color:${gColor};margin-left:4px">${grade}</span>`
        : '';
      return `
        <div class="fh-mission-item">
          <div class="fh-mission-id">${_fhEsc(m.id)}</div>
          <div class="fh-mission-prompt">${_fhEsc((m.prompt || '').slice(0, 60))}</div>
          <span class="fh-mission-score ${cls}">
            ${_fhEsc(m.status?.toUpperCase() || '')}${score != null ? ` · ${score}/100` : ''}${gradeTag}
          </span>
        </div>`;
    }).join('');
  }

  // ── Poll mission ─────────────────────────────────────────────────────────────
  // Logique exacte de forge_room_planet._pollMissionLogs :
  // 180 itérations × 2500ms = 7.5min max, stop sur completed/failed/404×3

  async _pollForgeMission(missionId, liveLog, statusEl) {
    this._polling = true;
    let errors    = 0;
    let errors404 = 0;

    for (let i = 0; i < 180; i++) {
      await new Promise(res => setTimeout(res, 2500));
      if (this._stopPoll) break;

      try {
        const r = await fetch(`${BACKEND}/v1/forge/mission/${missionId}`,
          { signal: AbortSignal.timeout(8000) });

        // 3 polls 404 consécutifs → mission introuvable
        if (r.status === 404) {
          errors404++;
          if (errors404 >= 3) {
            if (liveLog) {
              liveLog.innerHTML += `<div class="fh-log-line warn">⚠ Mission introuvable — backend redémarré ?</div>`;
              liveLog.scrollTop = liveLog.scrollHeight;
            }
            if (statusEl) statusEl.textContent = '⚠ Mission introuvable — backend redémarré ?';
            // Libère le VIP btn
            const vipBtn = this._q('#fh-stl-btn');
            if (vipBtn) { vipBtn.disabled = false; vipBtn.classList.remove('running'); }
            break;
          }
          errors++;
          if (errors > 6) break;
          continue;
        }
        errors404 = 0;

        if (!r.ok) { errors++; if (errors > 6) break; continue; }
        errors = 0;

        const d = await r.json();
        if (this._stopPoll) break;

        // Mise à jour étapes pipeline
        if (d.steps && typeof d.steps === 'object') {
          FORGE_STEPS.forEach(s => {
            if (d.steps[s.key] !== undefined) {
              this._updateForgeStep(s.key, d.steps[s.key]);
            }
          });
        }

        // Log live — 8 dernières lignes
        if (liveLog) {
          const logs = (d.logs || []).slice(-8);
          liveLog.innerHTML = logs.map(l => {
            const cls = l.level === 'success' ? 'ok'
                      : l.level === 'error'   ? 'err'
                      : l.level === 'warning' ? 'warn' : '';
            return `<div class="fh-log-line ${cls}">[${_fhEsc(l.ts)}] ${_fhEsc(l.msg)}</div>`;
          }).join('');
          liveLog.scrollTop = liveLog.scrollHeight;
        }

        if (d.status === 'completed') {
          this._showForgeMetrics(d);

          // ── Auto-open Bambu Studio avec le STL ──────────────
          const stlFile = d.files?.jarvis_stl || d.files?.model;
          if (stlFile) {
            this._log(`▶ Ouverture Bambu Studio — ${d.files?.jarvis_stl_name || 'STL'}`, 'ok');
            fetch(`${BACKEND}/v1/forge/bambu/${missionId}`, { method: 'POST' })
              .then(r => r.json())
              .then(bd => this._log(bd.ok !== false ? '✓ Bambu ouvert' : `⚠ Bambu: ${bd.detail || 'vérifier le chemin'}`, bd.ok !== false ? 'ok' : 'warn'))
              .catch(() => this._log('⚠ Bambu Studio introuvable — vérifier BAMBU_STUDIO_PATH dans .env', 'warn'));
          }

          // Libère le VIP btn
          const vipBtn = this._q('#fh-stl-btn');
          if (vipBtn) { vipBtn.disabled = false; vipBtn.classList.remove('running'); }

          // Refresh liste missions après 1.2s
          setTimeout(async () => {
            if (this._stopPoll) return;
            try {
              const rm = await fetch(`${BACKEND}/v1/forge/missions`, { signal: AbortSignal.timeout(4000) });
              if (rm.ok) { const dm = await rm.json(); this._renderMissions(dm.missions || []); }
            } catch {}
          }, 1200);
          break;
        }

        if (d.status === 'failed') {
          if (statusEl) {
            statusEl.textContent = `✗ Echec: ${d.error || 'pipeline error'}`;
            statusEl.style.color = '#ff4444';
          }
          this._log(`✗ Mission ${missionId} — ${d.error || 'échec'}`, 'err');
          const vipBtn = this._q('#fh-stl-btn');
          if (vipBtn) { vipBtn.disabled = false; vipBtn.classList.remove('running'); }
          break;
        }

      } catch { errors++; if (errors > 5) break; }
    }
    this._polling = false; // libère le mission watch
  }

  // ── Mission watch — détecte les missions lancées depuis Pipeline HUB / chat ──

  _startMissionWatch() {
    // Poll toutes les 5s — détecte les missions lancées depuis Pipeline HUB ou chat
    this._watchTimer = setInterval(async () => {
      if (this._destroyed || this._polling) return; // skip si déjà en train de tracker
      try {
        const r = await fetch(`${BACKEND}/v1/forge/missions`, { signal: AbortSignal.timeout(3000) });
        if (!r.ok) return;
        const d = await r.json();
        const running = (d.missions || []).find(m => m.status === 'running');
        if (!running) return;
        if (running.id === this._lastMissionId) return; // déjà connu

        // Nouvelle mission running détectée — reprendre le tracking
        const mid = running.id;
        this._lastMissionId = mid;
        this._stopPoll = false;

        const statusEl = this._q('#fh-stl-status');
        const liveLog  = this._q('#fh-live-log');
        if (statusEl) statusEl.textContent = `⬡ Mission ${mid} détectée`;
        if (liveLog)  liveLog.innerHTML = `<div class="fh-ll">[AUTO] Pipeline HUB → Forge HUB · Mission ${mid}</div>`;

        const wrap = this._q('#fh-stl-wrap');
        if (wrap) wrap.style.display = 'flex';
        const vipBtn = this._q('#fh-stl-btn');
        if (vipBtn) { vipBtn.disabled = true; vipBtn.classList.add('running'); }

        this._resetForgeSteps();
        this._pollForgeMission(mid, liveLog, statusEl);
      } catch {}
    }, 5000);
  }

  // ── Auto-resume mission en cours ─────────────────────────────────────────────

  async _autoResumeMission() {
    if (this._stopPoll) return;
    try {
      const r = await fetch(`${BACKEND}/v1/forge/missions`, { signal: AbortSignal.timeout(4000) });
      if (!r.ok) return;
      const d = await r.json();

      // Charge les missions récentes dans la liste
      this._renderMissions(d.missions || []);

      // Cherche une mission running
      const running = (d.missions || []).find(m => m.status === 'running');
      if (!running) return;

      const mid = running.id;
      this._lastMissionId = mid;

      this._resetForgeSteps();
      const metricsEl = this._q('#fh-forge-metrics');
      if (metricsEl) metricsEl.classList.remove('visible');
      const bambuBtn = this._q('#fh-bambu');
      if (bambuBtn) bambuBtn.style.display = 'none';

      const statusEl = this._q('#fh-stl-status');
      if (statusEl) statusEl.textContent = `⬡ Mission ${mid} en cours (reprise auto)`;

      const liveLog = this._q('#fh-live-log');
      if (liveLog) liveLog.innerHTML = `<div class="fh-log-line">[AUTO] Reprise mission ${mid}...</div>`;

      // Montre le prompt
      const wrap = this._q('#fh-stl-wrap');
      if (wrap) { wrap.style.display = 'flex'; wrap.style.flexDirection = 'column'; }
      const vipBtn = this._q('#fh-stl-btn');
      if (vipBtn) { vipBtn.disabled = true; vipBtn.classList.add('running'); }

      this._pollForgeMission(mid, liveLog, statusEl);
    } catch {}
  }

  // ── Bambu ─────────────────────────────────────────────────────────────────────

  async _openBambu() {
    if (!this._lastMissionId) return;
    const btn = this._q('#fh-bambu');
    if (btn) { btn.textContent = '⏳ OUVERTURE...'; btn.disabled = true; }
    try {
      const r = await fetch(`${BACKEND}/v1/forge/bambu/${this._lastMissionId}`, { method: 'POST' });
      if (r.ok) {
        const d = await r.json();
        if (btn) { btn.textContent = '✓ BAMBU OUVERT'; }
        this._log(`▶ Bambu lancé: ${d.file || ''}`, 'ok');
      } else {
        const e = await r.json().catch(() => ({}));
        if (btn) { btn.textContent = '▶ BAMBU STUDIO'; btn.disabled = false; }
        this._log(`✗ Bambu HTTP ${r.status}: ${e.detail || ''}`, 'err');
      }
    } catch (e) {
      if (btn) { btn.textContent = '▶ BAMBU STUDIO'; btn.disabled = false; }
      this._log(`✗ Bambu: ${e.message}`, 'err');
    }
  }

  // ── Forge Analytics ──────────────────────────────────────────────────────────

  async _runForgeAnalytics() {
    this._log('◆ FORGE ANALYTICS — analyse...');
    this._busy('forge-analytics', true);
    try {
      const r = await fetch(`${BACKEND}/v1/daily/run-task`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task: 'forge_analytics' }),
        signal: AbortSignal.timeout(60000),
      });
      const d = await r.json();
      this._log(`◆ Analytics: ${(d.result || d.message || 'OK').toString().slice(0, 100)}`);
      await this._saveToFolder('forge_analytics', d);
    } catch (e) {
      this._log(`✗ Analytics: ${e.message}`, 'err');
    } finally {
      this._busy('forge-analytics', false);
    }
  }

  // ── STL Sync ─────────────────────────────────────────────────────────────────

  async _runSTLSync() {
    this._log('⬢ STL SYNC — synchronisation...');
    this._busy('stl-sync', true);
    try {
      const r = await fetch(`${BACKEND}/v1/daily/run-task`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task: 'stl_sync' }),
        signal: AbortSignal.timeout(60000),
      });
      const d = await r.json();
      this._log(`⬢ STL Sync: ${(d.result || d.message || 'OK').toString().slice(0, 100)}`);
    } catch (e) {
      this._log(`✗ STL Sync: ${e.message}`, 'err');
    } finally {
      this._busy('stl-sync', false);
    }
  }

  // ── Forge Report ─────────────────────────────────────────────────────────────

  async _runForgeReport() {
    this._log('▣ FORGE REPORT — génération...');
    this._busy('forge-report', true);
    try {
      const r = await fetch(`${BACKEND}/v1/reports/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: 'Forge Report', agent: 'KAIZEN' }),
        signal: AbortSignal.timeout(30000),
      });
      const d = await r.json();
      this._log(`▣ Rapport Forge: ${d.filename || 'généré'}`);
      await this._saveToFolder('forge_report', d);
    } catch (e) {
      this._log(`✗ Forge Report: ${e.message}`, 'err');
    } finally {
      this._busy('forge-report', false);
    }
  }

  // ── STL Research ─────────────────────────────────────────────────────────────

  async _runSTLResearch() {
    this._log('◑ STL RESEARCH — QWEN local...');
    this._busy('stl-research', true);
    try {
      const r = await fetch(`${BACKEND}/task`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent: 'QWEN',
          task: 'Recherche tendances 3D print du jour: Thingiverse, Cults3D, Etsy. Top 5 idées pour D3Dprintix.',
        }),
        signal: AbortSignal.timeout(120000),
      });
      const d = await r.json();
      this._log(`◑ Research: ${(d.result || d.response || 'OK').toString().slice(0, 100)}`);
      await this._saveToFolder('stl_research', d);
    } catch (e) {
      this._log(`✗ STL Research: ${e.message}`, 'err');
    } finally {
      this._busy('stl-research', false);
    }
  }

  // ── Save to folder ────────────────────────────────────────────────────────────

  async _saveToFolder(type, data) {
    try {
      await fetch(`${BACKEND}/v1/report/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type, data }),
        signal: AbortSignal.timeout(10000),
      });
    } catch {
      // Non-bloquant — silencieux
    }
  }

  // ── Helpers ───────────────────────────────────────────────────────────────────

  /** Scoped querySelector */
  _q(selector) {
    return this.el?.querySelector(selector) ?? null;
  }

  /** Active/désactive un bouton pipeline avec préfixe fhb- */
  _busy(id, on) {
    const btn = this._q(`#fhb-${id}`);
    if (!btn) return;
    btn.disabled = on;
    btn.classList.toggle('running', on);
  }

  /** Ajoute une ligne dans le log général #fh-log (max 30 lignes) */
  _log(text, type = '') {
    const log = this._q('#fh-log');
    if (!log) return;
    const n  = new Date();
    const ts = [n.getHours(), n.getMinutes()].map(x => String(x).padStart(2, '0')).join(':');
    const el = document.createElement('div');
    el.className = `fh-log-line${type ? ' ' + type : ''}`;
    el.innerHTML = `<span class="fh-log-ts">${ts}</span> ${_fhEsc(text)}`;
    log.appendChild(el);
    const lines = log.querySelectorAll('.fh-log-line');
    if (lines.length > 30) lines[0].remove();
    log.scrollTop = log.scrollHeight;
    // Pulse activity dots
    const act = this._q('#fh-activity');
    act?.classList.add('live');
    setTimeout(() => act?.classList.remove('live'), 1500);
  }

  destroy() {
    if (this._destroyed) return;
    this._destroyed = true;
    this._stopPoll  = true;
    if (this._watchTimer) clearInterval(this._watchTimer);
    this.el?.remove();
    this.el = null;
  }
}
