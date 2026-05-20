const BASE = 'http://localhost:8000';

export async function fetchHubStatus() {
  const r = await fetch(`${BASE}/health`);
  return r.json();
}

export async function fetchAgents() {
  const r = await fetch(`${BASE}/v1/agents`);
  const d = await r.json();
  return d.agents ?? [];
}

export async function fetchMemory() {
  const r = await fetch(`${BASE}/v1/memory`);
  return r.json();
}

export async function chatWithJarvis(message: string): Promise<string> {
  const r = await fetch(`${BASE}/v1/chat/completions`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ message, stream: false, session_id: 'nexusx9-hub' }),
  });
  const d = await r.json();
  return d.choices?.[0]?.message?.content ?? 'Pas de réponse.';
}

export async function runCrewMission(mission: string): Promise<string> {
  const r = await fetch(`${BASE}/v1/crew/run`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ mission, mission_type: 'auto' }),
  });
  const d = await r.json();
  return d.result ?? d.error ?? 'Mission terminée.';
}