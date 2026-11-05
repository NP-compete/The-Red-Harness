export interface ToolChange {
  tool: string;
  changes: string[];
  needsReapproval: boolean;
  summary: string;
  approvedOn: string;
}

export interface PresentedToolChange {
  headline: string;
  detail: string;
  approvedOn: string;
  severity: 'low' | 'medium' | 'high';
  blocking: boolean;
  action: 'reapprove' | 'none';
}

const LOUD = new Set(['server-changed', 'description-changed']);

export function presentToolChange(change: ToolChange): PresentedToolChange | null {
  if (change.changes.length === 0) return null;

  return {
    headline: `${change.tool} has changed since you approved it`,
    detail: change.summary,
    approvedOn: formatDate(change.approvedOn),
    severity: severity(change),
    blocking: change.needsReapproval,
    action: change.needsReapproval ? 'reapprove' : 'none',
  };
}

function severity(change: ToolChange): 'low' | 'medium' | 'high' {
  if (change.changes.some((name) => LOUD.has(name))) return 'high';
  return change.needsReapproval ? 'medium' : 'low';
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  });
}
