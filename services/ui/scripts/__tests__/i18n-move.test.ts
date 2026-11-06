import { describe, expect, it } from 'vitest';

// @ts-expect-error -- plain JavaScript, no declarations
import { rewrite } from '../i18n-move.mjs';

/**
 * Where the braces go.
 *
 * Moving a string into the catalogue means replacing a literal
 * with a call, and the call needs wrapping in exactly one
 * context and must not be wrapped in any other. Between tags
 * and in a JSX attribute, `{t('k')}`; in an ordinary object
 * property, `{t('k')}` is a block and the file stops parsing.
 *
 * This is here because it went wrong: a table of tab labels
 * became `label: {t('…')}` and the page failed to compile. One
 * rule, three shapes, pinned.
 */

const moved = (source: string, strings: Record<string, string>) =>
  (rewrite(source, strings) as { source: string }).source;

describe('replacing a string with a call', () => {
  it('wraps text between tags', () => {
    expect(moved('export const A = () => <p>Save your work</p>;\n', { 'Save your work': 'x.save' })).toContain(
      "<p>{t('x.save')}</p>",
    );
  });

  it('wraps a JSX attribute', () => {
    expect(
      moved('export const A = () => <b aria-label="Close it" />;\n', { 'Close it': 'x.close' }),
    ).toContain("aria-label={t('x.close')}");
  });

  it('does not wrap an ordinary object property', () => {
    // The one that broke a page.
    const out = moved("export const TABS = [{ value: 'all', label: 'All tags' }];\n", {
      'All tags': 'x.allTags',
    });
    expect(out).toContain("label: t('x.allTags')");
    expect(out).not.toContain('label: {t(');
  });

  it('does not wrap an argument', () => {
    expect(moved("export const A = report('Eval Report');\n", { 'Eval Report': 'x.title' })).toContain(
      "report(t('x.title'))",
    );
  });
});

describe('several in one file', () => {
  it('moves them all', () => {
    const out = moved('export const A = () => <p>One<span>Two</span>Three</p>;\n', {
      One: 'x.one',
      Two: 'x.two',
      Three: 'x.three',
    });
    expect(out).toContain("{t('x.one')}");
    expect(out).toContain("{t('x.two')}");
    expect(out).toContain("{t('x.three')}");
  });

  it('splices from the end, so earlier edits do not move later ones', () => {
    // Replacing front-to-back shifts every position after the
    // first edit, and the second lands mid-token.
    const out = moved('export const A = () => <p>Short<span>A much longer sentence</span></p>;\n', {
      Short: 'x.a',
      'A much longer sentence': 'x.b',
    });
    expect(out).toBe("export const A = () => <p>{t('x.a')}<span>{t('x.b')}</span></p>;\n");
  });
});

describe('what it will not do', () => {
  it('reports a string it cannot find rather than guessing', () => {
    const done = rewrite('export const A = () => <p>Save</p>;\n', { 'Save it': 'x.save' }) as {
      absent: string[];
      moved: number;
    };
    expect(done.absent).toEqual(['Save it']);
    expect(done.moved).toBe(0);
  });

  it('leaves a near match alone', () => {
    const out = moved('export const A = () => <p>Save your work now</p>;\n', {
      'Save your work': 'x.save',
    });
    expect(out).toContain('Save your work now');
    expect(out).not.toContain("t('x.save')");
  });
});
