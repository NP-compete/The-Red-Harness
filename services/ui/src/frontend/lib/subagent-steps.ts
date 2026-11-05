/**
 * A delegation as a list of steps, built from the progress stream.
 *
 * The box used to show the subagent's streamed prose. That was the
 * wrong content: a report is long, starts with preamble, and the
 * orchestrator relays it in the answer anyway — so the reader got a
 * wall of text twice and still could not tell how far along it was.
 *
 * What they want while waiting is what it is *doing*. The stream
 * already carries that: each tool call arrives as an `activity`,
 * and prose arriving means it has finished calling things and
 * started writing.
 *
 * Accumulated here rather than in the component so the arithmetic
 * is testable and the component stays a renderer.
 */

/**
 * The marker for a step that is the subagent talking, not calling.
 *
 * There used to be exactly one of these, pushed when the first prose
 * arrived and never again — "it has stopped calling things and
 * started writing". That threw away the most useful thing in the
 * stream. The subagent is told, in PROMPT.md, to say what it is
 * about to do before it does it, so between every two tool calls
 * there is a sentence explaining the next one. All of it was
 * collapsed into a single line reading "writing".
 *
 * Now a say-step is pushed each time prose follows a call, so the
 * list reads as the subagent worked: said, did, said, did.
 */
export const WRITING = '__writing__';

export interface Step {
  /** Tool name, or {@link WRITING}. */
  tool: string;
  /**
   * Tool-call id, the identity of a step.
   *
   * The stream's chunks are cumulative, so the same call arrives
   * again on every chunk. Keying on the label instead produced a
   * fresh step each time and a list that read
   * "a", "a, b", "a, b, c".
   */
  id: string;
  startedAt: number;
  /** Unset while the step is still running. */
  endedAt?: number;
  /** What the subagent said at this point, for a {@link WRITING} step. */
  text?: string;
  /** What the subagent asked the tool for, pretty-printed. */
  args?: string;
  /**
   * What the tool answered.
   *
   * Arrives later than the call and on its own message, so a step
   * exists without one for as long as the tool is running. Matched
   * back by id — the newest step is not reliably the one that
   * finished, because several calls can be in flight at once.
   */
  result?: string;
}

export interface DelegationProgress {
  ns: string;
  agent?: string;
  instruction?: string;
  latest?: string;
  steps: Step[];
  startedAt: number;
}

export interface ProgressEvent {
  ns: string;
  agent?: string;
  instruction?: string;
  latest?: string;
  /** Every tool call emitted so far, cumulative. */
  calls?: { id: string; name: string; args?: string }[];
  /** Tool results, keyed by the id of the call they answer. */
  results?: { id: string; content: string }[];
  node?: string;
}

/** The most recent thing the subagent said, however long ago. */
function lastSaid(steps: Step[]): Step | undefined {
  for (let i = steps.length - 1; i >= 0; i -= 1) {
    if (steps[i].tool === WRITING) return steps[i];
  }
  return undefined;
}

/**
 * Fold one progress event into a delegation's state.
 *
 * Pure, and returns a new object, so React sees a change.
 */
export function applyProgress(
  previous: DelegationProgress | undefined,
  event: ProgressEvent,
  now: number,
): DelegationProgress {
  const base: DelegationProgress =
    previous ?? { ns: event.ns, steps: [], startedAt: now };

  const steps = [...base.steps];
  const seen = new Set(steps.map((s) => s.id));

  const closeOpen = () => {
    for (let i = 0; i < steps.length; i += 1) {
      if (steps[i].endedAt === undefined) steps[i] = { ...steps[i], endedAt: now };
    }
  };

  // Only calls we have not seen before. The chunks repeat every
  // call made so far, so without the id check each chunk would add
  // the whole list again.
  const fresh = (event.calls ?? []).filter((c) => !seen.has(c.id));
  if (fresh.length > 0) {
    // A new call means whatever was running has returned: the
    // stream carries no completion event, so the next call is the
    // only signal.
    closeOpen();
    for (const call of fresh) {
      steps.push({ tool: call.name, id: call.id, startedAt: now, args: call.args });
    }
  } else if (event.latest) {
    // Prose. `latest` is cumulative within one message and replaced
    // when a new one starts, so the open say-step is extended and a
    // closed one means this is the subagent speaking again after a
    // call — a new step, not an edit of the last.
    const last = steps[steps.length - 1];
    if (last && last.tool === WRITING && last.endedAt === undefined) {
      steps[steps.length - 1] = { ...last, text: event.latest };
    } else if (lastSaid(steps)?.text !== event.latest) {
      // Not the sentence we already have. `latest` is only replaced
      // once the *next* message starts streaming, so for a second or
      // two after a tool returns it still holds the line the
      // subagent said before the call. Opening a step on that put
      // the previous sentence back on screen as though it were new —
      // seen in the box holding "Reading …" for four seconds after
      // the read had finished.
      closeOpen();
      steps.push({
        tool: WRITING,
        id: `${WRITING}-${steps.length}`,
        startedAt: now,
        text: event.latest,
      });
    }
  }

  // A result closes the step it belongs to, which is better than the
  // old signal — "the next call started, so the last one must have
  // finished" could not tell which of several concurrent calls had
  // returned, and left the final one open until the prose arrived.
  for (const r of event.results ?? []) {
    const i = steps.findIndex((s) => s.id === r.id);
    if (i === -1) continue;
    steps[i] = {
      ...steps[i],
      result: r.content,
      endedAt: steps[i].endedAt ?? now,
    };
  }

  return {
    ...base,
    agent: event.agent ?? base.agent,
    instruction: event.instruction ?? base.instruction,
    // Cumulative chunks: the newest is the whole text so far.
    latest: event.latest ?? base.latest,
    steps,
  };
}

/**
 * Close every running step, for when the delegation finishes.
 *
 * Every, not just the last: several calls can be emitted at once
 * and all of them are open until something closes them.
 */
export function finishSteps(progress: DelegationProgress, now: number): Step[] {
  return progress.steps.map((s) => (s.endedAt === undefined ? { ...s, endedAt: now } : s));
}

/** `1.2s`, or `1m 04s` past a minute. */
export function formatDuration(ms: number): string {
  if (ms < 0) return '0.0s';
  const seconds = ms / 1000;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}m ${String(s).padStart(2, '0')}s`;
}

/** `0:42` — a running clock, not a precise measurement. */
export function formatElapsed(ms: number): string {
  const total = Math.max(0, Math.floor(ms / 1000));
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`;
}
