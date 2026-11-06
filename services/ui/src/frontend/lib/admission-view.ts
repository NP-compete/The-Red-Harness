export interface AdmissionState {
  verdict: 'start' | 'queue' | 'refused';
  position: number;
  reason: string;
  estimatedWaitSeconds: number | null;
}

export interface PresentedAdmission {
  headline: string;
  detail: string;
  started: false;
  severity: 'info' | 'medium';
  action: 'cancel' | 'retry-later';
}

export function presentAdmission(state: AdmissionState): PresentedAdmission | null {
  if (state.verdict === 'start') return null;

  if (state.verdict === 'refused') {
    return {
      headline: 'This run cannot start',
      detail: state.reason,
      started: false,
      severity: 'medium',
      action: 'retry-later',
    };
  }

  return {
    headline: state.position === 1 ? 'Next in the queue' : `${ordinal(state.position)} in the queue`,
    // Silence beats a wait time nobody measured.
    detail: state.estimatedWaitSeconds === null ? '' : `about ${minutes(state.estimatedWaitSeconds)}`,
    started: false,
    severity: 'info',
    action: 'cancel',
  };
}

function minutes(seconds: number): string {
  if (seconds < 60) return 'under a minute';
  const count = Math.round(seconds / 60);
  return `${count} minute${count === 1 ? '' : 's'}`;
}

function ordinal(position: number): string {
  const suffixes = ['th', 'st', 'nd', 'rd'];
  const remainder = position % 100;
  return `${position}${suffixes[(remainder - 20) % 10] ?? suffixes[remainder] ?? suffixes[0]}`;
}
