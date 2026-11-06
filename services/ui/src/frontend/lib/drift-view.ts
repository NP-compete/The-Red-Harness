export type DriftMovement = 'steady' | 'rising' | 'falling' | 'unknown';

export interface DriftState {
  movement: DriftMovement;
  gap: number;
  outliers: string[];
}

export interface PresentedDrift {
  headline: string;
  detail: string;
  outlierNote: string;
  severity: 'info' | 'high';
}

const HEADLINE: Record<DriftMovement, string> = {
  steady: 'Scores are holding steady',
  rising: 'Scores are rising',
  falling: 'Scores are falling',
  unknown: 'Not enough runs to tell',
};

function gapText(gap: number): string {
  const points = Math.round(Math.abs(gap) * 100);
  if (points === 0) {
    return 'At baseline';
  }
  return `${points} points ${gap < 0 ? 'below' : 'above'} baseline`;
}

export function presentDrift(drift: DriftState): PresentedDrift {
  const count = drift.outliers.length;

  return {
    headline: HEADLINE[drift.movement],
    // With too little history, a number would imply a confidence we lack.
    detail: drift.movement === 'unknown' ? '' : gapText(drift.gap),
    outlierNote:
      count === 0
        ? ''
        : `${count} run${count === 1 ? '' : 's'} sat well outside the rest: ${drift.outliers.join(', ')}`,
    severity: drift.movement === 'falling' ? 'high' : 'info',
  };
}
