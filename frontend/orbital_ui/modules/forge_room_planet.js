/**
 * Forge Room Planet — connects to existing /v1/forge/* endpoints.
 * No pipeline logic here — just UI that calls the existing Forge Room.
 */
const BACKEND = 'http://localhost:8000';

// 11 étapes du pipeline STL
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

// Calcule le grade A/B/C/D à partir du score numérique
function _scoreToGrade(score) {
  if (score == null || score === '—') return '—';
  const n = Number(score);
  if (n >= 90) return 'A';
  if (n >= 75) return 'B';
  if (n >= 60) return 'C';
  return 'D';
}

// Couleur CSS selon le grade
function _gradeColor(grade) {
  if (grade === 'A') return '#00ff88';
  if (grade === 'B') return '#00d4ff';
  if (grade === 'C') return '#ffd700';
  return '#ff4444';
}

const _FORGE_BACKEND = 'http://localhost:8000';

export const FORGE_CONFIG = {
  id: 'forge', icon: '🔧', name: 'THE FORGE ROOM',
  sub: 'FABRICATION INDUSTRIELLE FDM',
  color: 'var(--forge)', glow: 'rgba(255,107,53,.5)',
  orbitRadius: 220, speed: 0.18, size: 68,
  pollInterval: 0,
  renderer: {
    startPolling: false,

    async render(body) {
      // Charge les missions récentes
      let missions = [];
      try {
        const r = await fetch(`${_FORGE_BACKEND}/v1/forge/missions`, { signal: AbortSignal.timeout(4000) });
        if (r.ok) missions = (await r.json()).missions || [];
      } catch {}

      const missionRows = missions.slice(0, 5).map(m => {
        const score = m.score ?? m.report?.printability_score ?? null;
        const grade = score == null ? '' : score >= 90 ? 'A' : score >= 75 ? 'B' : score >= 60 ? 'C' : 'D';
        const color = grade === 'A' ? '#00ff88' : grade === 'B' ? '#c0c8d8' : grade === 'C' ? '#ffd700' : '#ff4444';
        const cls   = m.status === 'completed' ? '#00ff88' : m.status === 'failed' ? '#ff4444' : '#ffd700';
        return `<div class="panel-mission">
          <div class="panel-mission-id" style="color:rgba(255,107,53,.6)">${(m.id||'').slice(0,10)}</div>
          <div class="panel-mission-prompt">${(m.prompt||'').slice(0,55)}</div>
          <span class="panel-mission-score" style="color:${cls}">
            ${(m.status||'').toUpperCase()}${score!=null?` · ${score}/100`:''}
            ${grade?`<b style="color:${color};margin-left:3px">${grade}</b>`:''}
          </span>
        </div>`;
      }).join('') || '<div class="log-line" style="opacity:.4">Aucune mission</div>';

      body.innerHTML = `
        <div class="panel-section-title">NOUVELLE MISSION STL</div>
        <textarea class="panel-input" id="fp-prompt" rows="2"
          placeholder="dragon low-poly 15cm · boitier Arduino · engrenage FDM..."></textarea>
        <div style="display:flex;gap:6px;margin-top:6px">
          <button class="panel-btn" id="fp-launch" style="flex:1;border-color:rgba(255,107,53,.5);color:#ff6b35">
            ⬡ LANCER STL PIPELINE
          </button>
        </div>
        <div id="fp-status" style="font-size:9px;color:rgba(255,107,53,.6);min-height:14px;margin-top:4px"></div>

        <div class="panel-section-title" style="margin-top:10px">MISSIONS RÉCENTES</div>
        <div id="fp-missions" class="panel-log">${missionRows}</div>

        <div style="margin-top:12px;padding:8px;background:rgba(255,107,53,.04);border:1px solid rgba(255,107,53,.15);border-radius:6px;font-size:8px;color:rgba(255,107,53,.5);letter-spacing:.5px;text-align:center">
          ⬡ FORGE HUB (bas-droit) — suivi live des étapes pipeline
        </div>`;

      const btn    = body.querySelector('#fp-launch');
      const prompt = body.querySelector('#fp-prompt');
      const status = body.querySelector('#fp-status');

      btn.addEventListener('click', async () => {
        const txt = prompt.value.trim();
        if (!txt) { status.textContent = 'Décris ton objet 3D d\'abord.'; return; }
        btn.disabled = true;
        status.textContent = 'Lancement...';
        try {
          const r = await fetch(`${_FORGE_BACKEND}/v1/forge/mission`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt: txt }),
          });
          const d  = await r.json();
          const mid = d.mission_id || '?';
          status.textContent = `⬡ Mission ${mid} démarrée → suivi dans Forge Hub ↘`;
          status.style.color  = '#00ff88';
          prompt.value = '';
          // Refresh missions list
          setTimeout(() => this.refresh(body), 2000);
        } catch (e) {
          status.textContent = `✗ ${e.message}`;
          status.style.color = '#ff4444';
        } finally {
          btn.disabled = false;
        }
      });

      prompt.addEventListener('keydown', e => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); btn.click(); }
      });
    },

    async refresh(body) {
      try {
        const r = await fetch(`${_FORGE_BACKEND}/v1/forge/missions`, { signal: AbortSignal.timeout(4000) });
        if (!r.ok) return;
        const d = await r.json();
        const el = body.querySelector('#fp-missions');
        if (!el) return;
        const missions = (d.missions || []).slice(0, 5);
        el.innerHTML = missions.map(m => {
          const score = m.score ?? null;
          const cls   = m.status === 'completed' ? '#00ff88' : m.status === 'failed' ? '#ff4444' : '#ffd700';
          return `<div class="panel-mission">
            <div class="panel-mission-id" style="color:rgba(255,107,53,.6)">${(m.id||'').slice(0,10)}</div>
            <div class="panel-mission-prompt">${(m.prompt||'').slice(0,55)}</div>
            <span class="panel-mission-score" style="color:${cls}">${(m.status||'').toUpperCase()}${score!=null?` · ${score}/100`:''}</span>
          </div>`;
        }).join('') || '<div class="log-line" style="opacity:.4">Aucune mission</div>';
      } catch {}
    },

    destroy() {},
  },
};

// Module logic namespace
const forge_room_planet = {
  _lastMissionId: null,
  _stopPoll: false,

  buildSkeleton() {
    // Rendu des 11 étapes en attente
    const stepsHtml = FORGE_STEPS.map(s => `
      <div id="fstep-${s.key}" style="display:flex;align-items:center;gap:5px;padding:2px 4px;border-radius:3px;font-size:8px;letter-spacing:.5px;color:rgba(255,255,255,.25)">
        <span style="width:12px;text-align:center">${s.icon}</span>
        <span style="flex:1">${s.label}</span>
        <span class="fstep-status">PENDING</span>
      </div>`).join('');

    return `
      <div class="panel-section-title">NOUVELLE MISSION FORGE</div>
      <textarea class="panel-input" id="forge-prompt" rows="2"
        placeholder="dragon low-poly / boitier / engrenage..."></textarea>
      <div style="display:flex;gap:6px;margin-top:6px">
        <button class="panel-btn" id="forge-launch" style="flex:1">⬡ LANCER</button>
        <button class="panel-btn" id="forge-bambu" style="display:none;border-color:rgba(0,255,136,.4);color:#00ff88" onclick="forge_room_planet._openBambu()">▶ BAMBU</button>
      </div>
      <div id="forge-launch-status" style="font-size:9px;color:rgba(0,212,255,.5);min-height:14px;margin-top:3px"></div>

      <div class="panel-section-title" style="margin-top:8px">PIPELINE STATUS</div>
      <div id="forge-steps-live" style="display:flex;flex-direction:column;gap:2px;overflow-y:auto;max-height:160px;">${stepsHtml}</div>

      <div id="forge-metrics" style="display:none;gap:8px;margin-top:8px;flex-wrap:wrap">
        <div style="flex:1;background:rgba(0,0,0,.3);border:1px solid rgba(255,255,255,.06);border-radius:6px;padding:8px;text-align:center">
          <div id="forge-score-val" style="font-size:22px;font-weight:900;color:#ffd700;font-family:Orbitron,monospace">—</div>
          <div id="forge-grade" style="font-size:9px;letter-spacing:2px;color:rgba(255,255,255,.4)">SCORE</div>
        </div>
        <div style="flex:1;background:rgba(0,0,0,.3);border:1px solid rgba(255,255,255,.06);border-radius:6px;padding:8px">
          <div class="panel-metric" style="border:none;padding:2px 0"><span class="panel-metric-label">PAROIS</span><span class="panel-metric-value" id="fm-wall">—</span></div>
          <div class="panel-metric" style="border:none;padding:2px 0"><span class="panel-metric-label">SURPLOMBS</span><span class="panel-metric-value" id="fm-oh">—</span></div>
          <div class="panel-metric" style="border:none;padding:2px 0"><span class="panel-metric-label">MATIÈRE</span><span class="panel-metric-value" id="fm-mat">—</span></div>
          <div class="panel-metric" style="border:none;padding:2px 0"><span class="panel-metric-label">TEMPS EST.</span><span class="panel-metric-value" id="fm-time">—</span></div>
        </div>
      </div>

      <div class="panel-section-title" style="margin-top:8px">MISSIONS RÉCENTES</div>
      <div id="forge-missions" class="panel-log">Chargement...</div>

      <div class="panel-section-title">LOG LIVE</div>
      <div id="forge-live-log" class="panel-log" style="max-height:90px;font-size:8px"></div>`;
  },

  async _bindActions(body) {
    const btn     = body.querySelector('#forge-launch');
    const prompt  = body.querySelector('#forge-prompt');
    const status  = body.querySelector('#forge-launch-status');
    const liveLog = body.querySelector('#forge-live-log');

    btn.addEventListener('click', async () => {
      const txt = prompt.value.trim();
      if (!txt) return;
      btn.disabled = true;
      status.textContent = 'Lancement...';

      // Réinitialise le pipeline visuel
      this._resetSteps(body);

      // Cache métriques et bouton Bambu
      const metricsEl = body.querySelector('#forge-metrics');
      const bambuBtn  = body.querySelector('#forge-bambu');
      if (metricsEl) metricsEl.style.display = 'none';
      if (bambuBtn)  bambuBtn.style.display = 'none';

      try {
        const r = await fetch(`${BACKEND}/v1/forge/mission`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: txt }),
        });
        const d = await r.json();
        const mid = d.mission_id || '?';
        this._lastMissionId = mid;
        // Arrête tout poll précédent avant d'en démarrer un nouveau
        this._stopPoll = true;
        status.textContent = `Mission ${mid} démarrée`;
        prompt.value = '';
        // Lance le polling avec mise à jour des étapes
        this._stopPoll = false;
        this._pollMissionLogs(mid, body, liveLog);
      } catch (e) {
        status.textContent = 'Erreur: ' + e.message;
      } finally {
        btn.disabled = false;
      }
    });
  },

  // Remet toutes les étapes en état "pending"
  _resetSteps(body) {
    FORGE_STEPS.forEach(s => {
      const el = body.querySelector(`#fstep-${s.key}`);
      if (!el) return;
      el.style.color = 'rgba(255,255,255,.25)';
      el.style.background = 'transparent';
      const statusSpan = el.querySelector('.fstep-status');
      if (statusSpan) statusSpan.textContent = 'PENDING';
    });
  },

  // Met à jour une ligne d'étape selon son statut
  _updateStep(body, key, stepStatus) {
    const el = body.querySelector(`#fstep-${key}`);
    if (!el) return;
    const statusSpan = el.querySelector('.fstep-status');

    if (stepStatus === 'running') {
      el.style.color = '#ffd700';
      el.style.background = 'rgba(255,215,0,.07)';
      if (statusSpan) statusSpan.textContent = '▶ RUN';
    } else if (stepStatus === 'done' || stepStatus === 'completed') {
      el.style.color = '#00ff88';
      el.style.background = 'rgba(0,255,136,.04)';
      if (statusSpan) statusSpan.textContent = '✓ DONE';
    } else if (stepStatus === 'failed') {
      el.style.color = '#ff4444';
      el.style.background = 'rgba(255,68,68,.07)';
      if (statusSpan) statusSpan.textContent = '✗ FAIL';
    } else {
      // pending
      el.style.color = 'rgba(255,255,255,.25)';
      el.style.background = 'transparent';
      if (statusSpan) statusSpan.textContent = 'PENDING';
    }
  },

  // Affiche le score, grade et métriques du rapport final
  _showMetrics(body, d) {
    // Champs exacts du manufacturing_report.py
    const report = d.report || {};
    const score  = report.printability_score ?? null;
    const grade  = report.printability_grade ?? _scoreToGrade(score);
    const color  = _gradeColor(grade);
    const ready  = report.bambu_ready;

    // ── Métriques panel ──
    const metricsEl = body.querySelector('#forge-metrics');
    if (metricsEl) {
      metricsEl.style.cssText = 'display:flex;gap:8px;margin-top:8px';  // reset complet
    }

    const scoreEl = body.querySelector('#forge-score-val');
    const gradeEl = body.querySelector('#forge-grade');
    if (scoreEl) { scoreEl.textContent = score != null ? `${score}/100` : '—'; scoreEl.style.color = color; }
    if (gradeEl) { gradeEl.textContent = `GRADE ${grade}`; gradeEl.style.color = color; }

    const set = (id, val) => { const e = body.querySelector(id); if (e) e.textContent = val ?? '—'; };
    set('#fm-wall', report.wall_thickness_min_mm  != null ? `${report.wall_thickness_min_mm}mm` : '—');
    set('#fm-oh',   report.overhang_pct            != null ? `${report.overhang_pct}%`           : '—');
    set('#fm-mat',  report.estimated_material_g    != null ? `${report.estimated_material_g}g`   : '—');
    set('#fm-time', report.estimated_print_time_str ?? '—');

    // ── Bouton Bambu ──
    const bambuBtn = body.querySelector('#forge-bambu');
    if (bambuBtn) { bambuBtn.style.display = 'block'; }

    // ── Résumé toujours visible dans le log ──
    const logEl = body.querySelector('#forge-live-log');
    if (logEl) {
      const readyTxt = ready ? '✓ BAMBU READY' : '⚠ Non prêt';
      logEl.innerHTML += [
        `<div class="log-line ok" style="font-weight:700;margin-top:4px">`,
        `⬡ MISSION COMPLETE — Score: ${score ?? '?'}/100 Grade: ${grade} — ${readyTxt}`,
        `</div>`,
        `<div class="log-line" style="opacity:.7">`,
        `Parois: ${report.wall_thickness_min_mm ?? '?'}mm | OH: ${report.overhang_pct ?? '?'}% | ${report.estimated_material_g ?? '?'}g | ${report.estimated_print_time_str ?? '?'}`,
        `</div>`,
        `<div class="log-line" style="color:#ffd700;margin-top:2px">`,
        ready ? `▶ Clique BAMBU STUDIO pour ouvrir dans Bambu Lab` : `⚠ STL généré mais corrections recommandées`,
        `</div>`,
      ].join('');
      logEl.scrollTop = logEl.scrollHeight;
    }

    // ── Status bar ──
    const statusEl = body.querySelector('#forge-launch-status');
    if (statusEl) {
      statusEl.textContent = `✓ Complété — ${score}/100 Grade ${grade} ${ready ? '· BAMBU READY' : ''}`;
      statusEl.style.color = color;
    }
  },

  _renderMissions(body, missions) {
    const el = body.querySelector('#forge-missions');
    if (!el) return;
    if (!missions.length) {
      el.innerHTML = '<div class="log-line" style="opacity:.4">Aucune mission</div>';
      return;
    }
    el.innerHTML = missions.slice(0, 5).map(m => {
      const score = m.score ?? null;
      const grade = _scoreToGrade(score);
      const gColor = _gradeColor(grade);
      const cls = m.status === 'completed' ? 'score-ok' : m.status === 'failed' ? 'score-err' : 'score-run';
      const gradeTag = score != null
        ? `<span style="font-size:11px;font-weight:900;color:${gColor};margin-left:4px">${grade}</span>`
        : '';
      return `
        <div class="panel-mission">
          <div class="panel-mission-id">${m.id}</div>
          <div class="panel-mission-prompt">${(m.prompt || '').slice(0, 60)}</div>
          <span class="panel-mission-score ${cls}">${m.status?.toUpperCase()} ${score != null ? `· ${score}/100` : ''}${gradeTag}</span>
        </div>`;
    }).join('');
  },

  // Détecte une mission en cours (lancée depuis le chat) et la reprend dans le panel
  async _autoResumeMission(body) {
    if (this._stopPoll) return;
    try {
      const r = await fetch(`${BACKEND}/v1/forge/missions`, { signal: AbortSignal.timeout(4000) });
      if (!r.ok) return;
      const d = await r.json();
      // Cherche la mission running la plus récente
      const running = (d.missions || []).find(m => m.status === 'running');
      if (!running) return;

      const mid = running.id;
      this._lastMissionId = mid;

      // Affiche le panel pipeline (comme si on avait cliqué LANCER)
      this._resetSteps(body);
      const metricsEl = body.querySelector('#forge-metrics');
      const bambuBtn  = body.querySelector('#forge-bambu');
      if (metricsEl) metricsEl.style.display = 'none';
      if (bambuBtn)  bambuBtn.style.display  = 'none';

      const statusEl = body.querySelector('#forge-launch-status');
      if (statusEl) statusEl.textContent = `⬡ Mission ${mid} en cours (lancée depuis le chat)`;

      const promptEl = body.querySelector('#forge-prompt');
      if (promptEl) promptEl.value = running.prompt || '';

      const liveLog = body.querySelector('#forge-live-log');
      if (liveLog) liveLog.innerHTML = `<div class="log-line">[AUTO] Reprise mission ${mid}...</div>`;

      // Lance le polling sur cette mission
      this._pollMissionLogs(mid, body, liveLog);
    } catch {}
  },

  async _pollMissionLogs(missionId, body, logEl) {
    let errors    = 0;
    let errors404 = 0;    // compteur 404 consécutifs (Task 7.4)
    for (let i = 0; i < 180; i++) {        // 180 × 2.5s = 7.5min max
      await new Promise(r => setTimeout(r, 2500));
      // Stop demandé (panneau fermé ou nouvelle mission lancée)
      if (this._stopPoll) break;
      try {
        const r = await fetch(`${BACKEND}/v1/forge/mission/${missionId}`,
          { signal: AbortSignal.timeout(8000) });

        // 3 polls 404 consécutifs → mission introuvable, arrêt
        if (r.status === 404) {
          errors404++;
          if (errors404 >= 3) {
            if (logEl) {
              logEl.innerHTML += `<div class="log-line warn">⚠ Mission introuvable — backend redémarré ?</div>`;
              logEl.scrollTop = logEl.scrollHeight;
            }
            const statusEl = body.querySelector('#forge-launch-status');
            if (statusEl) statusEl.textContent = '⚠ Mission introuvable — backend redémarré ?';
            break;
          }
          errors++; if (errors > 6) break; continue;
        }
        errors404 = 0;   // reset si pas 404

        if (!r.ok) { errors++; if (errors > 6) break; continue; }
        errors = 0;
        const d = await r.json();

        // Vérif stop après await (panneau a pu fermer pendant le fetch)
        if (this._stopPoll) break;

        // Étapes du pipeline — mise à jour live
        if (d.steps && typeof d.steps === 'object') {
          FORGE_STEPS.forEach(s => {
            if (d.steps[s.key] !== undefined) {
              this._updateStep(body, s.key, d.steps[s.key]);
            }
          });
        }

        // Log live — 8 dernières lignes
        const logs = (d.logs || []).slice(-8);
        logEl.innerHTML = logs.map(l => {
          const cls = l.level === 'success' ? 'ok' : l.level === 'error' ? 'err' : l.level === 'warning' ? 'warn' : '';
          return `<div class="log-line ${cls}">[${l.ts}] ${l.msg}</div>`;
        }).join('');
        logEl.scrollTop = logEl.scrollHeight;

        if (d.status === 'completed') {
          this._showMetrics(body, d);
          // Refresh liste missions après 1s
          setTimeout(() => { if (!this._stopPoll) this._renderMissions(body, []); }, 1000);
          setTimeout(async () => {
            if (this._stopPoll) return;
            try {
              const rm = await fetch(`${BACKEND}/v1/forge/missions`, { signal: AbortSignal.timeout(4000) });
              if (rm.ok) { const dm = await rm.json(); this._renderMissions(body, dm.missions || []); }
            } catch {}
          }, 1200);
          break;
        }
        if (d.status === 'failed') {
          const errEl = body.querySelector('#forge-launch-status');
          if (errEl) errEl.textContent = `Echec: ${d.error || 'pipeline error'}`;
          break;
        }
      } catch { errors++; if (errors > 5) break; }
    }
  },

  // Appelé par ModulePanel.close() pour stopper le poll proprement
  stopPoll() {
    this._stopPoll = true;
  },

  async _openBambu() {
    if (!this._lastMissionId) return;
    const btn = document.querySelector('#forge-bambu');
    if (btn) { btn.textContent = '⏳ OUVERTURE...'; btn.disabled = true; }
    try {
      const r = await fetch(`${BACKEND}/v1/forge/bambu/${this._lastMissionId}`, { method: 'POST' });
      if (r.ok) {
        const d = await r.json();
        if (btn) { btn.textContent = '✓ BAMBU OUVERT'; }
        console.log('[forge] Bambu launched:', d.file);
      } else {
        const e = await r.json().catch(() => ({}));
        if (btn) { btn.textContent = '▶ BAMBU'; btn.disabled = false; }
        console.error('[forge] Bambu HTTP', r.status, e.detail);
      }
    } catch (e) {
      if (btn) { btn.textContent = '▶ BAMBU'; btn.disabled = false; }
      console.error('[forge] Bambu error:', e);
    }
  },
};
