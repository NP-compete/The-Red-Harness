import { describe, expect, it } from 'vitest';
import {
  applyProgress,
  finishSteps,
  formatDuration,
  formatElapsed,
  WRITING,
} from './subagent-steps';

/** Tool calls as the stream sends them: cumulative, id per call. */
const calls = (...names: string[]) => names.map((n) => ({ id: `id-${n}`, name: n }));
const ev = (o: Record<string, unknown>) => ({ ns: 'agent:x', ...o });

describe('applyProgress', () => {
  it('opens a step for the first tool call', () => {
    const p = applyProgress(undefined, ev({ calls: calls('gitlab_whoami') }), 1000);
    expect(p.steps).toEqual([
      { tool: 'gitlab_whoami', id: 'id-gitlab_whoami', startedAt: 1000 },
    ]);
  });

  it('does not repeat a call it has already seen', () => {
    // The chunks are cumulative, so the same call arrives on every
    // one. Keying on the label gave "a", then "a, b", then
    // "a, b, c" as three separate steps — the duplication.
    let p = applyProgress(undefined, ev({ calls: calls('a') }), 1000);
    p = applyProgress(p, ev({ calls: calls('a') }), 1500);
    p = applyProgress(p, ev({ calls: calls('a') }), 1800);
    expect(p.steps).toHaveLength(1);
  });

  it('adds only the calls it has not seen', () => {
    let p = applyProgress(undefined, ev({ calls: calls('a') }), 1000);
    p = applyProgress(p, ev({ calls: calls('a', 'b') }), 1500);
    p = applyProgress(p, ev({ calls: calls('a', 'b', 'c') }), 2000);
    expect(p.steps.map((s) => s.tool)).toEqual(['a', 'b', 'c']);
  });

  it('closes a running step when a new call appears', () => {
    // No completion event exists on the stream, so the next call is
    // the only signal the last one returned.
    let p = applyProgress(undefined, ev({ calls: calls('a') }), 1000);
    p = applyProgress(p, ev({ calls: calls('a', 'b') }), 2200);
    expect(p.steps[0].endedAt).toBe(2200);
    expect(p.steps[1].endedAt).toBeUndefined();
  });

  it('opens one step per call when several arrive together', () => {
    const p = applyProgress(undefined, ev({ calls: calls('a', 'b') }), 1000);
    expect(p.steps).toHaveLength(2);
  });

  it('adds a writing step when prose starts', () => {
    let p = applyProgress(undefined, ev({ calls: calls('a') }), 1000);
    p = applyProgress(p, ev({ latest: 'Found 15 open' }), 3000);
    expect(p.steps[0].endedAt).toBe(3000);
    expect(p.steps[1].tool).toBe(WRITING);
  });

  it('extends the writing step rather than repeating it', () => {
    let p = applyProgress(undefined, ev({ latest: 'Found' }), 1000);
    p = applyProgress(p, ev({ latest: 'Found 15 open merge requests' }), 1500);
    expect(p.steps.filter((s) => s.tool === WRITING)).toHaveLength(1);
  });

  it('keeps the newest cumulative text', () => {
    let p = applyProgress(undefined, ev({ latest: 'Found' }), 1000);
    p = applyProgress(p, ev({ latest: 'Found 15' }), 1500);
    expect(p.latest).toBe('Found 15');
  });

  it('remembers the agent once seen', () => {
    let p = applyProgress(undefined, ev({ agent: 'investigator' }), 1000);
    p = applyProgress(p, ev({ calls: calls('a') }), 1100);
    expect(p.agent).toBe('investigator');
  });

  it('records when the delegation started', () => {
    expect(applyProgress(undefined, ev({ calls: calls('a') }), 7000).startedAt).toBe(7000);
  });

  it('returns a new object so React re-renders', () => {
    const first = applyProgress(undefined, ev({ calls: calls('a') }), 1000);
    expect(applyProgress(first, ev({ calls: calls('a', 'b') }), 2000)).not.toBe(first);
  });
});

describe('finishSteps', () => {
  it('closes a step still running', () => {
    const p = applyProgress(undefined, ev({ calls: calls('a') }), 1000);
    expect(finishSteps(p, 4000)[0].endedAt).toBe(4000);
  });

  it('leaves an already-closed step at its own time', () => {
    let p = applyProgress(undefined, ev({ calls: calls('a') }), 1000);
    p = applyProgress(p, ev({ calls: calls('a', 'b') }), 2000);
    expect(finishSteps(p, 9000)[0].endedAt).toBe(2000);
  });
});

describe('formatting', () => {
  it('shows sub-minute durations to a tenth', () => {
    expect(formatDuration(1234)).toBe('1.2s');
  });

  it('switches to minutes past sixty seconds', () => {
    expect(formatDuration(64_000)).toBe('1m 04s');
  });

  it('never shows a negative duration', () => {
    // Clock skew between events should not render as "-0.3s".
    expect(formatDuration(-300)).toBe('0.0s');
  });

  it('shows elapsed time as a clock', () => {
    expect(formatElapsed(42_000)).toBe('0:42');
    expect(formatElapsed(125_000)).toBe('2:05');
  });
});

describe('tool inputs and outputs', () => {
  it('keeps the arguments a call was made with', () => {
    const p = applyProgress(undefined, {
      ns: 'agent:investigator',
      calls: [{ id: 'c1', name: 'datadog_search', args: '{\n  "query": "service:api"\n}' }],
    }, 1000);
    expect(p.steps[0].args).toContain('service:api');
  });

  it('lands a result on the call that asked for it, not the newest', () => {
    // Two calls in flight. The old signal — "a new call means the
    // last one returned" — cannot tell which of them finished.
    let p = applyProgress(undefined, {
      ns: 'agent:investigator',
      calls: [{ id: 'a', name: 'first' }, { id: 'b', name: 'second' }],
    }, 1000);
    p = applyProgress(p, { ns: 'agent:investigator', results: [{ id: 'a', content: 'rows: 3' }] }, 2000);

    expect(p.steps.find((s) => s.id === 'a')?.result).toBe('rows: 3');
    expect(p.steps.find((s) => s.id === 'b')?.result).toBeUndefined();
  });

  it('a result closes its own step and leaves the others running', () => {
    let p = applyProgress(undefined, {
      ns: 'agent:investigator',
      calls: [{ id: 'a', name: 'first' }, { id: 'b', name: 'second' }],
    }, 1000);
    p = applyProgress(p, { ns: 'agent:investigator', results: [{ id: 'a', content: 'done' }] }, 2500);

    expect(p.steps.find((s) => s.id === 'a')?.endedAt).toBe(2500);
    expect(p.steps.find((s) => s.id === 'b')?.endedAt).toBeUndefined();
  });

  it('ignores a result for a call it never saw', () => {
    const p = applyProgress(undefined, {
      ns: 'agent:investigator',
      results: [{ id: 'ghost', content: 'x' }],
    }, 1000);
    expect(p.steps).toHaveLength(0);
  });
});

describe('what the subagent said, interleaved with what it did', () => {
  const ns = 'agent:investigator';

  it('keeps the prose rather than a step called "writing"', () => {
    const p = applyProgress(undefined, { ns, latest: 'Checking Datadog for errors first.' }, 1000);
    expect(p.steps[0].tool).toBe(WRITING);
    expect(p.steps[0].text).toBe('Checking Datadog for errors first.');
  });

  it('extends the open say-step while the sentence streams', () => {
    let p = applyProgress(undefined, { ns, latest: 'Checking' }, 1000);
    p = applyProgress(p, { ns, latest: 'Checking Datadog' }, 1100);
    expect(p.steps).toHaveLength(1);
    expect(p.steps[0].text).toBe('Checking Datadog');
  });

  it('reads said, did, said — a new sentence after a call is a new step', () => {
    let p = applyProgress(undefined, { ns, latest: 'Checking Datadog first.' }, 1000);
    p = applyProgress(p, { ns, calls: [{ id: 'a', name: 'datadog_search' }] }, 2000);
    p = applyProgress(p, { ns, results: [{ id: 'a', content: '148 errors' }] }, 3000);
    p = applyProgress(p, { ns, latest: 'Now correlating with recent merges.' }, 3500);

    expect(p.steps.map((s) => s.tool)).toEqual([WRITING, 'datadog_search', WRITING]);
    expect(p.steps[0].text).toBe('Checking Datadog first.');
    expect(p.steps[2].text).toBe('Now correlating with recent merges.');
  });

  it('closes the sentence when a call starts', () => {
    let p = applyProgress(undefined, { ns, latest: 'About to search.' }, 1000);
    p = applyProgress(p, { ns, calls: [{ id: 'a', name: 'search' }] }, 2000);
    expect(p.steps[0].endedAt).toBe(2000);
  });
});

describe('stale narration after a tool returns', () => {
  const ns = 'agent:investigator';

  it('does not re-open the sentence it said before the call', () => {
    // `latest` is only replaced when the next message starts, so it
    // still holds the pre-call line for a moment after the result.
    let p = applyProgress(undefined, { ns, latest: 'Reading the skill file.' }, 1000);
    p = applyProgress(p, { ns, calls: [{ id: 'a', name: 'read_file' }] }, 2000);
    p = applyProgress(p, { ns, results: [{ id: 'a', content: 'ok' }] }, 3000);
    p = applyProgress(p, { ns, latest: 'Reading the skill file.' }, 3100);

    expect(p.steps.map((s) => s.tool)).toEqual([WRITING, 'read_file']);
  });

  it('still opens one when the subagent genuinely says something new', () => {
    let p = applyProgress(undefined, { ns, latest: 'Reading the skill file.' }, 1000);
    p = applyProgress(p, { ns, calls: [{ id: 'a', name: 'read_file' }] }, 2000);
    p = applyProgress(p, { ns, latest: 'It describes a read-only workflow.' }, 3100);

    expect(p.steps.map((s) => s.tool)).toEqual([WRITING, 'read_file', WRITING]);
    expect(p.steps[2].text).toBe('It describes a read-only workflow.');
  });
});
