export interface RunRecord {
  id: string;
  agent: string;
  outcome: 'ok' | 'failed';
  at: string;
  title: string;
  cost: number;
}

export interface Filter {
  agents: string[];
  outcomes: string[];
  since: string | null;
  text: string;
  minCost: number | null;
}

export interface FilteredRuns {
  matches: RunRecord[];
  hidden: number;
  description: string;
  emptyMessage: string;
}

const WINDOW = /^(\d+)([hd])$/;
const HOUR = 3_600_000;

export function applyFilter(runs: RunRecord[], filter: Filter, now: Date): FilteredRuns {
  const cutoff = filter.since === null ? null : since(filter.since, now);
  const text = filter.text.trim().toLowerCase();

  // Values within a field are alternatives; fields are all required.
  const matches = runs.filter(
    (run) =>
      (filter.agents.length === 0 || filter.agents.includes(run.agent)) &&
      (filter.outcomes.length === 0 || filter.outcomes.includes(run.outcome)) &&
      (cutoff === null || Date.parse(run.at) >= cutoff) &&
      (text === '' || run.title.toLowerCase().includes(text)) &&
      (filter.minCost === null || run.cost >= filter.minCost),
  );

  return {
    matches,
    hidden: runs.length - matches.length,
    description: describe(filter),
    emptyMessage: matches.length === 0 ? 'No runs match this filter' : '',
  };
}

function since(window: string, now: Date): number {
  const parsed = WINDOW.exec(window);
  // An unparsed window silently matching everything would be worse than this.
  if (!parsed) throw new Error(`${window} is not a time window`);
  const [, amount, unit] = parsed;
  const hours = Number(amount) * (unit === 'd' ? 24 : 1);
  return now.getTime() - hours * HOUR;
}

function describe(filter: Filter): string {
  const parts = [
    ...filter.agents,
    ...filter.outcomes,
    ...(filter.since ? [windowWords(filter.since)] : []),
    ...(filter.text.trim() ? [`"${filter.text.trim()}"`] : []),
    ...(filter.minCost !== null ? [`over ${filter.minCost}`] : []),
  ];
  return parts.length === 0 ? 'everything' : parts.join(', ');
}

function windowWords(window: string): string {
  const parsed = WINDOW.exec(window);
  if (!parsed) return window;
  const [, amount, unit] = parsed;
  return `last ${amount} ${unit === 'd' ? 'days' : 'hours'}`;
}
