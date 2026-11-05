export interface Posture {
  reads: boolean;
  interactiveRuns: boolean;
  unattendedRuns: boolean;
  approveEverythingRisky: boolean;
  concurrencyFactor: number;
  declaredBy: string;
  reason: string;
  until: string | null;
}

export interface PresentedIncident {
  headline: string;
  restrictions: string[];
  note: string;
  until: string;
  declaredBy: string;
  severity: 'medium' | 'high';
  dismissible: false;
}

export function presentIncident(posture: Posture, now: Date): PresentedIncident | null {
  const restrictions: string[] = [];
  if (!posture.interactiveRuns) restrictions.push('New runs are paused');
  if (!posture.unattendedRuns) restrictions.push('Scheduled runs are paused');
  if (posture.approveEverythingRisky) restrictions.push('Risky steps need approval');
  if (posture.concurrencyFactor < 1) restrictions.push('Fewer runs at a time');

  if (restrictions.length === 0) return null;

  return {
    headline: posture.reason,
    restrictions,
    // Worth saying only where something larger has been taken away.
    note:
      !posture.interactiveRuns && posture.reads
        ? 'You can still read existing conversations'
        : '',
    until: until(posture.until, now),
    declaredBy: posture.declaredBy,
    severity: posture.interactiveRuns ? 'medium' : 'high',
    dismissible: false,
  };
}

function until(at: string | null, now: Date): string {
  if (at === null) return '';
  const hours = Math.round((Date.parse(at) - now.getTime()) / 3_600_000);
  if (hours <= 0) return 'overdue to lift';
  return `expected to lift in ${hours} hour${hours === 1 ? '' : 's'}`;
}
