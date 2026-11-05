export interface RevisionState {
  blocked: string;
  reason: string;
  added: string[];
  narrowed: boolean;
  needsAgreement: boolean;
}

export interface PresentedRevision {
  headline: string;
  reason: string;
  change: string;
  actions: string[];
  blocking: boolean;
  severity: 'info' | 'medium';
}

export function presentRevision(revision: RevisionState): PresentedRevision {
  return {
    headline: `Could not do: ${revision.blocked}`,
    reason: revision.reason,
    change:
      revision.added.length > 0
        ? `Doing this instead: ${revision.added.join(', ')}`
        : 'Leaving this out of the plan',
    // Doing less than was agreed is the person's call, not the agent's.
    actions: revision.needsAgreement ? ['Carry on without it', 'Stop here'] : [],
    blocking: revision.needsAgreement,
    severity: revision.narrowed ? 'medium' : 'info',
  };
}
