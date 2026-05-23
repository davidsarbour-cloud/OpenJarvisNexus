import { Stars } from '@react-three/drei';

/**
 * Starfield -- 4 layered cosmic backdrops.
 *
 *   Layer 1 (deep void)    : far pin-stars, tiny + low saturation.
 *   Layer 2 (mid field)    : main star field.
 *   Layer 3 (near sparse)  : sharp, saturated, drifts faster.
 *   Layer 4 (FLASH)        : ~60 large bright stars at high saturation
 *                            -- the "diamonds" that punctuate the dark.
 *
 * Sharper than before: factors reduced ~30% so each point is smaller
 * and crisper, less blob-like. Saturations boosted on the near and
 * flash layers so they POP against the darker background.
 *
 * Depth perception still handled by THREE.scene.fog (declared in
 * OrbitalScene). No backdrop mesh.
 */
export function Starfield() {
  return (
    <group>
      <Stars
        radius={160}
        depth={60}
        count={3500}
        factor={2.0}
        saturation={0.15}
        fade
        speed={0.08}
      />

      <Stars
        radius={95}
        depth={35}
        count={1800}
        factor={2.8}
        saturation={0.40}
        fade
        speed={0.22}
      />

      <Stars
        radius={45}
        depth={18}
        count={350}
        factor={4.0}
        saturation={0.85}
        fade
        speed={0.55}
      />

      {/* FLASH layer -- sparse bright "diamond" stars */}
      <Stars
        radius={70}
        depth={15}
        count={70}
        factor={8.0}
        saturation={1.0}
        fade
        speed={0.35}
      />
    </group>
  );
}
