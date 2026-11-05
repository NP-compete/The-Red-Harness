import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';

import { describe, expect, it } from 'vitest';

/**
 * How much of the presentation layer reaches a screen.
 *
 * 124 modules in `lib` export functions that nothing outside
 * their own test calls. That number is pinned below so it can
 * only fall, and this is what it does and does not mean —
 * because the obvious reading of it is wrong.
 *
 * **The obvious reading.** "124 screens waiting to be plugged
 * in." Not so, and the difference matters for anybody planning
 * work from this number. Five were sampled against the agent to
 * check: the refusal presenter, the source-disagreement one, the
 * spend forecast, grounding, and the search explanation. In all
 * five the agent produces nothing of the shape the presenter
 * reads. These are not screens missing a wire; they are the
 * browser half of features whose other half does not exist, so
 * wiring one is a change to both sides and to what travels
 * between them.
 *
 * One of the five is worth knowing on its own: connecting the
 * refusal presenter would make the product worse. Its main case
 * is a missing connection, and the live path does not refuse —
 * it pauses and offers a Connect button, which fixes the problem
 * rather than describing it.
 *
 * **What it actually risks**, and it is the same thing the
 * unreachable modules in the agent risk. One: somebody fixes a
 * presentation bug in the copy that never runs, and the screen
 * keeps the bug. Two: a screen grows its own formatting beside
 * a module that already does it, and now there are two answers
 * to one question — which is how `cost-attribution-view` ended
 * up holding a currency symbol, a subagent share and an empty
 * message that the chargeback screen does not show, while the
 * screen renders the plain decimal the server sent.
 *
 * **So what the number is for.** Not a backlog to drive to
 * zero: wiring one up is a product decision about what a screen
 * shows, and deleting one throws away a decision somebody made.
 * It is a bound. Whatever this layer is, it should not be
 * getting more of it, and a presenter added without a caller
 * should be a deliberate choice rather than a thing that
 * happened.
 */

// Measured, then pinned. A change here is a change in how much
// of this layer is reachable, and the log says which:
//
// - 124: the first count, taken when `cost-attribution-view`
//   turned up holding tested formatting the chargeback screen
//   does not use. Counted by tokenising every file rather than
//   by substring, because a name like `presentPage` appears
//   inside prose and inside longer identifiers.
// - 122: `config-history-view` wired, to the same screen.
// - 123: `config-drift` wired to a screen. It is the first of
//   these to become reachable, and only because the agent half
//   was built first — which is the shape every one of the
//   others needs.
// - 121: `spend-forecast-view` deleted. Not a screen waiting to
//   be wired: the month forecast is already on screen through
//   `forecast-view`, reading the same `/limits/mine` payload,
//   and this was a second answer to the same question — down to
//   formatting the same currency a second way. Checked against
//   the live screen before deleting, which is the check this
//   file's own note asks for.
const CEILING = 121;

const FRONTEND = join(process.cwd(), 'src', 'frontend');
const LIB = join(FRONTEND, 'lib');

function everyFile(from: string): string[] {
  const out: string[] = [];
  for (const entry of readdirSync(from)) {
    const path = join(from, entry);
    if (statSync(path).isDirectory()) out.push(...everyFile(path));
    else if (/\.tsx?$/.test(entry)) out.push(path);
  }
  return out;
}

/** Identifiers in a file, so a name inside a longer word does not count. */
function tokensIn(path: string): Set<string> {
  return new Set(readFileSync(path, 'utf8').match(/[A-Za-z_$][\w$]*/g) ?? []);
}

const FILES = everyFile(FRONTEND);
const TOKENS = new Map(FILES.map((path) => [path, tokensIn(path)]));

function exportedFunctions(path: string): string[] {
  const source = readFileSync(path, 'utf8');
  return [...source.matchAll(/^export (?:async )?function (\w+)/gm)].map((m) => m[1]);
}

/** Modules whose every exported function is called only by its own test. */
function unusedPresenters(): string[] {
  const out: string[] = [];
  for (const path of FILES) {
    if (!path.startsWith(LIB)) continue;
    if (/\.test\.tsx?$/.test(path) || path.endsWith('.d.ts')) continue;

    const names = exportedFunctions(path);
    if (names.length === 0) continue;

    const ownTest = path.replace(/\.ts$/, '.test.ts');
    const elsewhere = FILES.filter((one) => one !== path && one !== ownTest);

    const used = names.filter((name) =>
      elsewhere.some((one) => TOKENS.get(one)?.has(name)),
    );
    if (used.length === 0) out.push(path.slice(LIB.length + 1));
  }
  return out.sort();
}

describe('the sweep is worth running', () => {
  it('there are modules to read', () => {
    expect(FILES.filter((p) => p.startsWith(LIB)).length).toBeGreaterThan(100);
  });

  it('it can see a function that is used', () => {
    // The control. `buildAppPath` is imported all over; a sweep
    // that called it unused would be measuring nothing.
    expect(unusedPresenters()).not.toContain('app-paths.ts');
  });

  it('it does not simply report everything', () => {
    const everyLibModule = FILES.filter(
      (p) => p.startsWith(LIB) && !/\.test\.tsx?$/.test(p),
    ).length;
    expect(unusedPresenters().length).toBeLessThan(everyLibModule);
  });
});

describe('the check can fail', () => {
  it('a name inside a longer identifier is not a use', () => {
    // `presentPage` must not be found inside `presentPageHeader`,
    // which is how a substring sweep reports a dead module as
    // live and quietly stops measuring.
    const tokens = new Set(
      'const presentPageHeader = 1'.match(/[A-Za-z_$][\w$]*/g) ?? [],
    );
    expect(tokens.has('presentPage')).toBe(false);
    expect(tokens.has('presentPageHeader')).toBe(true);
  });

  it('a real call is seen', () => {
    const tokens = new Set('presentPage(rows)'.match(/[A-Za-z_$][\w$]*/g) ?? []);
    expect(tokens.has('presentPage')).toBe(true);
  });
});

describe('the count only falls', () => {
  it('has not grown', () => {
    const found = unusedPresenters();
    expect(
      found.length,
      `${found.length} presenters are called by nothing but their own test, up ` +
        `from ${CEILING}. Either one was added without a screen, or a screen ` +
        `stopped using one. Both are worth a moment: a presenter with no ` +
        `caller is a second answer to a question some screen is already ` +
        `answering its own way.\nUnused now:\n  ${found.slice(0, 20).join('\n  ')}`,
    ).toBeLessThanOrEqual(CEILING);
  });

  it('wiring one up is noticed', () => {
    // If this fails low, the ceiling is stale and should be
    // lowered — the count is only useful while it is tight.
    const found = unusedPresenters();
    expect(
      found.length,
      `Only ${found.length} are unused now, against a ceiling of ${CEILING}. ` +
        `Lower the ceiling so it keeps biting.`,
    ).toBeGreaterThanOrEqual(CEILING - 5);
  });
});
