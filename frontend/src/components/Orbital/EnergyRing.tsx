import { useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

interface Props {
  /** Center radius of the torus. */
  radius: number;
  /** Tube cross-section radius. */
  tubeRadius: number;
  /** Glow color. */
  color: string;
  /** Tube segments around the main ring. */
  segments?: number;
  /** Cross-section tessellation. */
  tubeSegments?: number;
  /** Speed at which energy pulses travel around the ring. */
  flowSpeed?: number;
  /** Base alpha at the brightest sections. */
  baseOpacity?: number;
  /** Phase offset (rad) so several rings desync. */
  phase?: number;
}

/**
 * EnergyRing -- shader-driven torus that breaks vector-circle uniformity.
 *
 * Vertex shader: displaces each ring vertex along its tube normal using
 * a noise function of (angle, time). Tube thickness varies continuously
 * around the ring -- no two segments look identical.
 *
 * Fragment shader: alpha is the product of:
 *   - "flow" pulses traveling along the circumference (high freq)
 *   - a slow gating noise that creates random dim/bright zones
 *   - a Fresnel-on-tube term so the ring brightens at grazing view
 *
 * No depth-write, additive blending -- composites cleanly under bloom.
 */
export function EnergyRing({
  radius,
  tubeRadius,
  color,
  segments     = 128,
  tubeSegments = 10,
  flowSpeed    = 1.0,
  baseOpacity  = 0.55,
  phase        = 0,
}: Props) {
  const material = useMemo(() => {
    return new THREE.ShaderMaterial({
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      side: THREE.DoubleSide,
      uniforms: {
        uTime:        { value: 0 },
        uColor:       { value: new THREE.Color(color) },
        uFlowSpeed:   { value: flowSpeed },
        uBaseOpacity: { value: baseOpacity },
        uPhase:       { value: phase },
      },
      vertexShader: `
uniform float uTime;
uniform float uPhase;
varying float vAngle;
varying vec3  vWorldNormal;
varying vec3  vWorldPos;

float hash(float n) { return fract(sin(n) * 43758.5453); }
float n1d(float x) {
  float i = floor(x);
  float f = fract(x);
  f = f * f * (3.0 - 2.0 * f);
  return mix(hash(i), hash(i + 1.0), f);
}

void main() {
  float angle = atan(position.z, position.x);
  vAngle = angle;

  // Two octaves of 1D noise drive tube-thickness variation
  float t1 = n1d(angle * 2.3 + uTime * 0.35 + uPhase);
  float t2 = n1d(angle * 6.1 - uTime * 0.18 + uPhase);
  float thickMod = (t1 * 0.7 + t2 * 0.4) - 0.5;

  // Displace each surface vertex along its normal -- tube swells/thins
  vec3 displaced = position + normal * thickMod * 0.018;

  vec4 wp = modelMatrix * vec4(displaced, 1.0);
  vWorldPos    = wp.xyz;
  vWorldNormal = normalize(mat3(modelMatrix) * normal);
  gl_Position  = projectionMatrix * viewMatrix * wp;
}
      `,
      fragmentShader: `
uniform float uTime;
uniform vec3  uColor;
uniform float uFlowSpeed;
uniform float uBaseOpacity;
uniform float uPhase;
varying float vAngle;
varying vec3  vWorldNormal;
varying vec3  vWorldPos;

float hash(float n) { return fract(sin(n) * 43758.5453); }
float n1d(float x) {
  float i = floor(x);
  float f = fract(x);
  f = f * f * (3.0 - 2.0 * f);
  return mix(hash(i), hash(i + 1.0), f);
}

void main() {
  // Normalize angle to [0,1] for flow math
  float u = vAngle / 6.2831853 + 0.5 + uPhase * 0.15915;

  // Two pulse layers travelling along the ring at different freqs/speeds
  float pulseA = 0.5 + 0.5 * sin((u + uTime * uFlowSpeed * 0.12) * 6.2831853 * 9.0);
  float pulseB = 0.5 + 0.5 * sin((u - uTime * uFlowSpeed * 0.05) * 6.2831853 * 3.0);

  // Slow gating noise: chops the ring into bright/dim arcs
  float gate = smoothstep(0.32, 0.62, n1d(vAngle * 3.4 + uTime * 0.07 + uPhase));

  // Fresnel on the tube cross-section -- brightens at grazing view
  vec3  viewDir = normalize(cameraPosition - vWorldPos);
  float rim     = pow(1.0 - max(dot(viewDir, vWorldNormal), 0.0), 1.6);

  float energy = mix(pulseA, 1.0, 0.35) * (0.35 + 0.65 * pulseB) * (0.3 + 0.7 * gate);
  float alpha  = uBaseOpacity * energy * (0.55 + 0.6 * rim);

  gl_FragColor = vec4(uColor, alpha);
}
      `,
    });
  }, [color, flowSpeed, baseOpacity, phase]);

  // R3F useFrame: shader-uniform mutation is per-frame, not per-render —
  // the new react-hooks/immutability rule can't distinguish the two.
  useFrame(({ clock }) => {
    // eslint-disable-next-line react-hooks/immutability
    material.uniforms.uTime.value = clock.elapsedTime;
  });

  return (
    <mesh>
      <torusGeometry args={[radius, tubeRadius, tubeSegments, segments]} />
      <primitive object={material} attach="material" />
    </mesh>
  );
}
