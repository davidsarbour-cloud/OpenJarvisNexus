/**
 * Nexus9 — World · Valkyrie.
 *
 * Standalone page for the VALKYRIE agent (OpenAI gpt-image-1 image
 * generation). Thin wrapper: declares the card registry + image
 * candidates and hands the rest to <WorldShell>. The generate card
 * fires POST /v1/valkyrie/generate; the gallery card reads
 * GET /v1/valkyrie/gallery and refreshes on the `valkyrie:generated`
 * event the generate card emits.
 */
import { Images, Wand2 } from 'lucide-react';
import { ValkyrieGenerateCard } from '../components/CommandCenter/ValkyrieGenerateCard';
import { ValkyrieGalleryCard } from '../components/CommandCenter/ValkyrieGalleryCard';
import { WorldShell, type CardDef } from '../components/WorldShell/WorldShell';

type CardType = 'generate' | 'gallery';

const CARD_REGISTRY: Record<CardType, CardDef> = {
  generate: { label: 'GENERATE', sub: 'gpt-image-1 prompt → PNG', icon: Wand2,   Card: ValkyrieGenerateCard },
  gallery:  { label: 'GALLERY',  sub: 'Recent generations',       icon: Images,  Card: ValkyrieGalleryCard  },
};

export function WorldValkyriePage() {
  return (
    <WorldShell
      colorKey="valkyrie"
      imageCandidates={['/world/valkyrie.webp', '/world/valkyrie.png', '/world/valkyrie.jpg']}
      imageAlt="Valkyrie — OpenAI image generation"
      storageKey="nexus9.world-valkyrie.layout"
      cardRegistry={CARD_REGISTRY}
      worldLabel="Valkyrie"
      defaultSeeds={[
        { id: 'seed-gen', type: 'generate', side: 'left',  height: 320 },
        { id: 'seed-gal', type: 'gallery',  side: 'right', height: 380 },
      ]}
    />
  );
}
