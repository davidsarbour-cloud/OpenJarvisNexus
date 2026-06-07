import { Youtube } from 'lucide-react';
import { HudCard, CardValue } from './HudCard';
import { useLiveMetric } from '../../hooks/useLiveMetric';
import { fetchYouTubeStats } from '../../lib/apiLive';

/**
 * YouTubeStatsCard — public audience stats for the channel.
 * Mirror of GumroadRevenueCard. Backed by GET /v1/social/youtube/stats.
 * Shows "warn" (not "down") when the backend is reachable but YouTube isn't
 * connected yet (no YOUTUBE_API_KEY / YOUTUBE_CHANNEL_ID in backend/.env).
 */
const fmt = (n: number): string => {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
};

export function YouTubeStatsCard() {
  // Audience moves slowly — poll every 10 min, no WS topic needed.
  const { data, error, loading } = useLiveMetric(() => fetchYouTubeStats(), { intervalMs: 600_000 });
  const connected = !!data?.connected;
  const status = error ? 'down' : loading ? 'loading' : connected ? 'live' : 'warn';

  const subs = data?.subscribers ?? 0;
  const views = data?.views ?? 0;
  const videos = data?.videos ?? 0;

  return (
    <HudCard
      title="YouTube"
      subtitle={connected && data?.title ? data.title : 'Audience (/v1/social/youtube/stats)'}
      colorKey="cyberdeck"
      icon={Youtube}
      status={status}
    >
      {connected ? (
        <>
          <CardValue
            value={data?.subs_hidden ? '—' : fmt(subs)}
            unit="abonnés"
            colorKey="cyberdeck"
          />
          <div className="mt-2 text-[10px] flex flex-col gap-1">
            <div className="flex justify-between">
              <span style={{ color: 'var(--hud-text-dim)' }}>VUES</span>
              <span className="tabular-nums" style={{ color: 'var(--color-jarvis)' }}>{fmt(views)}</span>
            </div>
            <div className="flex justify-between">
              <span style={{ color: 'var(--hud-text-dim)' }}>VIDÉOS</span>
              <span className="tabular-nums" style={{ color: 'var(--color-docker)' }}>{videos}</span>
            </div>
          </div>
        </>
      ) : (
        <div className="text-[10px] leading-relaxed" style={{ color: 'var(--hud-text-dim)' }}>
          {error
            ? 'Backend injoignable.'
            : 'YouTube non connecté — configure YOUTUBE_API_KEY + YOUTUBE_CHANNEL_ID dans backend/.env, puis redémarre le backend.'}
        </div>
      )}
    </HudCard>
  );
}
