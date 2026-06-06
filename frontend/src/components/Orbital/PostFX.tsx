import {
  EffectComposer,
  Bloom,
  DepthOfField,
  ChromaticAberration,
  Noise,
  Vignette,
} from '@react-three/postprocessing';
import { BlendFunction, KernelSize } from 'postprocessing';
import { Vector2 } from 'three';

/**
 * PostFX -- cinematic holographic post-processing rig.
 *
 * Art direction (EVE / tactical hologram):
 *   - DOF              : focused on the orbital plane (camera dist 18 /
 *                        far 200 -> focusDistance = 18/200 = 0.09).
 *                        Wide DOF (low focalLength) keeps every planet
 *                        crisp; only far stars (depth > 60) get soft.
 *   - Bloom            : restrained, threshold 0.55. Only JARVIS hot
 *                        shells and the brightest noise peaks lift.
 *   - ChromaticAberration: micro fringe, ~0.4 px on 1080p.
 *   - Noise            : 3% grain to kill banding.
 *   - Vignette         : 60% darkness, frames the orbital plane.
 *
 * Order: DOF -> Bloom -> CA -> Noise -> Vignette.
 */
export function PostFX() {
  return (
    <EffectComposer multisampling={0} enableNormalPass={false}>
      {/* 1. Depth focused on orbital plane, very wide range */}
      <DepthOfField
        focusDistance={0.09}
        focalLength={0.012}
        bokehScale={0.32}
        height={480}
      />

      {/* 2. Restrained bloom */}
      <Bloom
        intensity={0.85}
        luminanceThreshold={0.35}
        luminanceSmoothing={0.85}
        mipmapBlur
        kernelSize={KernelSize.MEDIUM}
      />

      {/* 3. Lens glass -- micro CA */}
      <ChromaticAberration
        blendFunction={BlendFunction.NORMAL}
        offset={new Vector2(0.0004, 0.0003)}
        radialModulation={false}
        modulationOffset={0}
      />

      {/* 4. Film grain */}
      <Noise
        premultiply
        opacity={0.03}
        blendFunction={BlendFunction.SCREEN}
      />

      {/* 5. Tactical vignette */}
      <Vignette
        eskil={false}
        offset={0.35}
        darkness={0.6}
        blendFunction={BlendFunction.NORMAL}
      />
    </EffectComposer>
  );
}
