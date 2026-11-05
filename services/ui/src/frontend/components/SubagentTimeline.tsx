import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Check, ChevronRight, Loader2, MessageSquare, PencilLine } from 'lucide-react';
import {
  formatDuration,
  formatElapsed,
  WRITING,
  type Step,
} from '../lib/subagent-steps';
import { toolLabel } from '../lib/tool-label';

/**
 * What a subagent is doing, as steps rather than prose.
 *
 * The box used to stream the subagent's own text. Wrong content:
 * the report is long, opens with preamble, and the orchestrator
 * relays it in the answer anyway — so the reader got a wall of text
 * twice and still could not tell how far along it was, or whether a
 * two-minute delegation was working or stuck.
 *
 * A step list answers both. Each tool call is a line with a
 * duration; the last line says whether it is still calling things
 * or has started writing.
 *
 * A step opens. The name alone answers "how far along", not "was
 * that the right query, and what came back" — and a delegated call
 * is precisely the one nobody watched being made, so its arguments
 * and its result are the only evidence the answer rests on. Shut by
 * default, because the list is read while waiting and a tool result
 * is a JSON blob.
 */

/** One step's arguments or result, in the same frame the orchestrator uses. */
function Detail({ label, body }: { label: string; body: string }) {
  return (
    <div className="mt-1.5">
      <div className="mb-1 text-[0.625rem] font-medium uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      <pre className="max-h-56 overflow-auto whitespace-pre-wrap break-words rounded-lg border border-border bg-muted p-2 font-mono text-[0.6875rem] text-foreground">
        {body}
      </pre>
    </div>
  );
}

interface Props {
  steps: ReadonlyArray<Step>;
  /** Unset once the delegation has finished. */
  runningSince?: number;
}

export function SubagentTimeline({ steps, runningSince }: Props) {
  const { t } = useTranslation();

  // A clock that does not tick is worse than no clock: it reads as
  // frozen, which is the exact doubt it exists to answer.
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (runningSince === undefined) return;
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [runningSince]);

  const [expanded, setExpanded] = useState<Set<string>>(() => new Set());
  const toggle = (key: string) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      if (!next.delete(key)) next.add(key);
      return next;
    });

  if (steps.length === 0) return null;

  return (
    <ol className="space-y-1" data-testid="subagent-timeline">
      {steps.map((step, i) => {
        const running = step.endedAt === undefined;
        // A say-step is labelled with what it said. "Writing" is kept
        // only for the moment prose has started but no text has
        // arrived yet, which is a flicker rather than a state.
        const label =
          step.tool === WRITING
            ? (step.text?.trim() || t('subagents.writing'))
            : toolLabel(step.tool);
        const duration = running
          ? runningSince === undefined
            ? undefined
            : now - step.startedAt
          : (step.endedAt as number) - step.startedAt;

        const key = step.id || `${step.tool}-${step.startedAt}-${i}`;
        const saying = step.tool === WRITING;
        const inspectable = Boolean(step.args || step.result || (saying && step.text));
        const open = expanded.has(key);

        const icon = saying ? (
          running ? (
            <PencilLine className="w-3 h-3 shrink-0 text-blue-500" aria-hidden="true" />
          ) : (
            <MessageSquare className="w-3 h-3 shrink-0 text-muted-foreground" aria-hidden="true" />
          )
        ) : running ? (
          <Loader2 className="w-3 h-3 shrink-0 animate-spin text-blue-500" aria-hidden="true" />
        ) : (
          <Check className="w-3 h-3 shrink-0 text-green-500" aria-hidden="true" />
        );

        const row = (
          <>
            {icon}
            <span
              className={`min-w-0 flex-1 truncate text-left ${
                saying ? 'italic text-muted-foreground' : 'text-foreground'
              }`}
            >
              {label}
            </span>
            {!saying && duration !== undefined && (
              <span className="tabular-nums shrink-0">{formatDuration(duration)}</span>
            )}
          </>
        );

        return (
          <li key={key} className="text-xs text-muted-foreground">
            {inspectable ? (
              <button
                type="button"
                onClick={() => toggle(key)}
                aria-expanded={open}
                className="flex w-full items-center gap-2 rounded py-0.5 text-left hover:bg-secondary/40"
              >
                <ChevronRight
                  className={`w-3 h-3 shrink-0 transition-transform ${open ? 'rotate-90' : ''}`}
                  aria-hidden="true"
                />
                {row}
              </button>
            ) : (
              // No detail to show: a disclosure arrow that reveals
              // nothing is worse than none. `task` has no arguments
              // worth printing, and a running call has no result yet.
              <div className="flex items-center gap-2 py-0.5 pl-5">{row}</div>
            )}
            {open && (
              <div className="pb-1 pl-5">
                {saying && step.text && (
                  <p className="mt-1.5 whitespace-pre-wrap text-[0.6875rem] italic leading-relaxed text-muted-foreground">
                    {step.text}
                  </p>
                )}
                {step.args && <Detail label={t('chat.arguments')} body={step.args} />}
                {step.result && <Detail label={t('subagents.result')} body={step.result} />}
                {running && !step.result && (
                  <p className="mt-1.5 text-[0.6875rem] italic">{t('subagents.awaitingResult')}</p>
                )}
              </div>
            )}
          </li>
        );
      })}
    </ol>
  );
}

/**
 * The one line that stays outside the collapse: what it is doing now.
 *
 * The whole step list used to sit out here, so a subagent that made
 * a dozen calls pushed the rest of the conversation off the screen
 * and the reader had to scan a growing list to find the live line.
 * Collapsed, the question is only "what now, and how long" — the
 * history is a click away for anyone who wants it.
 */
export function SubagentCurrentStep({ steps, runningSince }: Props) {
  const { t } = useTranslation();

  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (runningSince === undefined) return;
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [runningSince]);

  if (steps.length === 0) return null;

  // The newest open step, else the last thing it finished — several
  // calls can be in flight at once, and the latest is the live one.
  const current =
    [...steps].reverse().find((s) => s.endedAt === undefined) ?? steps[steps.length - 1];
  const running = current.endedAt === undefined;
  // The same rule as the timeline: a say-step is labelled with what
  // it said. This line is the only part of the box visible while it
  // is collapsed, so leaving it reading "writing…" meant the live
  // narration existed in the data and nowhere on screen — the box
  // looked frozen for the whole of a delegation.
  const saying = current.tool === WRITING;
  const label = saying
    ? (current.text?.trim() || t('subagents.writing'))
    : toolLabel(current.tool);
  const duration = running
    ? runningSince === undefined
      ? undefined
      : now - current.startedAt
    : (current.endedAt as number) - current.startedAt;

  const done = steps.filter((s) => s.endedAt !== undefined).length;

  return (
    <div
      className="flex items-center gap-2 text-xs text-muted-foreground"
      data-testid="subagent-current-step"
    >
      {running ? (
        saying ? (
          <PencilLine className="w-3 h-3 shrink-0 text-blue-500" aria-hidden="true" />
        ) : (
          <Loader2 className="w-3 h-3 shrink-0 animate-spin text-blue-500" aria-hidden="true" />
        )
      ) : (
        <Check className="w-3 h-3 shrink-0 text-green-500" aria-hidden="true" />
      )}
      <span
        className={`min-w-0 flex-1 truncate ${saying ? 'italic text-muted-foreground' : 'text-foreground'}`}
        aria-live="polite"
      >
        {label}
      </span>
      {steps.length > 1 && (
        <span className="tabular-nums shrink-0 opacity-70">
          {done}/{steps.length}
        </span>
      )}
      {duration !== undefined && (
        <span className="tabular-nums shrink-0">{formatDuration(duration)}</span>
      )}
    </div>
  );
}

/** `Working · 0:42`, ticking. */
export function SubagentElapsed({ since }: { since: number }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, []);
  return <span className="tabular-nums">{formatElapsed(now - since)}</span>;
}

export default SubagentTimeline;
