/**
 * OrbitSystem — manages orbital mechanics.
 * Draws ring paths on a canvas overlay, advances planet angles,
 * and updates planet DOM positions each frame.
 */
export class OrbitSystem {
  constructor(canvas, stage) {
    this.canvas  = canvas;
    this.ctx     = canvas.getContext('2d');
    this.stage   = stage;
    this.planets = [];
    this._last   = performance.now();
    this._raf    = null;
    this._frameCount = 0;
    this._resize = this._onResize.bind(this);
    window.addEventListener('resize', this._resize);
    this._onResize();

    // Pause le RAF quand la page est cachée pour économiser le CPU
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        cancelAnimationFrame(this._raf);
        this._raf = null;
      } else if (this._running) {
        this._raf = requestAnimationFrame(this._loop.bind(this));
      }
    });
  }

  _onResize() {
    this.canvas.width  = this.stage.offsetWidth;
    this.canvas.height = this.stage.offsetHeight;
  }

  get cx() { return this.canvas.width  / 2; }
  get cy() { return this.canvas.height / 2; }

  addPlanet(planet) {
    this.planets.push(planet);
  }

  start() {
    this._running = true;
    this._raf = requestAnimationFrame(this._loop.bind(this));
  }

  stop() {
    this._running = false;
    cancelAnimationFrame(this._raf);
    window.removeEventListener('resize', this._resize);
  }

  _loop(now) {
    const dt = Math.min((now - this._last) / 1000, 0.1);
    this._last = now;
    this._frameCount++;

    const { ctx, cx, cy } = this;
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

    // Redessine les rings seulement toutes les 3 frames (statiques, pas besoin chaque frame)
    if (this._frameCount % 3 === 0) {
      const radii = [...new Set(this.planets.map(p => p.orbitRadius))].sort();
      for (const r of radii) this._drawRing(r);
    }

    // Update planet positions chaque frame (elles bougent)
    for (const planet of this.planets) {
      planet.advanceAngle(dt);
      const { x, y } = planet.getXY(cx, cy);
      planet.setPosition(x, y);
    }

    this._raf = requestAnimationFrame(this._loop.bind(this));
  }

  _drawRing(r) {
    const { ctx, cx, cy } = this;
    // Outer glow
    ctx.strokeStyle = 'rgba(0,212,255,0.04)';
    ctx.lineWidth = 6;
    ctx.setLineDash([]);
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.stroke();

    // Main ring (dashed)
    ctx.strokeStyle = 'rgba(0,212,255,0.09)';
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 16]);
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.stroke();

    ctx.setLineDash([]);
  }
}
