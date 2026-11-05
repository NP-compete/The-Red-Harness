export type TaskState = 'done' | 'running' | 'waiting' | 'failed' | 'skipped';

export interface PlanState {
  stages: string[][];
  fates: Record<string, TaskState>;
  depth: number;
}

export interface StageTask {
  name: string;
  state: TaskState;
}

export interface StageRow {
  position: number;
  tasks: StageTask[];
  state: TaskState;
}

export interface PresentedStages {
  rows: StageRow[];
  remaining: number;
  currentStage: number | null;
  summary: string;
}

export function presentStages(plan: PlanState): PresentedStages {
  const rows = plan.stages.map((names, index) => {
    const tasks = names.map((name) => ({ name, state: plan.fates[name] ?? 'waiting' }));
    return { position: index + 1, tasks, state: stateOf(tasks) };
  });

  const current = rows.find((row) => row.state === 'running' || row.state === 'waiting');

  return {
    rows,
    remaining: rows.filter((row) => row.state !== 'done' && row.state !== 'skipped').length,
    currentStage: current ? current.position : null,
    summary: summarise(plan),
  };
}

function stateOf(tasks: StageTask[]): TaskState {
  // One failure defines the stage; the rest of its work no longer matters.
  if (tasks.some((task) => task.state === 'failed')) return 'failed';
  if (tasks.some((task) => task.state === 'running')) return 'running';
  if (tasks.every((task) => task.state === 'skipped')) return 'skipped';
  if (tasks.every((task) => task.state === 'done' || task.state === 'skipped')) return 'done';
  return 'waiting';
}

function summarise(plan: PlanState): string {
  if (plan.stages.length === 0) return 'This plan cannot be run as written';
  const widest = Math.max(...plan.stages.map((stage) => stage.length));
  const parallel = widest > 1 ? `${widest} tasks can run together` : 'one task at a time';
  return `${plan.stages.length} stages, ${parallel}`;
}
