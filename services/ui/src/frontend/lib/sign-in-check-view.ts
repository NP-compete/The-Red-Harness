export interface SignInDecision {
  outcome: 'allowed' | 'step-up' | 'refused';
  stepUp: boolean;
  readOnly: boolean;
  exceptional: boolean;
  notify: boolean;
  reason: string;
}

export interface PresentedSignIn {
  headline: string;
  detail: string;
  note: string;
  blocked: boolean;
  severity: 'info' | 'high';
  action: 'confirm' | 'contact-admin' | 'request-seat';
}

export function presentSignIn(decision: SignInDecision): PresentedSignIn | null {
  // An ordinary sign-in with a seat has nothing to say.
  if (decision.outcome === 'allowed' && !decision.readOnly && !decision.exceptional) {
    return null;
  }

  if (decision.outcome === 'refused') {
    return {
      headline: 'You cannot sign in',
      detail: decision.reason,
      note: '',
      blocked: true,
      severity: 'high',
      action: 'contact-admin',
    };
  }

  if (decision.outcome === 'step-up') {
    return {
      headline: 'Confirm it is you',
      detail: decision.reason,
      note: exception(decision),
      // Being asked to prove who you are is not being turned away.
      blocked: false,
      severity: 'info',
      action: 'confirm',
    };
  }

  return {
    headline: decision.readOnly
      ? 'You are signed in but have no seat'
      : 'You are signed in',
    detail: '',
    note: exception(decision),
    blocked: false,
    severity: 'info',
    action: 'request-seat',
  };
}

function exception(decision: SignInDecision): string {
  return decision.exceptional ? 'This sign-in was allowed as an exception' : '';
}
