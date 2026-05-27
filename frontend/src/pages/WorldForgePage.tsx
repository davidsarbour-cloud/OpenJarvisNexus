/**
 * Nexus9 — World · Forge.
 *
 * Thin wrapper: declares the Forge-specific card registry + image
 * candidates and hands the rest to <WorldShell>. See
 * components/WorldShell/WorldShell.tsx for the dashboard mechanics.
 */
import {
  Activity, Box, FlaskConical, GitBranch, Hammer, Printer, Settings, Sparkles,
} from 'lucide-react';
import { ForgePipelinesCard } from '../components/CommandCenter/ForgePipelinesCard';
import { QuickForgeCard } from '../components/CommandCenter/QuickForgeCard';
import { NamedSatellite, LiveSatellite } from '../components/CommandCenter/FunctionalSatellites';
import { WorldShell, type CardDef } from '../components/WorldShell/WorldShell';

const PipelineMonitorForge = () => <NamedSatellite title="PIPELINE MONITOR" colorKey="forge" />;
const TestDroneForge       = () => <NamedSatellite title="TEST DRONE"        colorKey="forge" />;
const OptimizerDroneForge  = () => <NamedSatellite title="OPTIMIZER DRONE"   colorKey="forge" />;
const MeshyCredits         = () => <NamedSatellite title="MESHY CREDITS"     colorKey="forge" />;
const StlOutput            = () => <LiveSatellite  title="STL OUTPUT"        colorKey="forge" snapshotKey="stl_output" />;
const BambuQueue           = () => <NamedSatellite title="BAMBU QUEUE"       colorKey="forge" />;

type CardType =
  | 'pulse' | 'pipelinemon' | 'testdrone' | 'optimizerdrone'
  | 'meshy' | 'stl' | 'bambu' | 'quickforge';

const CARD_REGISTRY: Record<CardType, CardDef> = {
  pulse:          { label: 'PULSE',            sub: 'Pipeline Monitor',            icon: Activity,      Card: ForgePipelinesCard    },
  quickforge:     { label: 'QUICK FORGE',      sub: 'Launch STL mission inline',   icon: Hammer,        Card: QuickForgeCard        },
  pipelinemon:    { label: 'PIPELINE MONITOR', sub: 'Real-time pipeline status',   icon: GitBranch,     Card: PipelineMonitorForge  },
  testdrone:      { label: 'TEST DRONE',       sub: 'Automated STL / code checks', icon: FlaskConical,  Card: TestDroneForge        },
  optimizerdrone: { label: 'OPTIMIZER DRONE',  sub: 'STL orientation / params',    icon: Settings,      Card: OptimizerDroneForge   },
  meshy:          { label: 'MESHY CREDITS',    sub: 'API quota left',              icon: Sparkles,      Card: MeshyCredits          },
  stl:            { label: 'STL OUTPUT',       sub: 'Recent STL exports',          icon: Box,           Card: StlOutput             },
  bambu:          { label: 'BAMBU QUEUE',      sub: 'Bambu Lab printer state',     icon: Printer,       Card: BambuQueue            },
};

export function WorldForgePage() {
  return (
    <WorldShell
      colorKey="forge"
      imageCandidates={['/world/forge.webp', '/world/forge.png', '/world/forge.jpg']}
      imageAlt="Forge Labs — Engineering & Production"
      storageKey="nexus9.world-forge.layout"
      cardRegistry={CARD_REGISTRY}
      worldLabel="Forge"
    />
  );
}
