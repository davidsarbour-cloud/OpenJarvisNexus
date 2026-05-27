/**
 * CardAccentContext — when set by an ancestor, every HudCard inside
 * uses this ModuleKey for its tint (border, title, icon, glow) instead
 * of its own hardcoded `colorKey`. Used by the /world/* pages so each
 * room re-themes the embedded Command Center cards in its own colour.
 *
 * `null` means "no override" — cards keep their own colorKey.
 *
 * Kept in its own file (separate from HudCard.tsx) so React Refresh
 * can fast-refresh HudCard without bailing out on the mixed
 * value/component export.
 */
import { createContext } from 'react';
import type { ModuleKey } from '../../lib/colors';

export const CardAccentContext = createContext<ModuleKey | null>(null);
