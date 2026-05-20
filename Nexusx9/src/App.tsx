// src/App.tsx — NexusX9 Interface Complète
import { useState, useEffect, useRef, useCallback } from 'react'

// ── Types ────────────────────────────────────────────────
interface Agent {
  id: string
  name: string
  color: string
  glow: string
  orbitRadius: number
  speed: number
  angle: number
  status: 'idle' | 'active' | 'processing' | 'error'
  icon: string
  port?: string
}

interface Message {
  id: string
  role: 'user' | 'assistant' | 'agent'
  content: string
  agent?: string
  timestamp: Date
}

interface EnergyLine {
  id: string
  from: string
  to: string
  active: boolean
  opacity: number
}

// ── Constantes ───────────────────────────────────────────
const AGENTS: Agent[] = [
  { id: 'architecte', name: 'Architecte', color: '#00d4ff', glow: '#00d4ff',
    orbitRadius: 120, speed: 0.008, angle: 0, status: 'idle', icon: '🏛️' },
  { id: 'laboratoire', name: 'Laboratoire', color: '#ff6b35', glow: '#ff6b35',
    orbitRadius: 180, speed: 0.005, angle: 1.2, status: 'idle', icon: '🔬' },
  { id: 'surveillance', name: 'Surveillance', color: '#7fff00', glow: '#7fff00',
    orbitRadius: 240, speed: 0.003, angle: 2.5, status: 'idle', icon: '👁️' },
  { id: 'atelier', name: 'Atelier Code', color: '#bf00ff', glow: '#bf00ff',
    orbitRadius: 300, speed: 0.002, angle: 3.8, status: 'idle', icon: '⚙️' },
  { id: 'coffre', name: 'Coffre Mémoire', color: '#ffd700', glow: '#ffd700',
    orbitRadius: 360, speed: 0.0015, angle: 5.1, status: 'idle', icon: '🗄️' },
]

const API = 'http://localhost:8000'

// ── Composant Principal ──────────────────────────────────
export default function App() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animRef   = useRef<number>(0)
  const agentsRef = useRef<Agent[]>(AGENTS.map(a => ({ ...a })))

  const [messages, setMessages]       = useState<Message[]>([])
  const [input, setInput]             = useState('')
  const [loading, setLoading]         = useState(false)
  const [activeAgent, setActiveAgent] = useState<string | null>(null)
  const [systemOnline, setSystemOnline] = useState(false)
  const [pulse, setPulse]             = useState(0)
  const [energyLines, setEnergyLines] = useState<EnergyLine[]>([])
  const [stats, setStats]             = useState({ tasks: 0, uptime: 0, energy: 87 })
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // ── Canvas Animation ─────────────────────────────────
  const draw = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')!
    const W = canvas.width, H = canvas.height
    const cx = W / 2, cy = H / 2

    ctx.clearRect(0, 0, W, H)

    // Fond étoilé
    ctx.fillStyle = 'rgba(0,0,0,0.15)'
    ctx.fillRect(0, 0, W, H)

    // Mise à jour angles
    agentsRef.current = agentsRef.current.map(a => ({
      ...a, angle: a.angle + a.speed
    }))

    // Orbites
    agentsRef.current.forEach(agent => {
      ctx.beginPath()
      ctx.arc(cx, cy, agent.orbitRadius, 0, Math.PI * 2)
      ctx.strokeStyle = `${agent.color}22`
      ctx.lineWidth = 1
      ctx.setLineDash([4, 8])
      ctx.stroke()
      ctx.setLineDash([])
    })

    // Lignes énergétiques actives
    agentsRef.current.forEach(agent => {
      if (agent.status === 'active' || agent.status === 'processing') {
        const px = cx + Math.cos(agent.angle) * agent.orbitRadius
        const py = cy + Math.sin(agent.angle) * agent.orbitRadius
        const gradient = ctx.createLinearGradient(cx, cy, px, py)
        gradient.addColorStop(0, `${agent.color}00`)
        gradient.addColorStop(0.5, `${agent.color}88`)
        gradient.addColorStop(1, `${agent.color}44`)
        ctx.beginPath()
        ctx.moveTo(cx, cy)
        ctx.lineTo(px, py)
        ctx.strokeStyle = gradient
        ctx.lineWidth = agent.status === 'processing' ? 2 : 1
        ctx.stroke()
      }
    })

    // JARVIS — Soleil central
    const time = Date.now() / 1000
    const pulseScale = 1 + Math.sin(time * 2) * 0.05

    // Halo externe
    for (let i = 4; i >= 1; i--) {
      const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, 55 * i * 0.4)
      grad.addColorStop(0, `rgba(0,212,255,${0.06 / i})`)
      grad.addColorStop(1, 'transparent')
      ctx.beginPath()
      ctx.arc(cx, cy, 55 * i * 0.4, 0, Math.PI * 2)
      ctx.fillStyle = grad
      ctx.fill()
    }

    // Corps du soleil
    const sunGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, 45 * pulseScale)
    sunGrad.addColorStop(0, '#ffffff')
    sunGrad.addColorStop(0.3, '#00d4ff')
    sunGrad.addColorStop(0.7, '#0066ff')
    sunGrad.addColorStop(1, '#003399')
    ctx.beginPath()
    ctx.arc(cx, cy, 45 * pulseScale, 0, Math.PI * 2)
    ctx.fillStyle = sunGrad
    ctx.shadowBlur = 40
    ctx.shadowColor = '#00d4ff'
    ctx.fill()
    ctx.shadowBlur = 0

    // Anneaux du soleil
    ;[55, 65].forEach((r, i) => {
      ctx.beginPath()
      ctx.arc(cx, cy, r * pulseScale, 0, Math.PI * 2)
      ctx.strokeStyle = i === 0 ? 'rgba(0,212,255,0.6)' : 'rgba(0,212,255,0.3)'
      ctx.lineWidth = i === 0 ? 2 : 1
      ctx.stroke()
    })

    // Texte JARVIS
    ctx.fillStyle = '#ffffff'
    ctx.font = 'bold 11px monospace'
    ctx.textAlign = 'center'
    ctx.fillText('JARVIS', cx, cy + 4)

    // Planètes agents
    agentsRef.current.forEach(agent => {
      const px = cx + Math.cos(agent.angle) * agent.orbitRadius
      const py = cy + Math.sin(agent.angle) * agent.orbitRadius
      const size = agent.status === 'processing' ? 14 + Math.sin(time * 6) * 3 : 12

      // Halo planète
      const pGrad = ctx.createRadialGradient(px, py, 0, px, py, size * 2.5)
      pGrad.addColorStop(0, `${agent.color}44`)
      pGrad.addColorStop(1, 'transparent')
      ctx.beginPath()
      ctx.arc(px, py, size * 2.5, 0, Math.PI * 2)
      ctx.fillStyle = pGrad
      ctx.fill()

      // Corps planète
      ctx.beginPath()
      ctx.arc(px, py, size, 0, Math.PI * 2)
      ctx.fillStyle = agent.color
      ctx.shadowBlur = agent.status !== 'idle' ? 20 : 8
      ctx.shadowColor = agent.color
      ctx.fill()
      ctx.shadowBlur = 0

      // Icône
      ctx.font = `${size}px serif`
      ctx.textAlign = 'center'
      ctx.fillText(agent.icon, px, py + size * 0.35)

      // Label
      ctx.font = '10px monospace'
      ctx.fillStyle = agent.color
      ctx.fillText(agent.name, px, py + size + 14)

      // Indicateur statut
      const statusColors: Record<string, string> = {
        idle: '#666', active: '#00ff88', processing: '#ffaa00', error: '#ff3333'
      }
      ctx.beginPath()
      ctx.arc(px + size * 0.7, py - size * 0.7, 4, 0, Math.PI * 2)
      ctx.fillStyle = statusColors[agent.status]
      ctx.fill()
    })

    animRef.current = requestAnimationFrame(draw)
  }, [])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const resize = () => {
      canvas.width  = canvas.offsetWidth
      canvas.height = canvas.offsetHeight
    }
    resize()
    window.addEventListener('resize', resize)
    animRef.current = requestAnimationFrame(draw)

    // Check backend
    fetch(`${API}/health`)
      .then(r => r.json())
      .then(() => setSystemOnline(true))
      .catch(() => setSystemOnline(false))

    // Stats interval
    const statsInterval = setInterval(() => {
      setStats(s => ({ ...s, uptime: s.uptime + 1, energy: 80 + Math.random() * 15 }))
    }, 1000)

    return () => {
      cancelAnimationFrame(animRef.current)
      window.removeEventListener('resize', resize)
      clearInterval(statsInterval)
    }
  }, [draw])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // ── Envoi message ────────────────────────────────────
  const sendMessage = async () => {
    if (!input.trim() || loading) return
    const userMsg: Message = {
      id: Date.now().toString(), role: 'user',
      content: input, timestamp: new Date()
    }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    // Activer un agent aléatoire visuellement
    const randomAgent = AGENTS[Math.floor(Math.random() * AGENTS.length)]
    setActiveAgent(randomAgent.id)
    agentsRef.current = agentsRef.current.map(a =>
      a.id === randomAgent.id ? { ...a, status: 'processing' } : a
    )

    try {
      const res = await fetch(`${API}/v1/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: input, session_id: 'nexusx9' })
      })
      const data = await res.json()
      const reply: Message = {
        id: (Date.now() + 1).toString(), role: 'assistant',
        content: data.response || data.message || JSON.stringify(data),
        agent: randomAgent.name, timestamp: new Date()
      }
      setMessages(prev => [...prev, reply])
      setStats(s => ({ ...s, tasks: s.tasks + 1 }))
    } catch {
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(), role: 'agent',
        content: `⚠️ Backend non disponible. Vérifier http://localhost:8000`,
        agent: 'Système', timestamp: new Date()
      }])
    } finally {
      setLoading(false)
      setActiveAgent(null)
      agentsRef.current = agentsRef.current.map(a => ({ ...a, status: 'idle' }))
    }
  }

  // ── Rendu ─────────────────────────────────────────────
  return (
    <div style={styles.root}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.headerLeft}>
          <div style={styles.logo}>⬡ NexusX9</div>
          <div style={styles.statusDot(systemOnline)} />
          <span style={styles.statusText}>{systemOnline ? 'SYSTÈME EN LIGNE' : 'CONNEXION...'}</span>
        </div>
        <div style={styles.headerRight}>
          {[
            { label: 'ÉNERGIE', value: `${stats.energy.toFixed(0)}%`, color: '#00ff88' },
            { label: 'TÂCHES', value: stats.tasks.toString(), color: '#00d4ff' },
            { label: 'UPTIME', value: `${stats.uptime}s`, color: '#ffd700' },
          ].map(s => (
            <div key={s.label} style={styles.statBox}>
              <div style={{ color: '#666', fontSize: 9, letterSpacing: 1 }}>{s.label}</div>
              <div style={{ color: s.color, fontSize: 14, fontWeight: 700 }}>{s.value}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Corps principal */}
      <div style={styles.body}>
        {/* Système solaire */}
        <div style={styles.solarPanel}>
          <canvas ref={canvasRef} style={styles.canvas} />
          {/* Agents list */}
          <div style={styles.agentsList}>
            {AGENTS.map(agent => (
              <div key={agent.id} style={styles.agentRow(agent.color)}>
                <span>{agent.icon}</span>
                <span style={{ color: agent.color, fontSize: 11 }}>{agent.name}</span>
                <div style={styles.agentStatusDot(
                  agent.id === activeAgent ? 'processing' : 'idle',
                  agent.color
                )} />
              </div>
            ))}
          </div>
        </div>

        {/* Panel Chat */}
        <div style={styles.chatPanel}>
          <div style={styles.chatHeader}>
            <span style={{ color: '#00d4ff', fontSize: 11, letterSpacing: 2 }}>
              ◈ INTERFACE NEXUSX9
            </span>
            {loading && (
              <span style={{ color: '#ffaa00', fontSize: 10, animation: 'pulse 1s infinite' }}>
                ⟳ TRAITEMENT...
              </span>
            )}
          </div>

          {/* Messages */}
          <div style={styles.messages}>
            {messages.length === 0 && (
              <div style={styles.emptyState}>
                <div style={{ fontSize: 40, marginBottom: 12 }}>🌌</div>
                <div style={{ color: '#00d4ff', fontSize: 14 }}>Système NexusX9 initialisé</div>
                <div style={{ color: '#444', fontSize: 11, marginTop: 8 }}>
                  Posez une question aux agents
                </div>
              </div>
            )}
            {messages.map(msg => (
              <div key={msg.id} style={styles.messageRow(msg.role)}>
                <div style={styles.messageBubble(msg.role)}>
                  {msg.agent && (
                    <div style={{ color: '#ffd700', fontSize: 9, marginBottom: 4, letterSpacing: 1 }}>
                      ◈ {msg.agent.toUpperCase()}
                    </div>
                  )}
                  <div style={{ color: msg.role === 'user' ? '#fff' : '#ccc', fontSize: 13, lineHeight: 1.5 }}>
                    {msg.content}
                  </div>
                  <div style={{ color: '#444', fontSize: 9, marginTop: 4 }}>
                    {msg.timestamp.toLocaleTimeString()}
                  </div>
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div style={styles.inputArea}>
            <input
              style={styles.input}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && sendMessage()}
              placeholder="Commande JARVIS..."
              disabled={loading}
            />
            <button
              style={styles.sendBtn(loading)}
              onClick={sendMessage}
              disabled={loading}
            >
              {loading ? '⟳' : '▶'}
            </button>
          </div>

          {/* Suggestions rapides */}
          <div style={styles.suggestions}>
            {['Analyse le système', 'Génère du code', 'Rapport mémoire'].map(s => (
              <button
                key={s}
                style={styles.suggBtn}
                onClick={() => { setInput(s); }}
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Footer */}
      <div style={styles.footer}>
        {['BACKEND :8000', 'OLLAMA :11434', 'N8N :5678', 'VITE :5174'].map((s, i) => (
          <div key={s} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#00ff88' }} />
            <span style={{ color: '#444', fontSize: 9 }}>{s}</span>
          </div>
        ))}
        <span style={{ color: '#222', fontSize: 9 }}>NexusX9 v1.0 © 2026</span>
      </div>
    </div>
  )
}

// ── Styles ────────────────────────────────────────────────
const styles = {
  root: {
    width: '100vw', height: '100vh', background: '#050810',
    display: 'flex', flexDirection: 'column' as const,
    fontFamily: "'Courier New', monospace", overflow: 'hidden',
    color: '#fff',
  },
  header: {
    height: 52, borderBottom: '1px solid #0a1628',
    display: 'flex', alignItems: 'center',
    justifyContent: 'space-between', padding: '0 24px',
    background: 'rgba(0,5,20,0.9)',
    backdropFilter: 'blur(10px)',
  },
  headerLeft: { display: 'flex', alignItems: 'center', gap: 12 },
  logo: { color: '#00d4ff', fontSize: 18, fontWeight: 700, letterSpacing: 3 },
  statusDot: (online: boolean) => ({
    width: 8, height: 8, borderRadius: '50%',
    background: online ? '#00ff88' : '#ff4444',
    boxShadow: `0 0 8px ${online ? '#00ff88' : '#ff4444'}`,
  }),
  statusText: { color: '#444', fontSize: 9, letterSpacing: 2 },
  headerRight: { display: 'flex', gap: 24 },
  statBox: { textAlign: 'center' as const },
  body: {
    flex: 1, display: 'flex', overflow: 'hidden',
  },
  solarPanel: {
    width: '55%', position: 'relative' as const,
    borderRight: '1px solid #0a1628',
    background: 'radial-gradient(ellipse at center, #030810 0%, #010408 100%)',
  },
  canvas: { width: '100%', height: 'calc(100% - 140px)', display: 'block' },
  agentsList: {
    position: 'absolute' as const, bottom: 0, left: 0, right: 0,
    padding: '8px 16px', borderTop: '1px solid #0a1628',
    background: 'rgba(0,0,0,0.7)', display: 'flex', gap: 8, flexWrap: 'wrap' as const,
  },
  agentRow: (color: string) => ({
    display: 'flex', alignItems: 'center', gap: 6,
    padding: '4px 10px', borderRadius: 4,
    border: `1px solid ${color}33`, background: `${color}11`,
  }),
  agentStatusDot: (status: string, color: string) => ({
    width: 6, height: 6, borderRadius: '50%',
    background: status === 'processing' ? color : '#333',
    boxShadow: status === 'processing' ? `0 0 6px ${color}` : 'none',
  }),
  chatPanel: {
    width: '45%', display: 'flex', flexDirection: 'column' as const,
    background: '#030710',
  },
  chatHeader: {
    padding: '12px 20px', borderBottom: '1px solid #0a1628',
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    minHeight: 44,
  },
  messages: {
    flex: 1, overflowY: 'auto' as const, padding: '16px 16px',
    display: 'flex', flexDirection: 'column' as const, gap: 12,
  },
  emptyState: {
    display: 'flex', flexDirection: 'column' as const,
    alignItems: 'center', justifyContent: 'center',
    flex: 1, padding: 40, textAlign: 'center' as const,
  },
  messageRow: (role: string) => ({
    display: 'flex',
    justifyContent: role === 'user' ? 'flex-end' : 'flex-start',
  }),
  messageBubble: (role: string) => ({
    maxWidth: '82%', padding: '10px 14px', borderRadius: 8,
    background: role === 'user'
      ? 'linear-gradient(135deg, #003366, #004499)'
      : 'linear-gradient(135deg, #0a1020, #0d1525)',
    border: role === 'user' ? '1px solid #0066cc' : '1px solid #1a2535',
  }),
  inputArea: {
    padding: '12px 16px', display: 'flex', gap: 8,
    borderTop: '1px solid #0a1628',
  },
  input: {
    flex: 1, background: '#0a1020', border: '1px solid #1a2535',
    borderRadius: 6, padding: '10px 14px', color: '#fff',
    fontSize: 13, fontFamily: 'monospace', outline: 'none',
  },
  sendBtn: (loading: boolean) => ({
    width: 44, height: 44, borderRadius: 6,
    background: loading ? '#333' : 'linear-gradient(135deg, #0044cc, #0066ff)',
    border: 'none', color: '#fff', fontSize: 16, cursor: 'pointer',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
  }),
  suggestions: {
    padding: '8px 16px 12px', display: 'flex', gap: 6,
  },
  suggBtn: {
    padding: '4px 10px', borderRadius: 4, fontSize: 10,
    background: 'transparent', border: '1px solid #1a2535',
    color: '#556', cursor: 'pointer',
    fontFamily: 'monospace',
  },
  footer: {
    height: 32, borderTop: '1px solid #0a1628',
    display: 'flex', alignItems: 'center', gap: 20, padding: '0 20px',
    background: 'rgba(0,0,0,0.5)',
    justifyContent: 'space-between',
  },
}