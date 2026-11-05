export type ModeName = 'fast' | 'balanced' | 'accurate';

export interface ModeState {
  mode: ModeName;
  tier: string;
  wanted?: string;
  available?: ModeName[];
}

export interface PresentedMode {
  label: string;
  description: string;
  note: string;
  substituted: boolean;
  alternatives: ModeName[];
}

const DESCRIPTIONS: Record<ModeName, string> = {
  fast: 'Quick answers, lighter model.',
  balanced: 'The usual trade-off between speed and depth.',
  accurate: 'Slower and dearer, for work that needs it.',
};

export function presentMode({ mode, tier, wanted, available }: ModeState): PresentedMode {
  const substituted = wanted !== undefined && wanted !== tier;

  return {
    label: capitalise(mode),
    description: DESCRIPTIONS[mode] ?? '',
    // Saying which model actually answered keeps a quiet downgrade from
    // reading as the mode getting worse.
    note: substituted ? `Answered by ${tier}, because ${wanted} was unavailable.` : '',
    substituted,
    alternatives: (available ?? []).filter((option) => option !== mode),
  };
}

function capitalise(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}
