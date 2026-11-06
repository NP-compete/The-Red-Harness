export interface EscalationState {
  contact: string;
  stepIndex: number;
  waiting: boolean;
  repeated: boolean;
  gaveUp: boolean;
  approved: boolean;
  nextAt: string | null;
  reason: string;
  ladder: string[];
}

export interface LadderEntry {
  contact: string;
  state: 'asked' | 'current' | 'upcoming';
}

export interface PresentedEscalation {
  headline: string;
  detail: string;
  ladder: LadderEntry[];
  severity: 'low' | 'high';
  approved: false;
  action: 'escalate-now' | 'retry';
}

export function presentEscalation(
  state: EscalationState,
  now: Date,
): PresentedEscalation {
  const atLast = state.stepIndex >= state.ladder.length - 1;

  return {
    headline: headline(state),
    detail: state.gaveUp ? state.reason : upNext(state, now, atLast),
    ladder: state.ladder.map((contact, index) => ({
      contact,
      state: index < state.stepIndex ? 'asked' : index === state.stepIndex ? 'current' : 'upcoming',
    })),
    severity: state.gaveUp ? 'high' : 'low',
    // Nobody answering is never read as somebody agreeing.
    approved: false,
    action: state.gaveUp ? 'retry' : 'escalate-now',
  };
}

function headline(state: EscalationState): string {
  if (state.gaveUp) return 'Nobody answered';
  if (state.repeated) return `Asking ${state.contact} again`;
  if (!state.waiting && state.contact) return `Now asking ${state.contact}`;
  return `Waiting for ${state.ladder[state.stepIndex]}`;
}

function upNext(state: EscalationState, now: Date, atLast: boolean): string {
  if (atLast) return 'There is nobody else to ask after this';
  if (!state.nextAt) return '';
  const minutes = Math.max(1, Math.round((Date.parse(state.nextAt) - now.getTime()) / 60_000));
  const next = state.ladder[state.stepIndex + 1];
  return `If there is no answer in ${minutes} minute${minutes === 1 ? '' : 's'}, ${next} will be asked`;
}
