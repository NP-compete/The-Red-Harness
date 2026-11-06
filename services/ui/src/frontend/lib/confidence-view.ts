export type Stance = 'plain' | 'hedged' | 'decline';

export interface ConfidenceState {
  stance: Stance;
  hedge: string;
  concerns: string[];
  whatWouldHelp: string;
}

export interface PresentedConfidence {
  headline: string;
  concerns: string[];
  suggestion: string;
  showAnswer: boolean;
  severity: 'low' | 'medium';
}

export function presentConfidence(state: ConfidenceState): PresentedConfidence | null {
  if (state.stance === 'plain') {
    return null;
  }

  const declined = state.stance === 'decline';

  return {
    headline: declined ? 'Not enough to answer on' : 'Take this with some caution',
    concerns: state.concerns,
    suggestion: state.whatWouldHelp ? `Would help: ${state.whatWouldHelp}` : '',
    // A hedged answer is still an answer; a declined one is not one to show.
    showAnswer: !declined,
    severity: declined ? 'medium' : 'low',
  };
}
