/**
 * JarvisOrb — animated J.A.R.V.I.S core.
 * Concentric rotating rings (different speeds/directions) + pulsing center.
 * `speaking` intensifies the animation + glow while JARVIS responds.
 */
export function JarvisOrb({ speaking = false, size = 280 }: { speaking?: boolean; size?: number }) {
  const c = 'var(--color-jarvis)';
  const d1 = speaking ? '7s' : '26s';
  const d2 = speaking ? '5s' : '20s';
  const d3 = speaking ? '4s' : '32s';

  return (
    <div style={{ width: size, height: size, position: 'relative', userSelect: 'none' }}>
      <style>{`
        @keyframes jarvisCW  { from { transform: rotate(0deg);   } to { transform: rotate(360deg);  } }
        @keyframes jarvisCCW { from { transform: rotate(0deg);   } to { transform: rotate(-360deg); } }
        @keyframes jarvisPulse { 0%,100% { opacity: .5 } 50% { opacity: 1 } }
        @keyframes jarvisGlow  { 0%,100% { opacity: .25 } 50% { opacity: .55 } }
        .jarvis-ring { transform-origin: 100px 100px; transform-box: fill-box; }
      `}</style>

      {/* ambient glow */}
      <div
        style={{
          position: 'absolute', inset: '8%', borderRadius: '50%',
          background: 'radial-gradient(circle, var(--color-jarvis-glow) 0%, transparent 65%)',
          animation: 'jarvisGlow 3.2s ease-in-out infinite',
          opacity: speaking ? 0.7 : 0.4, transition: 'opacity .4s',
        }}
      />

      <svg
        viewBox="0 0 200 200"
        width={size}
        height={size}
        style={{
          position: 'relative',
          filter: `drop-shadow(0 0 ${speaking ? 22 : 12}px var(--color-jarvis-glow))`,
          transition: 'filter .4s',
        }}
      >
        {/* outer faint dashed ring — slow CW */}
        <g className="jarvis-ring" style={{ animation: `jarvisCW ${d1} linear infinite` }}>
          <circle cx="100" cy="100" r="94" fill="none" stroke={c} strokeWidth="1" opacity="0.35" strokeDasharray="2 7" />
        </g>

        {/* bold arc segments — medium CW */}
        <g className="jarvis-ring" style={{ animation: `jarvisCW ${d2} linear infinite` }}>
          <circle cx="100" cy="100" r="83" fill="none" stroke={c} strokeWidth="3" opacity="0.7" strokeLinecap="round" strokeDasharray="46 90" />
          <circle cx="100" cy="100" r="83" fill="none" stroke={c} strokeWidth="3" opacity="0.5" strokeLinecap="round" strokeDasharray="14 60" strokeDashoffset="160" />
        </g>

        {/* tick-mark ring — CCW */}
        <g className="jarvis-ring" style={{ animation: `jarvisCCW ${d3} linear infinite` }}>
          <circle cx="100" cy="100" r="70" fill="none" stroke={c} strokeWidth="6" opacity="0.45" strokeDasharray="1 5" />
        </g>

        {/* inner segmented ring — CCW faster */}
        <g className="jarvis-ring" style={{ animation: `jarvisCCW ${d2} linear infinite` }}>
          <circle cx="100" cy="100" r="56" fill="none" stroke={c} strokeWidth="2.5" opacity="0.75" strokeLinecap="round" strokeDasharray="60 50" />
        </g>

        {/* pulsing core ring */}
        <circle
          cx="100" cy="100" r="44" fill="none" stroke={c} strokeWidth="1.5" opacity="0.85"
          style={{ animation: 'jarvisPulse 2.4s ease-in-out infinite' }}
        />

        {/* center label */}
        <text
          x="100" y="105" textAnchor="middle" fontSize="13" letterSpacing="3" fontWeight="700" fill={c}
          style={{ filter: 'drop-shadow(0 0 6px var(--color-jarvis-glow))' }}
        >
          J.A.R.V.I.S
        </text>
      </svg>
    </div>
  );
}
