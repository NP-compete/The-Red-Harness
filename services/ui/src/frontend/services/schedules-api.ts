import { buildAppPath } from '../lib/app-paths';

/**
 * Scheduled tasks, as the browser sees them.
 *
 * These go through the generic `/proxy/agent/*` pass-through rather
 * than a hand-written BFF route, because the agent's own
 * `/runs/crons` endpoints already scope every one of them to the
 * caller: the row is selected by `user_id`, so a screen cannot ask
 * for somebody else's schedules by calling a different path.
 *
 * **There is deliberately no create here.** A schedule is written in
 * words to the agent, which turns it into a cron expression and
 * stops for approval before committing it. A form taking five
 * fields would be a second way in with none of the asking.
 *
 * `null` on anything other than a clean answer, as the other
 * services here do: an empty list and a failed load are different
 * facts, and drawing the second as the first tells somebody their
 * schedules are gone.
 */

export interface ScheduledTask {
  cron_id: string;
  schedule: string;
  /**
   * The conversation this schedule keeps its runs in.
   *
   * Every firing appends to it, which is the only reason the runs
   * survive: a cron with no thread is *stateless*, and a stateless
   * cron's thread is deleted after the run unless `on_run_completed`
   * says otherwise. Null only for schedules made before that was
   * fixed, or through the API directly.
   */
  thread_id: string | null;
  next_run_date: string | null;
  enabled: boolean;
  created_at: string | null;
  metadata?: Record<string, unknown>;
  payload?: { input?: { messages?: Array<{ content?: string }> }; timezone?: string };
}

async function call<T>(path: string, init?: RequestInit): Promise<T | null> {
  try {
    const response = await fetch(buildAppPath(`/api/proxy/agent/${path}`), {
      credentials: 'include',
      ...init,
      headers: init?.body ? { 'Content-Type': 'application/json' } : undefined,
    });
    if (!response.ok) return null;
    if (response.status === 204) return {} as T;
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

export async function listScheduledTasks(): Promise<ScheduledTask[] | null> {
  const body = await call<ScheduledTask[]>('runs/crons/search', {
    method: 'POST',
    body: JSON.stringify({ limit: 100 }),
  });
  return Array.isArray(body) ? body : null;
}

export async function cancelScheduledTask(cronId: string): Promise<boolean> {
  return (await call(`runs/crons/${encodeURIComponent(cronId)}`, { method: 'DELETE' })) !== null;
}

export async function setScheduledTaskEnabled(
  cronId: string,
  enabled: boolean
): Promise<boolean> {
  // Only `enabled` is sent. The same endpoint accepts a new schedule
  // and a new payload, and this screen pauses and resumes — it does
  // not rewrite what a task does.
  const body = await call(`runs/crons/${encodeURIComponent(cronId)}`, {
    method: 'PATCH',
    body: JSON.stringify({ enabled }),
  });
  return body !== null;
}

export interface RunCounts {
  total: number;
  succeeded: number;
  failed: number;
  /** Started and not finished: `pending` or `running`. */
  inFlight: number;
  /** Stopped on an approval it is still waiting for. */
  waiting: number;
}

/**
 * How a schedule has been getting on.
 *
 * Aegra's run vocabulary is `pending`, `running`, `error`, `success`,
 * `timeout`, `interrupted`. **A timeout counts as failed**: the run
 * did not produce an answer, and filing it with the successes is how
 * a schedule that has been quietly dying for a fortnight still looks
 * healthy. `interrupted` is counted separately rather than as a
 * failure — it is a run waiting on an approval nobody gave, which is
 * a different thing to fix.
 *
 * One request per schedule. That is fine for a page listing a
 * person's own schedules and would not be for hundreds; if this ever
 * needs to scale, the count belongs in the crons payload, not in a
 * loop here.
 */
export async function runCountsFor(threadId: string): Promise<RunCounts | null> {
  const runs = await call<Array<{ status?: string }>>(
    `threads/${encodeURIComponent(threadId)}/runs`
  );
  if (!Array.isArray(runs)) return null;
  const count = (...wanted: string[]) =>
    runs.filter((r) => wanted.includes(String(r.status))).length;
  return {
    total: runs.length,
    succeeded: count('success'),
    failed: count('error', 'timeout'),
    inFlight: count('pending', 'running'),
    waiting: count('interrupted'),
  };
}

/**
 * Put a schedule in a project, or take it out of one.
 *
 * **A schedule is moved by moving its conversation.** Projects group
 * threads, and a schedule owns exactly one — so there is no second
 * notion of project membership to keep in step with the first. Take
 * the thread with it and the schedule is wherever its runs are.
 */
export async function moveScheduledTaskToProject(
  threadId: string,
  projectId: string | null
): Promise<boolean> {
  const body = await call('projects/assign', {
    method: 'POST',
    body: JSON.stringify({ thread_id: threadId, project_id: projectId }),
  });
  return body !== null;
}

/** What the task was asked to do, as the person phrased it. */
export function instructionOf(task: ScheduledTask): string {
  return task.payload?.input?.messages?.[0]?.content?.trim() || '';
}
