/**
 * Saying that an answer repeats something from elsewhere.
 *
 * An answer built out of a ticket reads exactly like an answer
 * built out of what the agent knows. The reader can judge the
 * ticket — open it, know the team, perhaps have written it —
 * but only if they are told it is in there.
 *
 * Separate from the citations strip above it, which names
 * documents this deployment keeps. This names a third party:
 * material nobody here wrote or reviewed, which is a different
 * claim and deserves different words.
 */

import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { FromOutside } from './FromOutside';

describe('FromOutside', () => {
  it('shows nothing when the answer drew on nothing', () => {
    const { container } = render(<FromOutside sources={undefined} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('shows nothing for an empty list', () => {
    // An empty strip reads as "checked and found none",
    // which is a different claim from "did not need to look".
    const { container } = render(<FromOutside sources={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('names the source', () => {
    render(<FromOutside sources={['jira']} />);
    expect(screen.getByText(/jira/)).toBeInTheDocument();
  });

  it('names several', () => {
    render(<FromOutside sources={['jira', 'wiki']} />);
    expect(screen.getByText(/jira/)).toBeInTheDocument();
    expect(screen.getByText(/wiki/)).toBeInTheDocument();
  });

  it('says what the naming means', () => {
    // A bare server name next to an answer is decoration.
    // What makes it useful is that the words came from
    // somewhere nobody here reviewed.
    render(<FromOutside sources={['jira']} />);
    expect(screen.getByRole('note')).toHaveTextContent(/outside|elsewhere|not written/i);
  });

  it('survives a shape it does not recognise', () => {
    const { container } = render(<FromOutside sources={'jira' as never} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe('it is actually on the page', () => {
  it('the chat view mounts it', async () => {
    const source = await import('./ChatMessagesView?raw');
    expect(String(source.default)).toContain('<FromOutside');
  });
});
