import { describe, expect, it } from 'vitest';

// @ts-expect-error -- plain JavaScript, no declarations
import { placements, withHook } from '../i18n-hook.mjs';

/**
 * Which function gets the hook.
 *
 * Getting this wrong does not fail to compile — it compiles and
 * misbehaves. A hook inside a `map` callback runs a different
 * number of times depending on how many rows there are, which
 * is the one thing hooks may not do. A hook added to a class
 * never runs at all.
 */

const added = (source: string) => (withHook(source) as { source: string }).source;

describe('where the hook goes', () => {
  it('into a component that calls the translator', () => {
    const out = added("export function A() {\n  return <p>{t('x.a')}</p>;\n}\n");
    expect(out).toContain('const { t } = useTranslation();');
    expect(out).toContain("import { useTranslation } from 'react-i18next';");
  });

  it('once, into the component, not into the callback inside it', () => {
    // The bug this exists to avoid: a hook whose call count
    // depends on how many rows there are.
    const out = added(
      "export function A({ rows }) {\n  return rows.map((r) => <p key={r}>{t('x.a')}</p>);\n}\n",
    );
    expect(out.match(/useTranslation\(\)/g)).toHaveLength(1);
    const hook = out.indexOf('const { t } = useTranslation();');
    expect(hook).toBeLessThan(out.indexOf('rows.map'));
  });

  it('not twice when one is already there', () => {
    const before = "export function A() {\n  const { t } = useTranslation();\n  return <p>{t('x.a')}</p>;\n}\n";
    expect(withHook(before)).toMatchObject({ added: 0 });
  });

  it('nowhere, when nothing calls the translator', () => {
    expect(withHook('export function A() {\n  return <p>Hi</p>;\n}\n')).toMatchObject({ added: 0 });
  });

  it('not into a class — it would never run', () => {
    const source =
      "export class A extends Component {\n  render() {\n    return <p>{t('x.a')}</p>;\n  }\n}\n";
    const done = withHook(source) as { source: string; added: number; classes: string[] };
    expect(done.added).toBe(0);
    expect(done.source).toBe(source);
    // Reported rather than passed over: a class calling `t` is
    // still broken, and somebody has to know.
    expect(done.classes).toEqual(['A']);
  });
});

describe('where the import goes', () => {
  it('after a multi-line import, not inside it', () => {
    // The line-based version looked for the last line starting
    // with `import` and found the *opening* line of a block,
    // splicing the new import between the brace and its names.
    const out = added(
      "import { a } from 'x';\n" +
        'import {\n  b,\n  c,\n} from \'y\';\n' +
        "export function A() {\n  return <p>{t('x.a')}</p>;\n}\n",
    );
    expect(out).not.toMatch(/import \{\s*\nimport /);
    expect(out.indexOf("from 'y'")).toBeLessThan(out.indexOf('react-i18next'));
  });
});

describe('it does not add an import twice', () => {
  it('leaves an existing one alone', () => {
    const out = added(
      "import { useTranslation } from 'react-i18next';\nexport function A() {\n  return <p>{t('x.a')}</p>;\n}\n",
    );
    expect(out.match(/react-i18next/g)).toHaveLength(1);
  });
});

describe('what it reports', () => {
  it('names every class it could not help', () => {
    const { classes } = placements(
      "export class A extends Component { render() { return t('x'); } }\n" +
        "export class B extends Component { render() { return t('y'); } }\n",
    ) as { classes: string[] };
    expect(classes).toEqual(['A', 'B']);
  });
});
