import { readFileSync, readdirSync, statSync } from 'node:fs';
import { basename, join } from 'node:path';

import { describe, expect, it } from 'vitest';

/**
 * How many components nothing renders.
 *
 * A component nothing renders is not a feature. It has tests,
 * it passes them, and nobody can reach it — so the capability
 * is present in the codebase and absent from the product,
 * which reads as supported to anyone browsing the source.
 *
 * Five were found this way and were real gaps, now mounted:
 * the compaction marker (the transcript drew its own divider
 * and threw the summary away, so there was nothing to expand),
 * the stopping notice (pressing stop looked like finishing),
 * read-aloud, the thread usage line, and the share control —
 * the last of which meant nothing in the product could create
 * a share, while settings listed shares that could never
 * exist.
 *
 * The rest are parallel implementations: subagent progress
 * renders inline in the transcript, the eval dashboard is the
 * live surface and `EvalPanel` the spare, the theme is chosen
 * in appearance settings. For those the risk is not an absent
 * feature but two answers to one question — somebody fixes the
 * copy that never renders, or mounts it beside the one that
 * does.
 *
 * So this is a bound rather than a backlog. Mounting one of
 * these is usually wrong and deleting one needs a check that
 * the live path really covers it; what matters is that the
 * number stops growing by accident.
 */

// Measured, then pinned. A change here is a change in what is
// reachable, and the log says which:
//
// - 12: the first count, after five genuine gaps were found
//   and mounted.
const CEILING = 12;

const ROOT = join(__dirname, '..');
const COMPONENTS = join(ROOT, 'components');

function sources(dir: string): string[] {
  const out: string[] = [];
  for (const entry of readdirSync(dir)) {
    const path = join(dir, entry);
    if (statSync(path).isDirectory()) {
      if (entry !== '__tests__') out.push(...sources(path));
    } else if (/\.tsx$/.test(path) && !/\.test\.tsx$/.test(path)) {
      out.push(path);
    }
  }
  return out;
}

/** Every source file, keyed by path, so a file can be excluded. */
function everyFile(): Map<string, string> {
  const found = new Map<string, string>();
  const walk = (dir: string) => {
    for (const entry of readdirSync(dir)) {
      const path = join(dir, entry);
      if (statSync(path).isDirectory()) {
        if (entry !== '__tests__') walk(path);
      } else if (/\.tsx?$/.test(path) && !/\.test\.tsx?$/.test(path)) {
        found.set(path, readFileSync(path, 'utf-8'));
      }
    }
  };
  walk(ROOT);
  return found;
}

export function unmounted(): string[] {
  const files = everyFile();
  return sources(COMPONENTS)
    .filter((path) => {
      const name = basename(path, '.tsx');
      const word = new RegExp(`\\b${name}\\b`);
      // Everything but its own file: a component's own source
      // always names it, and the question is whether anything
      // else does. Paths are not searched — a file called
      // `Foo.tsx` would otherwise count as a mention of `Foo`.
      for (const [other, text] of files) {
        if (other !== path && word.test(text)) return false;
      }
      return true;
    })
    .map((path) => basename(path, '.tsx'));
}

describe('the sweep is worth running', () => {
  it('reads the components', () => {
    expect(sources(COMPONENTS).length).toBeGreaterThanOrEqual(80);
  });

  it('does not report something that is plainly rendered', () => {
    // The control. These are mounted, and a sweep calling them
    // unmounted would be measuring nothing.
    for (const mounted of ['InputForm', 'ChatMessagesView', 'ReasoningSelector']) {
      expect(unmounted()).not.toContain(mounted);
    }
  });
});

describe('the count only falls', () => {
  it('has not grown', () => {
    const found = unmounted();
    expect(found.length, {
      message:
        `${found.length} components are rendered by nothing, up from ${CEILING}. ` +
        `Either one was added without being mounted, or something that used to ` +
        `render one stopped — and a component nobody can reach is a feature ` +
        `that exists in the source and not in the product.\n  ${found.join('\n  ')}`,
    } as never).toBeLessThanOrEqual(CEILING);
  });

  it('is tight enough to keep biting', () => {
    expect(unmounted().length).toBeGreaterThanOrEqual(CEILING - 3);
  });
});
