/**
 * PlanetNode — individual planet DOM element on the orbital map.
 * Positioned by OrbitSystem based on angle + radius.
 */
export class PlanetNode {
  constructor({ id, icon, label, color, glow, radius, orbitRadius, speed, onActivate }) {
    this.id          = id;
    this.color       = color;
    this.glow        = glow;
    this.orbitRadius = orbitRadius;
    this.speed       = speed;       // radians per second
    this.angle       = Math.random() * Math.PI * 2;  // random start angle
    this.onActivate  = onActivate;
    this.status      = 'offline';
    this.isActive    = false;

    this.el = this._build(icon, label, color, glow, radius);
  }

  _build(icon, label, color, glow, size) {
    const el = document.createElement('div');
    el.className = 'planet';
    el.id = `planet-${this.id}`;
    el.style.setProperty('--pc', color);
    el.style.setProperty('--pg', glow);
    el.style.width = el.style.height = `${size || 64}px`;

    el.innerHTML = `
      <div class="planet-ring"></div>
      <div class="planet-activity"></div>
      <div class="planet-core">
        <div class="planet-status"></div>
        <div class="planet-icon">${icon}</div>
        <div class="planet-label">${label}</div>
      </div>`;

    el.addEventListener('click', () => {
      this.onActivate?.(this.id);
    });

    return el;
  }

  // Update position (called every frame by OrbitSystem)
  setPosition(cx, cy) {
    this.el.style.left = `${cx}px`;
    this.el.style.top  = `${cy}px`;
  }

  advanceAngle(dt) {
    this.angle += this.speed * dt;
  }

  getXY(centerX, centerY) {
    return {
      x: centerX + Math.cos(this.angle) * this.orbitRadius,
      y: centerY + Math.sin(this.angle) * this.orbitRadius,
    };
  }

  setStatus(status) {
    this.status = status;
    const dot = this.el.querySelector('.planet-status');
    dot.className = `planet-status ${status}`;
    const activity = this.el.querySelector('.planet-activity');
    activity.classList.toggle('active', status === 'busy');
  }

  setActive(active) {
    this.isActive = active;
    this.el.classList.toggle('active', active);
  }

  appendTo(container) {
    container.appendChild(this.el);
  }
}
