import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { InterruptBanner } from './InterruptBanner';
import type { InterruptInfo } from '../types/deep-agent';

// ── Fixtures ─────────────────────────────────────────────────────────────────

const toolApprovalInterrupt: InterruptInfo = {
  value: 'Do you approve this action? Please confirm or reject.',
  resumable: true,
};

const genericInterrupt: InterruptInfo = {
  value: 'What format would you prefer for the output?',
  resumable: true,
};

const mcpAuthInterrupt: InterruptInfo = {
  value: '',
  resumable: true,
  payload: {
    type: 'mcp_auth_required',
    mcp_name: 'github',
    connect_url: '/api/proxy/agent/mcp/github/connect',
    message: 'Connect your GitHub account.',
  },
};

/** The connect row links to Settings, so the banner needs a router. */
function renderBanner(props: Partial<{ onResume: () => void; onDismiss: () => void }> = {}) {
  return render(
    <MemoryRouter>
      <InterruptBanner
        interrupt={mcpAuthInterrupt}
        onResume={props.onResume ?? vi.fn()}
        onDismiss={props.onDismiss ?? vi.fn()}
      />
    </MemoryRouter>,
  );
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('InterruptBanner — tool approval branch', () => {
  it('renders "Action Required" for an approval interrupt', () => {
    render(
      <InterruptBanner interrupt={toolApprovalInterrupt} onResume={vi.fn()} onDismiss={vi.fn()} />,
    );
    expect(screen.getByText('Action Required')).toBeInTheDocument();
  });

  it('renders Approve and Reject buttons', () => {
    render(
      <InterruptBanner interrupt={toolApprovalInterrupt} onResume={vi.fn()} onDismiss={vi.fn()} />,
    );
    expect(screen.getByRole('button', { name: /approve/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /reject/i })).toBeInTheDocument();
  });

  it('calls onResume("approved") when Approve is clicked', async () => {
    const onResume = vi.fn();
    render(<InterruptBanner interrupt={toolApprovalInterrupt} onResume={onResume} onDismiss={vi.fn()} />);
    await userEvent.click(screen.getByRole('button', { name: /approve/i }));
    expect(onResume).toHaveBeenCalledWith('approved');
  });

  it('calls onResume("rejected") when Reject is clicked', async () => {
    const onResume = vi.fn();
    render(<InterruptBanner interrupt={toolApprovalInterrupt} onResume={onResume} onDismiss={vi.fn()} />);
    await userEvent.click(screen.getByRole('button', { name: /reject/i }));
    expect(onResume).toHaveBeenCalledWith('rejected');
  });

  it('calls onDismiss when the close button is clicked', async () => {
    const onDismiss = vi.fn();
    render(<InterruptBanner interrupt={toolApprovalInterrupt} onResume={vi.fn()} onDismiss={onDismiss} />);
    const closeBtn = screen.getByRole('button', { name: /close/i });
    await userEvent.click(closeBtn);
    expect(onDismiss).toHaveBeenCalledOnce();
  });

  it('renders the interrupt value text in the body', () => {
    render(
      <InterruptBanner interrupt={toolApprovalInterrupt} onResume={vi.fn()} onDismiss={vi.fn()} />,
    );
    expect(screen.getByText(/do you approve/i)).toBeInTheDocument();
  });

  // NOTE: in production, structured HITLInterruptValue interrupts (with action_requests)
  // are routed through ChatPage → ChatMessagesView → AIMessageRenderer, NOT through
  // InterruptBanner.  Those flows are covered by AIMessageRenderer.test.tsx.
});

describe('InterruptBanner — generic input branch', () => {
  it('renders "Input Required" for a non-approval interrupt', () => {
    render(
      <InterruptBanner interrupt={genericInterrupt} onResume={vi.fn()} onDismiss={vi.fn()} />,
    );
    expect(screen.getByText('Input Required')).toBeInTheDocument();
  });

  it('renders a text input and Send button', () => {
    render(
      <InterruptBanner interrupt={genericInterrupt} onResume={vi.fn()} onDismiss={vi.fn()} />,
    );
    expect(screen.getByRole('textbox', { name: /interrupt response/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /send/i })).toBeInTheDocument();
  });

  it('Send button is disabled when input is empty', () => {
    render(
      <InterruptBanner interrupt={genericInterrupt} onResume={vi.fn()} onDismiss={vi.fn()} />,
    );
    expect(screen.getByRole('button', { name: /send/i })).toBeDisabled();
  });

  it('calls onResume with the typed text when Send is clicked', async () => {
    const onResume = vi.fn();
    render(<InterruptBanner interrupt={genericInterrupt} onResume={onResume} onDismiss={vi.fn()} />);
    const input = screen.getByRole('textbox', { name: /interrupt response/i });
    await userEvent.type(input, 'JSON format please');
    await userEvent.click(screen.getByRole('button', { name: /send/i }));
    expect(onResume).toHaveBeenCalledWith('JSON format please');
  });

  it('calls onResume when Enter is pressed in the input', async () => {
    const onResume = vi.fn();
    render(<InterruptBanner interrupt={genericInterrupt} onResume={onResume} onDismiss={vi.fn()} />);
    const input = screen.getByRole('textbox', { name: /interrupt response/i });
    await userEvent.type(input, 'My response');
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(onResume).toHaveBeenCalledWith('My response');
  });

  it('does NOT call onResume on Enter when input is empty', () => {
    const onResume = vi.fn();
    render(<InterruptBanner interrupt={genericInterrupt} onResume={onResume} onDismiss={vi.fn()} />);
    const input = screen.getByRole('textbox', { name: /interrupt response/i });
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(onResume).not.toHaveBeenCalled();
  });
});

describe('InterruptBanner — MCP auth branch', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ connected: false }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    ));
    vi.stubGlobal('open', vi.fn());
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('names the integration and says where to connect it', () => {
    renderBanner();
    // It knew the integration all along and never said so: the old
    // copy was "To access external tools, you need to authenticate".
    expect(screen.getByText(/github/i)).toBeInTheDocument();
    expect(screen.queryByText(/to access external tools/i)).not.toBeInTheDocument();
    expect(screen.getByText(/settings/i)).toBeInTheDocument();
  });

  it('tells the reader to ask again, because nothing resumes for them', () => {
    renderBanner();
    expect(screen.getByText(/ask again/i)).toBeInTheDocument();
  });

  it('offers nothing to press — not a Connect button, not a link', () => {
    renderBanner();
    // The popup flow is gone: authenticating mid-answer put a
    // provider consent screen inside a reply and then restarted the
    // question on an event the reader had not asked for. A link to
    // Settings is no better; it still walks them out of the thread.
    expect(screen.queryByRole('button', { name: /^connect/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
  });

  it('never opens a popup', async () => {
    renderBanner();
    await waitFor(() => expect(vi.mocked(fetch)).toHaveBeenCalled());
    expect(vi.mocked(open)).not.toHaveBeenCalled();
  });

  it('does NOT render Approve / Reject buttons for MCP auth', () => {
    renderBanner();
    expect(screen.queryByRole('button', { name: /approve/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /reject/i })).not.toBeInTheDocument();
  });

  it('does not resume the paused run when the connection verifies', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ connected: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    const onResume = vi.fn();
    renderBanner({ onResume });

    // Connecting elsewhere removes the banner and nothing else. The
    // answer is produced by the reader asking again.
    await waitFor(() => {
      expect(screen.queryByTestId('mcp-connect-github')).not.toBeInTheDocument();
    });
    expect(onResume).not.toHaveBeenCalled();
  });

  it('stops claiming it is disconnected once it is connected elsewhere', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ connected: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    renderBanner();
    await waitFor(() => {
      expect(screen.queryByText(/is not connected/i)).not.toBeInTheDocument();
    });
  });
});

describe('InterruptBanner — approval risk', () => {
  const baseProps = {
    onResume: () => {},
    onDismiss: () => {},
  };

  it('renders a high-risk approval as danger, not warning', () => {
    render(
      <InterruptBanner
        {...baseProps}
        interrupt={{
          value: '[HIGH RISK] delete_user: Destructive and usually irreversible',
          resumable: true,
        }}
      />
    );

    expect(screen.getByText(/High-risk action/i)).toBeInTheDocument();
  });

  it('hides the risk marker from the reader', () => {
    render(
      <InterruptBanner
        {...baseProps}
        interrupt={{
          value: '[HIGH RISK] delete_user: Destructive and usually irreversible',
          resumable: true,
        }}
      />
    );

    expect(screen.queryByText(/\[HIGH RISK\]/)).not.toBeInTheDocument();
    expect(
      screen.getByText(/Destructive and usually irreversible/)
    ).toBeInTheDocument();
  });

  it('renders an ordinary approval as the standard prompt', () => {
    render(
      <InterruptBanner
        {...baseProps}
        interrupt={{
          value: 'write_file: Modifies files in the workspace. Approve?',
          resumable: true,
        }}
      />
    );

    expect(screen.getByText('Action Required')).toBeInTheDocument();
  });

  it('still shows both decisions for a high-risk action', () => {
    render(
      <InterruptBanner
        {...baseProps}
        interrupt={{
          value: '[HIGH RISK] execute: Runs arbitrary commands. Approve?',
          resumable: true,
        }}
      />
    );

    expect(screen.getByRole('button', { name: /approve/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /reject/i })).toBeInTheDocument();
  });
});

describe('one auth design, not several', () => {
  it('renders the same connect row the inline prompt uses', () => {
    renderBanner();

    // The shared component. A subagent's interrupt used to render a
    // blue pill under a sentence about "external tools" while the
    // orchestrator's own failure rendered an amber row naming the
    // integration — one event, two designs.
    expect(screen.getByTestId('mcp-connect-github')).toBeInTheDocument();
  });
});
