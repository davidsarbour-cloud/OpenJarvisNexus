import { useMemo } from 'react';
import * as THREE from 'three';

interface Props {
  radius: number;
  color: string;
  /** Optional tilt around the X axis (radians). */
  tilt?: number;
}

/**
 * OrbitRing -- clean orbital line only.
 *
 * A single continuous solid loop in the planet's colour, 256 segments
 * for smoothness, low opacity for subtlety. Additive blend so the
 * colour reads against the void without being neon.
 *
 * No waypoint markers, no rotating arc -- just the lane.
 */
export function OrbitRing({ radius, color, tilt = 0 }: Props) {
  const linePoints = useMemo(() => {
    const seg = 256;
    const arr = new Float32Array(seg * 3);
    for (let i = 0; i < seg; i++) {
      const a = (i / seg) * Math.PI * 2;
      arr[i * 3]     = Math.cos(a) * radius;
      arr[i * 3 + 1] = 0;
      arr[i * 3 + 2] = Math.sin(a) * radius;
    }
    return arr;
  }, [radius]);

  return (
    <group rotation={[tilt, 0, 0]}>
      <lineLoop>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[linePoints, 3]} />
        </bufferGeometry>
        <lineBasicMaterial
          color={color}
          transparent
          opacity={0.32}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </lineLoop>
    </group>
  );
}
