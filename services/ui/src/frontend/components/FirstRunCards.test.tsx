import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { FirstRunCards } from './FirstRunCards';

const api = vi.hoisted(() => ({ listDocuments: vi.fn() }));
vi.mock('../services/documents-api', () => api);

function documents(count: number) {
  api.listDocuments.mockResolvedValue({
    documents: Array.from({ length: count }, (_, i) => ({ path: `d${i}.md` })),
  });
}

/** The connect card is a link, so it needs somewhere to link within. */
function show(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

afterEach(() => vi.clearAllMocks());

describe('FirstRunCards', () => {
  it('greets an empty workspace', async () => {
    documents(0);
    show(<FirstRunCards chats={0} onAsk={vi.fn()} />);
    expect(await screen.findByText('Connect a source')).toBeInTheDocument();
  });

  it('says what connecting a source gets you', async () => {
    documents(0);
    show(<FirstRunCards chats={0} onAsk={vi.fn()} />);
    expect(
      await screen.findByText('Answers can draw on your own documents'),
    ).toBeInTheDocument();
  });

  it('counts what is left', async () => {
    documents(0);
    show(<FirstRunCards chats={0} onAsk={vi.fn()} />);
    expect(await screen.findByText(/2 things to get started/i)).toBeInTheDocument();
  });

  it('says "thing" when only one is left', async () => {
    documents(2);
    show(<FirstRunCards chats={0} onAsk={vi.fn()} />);
    expect(await screen.findByText(/1 thing to get started/i)).toBeInTheDocument();
  });

  it('stays out of the way of a workspace under way', async () => {
    documents(2);
    const { container } = show(<FirstRunCards chats={4} onAsk={vi.fn()} />);
    await new Promise((r) => setTimeout(r, 0));
    expect(container).toBeEmptyDOMElement();
  });

  it('shows nothing while it still does not know', () => {
    documents(0);
    const { container } = show(<FirstRunCards chats={0} onAsk={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('hands a first question back to the composer', async () => {
    documents(2);
    const onAsk = vi.fn();
    show(<FirstRunCards chats={0} onAsk={onAsk} />);
    await userEvent.click(await screen.findByRole('button', { name: /ask a question/i }));
    expect(onAsk).toHaveBeenCalled();
  });

  it('points at where a source is actually added', async () => {
    documents(0);
    show(<FirstRunCards chats={4} onAsk={vi.fn()} />);
    const link = await screen.findByRole('link', { name: /connect/i });
    expect(link).toHaveAttribute('href', expect.stringContaining('settings'));
  });

  it('is offered, never demanded', async () => {
    // Nothing here blocks the composer behind it.
    documents(0);
    show(<FirstRunCards chats={0} onAsk={vi.fn()} />);
    await screen.findByText('Connect a source');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
