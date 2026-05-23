import { useMemo, useRef, useState } from 'react';
import { useFrame, type ThreeEvent } from '@react-three/fiber';
import { Html } from '@react-three/drei';
import * as THREE from 'three';
import type { SpaceshipDef, ShipPattern } from './planets.config';

interface Props {
  def: SpaceshipDef;
  onSelect?: (def: SpaceshipDef) => void;
}

const TRAIL_LEN          = 64;
const PULSE_PERIOD       = 4.2;
const PULSE_DURATION     = 1.4;
const COMM_FLASH_PERIOD  = 7.3;
const COMM_FLASH_DUR     = 0.45;
const TAU = Math.PI * 2;

/**
 * Trajectory functions -- each pattern produces an intentional path.
 * Returns world-space (x, y, z) at parametrised time `t` (rad).
 *
 *   recon       -- circular inclined orbit, slow alt wobble.
 *   relay       -- rose curve with 5-petal modulation -> ship sweeps
 *                  through 5 distinct "docking points" per cycle.
 *   maintenance -- 2:1 Lissajous (figure-8) between two adjacent rings.
 *   patrol      -- wide outer circle with large vertical sweep.
 *
 * All return a stable, repeatable path -- not noise.
 */
function computePosition(
  pattern: ShipPattern,
  t: number,
  scale: number,
  scale2: number,
): { x: number; y: number; z: number } {
  switch (pattern) {
    case 'recon': {
      return {
        x: Math.cos(t) * scale,
        y: Math.sin(t * 1.3) * scale2,
        z: Math.sin(t) * scale,
      };
    }
    case 'relay': {
      // 5-petal rose: r(theta) = scale + scale2 * sin(2.5 * theta)
      const r = scale + Math.sin(t * 2.5) * scale2;
      return {
        x: Math.cos(t) * r,
        y: Math.sin(t * 5) * 0.5,
        z: Math.sin(t) * r,
      };
    }
    case 'maintenance': {
      // Figure-8 in XZ plane (Lissajous 2:1)
      return {
        x: Math.sin(t * 2) * scale,
        y: Math.sin(t * 3) * 0.4,
        z: Math.sin(t) * scale2,
      };
    }
    case 'patrol': {
      return {
        x: Math.cos(t) * scale,
        y: Math.sin(t * 1.7) * scale2,
        z: Math.sin(t) * scale,
      };
    }
  }
}

/**
 * Spaceship -- UFO drone following an intentional mission pattern.
 *
 * Body silhouette: LatheGeometry saucer with rim torus and 3 blinking
 * signal lights. The drone banks slightly toward the motion vector so
 * it looks like it's "flying through" its path rather than floating.
 *
 * Other layers (world-space): wake trail (64 verts), scanner pulse
 * (periodic billboard ring), comm flash (periodic emissive surge).
 */
export function Spaceship({ def, onSelect }: Props) {
  const groupRef     = useRef<THREE.Group>(null);
  const innerRef     = useRef<THREE.Group>(null);
  const bodyMatRef   = useRef<THREE.MeshStandardMaterial>(null);
  const rimRef       = useRef<THREE.Mesh>(null);
  const pulseRef     = useRef<THREE.Mesh>(null);
  const pulseMatRef  = useRef<THREE.MeshBasicMaterial>(null);
  const sig1Ref      = useRef<THREE.MeshBasicMaterial>(null);
  const sig2Ref      = useRef<THREE.MeshBasicMaterial>(null);
  const sig3Ref      = useRef<THREE.MeshBasicMaterial>(null);
  const [hover, setHover] = useState(false);

  const saucerGeom = useMemo(() => {
    const pts = [
      new THREE.Vector2(0.000,  0.060),
      new THREE.Vector2(0.025,  0.058),
      new THREE.Vector2(0.050,  0.050),
      new THREE.Vector2(0.080,  0.035),
      new THREE.Vector2(0.115,  0.018),
      new THREE.Vector2(0.160,  0.008),
      new THREE.Vector2(0.200,  0.002),
      new THREE.Vector2(0.220,  0.000),
      new THREE.Vector2(0.200, -0.005),
      new THREE.Vector2(0.160, -0.012),
      new THREE.Vector2(0.110, -0.020),
      new THREE.Vector2(0.060, -0.022),
      new THREE.Vector2(0.030, -0.020),
      new THREE.Vector2(0.000, -0.018),
    ];
    return new THREE.LatheGeometry(pts, 32);
  }, []);

  const trail = useMemo(() => {
    const positions = new Float32Array(TRAIL_LEN * 3);
    const colors    = new Float32Array(TRAIL_LEN * 3);
    const col = new THREE.Color(def.color);
    for (let i = 0; i < TRAIL_LEN; i++) {
      const t = 1 - i / (TRAIL_LEN - 1);
      const fade = t * t;
      colors[i * 3]     = col.r * fade * 1.4;
      colors[i * 3 + 1] = col.g * fade * 1.4;
      colors[i * 3 + 2] = col.b * fade * 1.4;
    }
    const geom = new THREE.BufferGeometry();
    geom.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geom.setAttribute('color',    new THREE.BufferAttribute(colors,    3));
    const mat = new THREE.LineBasicMaterial({
      vertexColors: true,
      transparent: true,
      opacity: 1.0,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    });
    return { line: new THREE.Line(geom, mat), positions };
  }, [def.color]);

  // Pre-allocated vectors / matrix reused each frame (no GC pressure)
  const tmpPrev   = useMemo(() => new THREE.Vector3(), []);
  const tmpNext   = useMemo(() => new THREE.Vector3(), []);
  const tmpUp     = useMemo(() => new THREE.Vector3(0, 1, 0), []);
  const tmpLookAt = useMemo(() => new THREE.Matrix4(), []);
  const tmpQuat   = useMemo(() => new THREE.Quaternion(), []);

  useFrame(({ clock, camera }) => {
    if (!groupRef.current) return;
    const t = clock.elapsedTime * def.speed + def.phase;
    const scale  = def.scale;
    const scale2 = def.scale2 ?? 1.5;

    const pos = computePosition(def.pattern, t, scale, scale2);
    groupRef.current.position.set(pos.x, pos.y, pos.z);

    // ---- Orientation: bank toward the velocity vector ----
    // Sample ahead by a tiny dt to derive heading. Build a look-at
    // quaternion (forward = velocity, up = world-Y) and slerp partway
    // so the saucer banks ~25% of the way to facing motion -- enough
    // to read as "intentional flight", not enough to look like a jet.
    const tNext = t + 0.03;
    const next  = computePosition(def.pattern, tNext, scale, scale2);
    tmpPrev.set(pos.x, pos.y, pos.z);
    tmpNext.set(next.x, next.y, next.z);
    tmpLookAt.lookAt(tmpPrev, tmpNext, tmpUp);
    tmpQuat.setFromRotationMatrix(tmpLookAt);
    groupRef.current.quaternion.slerp(tmpQuat, 0.18);

    // Inner spin -- saucer signature UFO Y rotation (continuous)
    if (innerRef.current) {
      innerRef.current.rotation.y = clock.elapsedTime * 1.4;
    }
    if (rimRef.current) {
      rimRef.current.rotation.y = -clock.elapsedTime * 0.9;
    }

    // ---- Trail ----
    const buf = trail.positions;
    for (let i = TRAIL_LEN - 1; i > 0; i--) {
      buf[i * 3]     = buf[(i - 1) * 3];
      buf[i * 3 + 1] = buf[(i - 1) * 3 + 1];
      buf[i * 3 + 2] = buf[(i - 1) * 3 + 2];
    }
    buf[0] = pos.x; buf[1] = pos.y; buf[2] = pos.z;
    trail.line.geometry.attributes.position.needsUpdate = true;

    // ---- Scanner pulse ----
    const cyc = (clock.elapsedTime + def.phase * 0.3) % PULSE_PERIOD;
    if (pulseRef.current && pulseMatRef.current) {
      if (cyc < PULSE_DURATION) {
        const p = cyc / PULSE_DURATION;
        pulseRef.current.visible = true;
        pulseRef.current.position.set(pos.x, pos.y, pos.z);
        pulseRef.current.quaternion.copy(camera.quaternion);
        pulseRef.current.scale.setScalar(0.35 + p * 1.7);
        pulseMatRef.current.opacity = 0.5 * (1 - p);
      } else {
        pulseRef.current.visible = false;
      }
    }

    // ---- Comm flash ----
    const commCyc = (clock.elapsedTime + def.phase * 0.7) % COMM_FLASH_PERIOD;
    const docking = commCyc < COMM_FLASH_DUR;

    // ---- Signal blinks ----
    const bl1 = Math.sin(clock.elapsedTime * 3.7 + def.phase * 1.3) > 0.55 ? 1 : 0;
    const bl2 = Math.sin(clock.elapsedTime * 2.4 + def.phase * 0.9 + 1.5) > 0.45 ? 1 : 0;
    const bl3 = docking ? (Math.sin(clock.elapsedTime * 18.0) > 0 ? 1 : 0)
                        : (Math.sin(clock.elapsedTime * 0.9 + def.phase) > 0.85 ? 1 : 0);
    if (sig1Ref.current) sig1Ref.current.opacity = 0.25 + bl1 * 0.75;
    if (sig2Ref.current) sig2Ref.current.opacity = 0.25 + bl2 * 0.7;
    if (sig3Ref.current) sig3Ref.current.opacity = 0.2  + bl3 * 0.8;

    if (bodyMatRef.current) {
      const target = docking ? 2.6 : (hover ? 2.0 : 1.3);
      bodyMatRef.current.emissiveIntensity = target;
    }
    void TAU; // satisfy lint (TAU exported for shader consumers if needed)
  });

  const handleClick = (e: ThreeEvent<MouseEvent>) => {
    e.stopPropagation();
    onSelect?.(def);
  };

  return (
    <>
      <primitive object={trail.line} />

      <mesh ref={pulseRef} visible={false}>
        <ringGeometry args={[0.22, 0.30, 32]} />
        <meshBasicMaterial
          ref={pulseMatRef}
          color={def.color}
          transparent
          opacity={0}
          side={THREE.DoubleSide}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </mesh>

      {/* Outer group: heading + position. Inner group: independent spin. */}
      <group ref={groupRef}>
        <group ref={innerRef}>
          <mesh
            onClick={handleClick}
            onPointerOver={(e) => { e.stopPropagation(); setHover(true); document.body.style.cursor = 'pointer'; }}
            onPointerOut={()    => { setHover(false); document.body.style.cursor = 'default'; }}
          >
            <primitive object={saucerGeom} attach="geometry" />
            <meshStandardMaterial
              ref={bodyMatRef}
              color={def.color}
              emissive={def.color}
              emissiveIntensity={1.3}
              roughness={0.35}
              metalness={0.55}
              side={THREE.DoubleSide}
            />
          </mesh>

          <mesh ref={rimRef}>
            <torusGeometry args={[0.222, 0.006, 6, 64]} />
            <meshBasicMaterial
              color={def.color}
              transparent
              opacity={0.9}
              depthWrite={false}
              blending={THREE.AdditiveBlending}
            />
          </mesh>

          <mesh position={[0, 0.075, 0]}>
            <sphereGeometry args={[0.038, 12, 12]} />
            <meshBasicMaterial
              ref={sig1Ref}
              color={def.color}
              transparent
              opacity={0.6}
              depthWrite={false}
              blending={THREE.AdditiveBlending}
            />
          </mesh>
          <mesh position={[0.22, 0, 0]}>
            <sphereGeometry args={[0.030, 12, 12]} />
            <meshBasicMaterial
              ref={sig2Ref}
              color={def.color}
              transparent
              opacity={0.55}
              depthWrite={false}
              blending={THREE.AdditiveBlending}
            />
          </mesh>
          <mesh position={[0, -0.028, 0]}>
            <sphereGeometry args={[0.042, 12, 12]} />
            <meshBasicMaterial
              ref={sig3Ref}
              color="#ffffff"
              transparent
              opacity={0.5}
              depthWrite={false}
              blending={THREE.AdditiveBlending}
            />
          </mesh>
        </group>

        {hover && (
          <Html center position={[0, 0.18, 0]} style={{ pointerEvents: 'none' }}>
            <div
              style={{
                fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
                fontSize: 9,
                fontWeight: 700,
                letterSpacing: '0.22em',
                color: def.color,
                background: 'rgba(2,5,11,0.85)',
                border: `1px solid ${def.color}`,
                padding: '1px 5px',
                whiteSpace: 'nowrap',
                textShadow: `0 0 6px ${def.glow}`,
              }}
            >
              {def.label}
            </div>
          </Html>
        )}
      </group>
    </>
  );
}
