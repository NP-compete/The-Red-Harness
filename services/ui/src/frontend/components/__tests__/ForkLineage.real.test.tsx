import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { ForkLineage } from '../ForkLineage';

const show = (ui: React.ReactElement) => render(<MemoryRouter>{ui}</MemoryRouter>);

const PARENT = { id: 'p1', title: 'Travel limits', forkedFrom: null, messageCount: 4 };
const FORK = { id: 'f1', title: 'Travel limits (fork)', forkedFrom: 'p1', messageCount: 2 };

describe('ForkLineage — a conversation and the one it came from', () => {
  it('counts the forks in the line', () => {
    show(<ForkLineage chats={[PARENT, FORK]} currentId="f1" />);
    expect(screen.getByText('1 fork')).toBeInTheDocument();
  });

  it('shows both conversations', () => {
    show(<ForkLineage chats={[PARENT, FORK]} currentId="f1" />);
    expect(screen.getByText('Travel limits')).toBeInTheDocument();
    expect(screen.getByText('Travel limits (fork)')).toBeInTheDocument();
  });

  it('marks which one is being read', () => {
    show(<ForkLineage chats={[PARENT, FORK]} currentId="f1" />);
    const current = screen.getByText('Travel limits (fork)').closest('li');
    expect(current).toHaveAttribute('aria-current', 'true');
  });

  it('shows nothing for a conversation that was never forked', () => {
    const { container } = show(<ForkLineage chats={[PARENT]} currentId="p1" />);
    expect(container).toBeEmptyDOMElement();
  });

  it('shows nothing when the parent is not in the list', () => {
    // The list is capped, so a fork of an older conversation can
    // arrive without it.
    const { container } = show(<ForkLineage chats={[FORK]} currentId="f1" />);
    expect(container).toBeEmptyDOMElement();
  });

  it('shows the line when reading the parent of a fork', () => {
    show(<ForkLineage chats={[PARENT, FORK]} currentId="p1" />);
    expect(screen.getByText('1 fork')).toBeInTheDocument();
  });

  it('lets you open the other conversation in the line', async () => {
    show(<ForkLineage chats={[PARENT, FORK]} currentId="f1" />);
    expect(
      await screen.findByRole('link', { name: /Travel limits$/ }),
    ).toHaveAttribute('href', '/chat/p1');
  });

  it('does not link the conversation already being read', () => {
    show(<ForkLineage chats={[PARENT, FORK]} currentId="f1" />);
    expect(screen.queryByRole('link', { name: /\(fork\)/ })).not.toBeInTheDocument();
  });

  it('still shows the name of the one being read', () => {
    show(<ForkLineage chats={[PARENT, FORK]} currentId="f1" />);
    expect(screen.getByText('Travel limits (fork)')).toBeInTheDocument();
  });
});
