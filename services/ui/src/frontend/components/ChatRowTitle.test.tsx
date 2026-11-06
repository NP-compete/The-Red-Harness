import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ChatRowTitle } from './ChatRowTitle';

describe('ChatRowTitle', () => {
  it('shows a title the conversation has earned', () => {
    render(<ChatRowTitle title="What is the travel limit?" />);
    expect(screen.getByText('What is the travel limit?')).toBeInTheDocument();
  });

  it('never leaves a row with nothing to identify it by', () => {
    render(<ChatRowTitle title="   " />);
    expect(screen.getByText('Untitled')).toBeInTheDocument();
  });

  it('says plainly when a conversation has not been named yet', () => {
    render(<ChatRowTitle title="New Chat" />);
    expect(screen.getByTitle('not named yet')).toBeInTheDocument();
  });

  it('treats the fallback name the same way', () => {
    render(<ChatRowTitle title="Chat" />);
    expect(screen.getByTitle('not named yet')).toBeInTheDocument();
  });

  it('adds no explanation to a real title', () => {
    render(<ChatRowTitle title="What is the travel limit?" />);
    expect(screen.queryByTitle('not named yet')).not.toBeInTheDocument();
  });

  it('shows an unnamed conversation in a quieter style', () => {
    render(<ChatRowTitle title="New Chat" />);
    expect(screen.getByText('New Chat')).toHaveClass('italic');
  });

  it('does not italicise a real title', () => {
    render(<ChatRowTitle title="What is the travel limit?" />);
    expect(screen.getByText('What is the travel limit?')).not.toHaveClass('italic');
  });

  it('says where a name came from when the first message gave it', () => {
    render(<ChatRowTitle title="What is the travel limit?" source="first-message" />);
    expect(screen.getByTitle('named from your first message')).toBeInTheDocument();
  });
});
