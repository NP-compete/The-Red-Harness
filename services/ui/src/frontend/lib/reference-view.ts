export interface ReferenceState {
  entity: string | null;
  resolved: boolean;
  shouldAsk: boolean;
  candidates: string[];
}

export interface PresentedReference {
  note: string;
  choices: string[];
  action: string;
  blocking: boolean;
}

export function presentReference(reference: ReferenceState): PresentedReference | null {
  // Nothing was inferred, so there is nothing to show or correct.
  if (!reference.resolved && !reference.shouldAsk) {
    return null;
  }

  if (reference.shouldAsk) {
    return {
      note: reference.candidates.length > 0 ? 'Which one did you mean?' : 'What should this apply to?',
      choices: reference.candidates,
      action: '',
      blocking: true,
    };
  }

  return {
    // Saying what it assumed is what makes a wrong assumption correctable.
    note: `Taking “it” to mean ${reference.entity}`,
    choices: [],
    action: 'Not that one',
    blocking: false,
  };
}
