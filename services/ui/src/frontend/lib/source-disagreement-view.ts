export interface DisagreementState {
  disagree: boolean;
  answers: string[];
  byAnswer: Record<string, string[]>;
  preferred: string;
  showBoth: boolean;
  reason: string;
}

export interface AnswerOption {
  answer: string;
  sources: string[];
  preferred: boolean;
}

export interface PresentedDisagreement {
  headline: string;
  detail: string;
  options: AnswerOption[];
  severity: 'medium' | 'high';
  dismissible: boolean;
  action: 'compare-sources';
}

export function presentDisagreement(
  state: DisagreementState,
): PresentedDisagreement | null {
  if (!state.disagree) return null;

  const undecided = state.preferred === '';

  const options = state.answers
    .map((answer) => ({
      answer,
      sources: state.byAnswer[answer] ?? [],
      preferred: answer === state.preferred,
    }))
    .sort((a, b) => Number(b.preferred) - Number(a.preferred) || a.answer.localeCompare(b.answer));

  return {
    headline: 'Sources disagree on this',
    detail: state.reason,
    // The losing answer stays visible; the disagreement is the finding.
    options,
    severity: undecided ? 'high' : 'medium',
    dismissible: !undecided,
    action: 'compare-sources',
  };
}
