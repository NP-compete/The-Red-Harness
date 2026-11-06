export interface CaseProposal {
  proposed: boolean;
  question: string;
  expected: string;
  fromRun: string;
  needsReview: boolean;
  reason: string;
  duplicateOf: string;
}

export interface PresentedCaseProposal {
  headline: string;
  question: string;
  expected: string;
  note: string;
  actions: string[];
  blocking: boolean;
}

export function presentCaseProposal(proposal: CaseProposal): PresentedCaseProposal | null {
  // A duplicate is worth pointing at; every other refusal is silent.
  if (!proposal.proposed && !proposal.duplicateOf) {
    return null;
  }

  const duplicate = Boolean(proposal.duplicateOf);

  return {
    headline: duplicate ? `Already covered by ${proposal.duplicateOf}` : 'Add this as a test case?',
    question: proposal.question,
    expected: `Expected: ${proposal.expected}`,
    note: proposal.needsReview
      ? 'This mentions someone, so it needs a read before it is added'
      : '',
    actions: duplicate ? [`Open ${proposal.duplicateOf}`] : ['Add case', 'Not this one'],
    blocking: false,
  };
}
