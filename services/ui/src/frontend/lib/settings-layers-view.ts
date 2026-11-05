export interface ResolvedSetting {
  key: string;
  label: string;
  value: string | null;
  layer: string;
  lockedBy: string;
  shadowed: string[];
  overriddenAttempts: string[];
}

export interface PresentedSetting {
  value: string;
  source: string;
  note: string;
  overriding: string[];
  editable: boolean;
}

const SOURCES: Record<string, string> = {
  user: 'set by you',
  team: 'set by your team',
  org: 'set by your organisation',
  default: 'the default',
};

const OWNERS: Record<string, string> = {
  user: 'you',
  team: 'your team',
  org: 'your organisation',
};

export function presentSetting(setting: ResolvedSetting): PresentedSetting {
  const locked = setting.lockedBy !== '';
  // Only worth mentioning if this person's own choice is the one being ignored.
  const yoursIgnored = setting.overriddenAttempts.includes('user');

  return {
    value: setting.value ?? 'not set',
    source: SOURCES[setting.layer] ?? 'not set',
    note: locked
      ? `Locked by ${OWNERS[setting.lockedBy] ?? setting.lockedBy}${
          yoursIgnored ? '; your own setting is not being used' : ''
        }`
      : '',
    overriding: setting.shadowed,
    editable: !locked,
  };
}
