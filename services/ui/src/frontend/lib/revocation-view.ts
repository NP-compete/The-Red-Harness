export interface RevocationState {
  verdict: 'valid' | 'revoked';
  mustSignInAgain: boolean;
  reason: string;
  wasThisDevice: boolean;
  otherSessionsEnded: number;
}

export interface PresentedRevocation {
  headline: string;
  detail: string;
  stillSignedIn: boolean;
  dismissible: boolean;
  severity: 'info' | 'high';
  action: 'sign-in' | 'none';
}

export function presentRevocation(state: RevocationState): PresentedRevocation | null {
  if (state.verdict === 'revoked') {
    return {
      headline: 'You have been signed out',
      detail: state.reason,
      stillSignedIn: false,
      // Being signed out is not something to dismiss and carry on past.
      dismissible: false,
      severity: 'high',
      action: 'sign-in',
    };
  }

  const others = state.otherSessionsEnded;
  if (others > 0) {
    return {
      // Confirming the sweep worked is reassurance, not an alarm.
      headline: `Signed out of ${others} other place${others === 1 ? '' : 's'}`,
      detail: '',
      stillSignedIn: true,
      dismissible: true,
      severity: 'info',
      action: 'none',
    };
  }

  return null;
}
