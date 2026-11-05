/**
 * The strip that answers "why did it not find that document".
 *
 * Folded away by default. A table of scores under every answer
 * is noise, and noise is what somebody stops reading before the
 * one that mattered — but the summary line has to say enough
 * that they know it is worth opening.
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { WhatWasSearched } from './WhatWasSearched';
import type { SearchedRecord } from '../lib/searched-view';

const used: SearchedRecord = {
  id: 'strong',
  title: 'Spending limits',
  scope: 'user',
  score: 1,
  used: true,
};

const missed: SearchedRecord = {
  id: 'weak',
  title: 'Old notes',
  scope: 'user',
  score: 0.33,
  used: false,
};

describe('WhatWasSearched', () => {
  it('shows nothing for an answer that searched nothing', () => {
    const { container } = render(<WhatWasSearched searched={undefined} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('shows nothing for an empty record', () => {
    const { container } = render(<WhatWasSearched searched={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('is folded away to begin with', () => {
    // A table of scores under every answer is noise.
    render(<WhatWasSearched searched={[used, missed]} />);
    expect(screen.queryByText('Old notes')).not.toBeInTheDocument();
  });

  it('says there is something to open', () => {
    render(<WhatWasSearched searched={[used, missed]} />);
    expect(screen.getByRole('group')).toHaveTextContent(/1/);
  });

  it('opens to the documents it weighed', async () => {
    render(<WhatWasSearched searched={[used, missed]} />);
    await userEvent.click(screen.getByRole('button'));
    expect(screen.getByText('Old notes')).toBeInTheDocument();
  });

  it('shows how well each matched', async () => {
    render(<WhatWasSearched searched={[used, missed]} />);
    await userEvent.click(screen.getByRole('button'));
    expect(screen.getByText('33%')).toBeInTheDocument();
  });

  it('marks the ones that were not used', async () => {
    // Without this the strip reads as a list of sources, and
    // somebody goes looking for a quote that is not there.
    render(<WhatWasSearched searched={[used, missed]} />);
    await userEvent.click(screen.getByRole('button'));
    expect(screen.getByTestId('missed-weak')).toBeInTheDocument();
  });

  it('shows the documents that were used as well', async () => {
    render(<WhatWasSearched searched={[used, missed]} />);
    await userEvent.click(screen.getByRole('button'));
    expect(screen.getByText('Spending limits')).toBeInTheDocument();
  });

  it('works when everything was used', async () => {
    render(<WhatWasSearched searched={[used]} />);
    await userEvent.click(screen.getByRole('button'));
    expect(screen.getByText('Spending limits')).toBeInTheDocument();
  });

  it('works when nothing was', async () => {
    // The turn somebody actually complains about.
    render(<WhatWasSearched searched={[missed]} />);
    await userEvent.click(screen.getByRole('button'));
    expect(screen.getByText('Old notes')).toBeInTheDocument();
  });
});

describe('it is actually on the page', () => {
  it('the chat view mounts it', async () => {
    const source = await import('./ChatMessagesView?raw');
    expect(String(source.default)).toContain('<WhatWasSearched');
  });
});
