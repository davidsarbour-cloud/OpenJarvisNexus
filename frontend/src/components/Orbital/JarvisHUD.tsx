/**
 * JarvisHUD — 2D holographic overlay over the 3D scene (Iron-Man / J.A.R.V.I.S. look).
 *
 * Pure CSS/SVG, pointer-events: none so it never blocks the canvas controls.
 * A rotating reticle ring, a top "NEURAL OPERATING SYSTEM" header, and bottom
 * status readouts. Drop it as a sibling of <Canvas>.
 */
const CY = '#16e0ff';

export function JarvisHUD() {
  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        pointerEvents: 'none',
        zIndex: 5,
        fontFamily: '"Courier New", ui-monospace, monospace',
        color: CY,
        textShadow: `0 0 8px ${CY}`,
        userSelect: 'none',
      }}
    >
      <style>{`
        @keyframes jhud-spin     { to { transform: rotate(360deg); } }
        @keyframes jhud-spin-rev { to { transform: rotate(-360deg); } }
        @keyframes jhud-blink    { 0%,100%{opacity:1} 50%{opacity:.35} }
      `}</style>

      {/* top header bar */}
      <div
        style={{
          position: 'absolute', top: 18, left: '50%', transform: 'translateX(-50%)',
          display: 'flex', alignItems: 'center', gap: 14, whiteSpace: 'nowrap',
          fontSize: 13, letterSpacing: 4,
        }}
      >
        <span style={{ fontWeight: 700 }}>J·A·R·V·I·S</span>
        <span style={{ opacity: 0.7 }}>NEURAL OPERATING SYSTEM</span>
        <span style={{ opacity: 0.5 }}>v9.6.1</span>
        <span style={{ color: '#36f9a0', textShadow: '0 0 8px #36f9a0' }}>
          ● STATUS: ONLINE
        </span>
      </div>

      {/* (rotating reticle removed) */}

      {/* bottom readouts */}
      <div
        style={{
          position: 'absolute', bottom: 22, left: '50%', transform: 'translateX(-50%)',
          display: 'flex', gap: 26, fontSize: 11, letterSpacing: 3, opacity: 0.85,
        }}
      >
        <span>CORE STABLE</span>
        <span>NEURAL LOAD 42%</span>
        <span style={{ animation: 'jhud-blink 2s ease-in-out infinite' }}>◆ ALL SYSTEMS NOMINAL</span>
        <span>UPLINK SECURE</span>
      </div>
    </div>
  );
}
