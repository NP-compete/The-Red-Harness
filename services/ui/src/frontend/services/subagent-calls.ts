import { buildAgentApiUrl } from '../lib/app-paths';
import { authenticatedFetch } from './authenticated-fetch';

export interface SubagentCall {
  name: string;
  args: Record<string, unknown>;
}

/**
 * What the delegated steps of a conversation actually ran.
 *
 * A subagent's work is reported as one line and a duration; the
 * queries and reads behind it are what say whether the answer rests
 * on anything. The agent decides who may see this, so an empty list
 * covers both "nothing ran" and "not for you" — neither is worth
 * putting in front of a reader.
 */
export async function getSubagentCalls(threadId: string): Promise<SubagentCall[]> {
  try {
    const response = await authenticatedFetch(
      buildAgentApiUrl(`/v1/eval/thread-tool-calls/${threadId}`),
      { method: 'GET' },
    );
    if (!response.ok) return [];

    const body = (await response.json()) as { tool_calls?: unknown };
    if (!Array.isArray(body.tool_calls)) return [];

    return body.tool_calls
      .filter(
        (call): call is { tool_name: string; arguments?: Record<string, unknown> } =>
          Boolean(call && typeof call === 'object' && 'tool_name' in call && call.tool_name),
      )
      .map((call) => ({ name: call.tool_name, args: call.arguments ?? {} }));
  } catch {
    return [];
  }
}
