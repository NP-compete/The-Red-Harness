import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { TodoProgress } from './TodoProgress';

const elapsed = vi.hoisted(() => ({ seconds: 0 }));
vi.mock('../hooks/useQuietFor', () => ({ useQuietFor: () => elapsed.seconds }));

const todos = [
  { content: 'Read the handbook', status: 'completed' as const },
  { content: 'Check the limit', status: 'in_progress' as const },
  { content: 'Write it up', status: 'pending' as const },
];

describe('TodoProgress', () => {
  it('says what is being done now', () => {
    render(<TodoProgress todos={todos} isLoading />);
    expect(screen.getByText(/Check the limit/)).toBeInTheDocument();
  });

  it('says where in the list that is', () => {
    render(<TodoProgress todos={todos} isLoading />);
    expect(screen.getByText(/3 steps so far/)).toBeInTheDocument();
  });

  it('says how long it has been going', () => {
    elapsed.seconds = 90;
    render(<TodoProgress todos={todos} isLoading />);
    expect(screen.getByText(/2 minutes/)).toBeInTheDocument();
  });

  it('counts a short run in seconds', () => {
    elapsed.seconds = 5;
    render(<TodoProgress todos={todos} isLoading />);
    expect(screen.getByText(/5 seconds/)).toBeInTheDocument();
  });

  it('says it is finished once the run ends', () => {
    render(<TodoProgress todos={todos} isLoading={false} />);
    expect(screen.getByText(/Finished/)).toBeInTheDocument();
  });

  it('promises no finish time it never measured', () => {
    elapsed.seconds = 30;
    render(<TodoProgress todos={todos} isLoading />);
    expect(screen.queryByText(/left/)).not.toBeInTheDocument();
  });

  it('shows nothing when there are no tasks', () => {
    const { container } = render(<TodoProgress todos={[]} isLoading />);
    expect(container).toBeEmptyDOMElement();
  });

  it('copes with a list where nothing is in progress', () => {
    const waiting = [{ content: 'Write it up', status: 'pending' as const }];
    render(<TodoProgress todos={waiting} isLoading />);
    expect(screen.getByText(/1 step/)).toBeInTheDocument();
  });
});
