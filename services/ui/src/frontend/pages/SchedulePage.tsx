import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { cronInWords, nextRunInWords } from '../lib/cron-in-words';
import { useAppDispatch, useAppSelector } from '../redux/hooks';
import {
  cancelScheduledTask,
  instructionOf,
  listScheduledTasks,
  moveScheduledTaskToProject,
  runCountsFor,
  setScheduledTaskEnabled,
  type RunCounts,
  type ScheduledTask,
} from '../services/schedules-api';
import { loadProjectsThunk, selectAllProjects } from '../redux/slices/projects';
import { getThreadsByProject } from '../services/projects-api';

/**
 * What this person has asked the agent to do without them.
 *
 * **Reading, pausing and stopping — never creating.** A schedule is
 * made by asking the agent in words; it writes the cron expression
 * and stops for approval before committing. So this screen shows
 * what exists and offers the two actions that undo it, which is the
 * asymmetry that matters: starting something unattended is worth a
 * prompt, stopping it is not.
 *
 * **The instruction is the heading, not the expression.** `0 8 * * *`
 * is how the machine says it; "check the current time" is what
 * somebody will recognise as theirs. The expression is shown beside
 * it because two tasks can share an instruction and differ only in
 * when they run.
 *
 * **A failed load is not an empty list.** The service answers `null`
 * when it could not read, and this draws that as an error rather
 * than as "nothing scheduled" — which would read as *your tasks are
 * gone*.
 *
 * **Open the runs, and move the schedule between projects.** Both
 * are the same fact underneath: a schedule owns one conversation,
 * every firing appends to it, and projects group conversations. So
 * the link goes to that thread and the move assigns that thread —
 * there is no second idea of where a schedule lives that could
 * disagree with the first.
 */
/** The describer returns lower case so it can sit mid-sentence. */
function capitalise(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export default function SchedulePage() {
  const { t } = useTranslation();
  const dispatch = useAppDispatch();
  const projects = useAppSelector(selectAllProjects);
  const [tasks, setTasks] = useState<ScheduledTask[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  // Which project each schedule's conversation is in. The crons
  // endpoint does not say — project membership lives on the thread —
  // so it is read from the project side and keyed by thread.
  const [projectOf, setProjectOf] = useState<Record<string, string>>({});
  // How each schedule has been getting on, keyed by its thread.
  const [counts, setCounts] = useState<Record<string, RunCounts>>({});

  const load = useCallback(async () => {
    const found = await listScheduledTasks();
    if (found === null) {
      setFailed(true);
      return;
    }
    setFailed(false);
    setTasks(found);

    // Counts come after the list rather than with it: the crons
    // endpoint does not carry them, and waiting on one request per
    // schedule before drawing anything would leave the page blank
    // for no reason. The tallies fill in.
    const tallies: Record<string, RunCounts> = {};
    await Promise.all(
      found.map(async (task) => {
        if (!task.thread_id) return;
        const got = await runCountsFor(task.thread_id);
        if (got) tallies[task.thread_id] = got;
      })
    );
    setCounts(tallies);
  }, []);

  const loadMembership = useCallback(async (known: typeof projects) => {
    const pairs: Record<string, string> = {};
    await Promise.all(
      known.map(async (project) => {
        try {
          for (const thread of await getThreadsByProject(project.project_id)) {
            pairs[thread.id] = project.project_id;
          }
        } catch {
          // A project whose threads will not load leaves its
          // schedules showing "No project", which is wrong but
          // quiet; refusing to draw the page over it would be worse.
        }
      })
    );
    setProjectOf(pairs);
  }, []);

  useEffect(() => {
    void load();
    if (projects.length === 0) void dispatch(loadProjectsThunk());
  }, [load, dispatch, projects.length]);

  useEffect(() => {
    if (projects.length > 0) void loadMembership(projects);
  }, [projects, loadMembership]);

  const act = async (cronId: string, run: () => Promise<boolean>) => {
    setBusy(cronId);
    const ok = await run();
    setBusy(null);
    if (ok) await load();
    else setFailed(true);
  };

  return (
    <div className="h-full overflow-y-auto chat-scroll">
      <div className="mx-auto max-w-3xl px-6 py-8">
        <h1 className="text-xl font-medium">{t('schedule.title')}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{t('schedule.subtitle')}</p>

        {failed && (
          <p role="alert" className="mt-6 text-sm text-destructive">
            {t('schedule.couldNotLoad')}
          </p>
        )}

        {tasks !== null && tasks.length === 0 && !failed && (
          <p className="mt-6 text-sm text-muted-foreground">{t('schedule.nothingScheduled')}</p>
        )}

        <ul className="mt-6 space-y-3 list-none">
          {(tasks ?? []).map((task) => {
            const instruction = instructionOf(task);
            const working = busy === task.cron_id;
            return (
              <li
                key={task.cron_id}
                className="rounded border border-border bg-card px-4 py-3"
              >
                <p className="text-sm font-medium">
                  {instruction || t('schedule.untitled')}
                </p>
                {task.thread_id && counts[task.thread_id] && (
                  <p className="mt-1 text-xs text-muted-foreground">
                    {t('schedule.runs', { count: counts[task.thread_id].total })}
                    {' · '}
                    {t('schedule.succeeded', {
                      count: counts[task.thread_id].succeeded,
                    })}
                    {/* Failures are named even at zero: "0 failed" is
                        the reassurance, and a count that only appears
                        when something is wrong teaches people not to
                        look. */}
                    {' · '}
                    <span
                      className={
                        counts[task.thread_id].failed > 0 ? 'text-destructive' : ''
                      }
                    >
                      {t('schedule.failed', { count: counts[task.thread_id].failed })}
                    </span>
                    {counts[task.thread_id].waiting > 0 &&
                      ` · ${t('schedule.waiting', {
                        count: counts[task.thread_id].waiting,
                      })}`}
                  </p>
                )}
                {/* Said the way a person would say it. The raw
                    expression is kept, quietly, because somebody
                    eventually needs to check the thing the sentence
                    is a paraphrase of — and because `cronInWords`
                    hands back the expression unchanged when it
                    cannot phrase one, which would otherwise read as
                    a sentence that happens to look like cron. */}
                <p className="mt-1 text-sm">
                  {capitalise(cronInWords(task.schedule))}
                  {task.enabled
                    ? task.next_run_date
                      ? ` · ${t('schedule.nextAt', {
                          at: nextRunInWords(task.next_run_date, new Date()),
                        })}`
                      : ''
                    : ` · ${t('schedule.paused')}`}
                </p>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  <code>{task.schedule}</code>
                  {task.payload?.timezone ? ` · ${task.payload.timezone}` : ' · UTC'}
                </p>
                <div className="mt-3 flex flex-wrap items-center gap-3">
                  {task.thread_id && (
                    <>
                      <a
                        href={`/chat/${task.thread_id}`}
                        className="text-xs text-muted-foreground hover:text-foreground underline"
                      >
                        {t('schedule.openRuns')}
                      </a>
                      <label className="flex items-center gap-1 text-xs text-muted-foreground">
                        {t('schedule.project')}
                        <select
                          disabled={working}
                          value={projectOf[task.thread_id] ?? ''}
                          onChange={(e) => {
                            const chosen = e.target.value || null;
                            const thread = task.thread_id as string;
                            void act(task.cron_id, async () => {
                              const ok = await moveScheduledTaskToProject(thread, chosen);
                              if (ok) await loadMembership(projects);
                              return ok;
                            });
                          }}
                          className="rounded border border-border bg-background px-1 py-0.5 text-xs"
                        >
                          <option value="">{t('schedule.noProject')}</option>
                          {projects.map((p) => (
                            <option key={p.project_id} value={p.project_id}>
                              {p.project_name}
                            </option>
                          ))}
                        </select>
                      </label>
                    </>
                  )}
                  <button
                    type="button"
                    disabled={working}
                    onClick={() =>
                      act(task.cron_id, () =>
                        setScheduledTaskEnabled(task.cron_id, !task.enabled)
                      )
                    }
                    className="text-xs text-muted-foreground hover:text-foreground disabled:opacity-50"
                  >
                    {task.enabled ? t('schedule.pause') : t('schedule.resume')}
                  </button>
                  <button
                    type="button"
                    disabled={working}
                    onClick={() => act(task.cron_id, () => cancelScheduledTask(task.cron_id))}
                    className="text-xs text-muted-foreground hover:text-destructive disabled:opacity-50"
                  >
                    {t('schedule.cancel')}
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
