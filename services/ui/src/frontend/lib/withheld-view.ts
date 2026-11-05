export interface WithheldState {
  withheld: number;
  requestable: string[];
  nothingLeft: boolean;
}

export interface PresentedWithheld {
  note: string;
  documents: string[];
  action: string;
  severity: 'info' | 'medium';
}

export function presentWithheld(state: WithheldState): PresentedWithheld | null {
  if (state.withheld === 0) {
    return null;
  }

  const one = state.withheld === 1;

  return {
    note: state.nothingLeft
      ? 'Everything found for this question is out of your reach'
      : `${state.withheld} result${one ? '' : 's'} you do not have access to ${one ? 'was' : 'were'} left out`,
    // Only documents the asker is already allowed to know about are named.
    documents: state.requestable,
    action: state.requestable.length > 0 ? 'Request access' : '',
    severity: state.nothingLeft ? 'medium' : 'info',
  };
}
