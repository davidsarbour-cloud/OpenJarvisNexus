/**
 * JarvisOrb — animated J.A.R.V.I.S core.
 * Concentric rotating rings (different speeds/directions) + pulsing center.
 * `speaking` intensifies everything while JARVIS responds: faster rings,
 * stronger glow, a breathing scale, radiating "sonar" pulses, and a live
 * voice-equalizer that replaces the centre label.
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
        @keyframes jarvisBreathe     { 0%,100% { transform: scale(1);   } 50% { transform: scale(1.03); } }
        @keyframes jarvisBreatheTalk { 0%,100% { transform: scale(.98); } 50% { transform: scale(1.06); } }
        @keyframes jarvisSonar { 0% { transform: scale(.5); opacity: .6 } 100% { transform: scale(1.25); opacity: 0 } }
        @keyframes jarvisBar   { 0%,100% { transform: scaleY(.3) } 50% { transform: scaleY(1) } }
        .jarvis-ring  { transform-origin: center; transform-box: fill-box; }
        .jarvis-sonar { transform-origin: center; transform-box: fill-box; }
      `}</style>

      {/* breathing wrapper — gentle idle pulse, deeper + faster while talking */}
      <div
        style={{
          width: '100%', height: '100%', position: 'relative',
          animation: `${speaking ? 'jarvisBreatheTalk 1.6s' : 'jarvisBreathe 5s'} ease-in-out infinite`,
        }}
      >
        {/* ambient glow */}
        <div
          style={{
            position: 'absolute', inset: '8%', borderRadius: '50%',
            background: 'radial-gradient(circle, var(--color-jarvis-glow) 0%, transparent 65%)',
            animation: 'jarvisGlow 3.2s ease-in-out infinite',
            opacity: speaking ? 0.75 : 0.4, transition: 'opacity .4s',
          }}
        />

        <svg
          viewBox="0 0 200 200"
          width={size}
          height={size}
          style={{
            position: 'relative',
            filter: `drop-shadow(0 0 ${speaking ? 26 : 12}px var(--color-jarvis-glow))`,
            transition: 'filter .4s',
          }}
        >
          {/* radiating sonar pulses — only while talking */}
          {speaking && (
            <>
              <circle
                className="jarvis-sonar" cx="100" cy="100" r="70" fill="none" stroke={c} strokeWidth="1.5"
                style={{ animation: 'jarvisSonar 1.8s ease-out infinite' }}
              />
              <circle
                className="jarvis-sonar" cx="100" cy="100" r="70" fill="none" stroke={c} strokeWidth="1.5"
                style={{ animation: 'jarvisSonar 1.8s ease-out infinite', animationDelay: '.9s' }}
              />
            </>
          )}

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

          {/* center label — hidden while the equalizer is live */}
          {!speaking && (
            <text
              x="100" y="105" textAnchor="middle" fontSize="13" letterSpacing="3" fontWeight="700" fill={c}
              style={{ filter: 'drop-shadow(0 0 6px var(--color-jarvis-glow))' }}
            >
              J.A.R.V.I.S
            </text>
          )}
        </svg>

        {/* live voice equalizer — overlaid centre, only while talking */}
        {speaking && (
          <div
            style={{
              position: 'absolute', inset: 0, display: 'flex',
              alignItems: 'center', justifyContent: 'center',
              gap: Math.max(2, size * 0.018), pointerEvents: 'none',
            }}
          >
            {[0, 1, 2, 3, 4].map((i) => (
              <div
                key={i}
                style={{
                  width: Math.max(2, size * 0.013),
                  height: size * 0.17,
                  background: c,
                  borderRadius: 999,
                  transformOrigin: 'center',
                  boxShadow: `0 0 ${size * 0.03}px var(--color-jarvis-glow)`,
                  animation: `jarvisBar ${0.5 + (i % 3) * 0.12}s ease-in-out ${i * 0.09}s infinite`,
                }}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
