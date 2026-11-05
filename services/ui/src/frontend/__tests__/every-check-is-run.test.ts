import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';

import { describe, expect, it } from 'vitest';

/**
 * A script that exits non-zero and that nothing runs.
 *
 * Four of them, in `package.json` and in no workflow:
 *
 * - `i18n:missing` finds a component asking for a key the
 *   catalogue does not define. i18next falls back to rendering
 *   the key, so the screen shows `settings.saveLabel` where a
 *   sentence should be and no test notices. The script's own
 *   docstring says it "exits non-zero when a key is missing,
 *   which makes it usable in CI" — and nothing used it.
 * - `i18n:report` sweeps every component for a user-facing
 *   string typed into source instead of the catalogue. It had no
 *   npm script at all and always exited 0 — a report, not a
 *   gate. It now exits non-zero on a finding, which is safe to
 *   start today because the count is zero across 488 files.
 * - `contract:check` compares the generated client contract
 *   against the agent's OpenAPI baseline.
 *
 * All three passed when they were wired in, which is the whole
 * point: a check earns its place before it is needed, not after
 * somebody spends an afternoon on the bug it would have caught.
 *
 * This test exists because wiring is the part that rots. The job
 * can be deleted in a one-line diff that reads like tidying, and
 * nothing else in the repository would notice.
 */

const ROOT = join(__dirname, '..', '..', '..');

// Found, not counted: `join(ROOT, '..')` was the repository root
// while the interface lived at `ui/`. It moved to `services/ui/`
// and this started looking for `services/.github`.
function repoRoot(from: string): string {
  let dir = from;
  while (dir !== dirname(dir)) {
    if (existsSync(join(dir, '.github'))) return dir;
    dir = dirname(dir);
  }
  throw new Error(`no .github above ${from}`);
}

const WORKFLOW = readFileSync(
  join(repoRoot(__dirname), '.github', 'workflows', 'ui.yml'),
  'utf8',
);
const PACKAGE = JSON.parse(readFileSync(join(ROOT, 'package.json'), 'utf8'));

/** Scripts whose whole purpose is to fail a build. */
const MUST_RUN_IN_CI = [
  'i18n:missing',
  'i18n:report',
  'contract:check',
];

describe('every check that can fail a build is run by one', () => {
  it('the workflow was actually read', () => {
    // A path typo would make every assertion below pass against
    // an empty string.
    expect(WORKFLOW).toContain('jobs:');
    expect(WORKFLOW.length).toBeGreaterThan(500);
  });

  it.each(MUST_RUN_IN_CI)('%s is a script that exists', (name) => {
    expect(PACKAGE.scripts[name]).toBeTruthy();
  });

  it.each(MUST_RUN_IN_CI)('%s is run by the workflow', (name) => {
    expect(WORKFLOW).toContain(`npm run ${name}`);
  });

  it('the other jobs are still there', () => {
    // So a rewrite that drops lint or the unit tests to make
    // room for this job fails here too.
    for (const name of ['npm run lint', 'npm run test:coverage', 'npm run build']) {
      expect(WORKFLOW).toContain(name);
    }
  });
});
