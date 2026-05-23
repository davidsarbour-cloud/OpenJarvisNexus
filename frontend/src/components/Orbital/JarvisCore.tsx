import { useMemo, useRef, useState } from 'react';
import { useFrame, type ThreeEvent } from '@react-three/fiber';
import { Html } from '@react-three/drei';
import * as THREE from 'three';
import { FresnelShell } from './FresnelShell';
import { EnergyRing } from './EnergyRing';
import { JARVIS_DEF, type JarvisDef } from './planets.config';

interface Props {
  onSelect?: (def: JarvisDef) => void;
}

/**
 * JARVIS Core -- AI stellar reactor. Clickable.
 *
 * 8 layers (plasma + 2 wireframe shells + Fresnel + 3 EnergyRings +
 * corona). The plasma core mesh is the click target; an Html label
 * floats above the corona with the JARVIS name (pointer-events none
 * so it does not eat clicks).
 */
export function JarvisCore({ onSelect }: Props) {
  const plasmaRef     = useRef<THREE.Mesh>(null);
  const icoShellRef   = useRef<THREE.LineSegments>(null);
  const dodecShellRef = useRef<THREE.LineSegments>(null);
  const ringAGroupRef = useRef<THREE.Group>(null);
  const ringBGroupRef = useRef<THREE.Group>(null);
  const ringCGroupRef = useRef<THREE.Group>(null);
  const [hover, setHover] = useState(false);

  const icoEdges   = useMemo(
    () => new THREE.EdgesGeometry(new THREE.IcosahedronGeometry(0.95, 1)),
    []
  );
  const dodecEdges = useMemo(
    () => new THREE.EdgesGeometry(new THREE.DodecahedronGeometry(1.10, 0)),
    []
  );

  const plasmaMat = useMemo(() => {
    const mat = new THREE.MeshStandardMaterial({
      color:             '#00d4ff',
      emissive:          '#00d4ff',
      emissiveIntensity: 1.84,
      roughness:         0.3,
      metalness:         0.1,
    });

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
          '#include <emissivemap_fragment>',
          `#include <emissivemap_fragment>
vec3 np = vObjectPos * 5.2;
float n1 = vnoise3(np + vec3(uTime * 0.24, 0.0, 0.0));
float n2 = vnoise3(np * 2.3 - vec3(0.0, uTime * 0.30, uTime * 0.16));
float plasma = pow(n1 * 0.6 + n2 * 0.7, 1.4);
totalEmissiveRadiance += emissive * plasma * 1.25;
`
        );

      mat.userData.shader = shader;
    };

    return mat;
  }, []);

  useFrame(({ clock }) => {
    const t = clock.elapsedTime;

    if (plasmaRef.current) {
      const k = (hover ? 1.05 : 1) * (1 + Math.sin(t * 1.5) * 0.03);
      plasmaRef.current.scale.setScalar(k);
      plasmaRef.current.rotation.y = t * 0.05;
      plasmaRef.current.rotation.x = t * 0.03;
    }
    const shader = (plasmaMat.userData as { shader?: { uniforms: { uTime: { value: number } } } }).shader;
    if (shader) shader.uniforms.uTime.value = t;

    if (icoShellRef.current) {
      icoShellRef.current.rotation.y = t * 0.22;
      icoShellRef.current.rotation.x = t * 0.07;
    }

    if (dodecShellRef.current) {
      dodecShellRef.current.rotation.y = -t * 0.13;
      dodecShellRef.current.rotation.z = t * 0.09;
    }

    if (ringAGroupRef.current) {
      ringAGroupRef.current.rotation.z = t * 0.18;
      ringAGroupRef.current.rotation.x = Math.PI * 0.35 + Math.sin(t * 0.2) * 0.04;
    }
    if (ringBGroupRef.current) {
      ringBGroupRef.current.rotation.y = -t * 0.11;
      ringBGroupRef.current.rotation.x = Math.PI * 0.6;
    }
    if (ringCGroupRef.current) {
      ringCGroupRef.current.rotation.x = t * 0.27;
      ringCGroupRef.current.rotation.z = Math.PI * 0.15;
    }
  });

  const handleClick = (e: ThreeEvent<MouseEvent>) => {
    e.stopPropagation();
    onSelect?.(JARVIS_DEF);
  };

  return (
    <group>
      {/* 1. Plasma core -- click target */}
      <mesh
        ref={plasmaRef}
        onClick={handleClick}
        onPointerOver={(e) => { e.stopPropagation(); setHover(true); document.body.style.cursor = 'pointer'; }}
        onPointerOut={()    => { setHover(false); document.body.style.cursor = 'default'; }}
      >
        <icosahedronGeometry args={[0.75, 4]} />
        <primitive object={plasmaMat} attach="material" />
      </mesh>

      {/* 2. Inner ico containment shell */}
      <lineSegments ref={icoShellRef}>
        <primitive object={icoEdges} attach="geometry" />
        <lineBasicMaterial
          color="#5fe6ff"
          transparent
          opacity={0.55}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </lineSegments>

      {/* 3. Outer dodeca machinery shell */}
      <lineSegments ref={dodecShellRef}>
        <primitive object={dodecEdges} attach="geometry" />
        <lineBasicMaterial
          color="#00a8d8"
          transparent
          opacity={0.42}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </lineSegments>

      {/* 4. Hot rim Fresnel */}
      <FresnelShell radius={1.20} color="#5fe6ff" power={4.0} intensity={0.8} />

      {/* 5. Equatorial energy ring */}
      <group ref={ringAGroupRef}>
        <EnergyRing
          radius={1.32}
          tubeRadius={0.014}
          color="#7fefff"
          flowSpeed={1.0}
          baseOpacity={0.45}
          phase={0.0}
          segments={144}
          tubeSegments={10}
        />
      </group>

      {/* 6. Polar counter-rotating ring */}
      <group ref={ringBGroupRef}>
        <EnergyRing
          radius={1.42}
          tubeRadius={0.010}
          color="#5fe6ff"
          flowSpeed={0.7}
          baseOpacity={0.28}
          phase={1.7}
          segments={128}
          tubeSegments={8}
        />
      </group>

      {/* 7. Fast oblique micro ring */}
      <group ref={ringCGroupRef}>
        <EnergyRing
          radius={1.26}
          tubeRadius={0.008}
          color="#9ff5ff"
          flowSpeed={1.6}
          baseOpacity={0.22}
          phase={3.4}
          segments={112}
          tubeSegments={8}
        />
      </group>

      {/* 8. Soft atmospheric corona */}
      <FresnelShell radius={1.65} color="#00a8d8" power={1.6} intensity={0.50} />

      <pointLight color="#00d4ff" intensity={2.0} distance={45} decay={1.6} />

      {/* Tactical HUD label -- above the corona, never eats clicks */}
      <Html
        center
        position={[0, 2.05, 0]}
        style={{ pointerEvents: 'none' }}
      >
        <div
          style={{
            fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: '0.32em',
            color: JARVIS_DEF.color,
            background: 'rgba(2,5,11,0.85)',
            border: `1px solid ${JARVIS_DEF.color}`,
            padding: '3px 10px',
            whiteSpace: 'nowrap',
            textShadow: `0 0 10px ${JARVIS_DEF.glow}`,
            transform: hover ? 'translateY(-2px) scale(1.05)' : 'translateY(0)',
            transition: 'transform 180ms ease-out',
          }}
        >
          {JARVIS_DEF.label}
        </div>
      </Html>
    </group>
  );
}
