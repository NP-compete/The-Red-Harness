import { render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { SubagentList } from './SubagentList';

function answers(subagents: unknown[]) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ subagents }) }),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

const CURATOR = {
  name: 'curator',
  tool_scope: 'inherited',
  tools: [],
  description: 'Finds data and establishes whether it can be trusted.',
  model: 'gemini-3.8-flash',
  provider: 'vertex',
  fallback: '',
  mcps: ['atlan'],
  skills: ['data-discovery'],
};

describe('SubagentList', () => {
  it('names the specialist', async () => {
    answers([CURATOR]);
    render(<SubagentList />);
    expect(await screen.findByText('curator')).toBeInTheDocument();
  });

  it('says which model it runs on', async () => {
    answers([CURATOR]);
    render(<SubagentList />);
    expect(await screen.findByText(/gemini-3\.8-flash/)).toBeInTheDocument();
  });

  it('names what it falls back to', async () => {
    answers([{ ...CURATOR, fallback: 'gemini-3.8-pro' }]);
    render(<SubagentList />);
    expect(await screen.findByText(/gemini-3\.8-pro/)).toBeInTheDocument();
  });

  it('says nothing about a fallback when there is none', async () => {
    answers([CURATOR]);
    render(<SubagentList />);
    await screen.findByText('curator');
    expect(screen.queryByText(/falls back/i)).not.toBeInTheDocument();
  });

  it('says nothing about a model the agent did not name', async () => {
    answers([{ ...CURATOR, model: '', provider: '' }]);
    render(<SubagentList />);
    await screen.findByText('curator');
    expect(screen.queryByText(/gemini/)).not.toBeInTheDocument();
  });

  it('says when a specialist gets every tool its servers expose', async () => {
    answers([CURATOR]);
    render(<SubagentList />);
    expect(await screen.findByText(/every tool/i)).toBeInTheDocument();
  });

  it('says how many tools a confined specialist may use', async () => {
    answers([{ ...CURATOR, tool_scope: 'explicit', tools: ['search', 'read'] }]);
    render(<SubagentList />);
    expect(await screen.findByText(/limited to 2 tools/i)).toBeInTheDocument();
  });

  it('counts a single permitted tool in the singular', async () => {
    answers([{ ...CURATOR, tool_scope: 'explicit', tools: ['search'] }]);
    render(<SubagentList />);
    expect(await screen.findByText(/limited to 1 tool\b/i)).toBeInTheDocument();
  });

  it('says when a specialist has no tools at all', async () => {
    answers([{ ...CURATOR, tool_scope: 'none', mcps: [], tools: [] }]);
    render(<SubagentList />);
    expect(await screen.findByText(/no tools/i)).toBeInTheDocument();
  });

  it('says nothing about scope when the agent did not report one', async () => {
    answers([{ ...CURATOR, tool_scope: undefined }]);
    render(<SubagentList />);
    await screen.findByText('curator');
    expect(screen.queryByText(/every tool|limited to|no tools/i)).not.toBeInTheDocument();
  });
});
