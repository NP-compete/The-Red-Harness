export interface ImpersonationSession {
  actingAs: string;
  really: string;
  expiresAt: string;
  readOnly: boolean;
  reason: string;
}

export interface PresentedImpersonation {
  headline: string;
  scope: string;
  reason: string;
  timeLeft: string;
  active: boolean;
  severity: 'medium' | 'high';
  action: 'stop';
  dismissible: false;
}

export function presentImpersonation(
  session: ImpersonationSession | null,
  now: Date,
): PresentedImpersonation | null {
  if (session === null) return null;

  const secondsLeft = (Date.parse(session.expiresAt) - now.getTime()) / 1000;

  return {
    headline: `You are acting as ${session.actingAs}`,
    scope: session.readOnly ? 'read only' : 'can make changes',
    reason: session.reason,
    timeLeft: secondsLeft <= 0 ? 'ended' : left(secondsLeft),
    active: secondsLeft > 0,
    severity: session.readOnly ? 'medium' : 'high',
    action: 'stop',
    // Forgetting whose account you are in is the whole risk here.
    dismissible: false,
  };
}

function left(seconds: number): string {
  if (seconds < 3600) {
    const minutes = Math.round(seconds / 60);
    return `${minutes} minute${minutes === 1 ? '' : 's'} left`;
  }
  const hours = Math.round(seconds / 3600);
  return `${hours} hour${hours === 1 ? '' : 's'} left`;
}
