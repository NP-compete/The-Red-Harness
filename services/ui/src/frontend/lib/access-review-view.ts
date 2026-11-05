export interface ReviewGrant {
  subject: string;
  agent: string;
  via: string;
  lastUsedDays: number | null;
  flagged: boolean;
}

export interface ReviewViewRow {
  subject: string;
  agent: string;
  source: string;
  lastUsed: string;
  action?: 'revoke';
}

export interface PresentedAccessReview {
  rows: ReviewViewRow[];
  toDecide: number;
  summary: string;
}

export function presentAccessReview(grants: ReviewGrant[]): PresentedAccessReview {
  const rows = grants.map<ReviewViewRow>((grant) => ({
    subject: grant.subject,
    agent: grant.agent,
    source: describeSource(grant.via),
    lastUsed: grant.lastUsedDays === null ? 'never used' : `${grant.lastUsedDays} days ago`,
    // Only flagged grants offer removal: a revoke button beside healthy
    // access invites a reviewer to click through the whole list.
    action: grant.flagged ? 'revoke' : undefined,
  }));

  const toDecide = grants.filter((grant) => grant.flagged).length;

  return { rows, toDecide, summary: summarise(toDecide, grants.length) };
}

function describeSource(via: string): string {
  if (via === 'direct') return 'Granted directly';
  if (via === 'service') return 'Service account';
  if (via.startsWith('group:')) return `Through the group ${via.slice('group:'.length)}`;
  return via;
}

function summarise(toDecide: number, total: number): string {
  if (total === 0) return 'No access has been granted yet';
  if (toDecide === 0) return 'Nothing needs a decision';
  return `${toDecide} of ${total} grants need a decision`;
}
