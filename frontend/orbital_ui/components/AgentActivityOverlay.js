/**
 * AgentActivityOverlay — polls existing /v1/agents endpoint.
 * Updates planet status dots + activity rings live.
 */
export class AgentActivityOverlay {
  constructor(backend, planets) {
    this.backend  = backend;
    this.planets  = planets;   // Map<id, PlanetNode>
    this._handle  = null;
    this.online   = false;
  }

  start(intervalMs = 6000) {
    this._poll();
    this._handle = setInterval(() => this._poll(), intervalMs);
  }

  stop() {
    clearInterval(this._handle);
  }

  // Map Nexus9 agent IDs → orbital planet IDs
  _agentToPlanet(agentName) {
    const map = {
      jarvis:  'jarvis',
      ultron:  'ultron',
      qwen:    'qwen',
      cortana: 'cyberdeck',
      bruce:   'missions',
      kaizen:  'forge',
      // backend uses lowercase ids
      jarvis:   'jarvis',
    };
    return map[agentName?.toLowerCase()] ?? null;
  }

  _statusToOrbital(backendStatus) {
    const s = (backendStatus || '').toLowerCase();
    if (['active', 'running', 'thinking', 'executing', 'busy'].includes(s)) return 'busy';
    if (['online', 'idle', 'ready', 'waiting'].includes(s)) return 'online';
    return 'offline';
  }

  async _poll() {
    try {
      const r = await fetch(`${this.backend}/v1/agents`, { signal: AbortSignal.timeout(4000) });
      if (!r.ok) throw new Error('HTTP ' + r.status);
      const data = await r.json();
      const agents = data.agents || data || [];
      this.online = true;

      // Reset all to offline first
      for (const p of this.planets.values()) p.setStatus('offline');

      // Apply backend statuses
      for (const agent of agents) {
        const pid = this._agentToPlanet(agent.id || agent.name);
        if (!pid) continue;
        const planet = this.planets.get(pid);
        if (planet) planet.setStatus(this._statusToOrbital(agent.status));
      }

      // JARVIS is always online if backend responds
      this.planets.get('jarvis')?.setStatus('online');

    } catch {
      this.online = false;
      // Show all as offline except jarvis stays as-is
      for (const [id, p] of this.planets) {
        if (id !== 'jarvis') p.setStatus('offline');
      }
    }
  }
}
