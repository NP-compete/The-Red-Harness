export interface FeatureState {
  feature: string;
  label: string;
  permitted: boolean;
  reason: string | null;
  selfServe: boolean;
  onTrial: boolean;
  trialEnds: string | null;
}

export interface PresentedFeatureLock {
  headline: string;
  detail: string;
  locked: boolean;
  severity: 'info' | 'medium' | 'high';
  action: 'enable' | 'ask-about-plan' | 'none';
}

const DAY = 86_400_000;

export function presentFeatureLock(
  state: FeatureState,
  now: Date,
): PresentedFeatureLock | null {
  if (state.permitted && !state.onTrial) return null;

  if (state.permitted && state.onTrial) {
    return {
      headline: `${state.label} is on trial`,
      detail: state.trialEnds ? `${days(state.trialEnds, now)} days left` : '',
      // A trial is working access; saying so is not the same as locking it.
      locked: false,
      severity: 'info',
      action: 'none',
    };
  }

  if (state.reason === 'suspended') {
    return {
      headline: 'Your organisation’s access is suspended',
      detail: '',
      locked: true,
      severity: 'high',
      action: 'none',
    };
  }

  if (state.reason === 'turned-off') {
    return {
      headline: `${state.label} is turned off`,
      detail: 'An administrator can turn this on',
      locked: true,
      severity: 'medium',
      action: state.selfServe ? 'enable' : 'ask-about-plan',
    };
  }

  if (state.reason === 'trial-ended') {
    return {
      headline: `Your trial of ${state.label} has ended`,
      detail: '',
      locked: true,
      severity: 'info',
      action: 'ask-about-plan',
    };
  }

  return {
    headline: `${state.label} is not on your plan`,
    detail: '',
    locked: true,
    severity: 'info',
    action: 'ask-about-plan',
  };
}

function days(at: string, now: Date): number {
  return Math.round((Date.parse(at) - now.getTime()) / DAY);
}
