import { describe, expect, it } from 'vitest';

// @ts-expect-error -- plain JavaScript, no declarations
import { componentFiles, sweep, untranslatedIn } from '../i18n-report.mjs';

/**
 * The catalogue stays the whole of the product's wording.
 *
 * Strings live in one file so they can be found, reviewed and
 * changed in one place. That only holds while new ones keep
 * going there, and the way it stops holding is undramatic:
 * somebody types a label into a component, nothing breaks, and
 * one day the catalogue is a partial record.
 *
 * The count may fall and may not rise. A number nobody can see
 * going the wrong way is a number that goes the wrong way.
 *
 * Measurement log — a change here is a change in what is
 * counted, not a regression:
 *
 * - 134: the first sweep that parsed the source instead of
 *   matching it, and the first to read configuration objects as
 *   well as markup.
 * - 116: the stream renderer and the notices around the
 *   composer moved into the catalogue.
 * - 74: the evaluation surface — panel, dashboard, run tables,
 *   dataset page.
 * - 28: the settings panels, the error boundaries, the dataset
 *   forms. Two of the drop are a change in what is counted: an
 *   entity that is only a gap stopped being a finding.
 * - 1: everything else, the last few as `<Trans>` where a
 *   sentence carries markup through its middle.
 *
 * The one that is left is deliberate and should stay. The
 * fallback copy in `useContent` mirrors what the server sends,
 * so that the greeting renders before the configuration call
 * resolves and still renders if it fails. Putting it in the
 * catalogue would let the two disagree, and the version
 * somebody sees would depend on how fast the network was.
 */
const CEILING = 1;

describe('the sweep is worth running', () => {
  it('reaches the whole interface', () => {
    // A sweep that reaches nothing passes for ever.
    expect(componentFiles().length).toBeGreaterThanOrEqual(400);
  });

  it('is not matching everything in sight', () => {
    // The other failure: a rule so loose that every file is a
    // finding, which nobody can act on and everybody turns off.
    expect(sweep().length).toBeLessThan(componentFiles().length);
  });
});

describe('what it counts as a string somebody reads', () => {
  it('catches text written between tags', () => {
    const found = untranslatedIn('export const A = () => <p>Save your work</p>;');
    expect(found.map((f: { text: string }) => f.text)).toEqual(['Save your work']);
  });

  it('catches a label a screen reader announces', () => {
    const found = untranslatedIn('export const A = () => <button aria-label="Close dialog" />;');
    expect(found.map((f: { text: string }) => f.text)).toEqual(['Close dialog']);
  });

  it('catches a placeholder', () => {
    const found = untranslatedIn('export const A = () => <input placeholder="Search chats" />;');
    expect(found).toHaveLength(1);
  });

  it('catches one written into a configuration object', () => {
    // The kind a sweep over markup never sees. A table of
    // columns or a list of tabs renders exactly like markup and
    // looks nothing like it.
    const found = untranslatedIn("export const TABS = [{ id: 'a', label: 'Shared with me' }];", 'x.ts');
    expect(found.map((f: { text: string }) => f.text)).toEqual(['Shared with me']);
  });

  it('catches an empty-state message in a configuration object', () => {
    const found = untranslatedIn(
      "export const V = { emptyMessage: 'Nothing here yet' };",
      'x.ts',
    );
    expect(found).toHaveLength(1);
  });
});

describe('what it leaves alone', () => {
  it('an entity that is only a gap', () => {
    // `&nbsp;&nbsp;` between two figures is layout somebody
    // could not get from CSS, not wording.
    expect(untranslatedIn('export const A = () => <p>&nbsp;&nbsp;</p>;')).toEqual([]);
  });

  it('a string already going through the catalogue', () => {
    expect(untranslatedIn("export const A = () => <p>{t('a.b')}</p>;")).toEqual([]);
  });

  it('the parts interpolated into one', () => {
    // These are the sentence's own values, not a second
    // sentence somebody forgot.
    expect(
      untranslatedIn("export const A = () => <p>{t('a.b', { name: 'Shared with me' })}</p>;"),
    ).toEqual([]);
  });

  it('class names', () => {
    expect(untranslatedIn('export const A = () => <p className="flex items-center gap-2" />;')).toEqual(
      [],
    );
  });

  it('a test identifier', () => {
    expect(untranslatedIn('export const A = () => <p data-testid="credential-missing" />;')).toEqual(
      [],
    );
  });

  it('a route, a URL and an identifier', () => {
    expect(untranslatedIn("export const P = { label: '/settings/components' };", 'x.ts')).toEqual([]);
    expect(untranslatedIn("export const P = { label: 'https://example.test/x' };", 'x.ts')).toEqual(
      [],
    );
    expect(untranslatedIn("export const P = { label: 'credential_missing' };", 'x.ts')).toEqual([]);
  });

  it('a property that is an identifier rather than a label', () => {
    // `name` and `value` are far more often a key than
    // something on screen, and a sweep with a false positive in
    // it is one people learn to ignore.
    expect(untranslatedIn("export const P = { name: 'Shared with me' };", 'x.ts')).toEqual([]);
  });

  it('a test file, where English is the point', () => {
    const everything = componentFiles() as string[];
    expect(everything.filter((f) => f.includes('.test.'))).toEqual([]);
  });
});

describe('the count', () => {
  it('has not risen', () => {
    const findings = sweep();
    const where = findings
      .slice(0, 12)
      .map((f: { file: string; line: number; text: string }) => `${f.file}:${f.line} ${f.text}`)
      .join('\n');
    expect(
      findings.length,
      `${findings.length} strings are written into components rather than the ` +
        `catalogue, up from ${CEILING}. The new ones are among:\n${where}`,
    ).toBeLessThanOrEqual(CEILING);
  });
});

describe('a property name is read by its last segment', () => {
  it('catches the snake_case forms in the same object', () => {
    /**
     * The exact-match version read `subtitle` and missed
     * `input_placeholder`, `welcome_heading` and
     * `quick_prompts_heading` beside it — so the report said one
     * untranslated string where there were six, and the number
     * looked like progress.
     */
    const found = untranslatedIn(
      `const FALLBACK = {
         subtitle: 'Ready to help with anything',
         input_placeholder: 'Ask anything...',
         welcome_heading: 'Welcome!',
       };`,
      'x.ts',
    );
    expect(found.map((one) => one.where).sort()).toEqual([
      'input_placeholder',
      'subtitle',
      'welcome_heading',
    ]);
  });

  it('still ignores a name nobody reads the value of', () => {
    expect(
      untranslatedIn(`const x = { api_endpoint: 'the main one' };`, 'x.ts'),
    ).toHaveLength(0);
  });
});

describe('a string that is deliberately in English', () => {
  it('is skipped when the code says why', () => {
    const found = untranslatedIn(
      `// i18n-exempt: mirrors the server's own defaults
       const FALLBACK = { heading: 'Welcome!' };`,
      'x.ts',
    );
    expect(found).toHaveLength(0);
  });

  it('is skipped for everything the marker covers, not just the first', () => {
    const found = untranslatedIn(
      `// i18n-exempt: mirrors the server
       const FALLBACK = { heading: 'Welcome!', subtitle: 'Ready to help' };`,
      'x.ts',
    );
    expect(found).toHaveLength(0);
  });

  it('does not excuse the file around it', () => {
    /** The marker is attached to a declaration, not sprayed over
     * everything after it. */
    const found = untranslatedIn(
      `// i18n-exempt: mirrors the server
       const FALLBACK = { heading: 'Welcome!' };
       const OTHER = { heading: 'Not exempt at all' };`,
      'x.ts',
    );
    expect(found.map((one) => one.text)).toEqual(['Not exempt at all']);
  });
});
