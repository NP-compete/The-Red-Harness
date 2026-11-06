export type Outcome = 'allowed' | 'needs_approval' | 'refused' | 'unavailable';
export type Code = 'no_authority' | 'policy_denied' | 'budget_exhausted';

export interface AuditEntry {
  at: string;
  subject: string;
  tool: string;
  outcome: Outcome;
  code?: Code;
  trust?: 'clean' | 'untrusted_read';
}

export interface AuditRow {
  at: string;
  subject: string;
  summary: string;
  flagged: boolean;
}

export interface PresentedAudit {
  rows: AuditRow[];
  counts: Record<Outcome, number>;
  empty: boolean;
}

const CAUSES: Record<Code, string> = {
  no_authority: 'not connected',
  policy_denied: 'not allowed',
  budget_exhausted: 'out of budget',
};

export function presentAudit(entries: AuditEntry[]): PresentedAudit {
  const counts: Record<Outcome, number> = {
    allowed: 0,
    needs_approval: 0,
    refused: 0,
    unavailable: 0,
  };
  entries.forEach((entry) => {
    counts[entry.outcome] += 1;
  });

  const rows = [...entries]
    .sort((a, b) => b.at.localeCompare(a.at))
    .map<AuditRow>((entry) => ({
      at: entry.at,
      subject: entry.subject,
      summary: summarise(entry),
      flagged: entry.trust === 'untrusted_read',
    }));

  return { rows, counts, empty: rows.length === 0 };
}

function summarise(entry: AuditEntry): string {
  if (entry.outcome === 'allowed') return `Allowed ${entry.tool}`;
  if (entry.outcome === 'needs_approval') return `Asked before ${entry.tool}`;
  if (entry.outcome === 'unavailable') return `Could not check ${entry.tool}`;

  const cause = entry.code ? CAUSES[entry.code] : undefined;
  return cause ? `Refused ${entry.tool} — ${cause}` : `Refused ${entry.tool}`;
}
