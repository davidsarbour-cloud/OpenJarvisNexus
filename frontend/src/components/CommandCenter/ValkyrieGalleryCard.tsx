/**
 * ValkyrieGalleryCard — recent gpt-image-1 generations grid.
 *
 * Wired to GET /v1/valkyrie/gallery. Auto-refreshes when the generate
 * card emits `valkyrie:generated`, plus a slow 30s poll as a fallback.
 * Click a thumbnail to open the full PNG in a new tab; hover reveals a
 * delete (×) button → DELETE /v1/valkyrie/image/{name}.
 */
import { useContext, useEffect, useState } from 'react';
import { Images, X } from 'lucide-react';
import { CardAccentContext } from './HudCard';
import { cssVar } from '../../lib/colors';
import type { ModuleKey } from '../../lib/colors';
import { getBase } from '../../lib/api';

interface GalleryImage {
  name: string;
  url: string;
  prompt?: string;
  size?: string;
  quality?: string;
  created_at?: string;
}

export function ValkyrieGalleryCard() {
  const ctxAccent = useContext(CardAccentContext);
  const colorKey: ModuleKey = ctxAccent ?? 'valkyrie';
  const c = cssVar(colorKey);
  const base = getBase();

  const [images, setImages] = useState<GalleryImage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch on mount + on the `valkyrie:generated` event + slow poll fallback.
  // The async runner is defined inside the effect (same pattern as
  // useLiveMetric) so setState is never called synchronously in the body.
  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      try {
        const r = await fetch(`${base}/v1/valkyrie/gallery?limit=60`);
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const j = await r.json();
        if (cancelled) return;
        setImages(Array.isArray(j.images) ? j.images : []);
        setError(null);
      } catch (e) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : 'failed');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    run();
    const onGen = () => run();
    window.addEventListener('valkyrie:generated', onGen);
    const iv = setInterval(() => { if (!document.hidden) run(); }, 30000);
    return () => {
      cancelled = true;
      window.removeEventListener('valkyrie:generated', onGen);
      clearInterval(iv);
    };
  }, [base]);

  const remove = async (name: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setImages((prev) => prev.filter((i) => i.name !== name)); // optimistic
    try {
      const r = await fetch(`${base}/v1/valkyrie/image/${encodeURIComponent(name)}`, { method: 'DELETE' });
      if (!r.ok) throw new Error();
    } catch {
      window.dispatchEvent(new CustomEvent('valkyrie:generated')); // revert via reload
    }
  };

  return (
    <div
      className="flex flex-col p-3 relative"
      style={{
        background: 'var(--hud-bg-elev)',
        border: '1px solid var(--hud-border)',
        borderTop: `2px solid ${c}`,
        boxShadow: 'inset 0 0 24px rgba(0,0,0,0.4)',
        minHeight: 200,
        height: '100%',
        fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
      }}
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-0.5">
        <Images size={14} style={{ color: c }} />
        <span className="text-[10px] font-bold tracking-[0.22em]" style={{ color: c }}>
          GALLERY
        </span>
        <span className="text-[9px] ml-auto" style={{ color: 'var(--hud-text-dim)' }}>
          {images.length}
        </span>
      </div>
      <div className="text-[9px] tracking-wider mb-2" style={{ color: 'var(--hud-text-dim)' }}>
        Recent generations · click to open
      </div>

      {/* Grid */}
      <div className="flex-1 overflow-y-auto">
        {error ? (
          <span className="text-[9px]" style={{ color: '#ff6b6b' }}>! {error}</span>
        ) : loading ? (
          <span className="text-[9px]" style={{ color: 'var(--hud-text-dim)', opacity: 0.55 }}>loading…</span>
        ) : images.length === 0 ? (
          <span className="text-[9px]" style={{ color: 'var(--hud-text-dim)', opacity: 0.55 }}>
            no images yet — generate one
          </span>
        ) : (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(64px, 1fr))',
              gap: 6,
            }}
          >
            {images.map((img) => (
              <button
                key={img.name}
                onClick={() => window.open(`${base}${img.url}`, '_blank', 'noopener,noreferrer')}
                title={img.prompt || img.name}
                className="relative group"
                style={{
                  aspectRatio: '1 / 1',
                  border: `1px solid ${c}`,
                  background: 'rgba(0,0,0,0.45)',
                  cursor: 'pointer',
                  overflow: 'hidden',
                  padding: 0,
                }}
              >
                <img
                  src={`${base}${img.url}`}
                  alt={img.prompt || img.name}
                  loading="lazy"
                  style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
                />
                <span
                  role="button"
                  tabIndex={0}
                  aria-label={`Supprimer ${img.name}`}
                  onClick={(e) => remove(img.name, e)}
                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') remove(img.name, e as unknown as React.MouseEvent); }}
                  className="absolute opacity-0 group-hover:opacity-100 flex items-center justify-center"
                  style={{
                    top: 2, right: 2, width: 15, height: 15,
                    background: 'rgba(0,0,0,0.7)', color: '#ff6b6b',
                    borderRadius: 2, transition: 'opacity 0.12s',
                  }}
                >
                  <X size={10} />
                </span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
