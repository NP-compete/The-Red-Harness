import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApprovalPolicy } from './ApprovalPolicy';

const api = vi.hoisted(() => ({ getApprovalPolicy: vi.fn() }));
vi.mock('../../services/permissions-api', () => api);

const POLICY = {
  enabled: true,
  live: true,
  workspace: [
    { operations: ['ls', 'read'], paths: ['docs/**'], allowed: true },
    { operations: ['edit', 'write'], paths: ['*.py', 'config/**'], allowed: false },
  ],
  otherwise: 'ask' as const,
  rules: [
    {
      tools: ['ls', 'read_file'],
      decision: 'allow' as const,
      risk: 'low' as const,
      reason: 'Read-only inspection of the workspace',
    },
    {
      tools: ['execute'],
      decision: 'ask' as const,
      risk: 'high' as const,
      reason: 'Runs arbitrary commands in the agent sandbox',
    },
  ],
};

beforeEach(() => {
  vi.clearAllMocks();
  api.getApprovalPolicy.mockResolvedValue(POLICY);
});

describe('ApprovalPolicy', () => {
  it('names the tools that run without asking', async () => {
    render(<ApprovalPolicy />);
    expect(await screen.findByText(/read_file/)).toBeInTheDocument();
  });

  it('says why each rule is what it is', async () => {
    render(<ApprovalPolicy />);
    expect(
      await screen.findByText('Runs arbitrary commands in the agent sandbox'),
    ).toBeInTheDocument();
  });

  it('says what happens to a tool no rule names', async () => {
    render(<ApprovalPolicy />);
    expect(await screen.findByText(/Anything else/)).toBeInTheDocument();
  });

  it('warns when nothing is ever confirmed with anybody', async () => {
    api.getApprovalPolicy.mockResolvedValue({ ...POLICY, enabled: false });
    render(<ApprovalPolicy />);
    expect(await screen.findByText(/Approvals are switched off/i)).toBeInTheDocument();
  });

  it('says nothing before the answer is in', () => {
    const { container } = render(<ApprovalPolicy />);
    expect(container).toBeEmptyDOMElement();
  });

  it('says nothing when the agent will not say', async () => {
    api.getApprovalPolicy.mockResolvedValue(null);
    const { container } = render(<ApprovalPolicy />);
    await vi.waitFor(() => expect(api.getApprovalPolicy).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });

  it('says where it may read', async () => {
    render(<ApprovalPolicy />);
    expect(await screen.findByText(/docs\/\*\*/)).toBeInTheDocument();
  });

  it('says where it may not write', async () => {
    render(<ApprovalPolicy />);
    const denied = await screen.findByText(/\*\.py/);
    expect(denied.closest('li')).toHaveTextContent(/may not/i);
  });

  it('says nothing about the workspace when no rule names a path', async () => {
    api.getApprovalPolicy.mockResolvedValue({ ...POLICY, workspace: [] });
    render(<ApprovalPolicy />);
    await screen.findByText(/Anything else/);
    expect(screen.queryByText(/may not/i)).not.toBeInTheDocument();
  });

  it('says when nothing it does reaches outside the conversation', async () => {
    api.getApprovalPolicy.mockResolvedValue({ ...POLICY, live: false });
    render(<ApprovalPolicy />);
    expect(await screen.findByText(/nothing outside this conversation/i)).toBeInTheDocument();
  });

  it('does not say that when its actions are real', async () => {
    render(<ApprovalPolicy />);
    await screen.findByText(/Anything else/);
    expect(screen.queryByText(/nothing outside this conversation/i)).not.toBeInTheDocument();
  });
});
