import type { CallState } from './tool-activity';

export interface RecordedCall {
  /** The call this entry belongs to, so a result can find it. */
  id: string;
  tool: string;
  state: CallState;
  /** When the call began, which is what a duration measures from. */
  startedAt: number;
  /** Zero until the result arrives: half a duration reads as a fast step. */
  ms: number;
  writes: boolean;
}

interface StreamedMessage {
  type?: string;
  tool_call_id?: string;
  tool_calls?: { id?: string; name?: string }[];
}

/**
 * Tool calls, recorded as the run streams.
 *
 * Derived from the messages the browser already receives rather than a
 * separate channel: a panel fed by events nobody sends shows nothing.
 */
export function recordToolCall(
  previous: RecordedCall[],
  message: StreamedMessage,
  now: number,
  changesThings: (tool: string) => boolean = () => false,
): RecordedCall[] {
  if (message.type === 'tool' && message.tool_call_id) {
    const id = message.tool_call_id;
    return previous.map((call) =>
      call.id === id
        ? { ...call, state: 'done' as CallState, ms: Math.max(0, now - call.startedAt) }
        : call,
    );
  }

  const calls = message.type === 'ai' ? (message.tool_calls ?? []) : [];
  if (calls.length === 0) {
    return previous;
  }

  const known = new Set(previous.map((call) => call.id));
  const added = calls
    .filter((call) => call.id && !known.has(call.id))
    .map<RecordedCall>((call) => {
      const tool = call.name ?? (call.id as string);
      return {
        id: call.id as string,
        tool,
        state: 'running',
        startedAt: now,
        ms: 0,
        writes: changesThings(tool),
      };
    });

  return added.length > 0 ? [...previous, ...added] : previous;
}

/**
 * Mark the calls whose effects someone wanted a person to see first.
 *
 * Applied where the approval policy is known rather than while
 * recording: what ran is a fact, whether it changes things is a
 * judgement that arrives separately.
 */
export function markWrites(
  calls: readonly RecordedCall[],
  isReversible: (tool: string) => boolean,
): RecordedCall[] {
  return calls.map((call) => ({ ...call, writes: !isReversible(call.tool) }));
}

/**
 * The tool still waiting on an answer, if any.
 *
 * One slow call looks exactly like a run that has died: nothing
 * arrives either way. Naming it is the difference between "nothing
 * has happened" and "this is taking a while".
 */
export function runningTool(calls: RecordedCall[]): string {
  for (let i = calls.length - 1; i >= 0; i -= 1) {
    if (calls[i].state !== 'done') return calls[i].tool;
  }
  return '';
}
