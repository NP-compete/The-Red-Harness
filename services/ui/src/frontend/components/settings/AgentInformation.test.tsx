import { configureStore } from '@reduxjs/toolkit';
import { render, screen } from '@testing-library/react';
import { Provider } from 'react-redux';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import configReducer from '../../redux/slices/config';
import userSettingsReducer from '../../redux/slices/userSettings';
import toastsReducer from '../../redux/slices/toasts';
import { AgentInformation } from './DeveloperSettings';

const structure = vi.hoisted(() => ({ fetchAgentStructure: vi.fn() }));
vi.mock('../../services/agent-structure', () => structure);

vi.mock('./ChannelsSection', () => ({ ChannelsSection: () => <div>channels</div> }));
vi.mock('./ReindexControl', () => ({ ReindexControl: () => <div>reindex</div> }));
vi.mock('./ExtractionStatus', () => ({ ExtractionStatus: () => <div>extraction</div> }));

beforeEach(() => {
  vi.clearAllMocks();
});

function show() {
  const store = configureStore({
    reducer: {
      config: configReducer,
      userSettings: userSettingsReducer,
      toasts: toastsReducer,
    },
  });
  return render(
    <Provider store={store}>
      <AgentInformation />
    </Provider>,
  );
}

describe('AgentInformation', () => {
  it('shows the operator sections once the structure loads', async () => {
    structure.fetchAgentStructure.mockResolvedValue({
      name: 'agent',
      orchestrator: { name: 'agent', skills: [], mcps: [] },
      subagents: {},
      mcp_servers: {},
      available_skills: [],
    });
    show();
    expect(await screen.findByText('channels')).toBeInTheDocument();
    expect(screen.getByText('reindex')).toBeInTheDocument();
    expect(screen.getByText('extraction')).toBeInTheDocument();
  });

  it('still shows them when the structure cannot be fetched', async () => {
    // They have nothing to do with the diagram; being nested inside it
    // meant one failed request took away the search index control and
    // the only statement of what reads an attachment.
    structure.fetchAgentStructure.mockRejectedValue(new Error('nope'));
    show();
    expect(await screen.findByText('channels')).toBeInTheDocument();
    expect(screen.getByText('reindex')).toBeInTheDocument();
    expect(screen.getByText('extraction')).toBeInTheDocument();
  });

  it('still says why the diagram is missing', async () => {
    structure.fetchAgentStructure.mockRejectedValue(new Error('nope'));
    show();
    expect(await screen.findByText(/structure is unavailable/i)).toBeInTheDocument();
  });
});
