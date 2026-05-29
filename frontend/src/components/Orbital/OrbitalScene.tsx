import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router';
import * as THREE from 'three';
import { Starfield } from './Starfield';
import { JarvisCore } from './JarvisCore';
import { Planet } from './Planet';
import { Spaceship } from './Spaceship';
import { OrbitRing } from './OrbitRing';
import { ModulePanel } from './ModulePanel';
import { PostFX } from './PostFX';
import {
  PLANETS,
  SPACESHIPS,
  type PlanetDef,
  type SpaceshipDef,
  type JarvisDef,
} from './planets.config';
import { useNexusStore } from '../../systems/nexusStore';

type Selection =
  | { kind: 'planet'; def: PlanetDef }
  | { kind: 'ship';   def: SpaceshipDef }
  | { kind: 'jarvis'; def: JarvisDef }
  | null;

/**
 * CameraBreathing -- animates the OrbitControls target along soft sin
 * curves so the camera never feels locked. Amplitudes tiny.
 */
function CameraBreathing({
  controlsRef,
}: {
  controlsRef: React.RefObject<{ target: THREE.Vector3 } | null>;
}) {
  useFrame(({ clock }) => {
    const ctrl = controlsRef.current;
    if (!ctrl) return;
    const t = clock.elapsedTime;
    ctrl.target.y = Math.sin(t * 0.18) * 0.15;
    ctrl.target.x = Math.cos(t * 0.13) * 0.08;
  });
  return null;
}

/**
 * OrbitalScene -- the whole Three.js stage as a self-contained component.
 *
 * Camera: [9, 6, 14] ~ distance 18, FOV 50. Backdrop: 3 star layers +
 * linear scene fog. Selection triggers the right-side ModulePanel for
 * planets, ships, or the JARVIS core.
 */
export function OrbitalScene() {
  const [selection, setSelection] = useState<Selection>(null);
  const setSelectedPlanet = useNexusStore((s) => s.setSelectedPlanet);
  const setFocusedService = useNexusStore((s) => s.setFocusedService);
  const navigate = useNavigate();

  const [canvasKey, setCanvasKey] = useState(0);
  const [lost, setLost] = useState(false);
  const lostTimer = useRef<number | null>(null);

  const controlsRef = useRef<{ target: THREE.Vector3 } | null>(null);

  const onPlanetSelect = (d: PlanetDef) => {
    // Click a planet → jump to its world page (forge → /world/forge, etc.),
    // like the sidebar hub icons. Keep the store in sync for the rest of the UI.
    setSelectedPlanet(d.id);
    setFocusedService(d.id);
    navigate(d.route ?? `/world/${d.id}`);
  };

  const onShipSelect = (d: SpaceshipDef) => {
    setSelection({ kind: 'ship', def: d });
    setFocusedService(d.id);
  };

  const onJarvisSelect = (d: JarvisDef) => {
    setSelection({ kind: 'jarvis', def: d });
    setFocusedService('jarvis');
  };

  const reinit = () => {
    if (lostTimer.current) {
      window.clearTimeout(lostTimer.current);
      lostTimer.current = null;
    }
    setLost(false);
    setCanvasKey((k) => k + 1);
  };

  useEffect(() => {
    return () => {
      if (lostTimer.current) window.clearTimeout(lostTimer.current);
    };
  }, []);

  return (
    <div className="absolute inset-0">
      <Canvas
        key={canvasKey}
        camera={{ position: [20, 14, 31], fov: 50, near: 0.1, far: 200 }}
        dpr={[1, 2]}
        gl={{ antialias: true, alpha: false, powerPreference: 'high-performance' }}
        onCreated={({ gl }) => {
          gl.setClearColor(new THREE.Color('#010204'));
          gl.toneMapping = THREE.ACESFilmicToneMapping;
          gl.toneMappingExposure = 0.95;

          const canvas = gl.domElement;

          const onLost = (e: Event) => {
            e.preventDefault();
            setLost(true);
            if (lostTimer.current) window.clearTimeout(lostTimer.current);
            lostTimer.current = window.setTimeout(() => {
              setCanvasKey((k) => k + 1);
              setLost(false);
              lostTimer.current = null;
            }, 5000);
          };

          const onRestored = () => {
            if (lostTimer.current) {
              window.clearTimeout(lostTimer.current);
              lostTimer.current = null;
            }
            setLost(false);
          };

          canvas.addEventListener('webglcontextlost', onLost, false);
          canvas.addEventListener('webglcontextrestored', onRestored, false);
        }}
      >
        <fog attach="fog" args={['#010204', 40, 140]} />

        <Starfield />

        <ambientLight intensity={0.2} color="#3a5878" />
        <hemisphereLight args={['#0080a0', '#000010', 0.35]} />

        <JarvisCore onSelect={onJarvisSelect} />

        {PLANETS.map((p) => (
          <OrbitRing key={`ring-${p.id}`} radius={p.orbit} color={p.color} tilt={p.tilt} />
        ))}

        {PLANETS.map((p) => (
          <Planet
            key={p.id}
            def={p}
            onSelect={onPlanetSelect}
          />
        ))}

        {SPACESHIPS.map((s) => (
          <Spaceship
            key={s.id}
            def={s}
            onSelect={onShipSelect}
          />
        ))}

        <OrbitControls
          ref={controlsRef as unknown as React.Ref<never>}
          enablePan={false}
          enableDamping
          dampingFactor={0.06}
          minDistance={6}
          maxDistance={52}
          maxPolarAngle={Math.PI * 0.85}
          autoRotate
          autoRotateSpeed={0.18}
        />

        <CameraBreathing controlsRef={controlsRef} />

        <PostFX />
      </Canvas>

      {lost && (
        <div
          className="absolute top-4 left-1/2 -translate-x-1/2 px-4 py-2 flex items-center gap-3 z-10"
          style={{
            background: 'rgba(0,0,0,0.85)',
            border: '1px solid var(--color-security)',
            color: 'var(--color-security)',
            fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
            fontSize: 11,
            letterSpacing: '0.22em',
          }}
        >
          <span>WEBGL CONTEXT LOST - ATTEMPTING RECOVERY...</span>
          <button
            onClick={reinit}
            className="px-2 py-0.5 text-[10px] tracking-[0.25em] cursor-pointer"
            style={{
              border: '1px solid var(--color-security)',
              background: 'transparent',
              color: 'var(--color-security)',
            }}
          >
            REINIT
          </button>
        </div>
      )}

      {selection && (
        <ModulePanel
          selection={selection}
          onClose={() => setSelection(null)}
        />
      )}

    </div>
  );
}
