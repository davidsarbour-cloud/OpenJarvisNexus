import { useState } from 'react';
import { FileText } from 'lucide-react';
import { HudCard } from './HudCard';
import { generateDailyReport } from '../../lib/apiLive';

/**
 * DailyReportCard — sits directly under the Daily Schedule in the Command
 * Center left dock. Clicking it hits POST /v1/reports/generate, which writes a
 * blank dated report into the brain (08_Command-Center/reports) and pops it
 * open in Notepad on the host machine.
 */
export function DailyReportCard() {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  const onClick = async () => {
    if (busy) return;
    setBusy(true);
    setMsg(null);
    setFailed(false);
    try {
      const r = await generateDailyReport();
      setMsg(`Ouvert dans Notepad : ${r.filename}`);
    } catch (e) {
      setFailed(true);
      setMsg(e instanceof Error ? e.message : 'Échec de la génération');
    } finally {
      setBusy(false);
    }
  };

  return (
    <HudCard
      title="Rapport du jour"
      subtitle="rapport vierge daté → Notepad"
      colorKey="jarvis"
      icon={FileText}
      status={busy ? 'loading' : failed ? 'warn' : 'live'}
    >
      <button
        type="button"
        onClick={onClick}
        disabled={busy}
        className="w-full py-2 text-[11px] font-bold tracking-[0.18em] transition-all"
        style={{
          background: 'rgba(0,212,255,0.08)',
          border: '1px solid var(--color-jarvis)',
          color: 'var(--color-jarvis)',
          cursor: busy ? 'wait' : 'pointer',
        }}
      >
        {busy ? 'GÉNÉRATION…' : '+ NOUVEAU RAPPORT'}
      </button>
      <div className="mt-2 text-[9px] tracking-wider" style={{ color: failed ? 'var(--color-cyberdeck)' : 'var(--hud-text-dim)' }}>
        {msg ?? 'Crée un rapport vierge daté par Nexus9 et l’ouvre dans Notepad.'}
      </div>
    </HudCard>
  );
}
