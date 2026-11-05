export interface PlanStep {
  tool: string;
  summary: string;
  writes: boolean;
}

export type PlanChoice = 'approve' | 'read-only' | 'edit';

export interface PlanRow {
  number: number;
  summary: string;
  tool: string;
  changes: boolean;
}

export interface PresentedPlan {
  steps: PlanRow[];
  changingCount: number;
  headline: string;
  choices: PlanChoice[];
}

export function presentPlan(steps: PlanStep[]): PresentedPlan {
  const rows = steps.map<PlanRow>((step, index) => ({
    number: index + 1,
    summary: step.summary,
    tool: step.tool,
    changes: step.writes,
  }));

  const changingCount = rows.filter((row) => row.changes).length;

  return {
    steps: rows,
    changingCount,
    headline: headlineFor(rows.length, changingCount),
    choices: choicesFor(rows.length, changingCount),
  };
}

function headlineFor(total: number, changing: number): string {
  if (total === 0) return 'This plan has no steps.';
  if (changing === 0) return `${total} steps, and nothing is changed.`;
  return `${total} steps. Approving allows ${changing} that change something.`;
}

function choicesFor(total: number, changing: number): PlanChoice[] {
  if (total === 0) return [];
  // Offering a research-only run is only meaningful when something
  // would otherwise be changed.
  return changing > 0 ? ['approve', 'read-only', 'edit'] : ['approve', 'edit'];
}
