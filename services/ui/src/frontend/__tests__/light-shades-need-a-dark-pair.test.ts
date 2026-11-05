import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';

import { describe, expect, it } from 'vitest';

/**
 * A pale colour needs a dark background to sit on.
 *
 * The 300 and 400 shades are chosen to read against a dark
 * panel. Used without a light-mode counterpart they stay pale
 * when the theme flips, and pale on near-white is the one
 * contrast failure nobody notices while building: the developer
 * is in dark mode, the text is legible, and the component ships.
 *
 * Found by the real thing, not by reasoning: the browser
 * accessibility sweep measured `text-red-400/80` on a settings
 * panel at **2.23:1** where 4.5:1 is required. That sweep only
 * sees a component it can reach and render in an error state,
 * which is why the rule also lives here, where it reads every
 * component whether or not a test gets one on screen.
 *
 * The convention this encodes is already the majority one in
 * this codebase: `text-red-600 dark:text-red-400`.
 */

const ROOT = join(__dirname, '..');

// Shades light enough to need a dark background.
const PALE = /\btext-(red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-(300|400)\b/g;

function sources(dir = ROOT): string[] {
  const out: string[] = [];
  for (const entry of readdirSync(dir)) {
    const path = join(dir, entry);
    if (statSync(path).isDirectory()) {
      out.push(...sources(path));
    } else if (/\.tsx?$/.test(path) && !/\.test\.tsx?$/.test(path) && !path.includes('__tests__')) {
      out.push(path);
    }
  }
  return out;
}

/**
 * Pale colour classes in this source with no light-mode pair.
 *
 * A `dark:` prefix on the class itself is fine — that is the
 * class saying where it belongs. What is flagged is the bare
 * form, with no sibling naming a colour for the other theme.
 */
export function unpaired(source: string): string[] {
  const found: string[] = [];
  for (const match of source.matchAll(PALE)) {
    const at = match.index ?? 0;
    // `dark:text-red-400` is the correct form.
    if (source.slice(Math.max(0, at - 5), at).endsWith('dark:')) continue;

    // A pair may sit anywhere in the same class list, so look at
    // the surrounding string rather than the adjacent token.
    const around = source.slice(Math.max(0, at - 200), at + 200);
    if (new RegExp(`dark:text-${match[1]}-`).test(around)) continue;

    found.push(match[0]);
  }
  return found;
}

function sweep(): { file: string; classes: string[] }[] {
  return sources()
    .map((path) => ({ file: relative(ROOT, path), classes: unpaired(readFileSync(path, 'utf-8')) }))
    .filter((one) => one.classes.length > 0);
}

describe('the sweep is worth running', () => {
  it('reads the whole interface', () => {
    expect(sources().length).toBeGreaterThanOrEqual(400);
  });

  it('can see a pale class', () => {
    expect(unpaired('const a = "text-red-400";')).toEqual(['text-red-400']);
  });
});

describe('what it leaves alone', () => {
  it('a pale class that says it is for dark mode', () => {
    expect(unpaired('const a = "dark:text-red-400";')).toEqual([]);
  });

  it('a pale class paired with a darker one', () => {
    expect(unpaired('const a = "text-red-600 dark:text-red-400";')).toEqual([]);
  });

  it('the pair in either order', () => {
    expect(unpaired('const a = "dark:text-red-400 text-red-600";')).toEqual([]);
  });

  it('a shade that already reads on white', () => {
    expect(unpaired('const a = "text-red-600";')).toEqual([]);
    expect(unpaired('const a = "text-red-700";')).toEqual([]);
  });

  it('a background, not a text colour', () => {
    expect(unpaired('const a = "bg-red-400";')).toEqual([]);
  });
});

describe('every pale text colour names a light-mode partner', () => {
  it('none is left bare', () => {
    const offenders = sweep();
    const where = offenders.map((o) => `${o.file}: ${o.classes.join(', ')}`).join('\n');
    expect(
      offenders,
      `A 300 or 400 shade is chosen to read on a dark panel. Bare, it stays ` +
        `pale in light mode — which measured 2.23:1 against the 4.5:1 ` +
        `required the last time it happened. Pair each with a darker ` +
        `light-mode colour, as in \`text-red-600 dark:text-red-400\`:\n${where}`,
    ).toEqual([]);
  });
});
