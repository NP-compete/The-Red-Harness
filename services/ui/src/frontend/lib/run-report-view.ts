export interface RunReport {
  outcome: 'done' | 'partial' | 'failed' | 'stopped';
  headline: string;
  took: string;
  cost: string;
  currency: string;
  changes: string[];
  permanent: string[];
  gaps: string[];
  unsupported: string[];
  reversible: boolean;
  needsAttention: boolean;
}

export interface ReportSection {
  title: string;
  items: string[];
  tone: 'neutral' | 'warning';
}

export interface PresentedReport {
  headline: string;
  meta: string;
  sections: ReportSection[];
  severity: 'none' | 'medium' | 'high';
  action: 'undo' | 'retry' | 'none';
}

export function presentReport(report: RunReport): PresentedReport {
  const amount = Number(report.cost);

  const sections: ReportSection[] = [
    { title: 'Changed', items: report.changes, tone: 'neutral' as const },
    { title: 'Cannot be undone', items: report.permanent, tone: 'warning' as const },
    { title: 'Not answered', items: report.gaps, tone: 'warning' as const },
    { title: 'Not backed by a source', items: report.unsupported, tone: 'warning' as const },
    // An empty heading says nothing and costs a line.
  ].filter((section) => section.items.length > 0);

  return {
    headline: report.headline,
    meta: amount > 0 ? `${report.took} · ${money(amount, report.currency)}` : report.took,
    sections,
    severity: severity(report),
    action: action(report),
  };
}

function severity(report: RunReport): 'none' | 'medium' | 'high' {
  if (report.outcome === 'failed' || report.outcome === 'stopped') return 'high';
  return report.needsAttention ? 'medium' : 'none';
}

function action(report: RunReport): 'undo' | 'retry' | 'none' {
  if (report.outcome === 'failed') return 'retry';
  return report.reversible ? 'undo' : 'none';
}

function money(amount: number, currency: string): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(amount);
}
