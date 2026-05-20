/**
 * ModulePanel — sliding panel that opens when a planet is clicked.
 * Renders module-specific content provided by each planet module.
 * Chaque planète a une image bannière unique en haut du panel.
 */

// Bannière CSS unique par planète (id → gradient)
const _BANNERS = {
  forge:     'radial-gradient(ellipse at 70% 40%, rgba(255,107,53,.7) 0%, rgba(180,60,10,.3) 40%, transparent 70%), linear-gradient(160deg, #120500 0%, #2a0d00 100%)',
  ultron:    'radial-gradient(ellipse at 30% 60%, rgba(139,92,246,.7) 0%, rgba(80,20,160,.3) 40%, transparent 70%), linear-gradient(160deg, #08001a 0%, #1a0035 100%)',
  vault:     'radial-gradient(ellipse at 50% 50%, rgba(0,212,255,.6) 0%, rgba(0,100,160,.3) 40%, transparent 70%), linear-gradient(160deg, #001220 0%, #002840 100%)',
  qwen:      'radial-gradient(ellipse at 40% 60%, rgba(0,255,136,.6) 0%, rgba(0,140,70,.3) 40%, transparent 70%), linear-gradient(160deg, #001408 0%, #002818 100%)',
  cortana:   'radial-gradient(ellipse at 60% 40%, rgba(0,180,255,.6) 0%, rgba(0,80,180,.3) 40%, transparent 70%), linear-gradient(160deg, #000f20 0%, #001e40 100%)',
  bruce:     'radial-gradient(ellipse at 50% 70%, rgba(255,50,70,.7) 0%, rgba(180,10,30,.3) 40%, transparent 70%), linear-gradient(160deg, #150003 0%, #2a0008 100%)',
  cyberdeck: 'radial-gradient(ellipse at 30% 30%, rgba(0,255,80,.5) 0%, rgba(0,160,40,.25) 40%, transparent 70%), linear-gradient(160deg, #001200 0%, #002400 100%)',
  commerce:  'radial-gradient(ellipse at 65% 45%, rgba(168,85,247,.6) 0%, rgba(90,20,180,.3) 40%, transparent 70%), linear-gradient(160deg, #08001e 0%, #18003c 100%)',
  missions:  'radial-gradient(ellipse at 40% 60%, rgba(255,215,0,.6) 0%, rgba(180,130,0,.3) 40%, transparent 70%), linear-gradient(160deg, #130e00 0%, #281c00 100%)',
};

export class ModulePanel {
  constructor() {
    this.el          = document.getElementById('module-panel');
    this.currentId   = null;
    this._renderer   = null;
    this._pollHandle = null;

    document.getElementById('panel-close').addEventListener('click', () => this.close());
  }

  open(config) {
    // Nettoyage complet de l'ancien module avant d'en ouvrir un nouveau
    this._cleanup();

    this.currentId = config.id;
    this._renderer = config.renderer;

    // Apply color theme
    this.el.style.setProperty('--pc', config.color);
    this.el.style.setProperty('--pg', config.glow);

    // Header
    this.el.querySelector('.panel-icon').textContent    = config.icon;
    this.el.querySelector('.panel-title').textContent   = config.name;
    this.el.querySelector('.panel-sub').textContent     = config.sub;

    // ── Bannière image planète ──────────────────────────────
    const banner = config.banner || _BANNERS[config.id] ||
      `radial-gradient(ellipse at 50% 50%, ${config.glow || 'rgba(0,212,255,.4)'} 0%, transparent 70%), linear-gradient(160deg, #040810 0%, #0a1020 100%)`;
    this._renderBanner(banner, config);

    // Body — renderer fills this
    const body = this.el.querySelector('.panel-body');
    body.innerHTML = '<div class="log-line" style="opacity:.4;font-size:9px">Connecting...</div>';
    this.el.classList.add('open');

    // Delegate rendering to the module
    // Capture snapshot local pour éviter que le handle appartienne à un module déjà remplacé
    const renderer = config.renderer;
    renderer.render(body).then(() => {
      // Vérifie que ce renderer est toujours le courant (panneau pas rouvert entre temps)
      if (this._renderer !== renderer) return;
      if (renderer.startPolling) {
        this._pollHandle = setInterval(() => {
          // Sécurité : ne rafraîchit que si le renderer est toujours actif
          if (this._renderer === renderer) renderer.refresh(body);
        }, config.pollInterval || 5000);
      }
    });
  }

  close() {
    this._cleanup();
    this.el.classList.remove('open');
    this.currentId = null;
  }

  _cleanup() {
    // Arrête le polling en cours
    if (this._pollHandle !== null) {
      clearInterval(this._pollHandle);
      this._pollHandle = null;
    }
    // Détruit le renderer courant (arrête ses propres intervals/polls)
    if (this._renderer) {
      if (typeof this._renderer.destroy === 'function') {
        this._renderer.destroy();
      }
      this._renderer = null;
    }
  }

  _renderBanner(gradient, config) {
    let banner = this.el.querySelector('.panel-banner');
    if (!banner) {
      banner = document.createElement('div');
      banner.className = 'panel-banner';
      // Insérer avant panel-body
      const body = this.el.querySelector('.panel-body');
      this.el.insertBefore(banner, body);
    }
    banner.style.background = gradient;
    banner.innerHTML = `
      <div class="panel-banner-scanlines"></div>
      <div class="panel-banner-icon">${config.icon || '⬡'}</div>
      <div class="panel-banner-info">
        <div class="panel-banner-name">${config.name || ''}</div>
        <div class="panel-banner-sub">${config.sub || ''}</div>
      </div>`;
  }

  setStatus(status, text) {
    const dot = this.el.querySelector('.panel-status-dot');
    const txt = this.el.querySelector('.panel-status-txt');
    dot.className = `panel-status-dot ${status}`;
    txt.textContent = text;
  }

  isOpen(id) {
    return this.el.classList.contains('open') && this.currentId === id;
  }
}
