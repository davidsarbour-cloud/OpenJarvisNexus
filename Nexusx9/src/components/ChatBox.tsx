import { useState, useRef, useEffect } from 'react';
import { chatWithJarvis, runCrewMission } from '../api';
import type { ChatMessage } from '../types';

interface Props {
  addAlert: (level: 'info'|'warn'|'error', msg: string) => void;
  onAgentBusy: (id: string, action?: string) => void;
}

export function ChatBox({ addAlert, onAgentBusy }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role:'assistant', content:'Bonjour David ! Hub NexusX9 en ligne. Comment puis-je t\'aider ?', ts: Date.now() }
  ]);
  const [input,   setInput]   = useState('');
  const [busy,    setBusy]    = useState(false);
  const [mode,    setMode]    = useState<'jarvis'|'crew'>('jarvis');
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior:'smooth' }); }, [messages]);

  const send = async () => {
    const txt = input.trim();
    if (!txt || busy) return;
    setInput('');
    setBusy(true);

    const userMsg: ChatMessage = { role:'user', content:txt, ts:Date.now() };
    setMessages(prev => [...prev, userMsg]);

    try {
      if (mode === 'crew') {
        onAgentBusy('architect', 'Mission crew...');
        onAgentBusy('researcher','Recherche...');
        onAgentBusy('coder',    'Développement...');
        const result = await runCrewMission(txt);
        setMessages(prev => [...prev, { role:'assistant', content:result, agent:'crew', ts:Date.now() }]);
        addAlert('info', 'Mission crew terminée');
      } else {
        onAgentBusy('architect', 'Traitement...');
        const reply = await chatWithJarvis(txt);
        setMessages(prev => [...prev, { role:'assistant', content:reply, agent:'jarvis', ts:Date.now() }]);
      }
    } catch (e: any) {
      addAlert('error', `Erreur chat: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-2 p-3">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className="max-w-[85%] rounded px-3 py-2 text-[12px] font-mono leading-relaxed border"
              style={{
                background:  m.role === 'user' ? '#00e5ff11' : '#b44dff0a',
                borderColor: m.role === 'user' ? '#00e5ff33' : '#b44dff33',
                color: '#c8d8ff',
              }}
            >
              {m.agent && (
                <div className="text-[10px] text-nx-dim mb-1 tracking-widest uppercase">
                  {m.agent === 'crew' ? '👥 CrewAI' : '🤖 Jarvis'}
                </div>
              )}
              <div className="whitespace-pre-wrap">{m.content}</div>
            </div>
          </div>
        ))}
        {busy && (
          <div className="flex justify-start">
            <div className="px-3 py-2 border border-nx-border rounded font-mono text-[12px] text-nx-cyan animate-pulse">
              {mode === 'crew' ? '👥 Équipe en action...' : '⚡ Traitement...'}
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Mode selector */}
      <div className="flex border-t border-nx-border px-3 pt-2 gap-2">
        {(['jarvis','crew'] as const).map(m => (
          <button key={m} onClick={() => setMode(m)}
                  className="px-3 py-1 text-[10px] font-mono tracking-widest rounded border transition-all"
                  style={{
                    borderColor: mode === m ? '#00e5ff' : '#0f1e3d',
                    color:       mode === m ? '#00e5ff' : '#334466',
                    background:  mode === m ? '#00e5ff14' : 'transparent',
                  }}>
            {m === 'jarvis' ? '⚡ JARVIS' : '👥 CREW'}
          </button>
        ))}
      </div>

      {/* Input */}
      <div className="flex gap-2 p-3">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
          placeholder={mode === 'crew' ? 'Décris la mission pour le crew...' : 'Message Jarvis...'}
          disabled={busy}
          className="flex-1 px-3 py-2 rounded border bg-nx-bg font-mono text-[12px] focus:outline-none placeholder-nx-dim/50"
          style={{ borderColor: busy ? '#0f1e3d' : '#00e5ff33', color:'#c8d8ff' }}
        />
        <button onClick={send} disabled={busy}
                className="px-4 py-2 rounded border font-hud font-bold text-[12px] tracking-widest transition-all disabled:opacity-30"
                style={{ borderColor:'#00e5ff', color:'#00e5ff', background:'#00e5ff14',
                         boxShadow:'0 0 12px #00e5ff22' }}>
          {busy ? '...' : '▶'}
        </button>
      </div>
    </div>
  );
}