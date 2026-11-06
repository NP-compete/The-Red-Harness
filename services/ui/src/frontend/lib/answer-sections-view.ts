export interface AnswerSection {
  question: string;
  text: string;
  sources: string[];
  answered: boolean;
  unsourced: boolean;
}

export interface AssembledAnswer {
  sections: AnswerSection[];
  allSources: string[];
  complete: boolean;
  useHeadings: boolean;
}

export interface AnswerBlock {
  heading: string;
  text: string;
  sources: string[];
  state: 'answered' | 'unsourced' | 'missing';
}

export interface PresentedAnswer {
  blocks: AnswerBlock[];
  sources: string[];
  sourcedShare: string;
  warning: string;
  action: 'search-again' | 'none';
}

export function presentAnswer(answer: AssembledAnswer): PresentedAnswer {
  const missing = answer.sections.filter((section) => !section.answered).length;
  const sourced = answer.sections.filter((section) => section.sources.length > 0).length;

  return {
    blocks: answer.sections.map((section) => ({
      heading: answer.useHeadings ? capitalise(section.question) : '',
      text: section.text,
      sources: section.sources,
      state: !section.answered ? 'missing' : section.unsourced ? 'unsourced' : 'answered',
    })),
    sources: answer.allSources,
    sourcedShare: `${sourced} of ${answer.sections.length} parts have sources`,
    // A gap stated once at the top; the blocks say where it is.
    warning:
      missing > 0 ? `${missing} part${missing === 1 ? '' : 's'} of your question is unanswered` : '',
    action: missing > 0 ? 'search-again' : 'none',
  };
}

function capitalise(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}
