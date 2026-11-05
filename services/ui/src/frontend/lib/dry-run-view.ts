export interface PreviewStep {
  tool: string;
  target: string;
  harmless: boolean;
}

export interface PreviewState {
  steps: PreviewStep[];
  wouldChange: number;
  estimatedCost: string;
  currency: string;
  needsApproval: string[];
  permanent: string[];
  runnable: boolean;
  summary: string;
  reason: string;
}

export interface PreviewRow {
  label: string;
  changes: boolean;
}

export interface PresentedPreview {
  headline: string;
  detail: string;
  rows: PreviewRow[];
  approvals: string[];
  cost: string;
  warning: string;
  canRun: boolean;
  severity: 'info' | 'medium';
}

export function presentPreview(state: PreviewState): PresentedPreview {
  const amount = Number(state.estimatedCost);
  const stuck = state.permanent.length;

  return {
    // Said first and plainly, so a preview is never mistaken for a result.
    headline: 'Nothing has run yet',
    detail: state.summary,
    rows: state.steps.map((step) => ({
      label: `${step.tool} → ${step.target}`,
      changes: !step.harmless,
    })),
    approvals: state.needsApproval,
    cost: amount > 0 ? `about ${money(amount, state.currency)}` : '',
    warning: stuck > 0 ? `${stuck} of these cannot be undone afterwards` : '',
    canRun: state.runnable,
    severity: stuck > 0 ? 'medium' : 'info',
  };
}

function money(amount: number, currency: string): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(amount);
}
