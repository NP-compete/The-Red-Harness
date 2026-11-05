export interface DeprecationStatus {
  tool: string;
  stage: 'current' | 'deprecated' | 'removed';
  usable: boolean;
  replacement: string;
  daysLeft: number;
  message: string;
}

export interface PresentedDeprecation {
  message: string;
  timeLeft: string;
  replacement: string;
  stillWorks: boolean;
  severity: 'low' | 'medium' | 'high';
  action: 'switch' | 'contact-admin' | 'none';
}

const SOON_DAYS = 14;

export function presentDeprecation(
  status: DeprecationStatus,
): PresentedDeprecation | null {
  if (status.stage === 'current') return null;

  const removed = status.stage === 'removed';

  return {
    message: status.message,
    timeLeft: removed ? 'removed' : timeLeft(status.daysLeft),
    replacement: status.replacement,
    stillWorks: status.usable,
    severity: removed ? 'high' : status.daysLeft <= SOON_DAYS ? 'medium' : 'low',
    // Stranded with nothing to move to is a question for whoever retired it.
    action: status.replacement ? 'switch' : removed ? 'contact-admin' : 'none',
  };
}

function timeLeft(days: number): string {
  if (days > SOON_DAYS) {
    const weeks = Math.round(days / 7);
    return `${weeks} week${weeks === 1 ? '' : 's'} left`;
  }
  return `${days} day${days === 1 ? '' : 's'} left`;
}
