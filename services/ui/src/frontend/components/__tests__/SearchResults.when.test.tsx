import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { SearchResults } from '../SearchResults';

const hit = (over: Record<string, unknown> = {}) => ({
  thread_id: 't1',
  title: 'Who is my manager?',
  rank: 0.83,
  snippet: 'Your <<manager>> is Nirav Kumar.',
  updated_at: new Date(Date.now() - 3 * 3600_000).toISOString(),
  ...over,
});

const show = (hits: unknown[]) =>
  render(
    <SearchResults
      hits={hits as never}
      loading={false}
      error={null}
      excludeIds={new Set()}
      onSelect={vi.fn()}
    />,
  );

describe('SearchResults — telling similar results apart', () => {
  it('says when the conversation was last active', () => {
    show([hit()]);
    expect(screen.getByText('3 hours ago')).toBeInTheDocument();
  });

  it('says nothing when the agent gave no date', () => {
    show([hit({ updated_at: null })]);
    expect(screen.getByText('Who is my manager?')).toBeInTheDocument();
    expect(screen.queryByText(/ago/)).not.toBeInTheDocument();
  });

  it('still shows the matching text', () => {
    show([hit()]);
    expect(screen.getByText('manager')).toBeInTheDocument();
  });
});
