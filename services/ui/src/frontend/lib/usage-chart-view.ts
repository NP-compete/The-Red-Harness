export interface UsagePoint {
  at: string;
  runs: number;
  cost: number;
}

export interface Window {
  days: number;
  now: Date;
}

export interface UsageBucket {
  label: string;
  day: string;
  runs: number;
  cost: number;
}

export interface BucketedUsage {
  buckets: UsageBucket[];
  total: { runs: number; cost: number };
  peak: number;
  busiest: string;
  outsideWindow: number;
}

const DAY = 86_400_000;

export function bucketUsage(points: UsagePoint[], window: Window): BucketedUsage {
  if (window.days < 1) throw new Error('a window must cover at least one day');

  const days = Array.from({ length: window.days }, (_, index) => {
    const date = new Date(window.now.getTime() - (window.days - 1 - index) * DAY);
    return dayKey(date);
  });

  const buckets: UsageBucket[] = days.map((day) => ({
    label: label(day),
    day,
    runs: 0,
    cost: 0,
  }));

  const byDay = new Map(buckets.map((bucket) => [bucket.day, bucket]));
  let outside = 0;

  for (const point of points) {
    const bucket = byDay.get(dayKey(new Date(point.at)));
    // Older than the window: counted, so a shrinking total is explainable.
    if (!bucket) {
      outside += 1;
      continue;
    }
    bucket.runs += point.runs;
    bucket.cost += point.cost;
  }

  const peak = Math.max(0, ...buckets.map((bucket) => bucket.runs));
  // On a tie the most recent peak is the useful one to name.
  const busiest =
    peak > 0 ? ([...buckets].reverse().find((bucket) => bucket.runs === peak)?.label ?? '') : '';

  return {
    buckets,
    total: {
      runs: buckets.reduce((sum, bucket) => sum + bucket.runs, 0),
      cost: round(buckets.reduce((sum, bucket) => sum + bucket.cost, 0)),
    },
    peak,
    busiest,
    outsideWindow: outside,
  };
}

function dayKey(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function label(day: string): string {
  return new Date(`${day}T00:00:00Z`).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    timeZone: 'UTC',
  });
}

function round(value: number): number {
  return Math.round(value * 100) / 100;
}
