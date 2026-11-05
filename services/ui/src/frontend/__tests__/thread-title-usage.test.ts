import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

/**
 * A chat's title and preview are the sidebar, the rename box and
 * what a screen reader announces. They were being cut by hand in
 * several places, each with its own length, none of them stopping a
 * question carrying an email address from becoming a label — so this
 * fails the build when another appears.
 */
const ROOT = join(__dirname, '..');
// Where chat records are assembled. `lib/` is left out on purpose: a
// presenter shortening the text it was handed is doing its job, and
// `preview` there means a tool result, not a chat.
const ASSEMBLED_IN = ['components', 'pages', 'services', 'hooks', 'redux'];
const CUTTING_BY_HAND = /(title|preview):[^\n]*\b(substring|slice)\s*\(/;

function sourceFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((entry) => {
    const path = join(dir, entry);
    if (statSync(path).isDirectory()) {
      return entry === 'node_modules' ? [] : sourceFiles(path);
    }
    if (!/\.tsx?$/.test(entry) || /\.test\./.test(entry)) return [];
    return [path];
  });
}

describe('deriving a chat title', () => {
  it('goes through the one helper that knows what not to publish', () => {
    const offenders = ASSEMBLED_IN.flatMap((dir) => sourceFiles(join(ROOT, dir))).filter(
      (path) => CUTTING_BY_HAND.test(readFileSync(path, 'utf8')),
    );
    expect(offenders.map((path) => path.slice(ROOT.length + 1))).toEqual([]);
  });
});
