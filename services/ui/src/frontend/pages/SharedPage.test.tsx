import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { SharedPage } from './SharedPage';

const api = vi.hoisted(() => ({ readShared: vi.fn() }));
vi.mock('../services/shared-read', () => api);

function show() {
  return render(
    <MemoryRouter initialEntries={['/shared/s1']}>
      <Routes>
        <Route path="/shared/:shareId" element={<SharedPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  api.readShared.mockResolvedValue({
    state: 'ok',
    title: 'Travel limits',
    capturedAt: '2026-03-01T12:00:00Z',
    messages: [
      { type: 'human', content: 'What is the travel limit?' },
      { type: 'ai', content: '500 euros per trip.' },
    ],
    attachmentNames: [],
  });
});

describe('SharedPage', () => {
  it('shows the conversation title', async () => {
    show();
    expect(await screen.findByText('Travel limits')).toBeInTheDocument();
  });

  it('shows what was asked', async () => {
    show();
    expect(await screen.findByText('What is the travel limit?')).toBeInTheDocument();
  });

  it('shows what was answered', async () => {
    show();
    expect(await screen.findByText('500 euros per trip.')).toBeInTheDocument();
  });

  it('says plainly that this is a snapshot, not the live conversation', async () => {
    show();
    expect(await screen.findByText(/snapshot/i)).toBeInTheDocument();
  });

  it('offers no way to continue the conversation', async () => {
    show();
    await screen.findByText('Travel limits');
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  });

  it('names attachments without offering the files', async () => {
    api.readShared.mockResolvedValue({
      state: 'ok', title: 't', capturedAt: null, messages: [], attachmentNames: ['handbook.pdf'],
    });
    show();
    expect(await screen.findByText('handbook.pdf')).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /handbook/ })).not.toBeInTheDocument();
  });

  it('renders the answer as the markdown it is', async () => {
    api.readShared.mockResolvedValue({
      state: 'ok',
      title: 't',
      capturedAt: null,
      messages: [{ type: 'ai', content: '### Connected\n\n- **Atlan** is ready' }],
      attachmentNames: [],
    });
    show();
    expect(await screen.findByRole('heading', { name: 'Connected' })).toBeInTheDocument();
    expect(screen.getByText('Atlan')).toBeInTheDocument();
  });

  it('shows a question as the plain text it was typed as', async () => {
    api.readShared.mockResolvedValue({
      state: 'ok',
      title: 't',
      capturedAt: null,
      messages: [{ type: 'human', content: 'what about **this**?' }],
      attachmentNames: [],
    });
    show();
    expect(await screen.findByText('what about **this**?')).toBeInTheDocument();
  });

  it('does not run markup smuggled into a shared answer', async () => {
    api.readShared.mockResolvedValue({
      state: 'ok',
      title: 't',
      capturedAt: null,
      messages: [{ type: 'ai', content: '<img src=x onerror="alert(1)">' }],
      attachmentNames: [],
    });
    const { container } = show();
    await screen.findByText('t');
    expect(container.querySelector('img[onerror]')).toBeNull();
  });

  it('says when a link was taken down', async () => {
    api.readShared.mockResolvedValue({ state: 'gone', reason: 'This link was revoked' });
    show();
    expect(await screen.findByText('This link was revoked')).toBeInTheDocument();
  });

  it('says when a link has expired, in its own words', async () => {
    api.readShared.mockResolvedValue({ state: 'gone', reason: 'This link has expired' });
    show();
    expect(await screen.findByText('This link has expired')).toBeInTheDocument();
  });

  it('says when a link is not valid at all', async () => {
    api.readShared.mockResolvedValue({ state: 'missing' });
    show();
    expect(await screen.findByText(/not a valid link/i)).toBeInTheDocument();
  });

  it('asks the reader to sign in when the link needs it', async () => {
    api.readShared.mockResolvedValue({ state: 'sign-in' });
    show();
    expect(await screen.findByText(/sign in/i)).toBeInTheDocument();
  });
});
