import { render, screen } from '@testing-library/react';
import { Trans } from 'react-i18next';
import { describe, expect, it } from 'vitest';

import '../index';

/**
 * Sentences that carry markup through their middle.
 *
 * Most strings are a whole sentence and move into the catalogue
 * unchanged. A few have a `<code>` or a `<strong>` in the
 * middle, and splitting them into three fragments is how a
 * sentence ends up half translated — so those are one entry
 * with numbered placeholders, reassembled at render.
 *
 * The numbers are the risk. `components` is positional, and an
 * index with nothing to match it does not announce itself — the
 * sentence is cut off at that point and the remainder is
 * dropped. Nothing in the type system says otherwise: it
 * compiles, and what is left reads like a complete thought that
 * happens to be shorter. So these assert the whole sentence.
 *
 * So each of these renders here. One of them sits behind a
 * toggle that is off by default and was not reachable in a
 * browser, which is the reason this file exists rather than a
 * screenshot.
 */

const renders = (node: React.ReactElement) => {
  const { container } = render(node);
  return container.textContent ?? '';
};

describe('a sentence with markup in the middle', () => {
  it('the empty dataset names the button in bold', () => {
    const said = renders(
      <Trans
        i18nKey="evalUi.emptyDataset"
        components={[<span key="0" />, <span key="1" className="font-medium" />]}
      />,
    );
    expect(said).toBe('No test cases yet. Click Add Test Case to get started.');
  });

  it('the extraction line names the engine in a code span', () => {
    const said = renders(
      <Trans
        i18nKey="settings.extractionReadBy"
        values={{ engine: 'docling', limit: ', up to 10 MB each' }}
        components={[<span key="0" />, <code key="1" />]}
      />,
    );
    expect(said).toBe('Attachments are read by docling, up to 10 MB each.');
  });

  it('the arguments help explains the blank value', () => {
    // Four placeholders, the most of any of them, and the one
    // that is hardest to see in a running page.
    const said = renders(
      <Trans
        i18nKey="evalCase.argumentsHelp"
        components={[<span key="0" />, <span key="1" />, <span key="2" />, <code key="3" />]}
      />,
    );
    expect(said).toContain('leave value blank to match any value');
    expect(said).toContain('.*');
    expect(said).toContain('Omit a key entirely to skip checking it.');
  });
});

// Kept, but it is the weaker of the two checks: see below for
// what a wrong index really does.
describe('no placeholder reaches the screen', () => {
  it.each([
    ['evalUi.emptyDataset', [<span key="0" />, <span key="1" />]],
    ['settings.extractionReadBy', [<span key="0" />, <code key="1" />]],
    ['evalCase.argumentsHelp', [<span key="0" />, <span key="1" />, <span key="2" />, <code key="3" />]],
  ])('%s renders no raw tag', (key, components) => {
    const said = renders(
      <Trans i18nKey={key as string} values={{ engine: 'x', limit: '' }} components={components as React.ReactElement[]} />,
    );
    expect(said).not.toMatch(/<\/?\d>/);
  });
});

describe('what getting the numbers wrong actually does', () => {
  it('drops the rest of the sentence, silently', () => {
    // Not what was expected. A placeholder with nothing to
    // match it does not render as the literal `<1>` — the
    // sentence simply stops there, and what is left reads like
    // a complete thought that happens to be shorter.
    //
    // Which is why the tests above assert the whole sentence
    // rather than the absence of a tag: a truncation has no
    // tag in it to find.
    const said = renders(
      <Trans i18nKey="evalCase.argumentsHelp" components={[<span key="0" />]} />,
    );
    expect(said).toBe('Arguments — leave value blank to match any value (');
    expect(said).not.toContain('Omit a key entirely to skip checking it.');
  });
});

describe('the markup survives, not only the words', () => {
  it('keeps the bold on the button name', () => {
    render(
      <Trans
        i18nKey="evalUi.emptyDataset"
        components={[<span key="0" />, <span key="1" className="font-medium" />]}
      />,
    );
    // Flattening to one plain sentence would read the same and
    // lose the emphasis that points at the control.
    expect(screen.getByText('Add Test Case')).toHaveClass('font-medium');
  });
});
