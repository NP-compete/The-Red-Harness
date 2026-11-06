import { render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (k: string, o?: Record<string, unknown>) => (o?.name ? `${k}:${o.name}` : k),
  }),
}));

vi.mock('../services/mcp-oauth-api', () => ({
  openMcpOAuthPopup: vi.fn(),
  startMcpOAuthConnect: vi.fn(),
  verifyMcpOAuthConnected: vi.fn(),
}));

import { McpAuthPrompt } from './McpAuthPrompt';
import {
  openMcpOAuthPopup,
  startMcpOAuthConnect,
  verifyMcpOAuthConnected,
} from '../services/mcp-oauth-api';

const requests = [{ mcpName: 'dataverse', reason: 'not_connected' }];

const renderPrompt = (reqs = requests) =>
  render(
    <MemoryRouter>
      <McpAuthPrompt requests={reqs} />
    </MemoryRouter>,
  );

describe('McpAuthPrompt — it notifies, it does not authenticate', () => {
  beforeEach(() => {
    vi.mocked(verifyMcpOAuthConnected).mockReset();
    vi.mocked(startMcpOAuthConnect).mockReset();
    vi.mocked(openMcpOAuthPopup).mockReset();
  });

  it('tells the reader where to go, and offers nothing to press', async () => {
    vi.mocked(verifyMcpOAuthConnected).mockResolvedValue(false);
    renderPrompt();

    expect(
      await screen.findByText('mcpAuth.notConnectedGoToSettings:Dataverse'),
    ).toBeInTheDocument();
    // Not a button and not a link. Either one reads as the next step
    // in the conversation and takes the reader away mid-question.
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
  });

  it('never starts an OAuth flow of its own', async () => {
    vi.mocked(verifyMcpOAuthConnected).mockResolvedValue(false);
    renderPrompt();
    await screen.findByTestId('mcp-auth-prompt');

    expect(vi.mocked(startMcpOAuthConnect)).not.toHaveBeenCalled();
    expect(vi.mocked(openMcpOAuthPopup)).not.toHaveBeenCalled();
  });

  it('names the integration readably rather than as an identifier', async () => {
    vi.mocked(verifyMcpOAuthConnected).mockResolvedValue(false);
    renderPrompt([{ mcpName: 'unstructured-data', reason: 'not_connected' }]);

    expect(
      await screen.findByText('mcpAuth.notConnectedGoToSettings:Unstructured data'),
    ).toBeInTheDocument();
  });

  it('goes away once the integration is connected', async () => {
    // The prompt is pinned to a message and a message does not
    // change. Connecting from the settings page left this banner
    // insisting the opposite, on a turn the user had already fixed.
    vi.mocked(verifyMcpOAuthConnected).mockResolvedValue(true);
    renderPrompt();

    await waitFor(() =>
      expect(screen.queryByTestId('mcp-auth-prompt')).not.toBeInTheDocument(),
    );
  });

  it('stays as-is while the integration is still disconnected', async () => {
    vi.mocked(verifyMcpOAuthConnected).mockResolvedValue(false);
    renderPrompt();

    expect(
      await screen.findByText('mcpAuth.notConnectedGoToSettings:Dataverse'),
    ).toBeInTheDocument();
  });

  it('re-checks when the tab regains focus', async () => {
    vi.mocked(verifyMcpOAuthConnected).mockResolvedValue(false);
    renderPrompt();
    await screen.findByText('mcpAuth.notConnectedGoToSettings:Dataverse');

    // Connected in the other tab the user just came back from.
    vi.mocked(verifyMcpOAuthConnected).mockResolvedValue(true);
    window.dispatchEvent(new Event('focus'));

    await waitFor(() =>
      expect(screen.queryByTestId('mcp-auth-prompt')).not.toBeInTheDocument(),
    );
  });
});

describe('several unconnected integrations are one notice, not a stack', () => {
  // `t` is mocked above to render as `key:name`, so these assert on
  // the key chosen and the joined list passed to it.
  beforeEach(() => {
    vi.mocked(verifyMcpOAuthConnected).mockReset();
  });

  it('names them all in a single box', async () => {
    // Six produced six boxes differing only in the first word, each
    // repeating the same instruction to visit the same page.
    vi.mocked(verifyMcpOAuthConnected).mockResolvedValue(false);
    renderPrompt([
      { mcpName: 'atlan', reason: 'not_connected' },
      { mcpName: 'datadog', reason: 'not_connected' },
      { mcpName: 'miro', reason: 'not_connected' },
    ]);

    const box = await screen.findByText(/notConnectedGoToSettingsMany:/);
    expect(box.textContent).toContain('Atlan');
    expect(box.textContent).toContain('Datadog');
    expect(box.textContent).toContain('Miro');
  });

  it('uses the plural sentence, and says it once', async () => {
    vi.mocked(verifyMcpOAuthConnected).mockResolvedValue(false);
    renderPrompt([
      { mcpName: 'atlan', reason: 'not_connected' },
      { mcpName: 'miro', reason: 'not_connected' },
    ]);

    const prompt = await screen.findByTestId('mcp-auth-prompt');
    const said = (prompt.textContent ?? '').match(/GoToSettings/g);
    expect(said).toHaveLength(1);
  });

  it('keeps the singular sentence for a single integration', async () => {
    vi.mocked(verifyMcpOAuthConnected).mockResolvedValue(false);
    renderPrompt([{ mcpName: 'miro', reason: 'not_connected' }]);

    expect(
      await screen.findByText('mcpAuth.notConnectedGoToSettings:Miro'),
    ).toBeInTheDocument();
  });

  it('keeps expired apart from not-connected — different fixes', async () => {
    vi.mocked(verifyMcpOAuthConnected).mockResolvedValue(false);
    renderPrompt([
      { mcpName: 'atlan', reason: 'not_connected' },
      { mcpName: 'miro', reason: 'expired' },
    ]);

    expect(
      await screen.findByText('mcpAuth.notConnectedGoToSettings:Atlan'),
    ).toBeInTheDocument();
    expect(
      await screen.findByText('mcpAuth.expiredGoToSettings:Miro'),
    ).toBeInTheDocument();
  });

  it('drops the ones that connected and re-reads as a shorter sentence', async () => {
    vi.mocked(verifyMcpOAuthConnected).mockImplementation(
      async (name: string) => name === 'datadog',
    );
    renderPrompt([
      { mcpName: 'atlan', reason: 'not_connected' },
      { mcpName: 'datadog', reason: 'not_connected' },
    ]);

    // One left, so it drops back to the singular sentence.
    expect(
      await screen.findByText('mcpAuth.notConnectedGoToSettings:Atlan'),
    ).toBeInTheDocument();
  });
});
