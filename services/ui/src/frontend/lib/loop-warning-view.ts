export interface LoopState {
  pattern: 'progressing' | 'repeating' | 'alternating' | 'same-failure';
  shouldStop: boolean;
  repeated: string;
  times: number;
  reason: string;
}

export interface PresentedLoop {
  headline: string;
  detail: string;
  culprit: string;
  failed: false;
  answered: false;
  severity: 'info' | 'medium';
  action: 'redirect' | 'none';
}

const HEADLINES = {
  repeating: 'This run is repeating itself',
  alternating: 'This run is going back and forth',
  'same-failure': 'This run keeps hitting the same problem',
} as const;

export function presentLoop(state: LoopState): PresentedLoop | null {
  if (state.pattern === 'progressing') return null;

  return {
    headline: HEADLINES[state.pattern],
    detail: state.reason,
    culprit: state.repeated,
    // Going in circles is not the same as failing, and not the same as
    // having answered; both would be the wrong thing to tell someone.
    failed: false,
    answered: false,
    severity: state.shouldStop ? 'medium' : 'info',
    action: state.shouldStop ? 'redirect' : 'none',
  };
}
