import { useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

interface Props {
  /** number of particles */
  count?: number;
  /** orb radius in world units */
  radius?: number;
  /** core color */
  color?: string;
  /** base point size */
  size?: number;
  /** turbulence amount (higher = more scattered/galaxy, lower = tight ball) */
  turbulence?: number;
}

/**
 * NeuralOrb — the "arc reactor" / J.A.R.V.I.S. particle sphere.
 *
 * A dense cloud of additively-blended points filling a sphere volume, with
 * animated turbulence + twinkle in the vertex shader. Pair it with a strong
 * Bloom pass (PostFX) for the glowing core look.
 */
export function NeuralOrb({
  count = 30000,
  radius = 1.4,
  color = '#16e0ff',
  size = 9,
  turbulence = 0.045,
}: Props) {
  const pointsRef = useRef<THREE.Points>(null);
  const matRef = useRef<THREE.ShaderMaterial>(null);

  // positions (uniform sphere volume) + per-point scale/seed
  const { positions, scales } = useMemo(() => {
    const positions = new Float32Array(count * 3);
    const scales = new Float32Array(count);
    for (let i = 0; i < count; i++) {
      // random direction
      const u = Math.random() * 2 - 1;
      const theta = Math.random() * Math.PI * 2;
      const r = radius * Math.cbrt(Math.random()); // uniform in volume -> bright center via additive
      const s = Math.sqrt(1 - u * u);
      positions[i * 3] = r * s * Math.cos(theta);
      positions[i * 3 + 1] = r * s * Math.sin(theta);
      positions[i * 3 + 2] = r * u;
      scales[i] = 0.5 + Math.random() * 1.2;
    }
    return { positions, scales };
  }, [count, radius]);

  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uSize: { value: size },
      uColor: { value: new THREE.Color(color) },
      uTurb: { value: turbulence },
    }),
    [size, color, turbulence]
  );

  useFrame((state, delta) => {
    if (matRef.current) matRef.current.uniforms.uTime.value = state.clock.elapsedTime;
    if (pointsRef.current) {
      pointsRef.current.rotation.y += delta * 0.08;
      pointsRef.current.rotation.x += delta * 0.02;
    }
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        <bufferAttribute attach="attributes-aScale" args={[scales, 1]} />
      </bufferGeometry>
      <shaderMaterial
        ref={matRef}
        uniforms={uniforms}
        transparent
        depthWrite={false}
        blending={THREE.AdditiveBlending}
        vertexShader={/* glsl */ `
          uniform float uTime;
          uniform float uSize;
          uniform float uTurb;
          attribute float aScale;
          varying float vGlow;

          void main() {
            vec3 p = position;
            float t = uTime * 0.15;
            // cheap animated turbulence (swirling galaxy feel)
            vec3 n = vec3(
              sin(p.y * 3.0 + t)        + cos(p.z * 2.0 - t),
              sin(p.z * 3.0 + t * 1.1)  + cos(p.x * 2.0 - t),
              sin(p.x * 3.0 + t * 0.9)  + cos(p.y * 2.0 - t)
            );
            p += n * uTurb;

            // twinkle
            vGlow = 0.55 + 0.45 * sin(uTime * 2.0 + (p.x + p.y + p.z) * 8.0);

            vec4 mv = modelViewMatrix * vec4(p, 1.0);
            gl_PointSize = uSize * aScale * (1.0 / -mv.z);
            gl_Position = projectionMatrix * mv;
          }
        `}
        fragmentShader={/* glsl */ `
          uniform vec3 uColor;
          varying float vGlow;

          void main() {
            float d = length(gl_PointCoord - 0.5);
            if (d > 0.5) discard;
            float a = smoothstep(0.5, 0.0, d);          // soft round dot
            gl_FragColor = vec4(uColor * vGlow, a * 0.9);
          }
        `}
      />
    </points>
  );
}
