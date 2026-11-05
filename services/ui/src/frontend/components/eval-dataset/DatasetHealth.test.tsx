import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { DatasetHealth } from './DatasetHealth';

describe('DatasetHealth', () => {
  it('says how many cases there are', () => {
    render(<DatasetHealth caseCount={12} />);
    expect(screen.getByText('12 cases')).toBeInTheDocument();
  });

  it('counts a single case properly', () => {
    render(<DatasetHealth caseCount={1} />);
    expect(screen.getByText('1 case')).toBeInTheDocument();
  });

  it('warns that a handful of cases cannot tell a change from noise', () => {
    render(<DatasetHealth caseCount={3} />);
    expect(
      screen.getByText('Too few cases to tell a real change from noise'),
    ).toBeInTheDocument();
  });

  it('says plainly that nothing is held back once there are enough cases', () => {
    render(<DatasetHealth caseCount={30} />);
    expect(
      screen.getByText('With nothing held back, improvements cannot be checked honestly'),
    ).toBeInTheDocument();
  });

  it('shows nothing at all for an empty dataset', () => {
    const { container } = render(<DatasetHealth caseCount={0} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('treats too few cases as the more pressing problem', () => {
    render(<DatasetHealth caseCount={3} />);
    expect(screen.queryByText(/held back/)).not.toBeInTheDocument();
  });
});
