export interface ResponseTiming {
  totalDurationMs: number;
  timeToFirstTokenMs: number | null;
  /** The reply stopped before the agent had finished it. */
  cutShort: boolean;
}

export interface PresentedTiming {
  line: string;
  firstToken: string;
  /** The same, spelled out: figures alone read as punctuation. */
  spoken: string;
}

/**
 * How long an answer took, and whether it is all of it.
 *
 * A reply that ends mid-sentence used to carry the same footer as
 * one that finished — "Response time: 9.1s" under a truncated
 * paragraph reads as an answer that was complete in nine seconds.
 */
export function presentResponseTiming(timing: ResponseTiming): PresentedTiming {
  const seconds = (timing.totalDurationMs / 1000).toFixed(1);
  const firstToken =
    timing.timeToFirstTokenMs != null
      ? `First token: ${Math.round(timing.timeToFirstTokenMs)}ms`
      : '';

  if (timing.cutShort) {
    return {
      line: `Stopped early after ${seconds}s`,
      firstToken,
      spoken: `This answer stopped early, after ${seconds} seconds`,
    };
  }

  return {
    line: `Response time: ${seconds}s`,
    firstToken,
    spoken: [
      `This answer took ${seconds} seconds`,
      timing.timeToFirstTokenMs != null
        ? `first token after ${Math.round(timing.timeToFirstTokenMs)} milliseconds`
        : '',
    ]
      .filter(Boolean)
      .join(', '),
  };
}
