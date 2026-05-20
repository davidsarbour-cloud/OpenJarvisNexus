/**
 * StarCore — central JARVIS star element.
 * Clicking opens the existing Nexus9 chat panel.
 */
export class StarCore {
  constructor(container, onActivate) {
    this.el = this._build();
    container.appendChild(this.el);
    this.el.addEventListener('click', () => onActivate?.('jarvis'));
  }

  _build() {
    const el = document.createElement('div');
    el.id = 'jarvis-star';
    el.innerHTML = `
      <div class="star-core">
        <div class="star-corona"></div>
        <div class="star-corona"></div>
        <div class="star-icon">☀</div>
        <div class="star-label">JARVIS</div>
      </div>`;
    return el;
  }

  // Visual feedback when JARVIS is processing
  setBusy(busy) {
    const core = this.el.querySelector('.star-core');
    if (busy) core.style.animationDuration = '1s';
    else       core.style.animationDuration = '';
  }
}
