import { render as renderBare, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { ForkLineage } from './ForkLineage';

// The lineage links to the other conversations in the line, so it
// renders inside the router it always has around it in the app.
const render = (ui: React.ReactElement) => renderBare(<MemoryRouter>{ui}</MemoryRouter>);

const chats = [
  { id: 't1', title: 'What is the travel limit?', forkedFrom: null, messageCount: 6 },
  { id: 't2', title: 'What is the travel limit? (fork)', forkedFrom: 't1', messageCount: 4 },
  { id: 't3', title: 'Another angle', forkedFrom: 't2', messageCount: 2 },
];

describe('ForkLineage', () => {
  it('says nothing about a conversation nobody forked', () => {
    const { container } = render(<ForkLineage chats={[chats[0]]} currentId="t1" />);
    expect(container).toBeEmptyDOMElement();
  });

  it('shows the conversation a fork came from', () => {
    render(<ForkLineage chats={chats} currentId="t2" />);
    expect(screen.getByText('What is the travel limit?')).toBeInTheDocument();
  });

  it('shows the fork itself', () => {
    render(<ForkLineage chats={chats} currentId="t2" />);
    expect(screen.getByText('What is the travel limit? (fork)')).toBeInTheDocument();
  });

  it('marks where the reader is', () => {
    render(<ForkLineage chats={chats} currentId="t2" />);
    expect(screen.getByRole('listitem', { current: true })).toHaveTextContent(
      'What is the travel limit? (fork)',
    );
  });

  it('indents each fork under what it came from', () => {
    render(<ForkLineage chats={chats} currentId="t3" />);
    const rows = screen.getAllByRole('listitem');
    expect(rows.map((r) => r.getAttribute('data-depth'))).toEqual(['0', '1', '2']);
  });

  it('says how many forks there are', () => {
    render(<ForkLineage chats={chats} currentId="t2" />);
    expect(screen.getByText('2 forks')).toBeInTheDocument();
  });

  it('counts a single fork properly', () => {
    render(<ForkLineage chats={chats.slice(0, 2)} currentId="t2" />);
    expect(screen.getByText('1 fork')).toBeInTheDocument();
  });

  it('says how long each branch is', () => {
    render(<ForkLineage chats={chats} currentId="t2" />);
    expect(screen.getByText('6 messages')).toBeInTheDocument();
  });

  it('shows nothing on a conversation unrelated to any fork', () => {
    const lone = [...chats, { id: 't9', title: 'Elsewhere', forkedFrom: null, messageCount: 1 }];
    const { container } = render(<ForkLineage chats={lone} currentId="t9" />);
    expect(container).toBeEmptyDOMElement();
  });

  describe('telling two forks of the same conversation apart', () => {
    // Same parent, same title, same depth. Where the fork was taken
    // is the only thing that distinguishes them.
    const siblings = [
      { id: 't1', title: 'What is the travel limit?', forkedFrom: null, messageCount: 12, forkedAt: null },
      { id: 't2', title: 'What is the travel limit? (fork)', forkedFrom: 't1', messageCount: 5, forkedAt: 4 },
      { id: 't3', title: 'What is the travel limit? (fork)', forkedFrom: 't1', messageCount: 5, forkedAt: 8 },
    ];

    it('says where the first one was taken', () => {
      render(<ForkLineage chats={siblings} currentId="t2" />);
      expect(screen.getByText(/from message 4/i)).toBeInTheDocument();
    });

    it('says where the other one was taken', () => {
      render(<ForkLineage chats={siblings} currentId="t2" />);
      expect(screen.getByText(/from message 8/i)).toBeInTheDocument();
    });

    it('says nothing of the kind about the conversation nobody forked', () => {
      render(<ForkLineage chats={siblings} currentId="t2" />);
      expect(screen.queryAllByText(/from message/i)).toHaveLength(2);
    });
  });


  describe('a conversation whose length it does not know', () => {
    // Only the open conversation has its messages loaded. "0 messages"
    // for the others is not a small inaccuracy — it is a claim that
    // the conversation is empty, about threads that plainly are not.
    const unknown = [
      { id: 't1', title: 'Parent', forkedFrom: null, messageCount: undefined },
      { id: 't2', title: 'A fork', forkedFrom: 't1', messageCount: 5, forkedAt: 4 },
    ];

    it('does not call it empty', () => {
      render(<ForkLineage chats={unknown} currentId="t2" />);
      expect(screen.queryByText(/0 messages/i)).not.toBeInTheDocument();
    });

    it('still lists the conversation', () => {
      render(<ForkLineage chats={unknown} currentId="t2" />);
      expect(screen.getByText('Parent')).toBeInTheDocument();
    });

    it('still counts the one it does know', () => {
      render(<ForkLineage chats={unknown} currentId="t2" />);
      expect(screen.getByText(/5 messages/i)).toBeInTheDocument();
    });

    it('says nothing about a count of zero it was actually given', () => {
      // Genuinely empty is still worth not saying: an empty fork is
      // a thread nobody has used, and the row already shows that.
      const empty = [
        { id: 't1', title: 'Parent', forkedFrom: null, messageCount: 0 },
        { id: 't2', title: 'A fork', forkedFrom: 't1', messageCount: 5, forkedAt: 4 },
      ];
      render(<ForkLineage chats={empty} currentId="t2" />);
      expect(screen.queryByText(/0 messages/i)).not.toBeInTheDocument();
    });
  });

});
