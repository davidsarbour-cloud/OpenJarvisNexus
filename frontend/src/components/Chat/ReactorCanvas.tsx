import { Canvas } from '@react-three/fiber';
import { NeuralOrb } from '../Orbital/NeuralOrb';

/**
 * ReactorCanvas — arc-reactor particle core for the chat JARVIS orb.
 *
 * NO postprocessing on purpose: the EffectComposer makes the canvas opaque
 * (a visible square over the page grid). Keeping a plain transparent canvas
 * lets the grid show through — no box. The glow comes from the additive
 * particles themselves + the CSS halo behind the orb.
 */
export function ReactorCanvas({ speaking = false }: { speaking?: boolean }) {
  return (
    <Canvas
      style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}
      camera={{ position: [0, 0, 3.2], fov: 50 }}
      dpr={[1, 2]}
      gl={{ alpha: true, antialias: true }}
    >
      <NeuralOrb
        count={64000}
        radius={1.15}
        color="#1ce6ff"
        size={speaking ? 5 : 4.5}
        turbulence={0.018}
      />
    </Canvas>
  );
}
