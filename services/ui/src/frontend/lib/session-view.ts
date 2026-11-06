export interface SessionState {
  state: 'live' | 'idle-expired' | 'expired' | 'reauth-needed';
  usable: boolean;
  sessionStillValid: boolean;
  warn: boolean;
  idleAt: string | null;
  endsAt: string | null;
  reason: string;
  unsavedWork: boolean;
}

export interface PresentedSession {
  /** Catalogue keys, not words: this runs where there is no
   *  translator, and a warning about losing your session is the
   *  last thing to show in a language somebody may not read. */
  headline: string;
  /** What the headline counts, when it counts anything. */
  headlineCount: number;
  detail: string;
  signedOut: boolean;
  severity: 'medium' | 'high';
  action: 'stay-signed-in' | 'sign-in' | 'confirm';
  dismissible: boolean;
}

export function presentSession(session: SessionState, now: Date): PresentedSession | null {
  if (session.state === 'reauth-needed') {
    return {
      headline: 'session.confirmIdentity',
      headlineCount: 0,
      detail: '',
      // Still signed in; only this one action needs proof.
      signedOut: false,
      severity: 'medium',
      action: 'confirm',
      dismissible: true,
    };
  }

  if (!session.usable) {
    return {
      headline: 'session.signedOut',
      headlineCount: 0,
      // The server's own words for why; not ours to translate.
      detail: session.reason,
      signedOut: true,
      severity: 'high',
      action: 'sign-in',
      dismissible: false,
    };
  }

  if (!session.warn) return null;

  const left = minutes(session.idleAt, now);

  return {
    headline: left === null ? 'session.signOutSoon' : 'session.signOutIn',
    headlineCount: left ?? 0,
    detail: session.unsavedWork ? 'session.unsavedWork' : '',
    signedOut: false,
    severity: 'medium',
    action: 'stay-signed-in',
    dismissible: true,
  };
}

/** Whole minutes left, or null when there is no time to report. */
function minutes(at: string | null, now: Date): number | null {
  if (at === null) return null;
  return Math.max(1, Math.round((Date.parse(at) - now.getTime()) / 60_000));
}
