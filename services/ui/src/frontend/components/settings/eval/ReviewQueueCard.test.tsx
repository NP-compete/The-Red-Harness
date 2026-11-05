import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ReviewQueueCard } from './ReviewQueueCard';

describe('ReviewQueueCard', () => {
  it('says nothing when no run has been read', () => {
    const { container } = render(<ReviewQueueCard />);
    expect(container).toBeEmptyDOMElement();
  });

  it('says nothing when every graded turn stands on its own', () => {
    const { container } = render(<ReviewQueueCard review={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('says how many turns need a person', () => {
    render(
      <ReviewQueueCard
        review={[
          { item: 'q1', reason: 'disagreement' },
          { item: 'q2', reason: 'failed' },
        ]}
      />,
    );
    expect(screen.getByText('2 items need review')).toBeInTheDocument();
  });

  it('counts one turn in the singular', () => {
    render(<ReviewQueueCard review={[{ item: 'q1', reason: 'failed' }]} />);
    expect(screen.getByText('1 item needs review')).toBeInTheDocument();
  });

  it('names the turn', () => {
    render(<ReviewQueueCard review={[{ item: 'q1', reason: 'failed' }]} />);
    expect(screen.getByText('q1')).toBeInTheDocument();
  });

  it('says in plain words why the graders need help', () => {
    render(<ReviewQueueCard review={[{ item: 'q1', reason: 'disagreement' }]} />);
    expect(screen.getByText('The graders disagreed')).toBeInTheDocument();
  });

  it('explains a grade that was too close to call', () => {
    render(<ReviewQueueCard review={[{ item: 'q1', reason: 'low_confidence' }]} />);
    expect(screen.getByText('The grade was not a confident one')).toBeInTheDocument();
  });

  it('keeps the order the agent ranked them in', () => {
    render(
      <ReviewQueueCard
        review={[
          { item: 'q2', reason: 'disagreement' },
          { item: 'q1', reason: 'failed' },
        ]}
      />,
    );
    const rows = screen.getAllByRole('listitem').map((li) => li.textContent);
    expect(rows[0]).toContain('q2');
  });
});
