import { useNavigate } from 'react-router';
import { VaultGraphOverlay } from '../components/VaultGraph/VaultGraphOverlay';

/**
 * BrainPage — route `/vault-graph`.
 * Full-screen Obsidian brain graph (live via the vault_graph sidecar,
 * ws://localhost:8083). The overlay's X returns to the Command Center.
 */
export function BrainPage() {
  const navigate = useNavigate();
  return <VaultGraphOverlay open onClose={() => navigate('/')} />;
}
