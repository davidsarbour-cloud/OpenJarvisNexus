import { useMemo, useRef, useState } from 'react';
import { useFrame, type ThreeEvent } from '@react-three/fiber';
import { Html } from '@react-three/drei';
import * as THREE from 'three';
import type { PlanetDef } from './planets.config';
import { FresnelShell } from './FresnelShell';

interface PlanetProps {
  def: PlanetDef;
  onSelect: (def: PlanetDef) => void;
}

/**
 * Planet -- sci-fi technological world.
 *
 * - Pure XZ orbit inside a tilted wrapper group (same rotation as the
 *   matching OrbitRing -> planet pinned to its line).
 * - MeshStandardMaterial enriched via onBeforeCompile:
 *     albedo variation / patches / gas-giant bands / circuit veins /
 *     body fresnel rim. Optional FIRE overlay (FORGE only).
 * - Optional Saturn-style 2-band RING (CYBERDECK).
 * - Tight FresnelShell silhouette.
 */
export function Planet({ def, onSelect }: PlanetProps) {
  const groupRef = useRef<THREE.Group>(null);
  const meshRef  = useRef<THREE.Mesh>(null);
  const [hover, setHover] = useState(false);

  const material = useMemo(() => {
    const mat = new THREE.MeshStandardMaterial({
      color: def.color,
      emissive: def.color,
      emissiveIntensity: 0.35,
      roughness: 0.55,
      metalness: 0.2,
    });

    // Conditional fire layer GLSL -- only injected when def.fire is true.
    const fireGLSL = def.fire ? `
// FIRE: red-orange high-frequency eruptions with 6Hz flicker.
// Subtle and threshold-gated so the planet stays its native colour
// most of the surface; only "hot spots" burn through.
vec3 fp = vObjectPos * 4.2 + vec3(uTime * 0.08, uTime * 0.12, uTime * 0.05);
float fnoise = vnoise3(fp);
float fire = smoothstep(0.62, 0.90, fnoise);
fire *= 0.65 + 0.35 * sin(uTime * 6.0 + fnoise * 10.0);
vec3 fireColor = vec3(1.0, 0.42, 0.12);
totalEmissiveRadiance += fireColor * fire * 1.4;
` : '';

    mat.onBeforeCompile = (shader) => {
      shader.uniforms.uTime = { value: 0 };

      shader.vertexShader = shader.vertexShader
        .replace(
          '#include <common>',
          `#include <common>
varying vec3 vObjectPos;`
        )
        .replace(
          '#include <begin_vertex>',
          `#include <begin_vertex>
vObjectPos = position;`
        );

      shader.fragmentShader = shader.fragmentShader
        .replace(
          '#include <common>',
          `#include <common>
uniform float uTime;
varying vec3 vObjectPos;

float hash3(vec3 p) {
  p = fract(p * 0.3183099 + vec3(0.71, 0.113, 0.419));
  p *= 17.0;
  return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
}

float vnoise3(vec3 p) {
  vec3 i = floor(p);
  vec3 f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  return mix(
    mix(mix(hash3(i + vec3(0.0,0.0,0.0)), hash3(i + vec3(1.0,0.0,0.0)), f.x),
        mix(hash3(i + vec3(0.0,1.0,0.0)), hash3(i + vec3(1.0,1.0,0.0)), f.x), f.y),
    mix(mix(hash3(i + vec3(0.0,0.0,1.0)), hash3(i + vec3(1.0,0.0,1.0)), f.x),
        mix(hash3(i + vec3(0.0,1.0,1.0)), hash3(i + vec3(1.0,1.0,1.0)), f.x), f.y),
    f.z
  );
}
`
        )
        .replace(
          '#include <color_fragment>',
          `#include <color_fragment>
float albedoN = vnoise3(vObjectPos * 0.95 - vec3(uTime * 0.005, 0.0, 0.0));
diffuseColor.rgb *= 0.91 + 0.18 * albedoN;
`
        )
        .replace(
          '#include <emissivemap_fragment>',
          `#include <emissivemap_fragment>

vec3 np = vObjectPos * 3.2;
float n1 = vnoise3(np + vec3(0.0, uTime * 0.03, 0.0));
float n2 = vnoise3(np * 2.4 - vec3(uTime * 0.02, 0.0, uTime * 0.015));
float patches = smoothstep(0.58, 0.88, n1 * 0.7 + n2 * 0.35);

float lat   = vObjectPos.y / max(length(vObjectPos), 0.0001);
float bands = sin(lat * 6.0 + n1 * 2.5 + uTime * 0.25);
bands       = pow(0.5 + 0.5 * bands, 5.0) * 0.25;

vec3 vp = vObjectPos * 7.5 + vec3(0.0, 0.0, uTime * 0.03);
float vRaw = vnoise3(vp);
float veins = smoothstep(0.74, 0.84, vRaw) * 0.9;

vec3 V = normalize(vViewPosition);
float bodyFres = pow(1.0 - max(dot(normalize(normal), V), 0.0), 2.6);
float atmRim = bodyFres * 0.55;

totalEmissiveRadiance += emissive * (patches * 1.3 + bands + veins + atmRim);
${fireGLSL}
`
        );

      mat.userData.shader = shader;
    };

    return mat;
  }, [def.color, def.fire]);

  // R3F useFrame runs per animation frame (rAF), not per React render —
  // mutating mesh refs / Three.js objects here is the canonical pattern.
  // The new react-hooks/immutability rule can't distinguish render time
  // from frame time, so we silence it across the whole useFrame body.
  /* eslint-disable react-hooks/immutability */
  useFrame(({ clock }) => {
    if (!groupRef.current) return;
    const t = clock.elapsedTime * def.speed + def.phase;
    groupRef.current.position.x = Math.cos(t) * def.orbit;
    groupRef.current.position.z = Math.sin(t) * def.orbit;
    groupRef.current.position.y = 0;

    if (meshRef.current) {
      meshRef.current.rotation.y = clock.elapsedTime * 0.25;
      const k = hover ? 1.12 : 1;
      meshRef.current.scale.lerp(new THREE.Vector3(k, k, k), 0.12);
    }

    const shader = (material.userData as { shader?: { uniforms: { uTime: { value: number } } } }).shader;
    if (shader) shader.uniforms.uTime.value = clock.elapsedTime;

    const base   = hover ? 0.7 : 0.35;
    const speed  = hover ? 2.4 : 1.0;
    const wobble = Math.sin(clock.elapsedTime * speed + def.phase) * 0.08;
    material.emissiveIntensity = base + wobble;
  });
  /* eslint-enable react-hooks/immutability */

  const handleClick = (e: ThreeEvent<MouseEvent>) => {
    e.stopPropagation();
    onSelect(def);
  };

  // --- Saturn-style ring (CYBERDECK) ---
  const ringMesh = def.ring && (() => {
    const r = def.ring;
    const op = r.opacity ?? 1;
    return (
      <group rotation={[Math.PI / 2 + r.tilt, 0, r.roll ?? 0]}>
        {/* Inner band */}
        <mesh>
          <ringGeometry args={[def.radius * r.inner, def.radius * r.innerOuter, 96, 1]} />
          <meshBasicMaterial
            color={r.color}
            transparent
            opacity={0.55 * op}
            side={THREE.DoubleSide}
            depthWrite={false}
            blending={THREE.AdditiveBlending}
          />
        </mesh>
        {/* Outer band (after Cassini-style gap) */}
        <mesh>
          <ringGeometry args={[def.radius * r.outerInner, def.radius * r.outer, 96, 1]} />
          <meshBasicMaterial
            color={r.color}
            transparent
            opacity={0.40 * op}
            side={THREE.DoubleSide}
            depthWrite={false}
            blending={THREE.AdditiveBlending}
          />
        </mesh>
      </group>
    );
  })();

  return (
    <group rotation={[def.tilt ?? 0, 0, 0]}>
      <group ref={groupRef}>
        <mesh
          ref={meshRef}
          onClick={handleClick}
          onPointerOver={(e) => { e.stopPropagation(); setHover(true); document.body.style.cursor = 'pointer'; }}
          onPointerOut={()    => { setHover(false); document.body.style.cursor = 'default'; }}
        >
          <sphereGeometry args={[def.radius, 56, 56]} />
          <primitive object={material} attach="material" />
        </mesh>

        <FresnelShell
          radius={def.radius * 1.18}
          color={def.color}
          power={3.0}
          intensity={hover ? 0.34 : 0.22}
          segments={24}
        />

        {ringMesh}

        <Html
          center
          position={[0, def.radius + 0.5, 0]}
          style={{ pointerEvents: 'none' }}
        >
          <div
            style={{
              fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
              fontSize: 10,
              fontWeight: 700,
              letterSpacing: '0.22em',
              color: def.color,
              background: 'rgba(2,5,11,0.85)',
              border: `1px solid ${def.color}`,
              padding: '2px 6px',
              whiteSpace: 'nowrap',
              textShadow: `0 0 8px ${def.glow}`,
              transform: 'translateY(-2px)',
            }}
          >
            {def.label}
          </div>
        </Html>
      </group>
    </group>
  );
}
