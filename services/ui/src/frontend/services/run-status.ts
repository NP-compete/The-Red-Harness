import { buildAgentApiUrl } from '../lib/app-paths';
import { authenticatedFetch } from './authenticated-fetch';

const STOPPED = 'This run stopped before it could finish.';

interface Run {
  status?: string;
  error_message?: string | null;
  created_at?: string;
}

/**
 * Why a conversation's last run can no longer be carried on, if so.
 *
 * A run that dies while paused leaves the thread waiting on an
 * approval for ever: the prompt still renders, the buttons still
 * look live, and pressing them reaches a run the agent has already
 * given up on. Asking what became of it is the difference between
 * "waiting for you" and "this is not going to happen".
 */
async function latestRun(threadId: string): Promise<Run | null> {
  try {
    const response = await authenticatedFetch(
      buildAgentApiUrl(`/threads/${threadId}/runs`),
      { method: 'GET' },
    );
    if (!response.ok) return null;

    const runs = (await response.json()) as Run[];
    if (!Array.isArray(runs) || runs.length === 0) return null;

    // Newest first: an old run says nothing about the one happening
    // now.
    return [...runs].sort(
      (a, b) => Date.parse(b.created_at ?? '') - Date.parse(a.created_at ?? ''),
    )[0];
  } catch {
    return null;
  }
}

/**
 * Why a conversation's last run can no longer be carried on, if so.
 *
 * A run that dies while paused leaves the thread waiting on an
 * approval for ever: the prompt still renders, the buttons still
 * look live, and pressing them reaches a run the agent has already
 * given up on. Asking what became of it is the difference between
 * "waiting for you" and "this is not going to happen".
 */
export async function deadRunReason(threadId: string): Promise<string | null> {
  const latest = await latestRun(threadId);
  if (!latest) return null;
  if (latest.status !== 'error' && latest.status !== 'failed') return null;
  return latest.error_message || STOPPED;
}

/**
 * Whether the agent is still working on this conversation.
 *
 * Asking to stop does not stop anything at once — the step in flight
 * runs to its end first. Only the agent knows when that has
 * happened, so the only honest way to tell someone their stop has
 * landed is to ask it.
 */
export async function runStillGoing(threadId: string): Promise<boolean> {
  const latest = await latestRun(threadId);
  return latest?.status === 'running' || latest?.status === 'pending';
}
