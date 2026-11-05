import type { ReadItem, ReadShape } from '../components/ReadMaterial';

interface LooseMessage {
  type?: string;
  content?: unknown;
  tool_call_id?: string;
  tool_calls?: { id?: string; name?: string; content?: unknown; shape?: AgentShape }[];
  shape?: AgentShape;
}

interface AgentShape {
  kind?: string;
  rows?: number;
  columns?: string[];
  language?: string;
  needs_paging?: boolean;
  needs_collapsing?: boolean;
}

/** The agent names these in snake case; the view reads camel. */
function asShape(shape: AgentShape | undefined): ReadShape | undefined {
  if (!shape?.kind) return undefined;
  return {
    kind: shape.kind as ReadShape['kind'],
    rows: shape.rows ?? 0,
    columns: shape.columns ?? [],
    language: shape.language ?? '',
    needsPaging: shape.needs_paging ?? false,
    needsCollapsing: shape.needs_collapsing ?? false,
  };
}

/**
 * The tool output this answer was built from.
 *
 * Bounded by the question above it: material from an earlier turn did
 * not inform this answer, and showing it as though it did would be a
 * false account of the work.
 */
export function readsForAnswer(messages: LooseMessage[], answerIndex: number): ReadItem[] {
  const names = new Map<string, string>();
  const reads: ReadItem[] = [];

  let start = 0;
  for (let i = answerIndex - 1; i >= 0; i--) {
    if (messages[i]?.type === 'human') {
      start = i + 1;
      break;
    }
  }

  for (let i = start; i < answerIndex; i++) {
    const message = messages[i];
    for (const call of message?.tool_calls ?? []) {
      if (call?.id) names.set(call.id, call.name ?? call.id);
      // The thread arrives with each result folded into the call that
      // asked for it; a call with no content is still waiting.
      if (typeof call?.content === 'string') {
        reads.push({
          source: call.name ?? call.id ?? '',
          text: call.content,
          shape: asShape(call.shape),
        });
      }
    }
    if (message?.type !== 'tool') continue;

    const id = message.tool_call_id ?? '';
    reads.push({
      source: names.get(id) ?? id,
      text: typeof message.content === 'string' ? message.content : '',
      shape: asShape(message.shape),
    });
  }

  return reads;
}
