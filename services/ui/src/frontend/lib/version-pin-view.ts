export interface VersionState {
  version: string;
  currentVersion: string;
  outcome: 'pinned' | 'current' | 'pin-expired';
  behaviourMayChange: boolean;
  reason: string;
  pinnedBy: string;
}

export interface PresentedVersionPin {
  headline: string;
  detail: string;
  stable: boolean;
  chosenByPerson: boolean;
  severity: 'low' | 'medium';
  action: 'update' | 'none';
}

const SYSTEM = 'system';

export function presentVersionPin(state: VersionState): PresentedVersionPin | null {
  if (state.outcome === 'current') return null;

  const moved = state.outcome === 'pin-expired';

  return {
    headline: moved
      ? `This conversation has moved to version ${state.version}`
      : `This conversation is using version ${state.version}`,
    detail: moved ? state.reason : `Version ${state.currentVersion} is available`,
    stable: !state.behaviourMayChange,
    chosenByPerson: state.pinnedBy !== SYSTEM,
    severity: moved ? 'medium' : 'low',
    // Nothing to update to once the move has already happened.
    action: moved ? 'none' : 'update',
  };
}
