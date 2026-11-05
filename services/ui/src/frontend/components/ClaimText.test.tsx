import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ClaimMarked } from './ClaimText';

const unsupported = { text: 'The fee rose to 750.', supported: false, contradicted: false };

describe('ClaimMarked', () => {
  it('leaves the text alone when nothing was flagged', () => {
    const { container } = render(<ClaimMarked claims={[]}>The fee rose to 750.</ClaimMarked>);
    expect(container.textContent).toBe('The fee rose to 750.');
    expect(container.querySelector('mark')).toBeNull();
  });

  it('marks a sentence that nothing read backs up', () => {
    render(
      <ClaimMarked claims={[unsupported]}>Rates were reviewed. The fee rose to 750.</ClaimMarked>,
    );
    expect(screen.getByText('The fee rose to 750.').tagName).toBe('MARK');
  });

  it('keeps the rest of the paragraph unmarked', () => {
    const { container } = render(
      <ClaimMarked claims={[unsupported]}>Rates were reviewed. The fee rose to 750.</ClaimMarked>,
    );
    expect(container.textContent).toBe('Rates were reviewed. The fee rose to 750.');
    expect(container.querySelectorAll('mark')).toHaveLength(1);
  });

  it('says why a sentence is marked', () => {
    render(<ClaimMarked claims={[unsupported]}>The fee rose to 750.</ClaimMarked>);
    expect(screen.getByText('The fee rose to 750.')).toHaveAccessibleDescription(
      'Not backed by what was read',
    );
  });

  it('distinguishes a sentence the sources contradict', () => {
    render(
      <ClaimMarked claims={[{ ...unsupported, contradicted: true }]}>
        The fee rose to 750.
      </ClaimMarked>,
    );
    expect(screen.getByText('The fee rose to 750.')).toHaveAccessibleDescription(
      'Contradicted by what was read',
    );
  });

  it('does not mark sentences that are backed up', () => {
    const { container } = render(
      <ClaimMarked claims={[{ ...unsupported, supported: true }]}>
        The fee rose to 750.
      </ClaimMarked>,
    );
    expect(container.querySelector('mark')).toBeNull();
  });

  it('passes formatting inside the paragraph through untouched', () => {
    const { container } = render(
      <ClaimMarked claims={[unsupported]}>
        <strong>Note.</strong> The fee rose to 750.
      </ClaimMarked>,
    );
    expect(container.querySelector('strong')?.textContent).toBe('Note.');
    expect(screen.getByText('The fee rose to 750.').tagName).toBe('MARK');
  });

  it('leaves the text alone when the flagged sentence is not in it', () => {
    const { container } = render(
      <ClaimMarked claims={[{ ...unsupported, text: 'Something else entirely.' }]}>
        The fee rose to 750.
      </ClaimMarked>,
    );
    expect(container.querySelector('mark')).toBeNull();
  });
});
