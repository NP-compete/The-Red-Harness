export interface ProgressState {
  doing: string;
  done: number;
  total: number;
  fraction: number | null;
  remainingSeconds: number | null;
  elapsedSeconds: number;
  totalIsFinal: boolean;
  overrunning: boolean;
}

/** A catalogue key with whatever it interpolates. */
export interface Phrase {
  key: string;
  count?: number;
  values?: Record<string, number>;
}

export interface PresentedProgress {
  /** What the agent is doing, in its own words — not translatable.
   *  Empty once the run is finished, which `finished` then says. */
  doing: string;
  finished: boolean;
  steps: Phrase;
  /** Absent when nothing measured how long is left. */
  remaining: Phrase | null;
  elapsed: Phrase;
  /** Absent unless the run is slower than usual. */
  note: Phrase | null;
  bar: number | null;
}

export function presentProgress(state: ProgressState): PresentedProgress {
  const finished = state.doing === '';

  return {
    doing: finished ? '' : capitalise(state.doing),
    finished,
    steps: state.totalIsFinal
      ? {
          key: 'progress.stepOf',
          values: {
            done: Math.min(state.done + 1, state.total),
            total: state.total,
          },
        }
      : { key: 'progress.stepsSoFar', count: state.total },
    // Silence beats a number that was never measured.
    remaining:
      finished || state.remainingSeconds === null
        ? null
        : howLong(state.remainingSeconds, 'progress.leftSeconds', 'progress.leftMinutes'),
    elapsed: howLong(
      state.elapsedSeconds,
      'progress.elapsedSeconds',
      'progress.elapsedMinutes',
    ),
    note: state.overrunning ? { key: 'progress.overrunning' } : null,
    bar: state.fraction,
  };
}

/** Seconds below a minute, minutes above it, as a key and a count. */
function howLong(seconds: number, underMinute: string, overMinute: string): Phrase {
  if (seconds < 60) return { key: underMinute, count: Math.round(seconds) };
  return { key: overMinute, count: Math.round(seconds / 60) };
}

function capitalise(text: string): string {
  // A no-op in scripts with no letter case, which is the right
  // answer there rather than a special case.
  return text.charAt(0).toUpperCase() + text.slice(1);
}
