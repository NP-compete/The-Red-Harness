export interface SearchExplanation {
  original: string;
  query: string;
  expanded: string[];
  removed: string[];
  tooVague: boolean;
  resultCount: number;
}

export interface PresentedSearchExplanation {
  original: string;
  searched: string;
  summary: string;
  notes: string[];
  warning: string;
  openByDefault: boolean;
  action: 'search-exact' | 'none';
}

export function presentSearchExplanation(
  explanation: SearchExplanation,
): PresentedSearchExplanation {
  const empty = explanation.resultCount === 0;

  const notes = [
    ...explanation.expanded.map((term) => `also searched for what ${term} stands for`),
    ...(explanation.removed.length > 0
      ? [`ignored ${explanation.removed.length} common words`]
      : []),
  ];

  return {
    original: explanation.original,
    searched: explanation.query,
    summary: empty
      ? 'Nothing found'
      : `${explanation.resultCount} result${explanation.resultCount === 1 ? '' : 's'}`,
    notes,
    warning: explanation.tooVague
      ? 'That was a bit vague — try naming what you are looking for'
      : '',
    // Only worth reading when the results were surprising.
    openByDefault: empty,
    action: empty ? 'search-exact' : 'none',
  };
}
