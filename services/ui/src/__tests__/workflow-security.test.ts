import * as fs from 'node:fs';
import * as path from 'node:path';
import { describe, expect, it } from 'vitest';
import { parse } from 'yaml';

/**
 * E26-T6 and T7, asserted rather than reviewed.
 *
 * The threat is specific: a pull request from a fork edits a
 * workflow or a test and walks out with a token. Review catches that
 * on the days somebody looks carefully; a test catches it on the
 * others. `tests/unit/test_workflow_security.py` applies the same
 * three rules from the Python side; since the merge both see every
 * workflow, so either would catch a new one.
 *
 * **Every workflow declares `permissions:`.** An omitted block means
 * whatever the repository default happens to be, which somebody can
 * widen later without touching a workflow file.
 *
 * **No `pull_request_target`.** It runs with the base repository's
 * secrets against the fork's code.
 *
 * **No secret reachable from a fork.** `pull_request` fires on
 * forks, so a step with that trigger must not read `secrets.*`
 * beyond the automatic `GITHUB_TOKEN` — unless it carries the fork
 * guard, in which case it does not run for a fork at all.
 */


// Found, not counted. These hops were right when the interface
// lived at `ui/`; it moved to `services/ui/` and every one of them
// became short by a directory, which nothing noticed because this
// suite ran in a workflow of its own and in no local command.
function repoRoot(from: string): string {
  let dir = from;
  while (dir !== path.dirname(dir)) {
    if (fs.existsSync(path.join(dir, '.github'))) return dir;
    dir = path.dirname(dir);
  }
  throw new Error(`no .github above ${from}`);
}

const DIR = path.join(repoRoot(__dirname), '.github', 'workflows');
const FORK_GUARD = 'github.event.pull_request.head.repo.fork != true';
const ALLOWED = new Set(['GITHUB_TOKEN']);

const files = fs
  .readdirSync(DIR)
  .filter((name) => name.endsWith('.yml') || name.endsWith('.yaml'));

interface Workflow {
  on?: unknown;
  true?: unknown;
  permissions?: unknown;
  jobs?: Record<string, { if?: unknown; permissions?: unknown; steps?: unknown[] }>;
}

function load(name: string): Workflow {
  return parse(fs.readFileSync(path.join(DIR, name), 'utf8')) as Workflow;
}

function triggers(doc: Workflow): string[] {
  const on = doc.on ?? doc.true;
  if (typeof on === 'string') return [on];
  if (Array.isArray(on)) return on as string[];
  if (on && typeof on === 'object') return Object.keys(on);
  return [];
}

function secretsIn(value: unknown): string[] {
  const text = JSON.stringify(value ?? '');
  const found = text.match(/secrets\.([A-Za-z_][A-Za-z0-9_]*)/g) ?? [];
  return [...new Set(found.map((s) => s.slice('secrets.'.length)))].filter(
    (name) => !ALLOWED.has(name),
  );
}

describe('workflow security', () => {
  it('finds workflows to check', () => {
    // A path typo would make every test below vacuously pass.
    expect(files.length).toBeGreaterThan(0);
  });

  it.each(files)('%s declares permissions', (name) => {
    const doc = load(name);
    const jobs = Object.values(doc.jobs ?? {});
    const declared =
      doc.permissions !== undefined || jobs.every((j) => j.permissions !== undefined);
    expect(declared, `${name} inherits the repository default`).toBe(true);
  });

  it.each(files)('%s does not use pull_request_target', (name) => {
    expect(triggers(load(name))).not.toContain('pull_request_target');
  });

  it.each(files)('%s exposes no secret to a fork', (name) => {
    const doc = load(name);
    if (!triggers(doc).includes('pull_request')) return;

    const exposed: Record<string, string[]> = {};
    for (const [jobName, job] of Object.entries(doc.jobs ?? {})) {
      const jobGuarded = String(job.if ?? '').includes(FORK_GUARD);
      for (const step of (job.steps ?? []) as { if?: unknown; name?: string }[]) {
        if (jobGuarded || String(step.if ?? '').includes(FORK_GUARD)) continue;
        const found = secretsIn(step);
        if (found.length) exposed[`${jobName}.${step.name ?? '?'}`] = found;
      }
    }
    expect(exposed, `${name} leaks a secret to forks`).toEqual({});
  });
});
