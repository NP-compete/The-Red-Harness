export interface ClarificationState {
  ask: boolean;
  stop: boolean;
  question: string;
  options: string[];
  assuming: string;
  reason: string;
}

export interface PresentedClarification {
  question: string;
  choices: string[];
  state: 'waiting-for-you' | 'assumed' | 'stopped';
  blocking: boolean;
  allowsFreeText: true;
  severity: 'info' | 'medium';
}

export function presentClarification(
  state: ClarificationState,
): PresentedClarification | null {
  if (state.ask) {
    return {
      question: state.question,
      choices: state.options,
      state: 'waiting-for-you',
      blocking: true,
      // The right answer is often none of the offered ones.
      allowsFreeText: true,
      severity: 'info',
    };
  }

  if (state.stop) {
    return {
      question: `This run stopped: ${state.reason}`,
      choices: [],
      state: 'stopped',
      blocking: false,
      allowsFreeText: true,
      severity: 'medium',
    };
  }

  if (state.assuming) {
    return {
      question: `Assuming you meant ${state.assuming}`,
      choices: [],
      state: 'assumed',
      // Said out loud while the work continues, so it can be corrected.
      blocking: false,
      allowsFreeText: true,
      severity: 'info',
    };
  }

  return null;
}
