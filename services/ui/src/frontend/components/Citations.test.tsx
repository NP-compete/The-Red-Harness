import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { Citations } from './Citations';

const CITED = [
  { document_id: 'corpus:hr/leave.md', title: 'leave', scope: 'agent' },
  { document_id: 'user:1', title: 'My notes', scope: 'user' },
];

describe('Citations', () => {
  it('shows nothing when an answer cited nothing', () => {
    // An empty strip reads as "checked and found nothing",
    // which is not what happened.
    const { container } = render(<Citations cited={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('shows nothing when there is no citation field at all', () => {
    const { container } = render(<Citations cited={undefined} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('names each document', () => {
    render(<Citations cited={CITED} />);
    expect(screen.getByText('leave')).toBeInTheDocument();
    expect(screen.getByText('My notes')).toBeInTheDocument();
  });

  it('says where each came from', () => {
    // So a curated policy and a file dropped in a chat are not
    // read with the same trust.
    render(<Citations cited={CITED} />);
    expect(screen.getByText(/from this agent/i)).toBeInTheDocument();
    expect(screen.getByText(/your documents/i)).toBeInTheDocument();
  });

  it('lets the reader open the source', () => {
    render(<Citations cited={CITED} />);
    expect(
      screen.getByRole('button', { name: /open leave/i }),
    ).toBeInTheDocument();
  });

  it('tells the reader these are what the answer used', () => {
    // Not "related documents". The claim being made matters.
    render(<Citations cited={CITED} />);
    expect(screen.getByText(/answer used/i)).toBeInTheDocument();
  });
});
