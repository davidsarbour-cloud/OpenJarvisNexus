/**
 * GalaxyBackground — canvas star field + shooting stars
 * Pure visual layer, zero backend dependency.
 */
export class GalaxyBackground {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx    = canvas.getContext('2d');
    this.stars  = [];
    this.shooters = [];
    this._raf   = null;
    this._resize = this._onResize.bind(this);

    window.addEventListener('resize', this._resize);
    this._onResize();
    this._initStars();
    this._loop();

    // Pause le RAF quand la page est cachée pour économiser le CPU
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        cancelAnimationFrame(this._raf);
        this._raf = null;
      } else {
        this._loop();
      }
    });
  }

  _onResize() {
    this.canvas.width  = window.innerWidth;
    this.canvas.height = window.innerHeight;
  }

  _initStars() {
    this.stars = [];
    // Réduit de /4000 à /6000 pour moins de charge CPU
    const w = window.innerWidth;
    const h = window.innerHeight;
    const n = Math.floor((w * h) / 6000);
    for (let i = 0; i < n; i++) {
      this.stars.push({
        x: Math.random() * w,
        y: Math.random() * h,
        r: Math.random() * 1.4 + 0.2,
        a: Math.random(),
        da: (Math.random() - 0.5) * 0.003,
        color: this._starColor(),
      });
    }
  }

  _starColor() {
    const palette = ['#ffffff', '#cce8ff', '#b0c8e8', '#a0c0ff', '#80a8e8', '#00d4ff', '#a855f7'];
    return palette[Math.floor(Math.random() * palette.length)];
  }

  _spawnShooter() {
    if (this.shooters.length >= 3) return;
    const y = Math.random() * window.innerHeight * 0.6;
    this.shooters.push({
      x: -80, y,
      vx: Math.random() * 6 + 4,
      vy: Math.random() * 2 + 1,
      len: Math.random() * 80 + 60,
      a: 1,
    });
  }

  _loop() {
    const now = performance.now();

    // FPS cap à 60fps — skip si le frame est trop rapide (< 16ms)
    if (this._lastFrame !== undefined && now - this._lastFrame < 16) {
      this._raf = requestAnimationFrame(this._loop.bind(this));
      return;
    }
    this._lastFrame = now;

    const { ctx, canvas } = this;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Static stars
    for (const s of this.stars) {
      s.a = Math.max(0.05, Math.min(1, s.a + s.da));
      if (s.a <= 0.05 || s.a >= 1) s.da *= -1;
      ctx.globalAlpha = s.a * 0.7;
      ctx.fillStyle = s.color;
      ctx.beginPath();
      ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
      ctx.fill();
    }

    // Shooting stars
    if (Math.random() < 0.004) this._spawnShooter();
    ctx.globalAlpha = 1;
    this.shooters = this.shooters.filter(s => {
      s.x += s.vx; s.y += s.vy; s.a -= 0.018;
      if (s.a <= 0 || s.x > canvas.width + 100) return false;
      const grad = ctx.createLinearGradient(s.x, s.y, s.x - s.len, s.y - s.vy * (s.len / s.vx));
      grad.addColorStop(0, `rgba(255,255,255,${s.a})`);
      grad.addColorStop(1, 'transparent');
      ctx.strokeStyle = grad;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(s.x, s.y);
      ctx.lineTo(s.x - s.len, s.y - s.vy * (s.len / s.vx));
      ctx.stroke();
      return true;
    });

    ctx.globalAlpha = 1;
    this._raf = requestAnimationFrame(this._loop.bind(this));
  }

  destroy() {
    cancelAnimationFrame(this._raf);
    window.removeEventListener('resize', this._resize);
  }
}
