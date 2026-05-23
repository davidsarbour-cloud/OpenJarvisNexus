import { useMemo } from 'react';
import * as THREE from 'three';

interface Props {
  /** Outer shell radius (should slightly exceed the body it wraps). */
  radius: number;
  /** Glow color (hex / CSS). */
  color: string;
  /** Power curve — higher = thinner rim, lower = broader halo. Default 2.4. */
  power?: number;
  /** Output multiplier. Keep ≤ 1.0 to stay below bloom luminance threshold. */
  intensity?: number;
  /** Geometry segments. 32 is plenty for a soft shell. */
  segments?: number;
}

/**
 * FresnelShell — a transparent sphere with a rim-glow ShaderMaterial.
 *
 * The fragment computes a Fresnel term (1 − dot(viewDir, normal))^power.
 * Result: edges glow strongly (silhouette), center is fully transparent.
 * Front-side, additive, no depth-write — composites cleanly over the
 * planet body underneath without occluding it.
 *
 * Use it to wrap planets ("atmosphere") or the JARVIS core ("corona").
 * One shared, low-cost material per instance — no postprocessing needed.
 */
export function FresnelShell({
  radius,
  color,
  power = 2.4,
  intensity = 0.9,
  segments = 32,
}: Props) {
  const material = useMemo(() => {
    return new THREE.ShaderMaterial({
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      side: THREE.FrontSide,
      uniforms: {
        uColor:     { value: new THREE.Color(color) },
        uPower:     { value: power },
        uIntensity: { value: intensity },
      },
      vertexShader: /* glsl */ `
        varying vec3 vWorldPos;
        varying vec3 vWorldNormal;
        void main() {
          vec4 wp = modelMatrix * vec4(position, 1.0);
          vWorldPos    = wp.xyz;
          vWorldNormal = normalize(mat3(modelMatrix) * normal);
          gl_Position  = projectionMatrix * viewMatrix * wp;
        }
      `,
      fragmentShader: /* glsl */ `
        uniform vec3  uColor;
        uniform float uPower;
        uniform float uIntensity;
        varying vec3  vWorldPos;
        varying vec3  vWorldNormal;
        void main() {
          vec3  viewDir = normalize(cameraPosition - vWorldPos);
          float ndotv   = max(dot(viewDir, vWorldNormal), 0.0);
          float fres    = pow(1.0 - ndotv, uPower);
          // Premultiplied-alpha additive: alpha drives output magnitude.
          gl_FragColor = vec4(uColor * uIntensity * fres, fres);
        }
      `,
    });
  }, [color, power, intensity]);

  return (
    <mesh>
      <sphereGeometry args={[radius, segments, segments]} />
      <primitive object={material} attach="material" />
    </mesh>
  );
}
