export interface ThreadEffort {
  modelCalls: number;
  toolCalls: number;
}

/**
 * How much work a conversation took, counted from the turns on screen.
 *
 * A long wait and a short answer look the same in the transcript. The
 * number of times the model was asked, and how many tools it reached
 * for, is what tells those apart — and a run that went round in
 * circles shows up here before it shows up anywhere else.
 */
export function countEffort(messages: unknown[]): ThreadEffort | null {
  const effort: ThreadEffort = { modelCalls: 0, toolCalls: 0 };

  for (const message of messages) {
    const turn = message as { type?: string; tool_calls?: unknown[] };
    if (turn?.type !== 'ai') continue;
    effort.modelCalls += 1;
    if (Array.isArray(turn.tool_calls)) effort.toolCalls += turn.tool_calls.length;
  }

  return effort.modelCalls > 0 ? effort : null;
}
