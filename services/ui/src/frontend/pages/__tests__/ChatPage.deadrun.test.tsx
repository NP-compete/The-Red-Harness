import { configureStore } from '@reduxjs/toolkit';
import { render, screen } from '@testing-library/react';
import { Provider } from 'react-redux';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import chatsReducer from '../../redux/slices/chats';
import configReducer from '../../redux/slices/config';
import personalizationReducer from '../../redux/slices/personalization';
import projectsReducer from '../../redux/slices/projects';
import toastsReducer from '../../redux/slices/toasts';
import userSettingsReducer from '../../redux/slices/userSettings';
import { ChatPage } from '../ChatPage';

const THREAD = 't1';

const api = vi.hoisted(() => ({
  getThreadStateAndInterrupt: vi.fn(),
  deadRunReason: vi.fn(),
}));

vi.mock('../../services/agent-rest', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  getThreadStateAndInterrupt: api.getThreadStateAndInterrupt,
}));
vi.mock('../../services/run-status', () => ({ deadRunReason: api.deadRunReason }));
vi.mock('../../services/feedback-api', () => ({
  getThreadFeedback: vi.fn().mockResolvedValue({}),
}));
// Hydration is skipped for a chat this browser just created, which is
// how a new conversation avoids asking the agent about itself.
vi.mock('../../services/newChatTracker', () => ({
  isClientCreatedChat: () => false,
  markChatAsClientCreated: vi.fn(),
  clearClientCreatedChat: vi.fn(),
}));
vi.mock('../../hooks/useStreamingAPI', () => ({
  MAX_RETRIES: 5,
  useStreamingAPI: () => ({
    messages: [],
    streamEvents: [],
    isLoading: false,
    pendingInterrupt: null,
    submit: vi.fn(),
    cancel: vi.fn(),
    setMessages: vi.fn(),
  }),
}));

const INTERRUPT = {
  value: {
    action_requests: [
      { name: 'write_file', args: { file_path: '/reports/x.md' }, description: 'write_file' },
    ],
  },
  resumable: true,
};

function show() {
  const store = configureStore({
    preloadedState: {
      // The chat list is normally loaded by the layout above this
      // page; until it is, the page shows a spinner and no effect
      // of its own has run.
      chats: {
        ...chatsReducer(undefined, { type: '@@init' }),
        isLoadingThreads: false,
        // Hydration only runs for a conversation the browser has
        // already listed; the layout above this page loads that list.
        chats: [
          {
            id: THREAD,
            title: 'Write a file',
            preview: '',
            timestamp: new Date().toISOString(),
            messages: [],
            historicalActivities: {},
            feedback: {},
          },
        ],
      },
    },
    reducer: {
      chats: chatsReducer,
      config: configReducer,
      personalization: personalizationReducer,
      projects: projectsReducer,
      toasts: toastsReducer,
      userSettings: userSettingsReducer,
    },
  });
  return render(
    <Provider store={store}>
      <MemoryRouter initialEntries={[`/chat/${THREAD}`]}>
        <ChatPage threadId={THREAD} />
      </MemoryRouter>
    </Provider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  api.getThreadStateAndInterrupt.mockResolvedValue({
    messages: [{ type: 'human', content: 'write a file', id: 'm1' }],
    interrupt: INTERRUPT,
  });
  api.deadRunReason.mockResolvedValue(null);
});

describe('ChatPage — a conversation paused on an approval', () => {
  it('asks what became of the run', async () => {
    show();
    await vi.waitFor(() => expect(api.deadRunReason).toHaveBeenCalledWith(THREAD));
  });

  it('says why when the run died, instead of offering the approval', async () => {
    api.deadRunReason.mockResolvedValue('Max retries exceeded');
    show();
    expect(await screen.findByText(/Max retries exceeded/)).toBeInTheDocument();
  });

  it('does not ask about the run when nothing is paused', async () => {
    api.getThreadStateAndInterrupt.mockResolvedValue({ messages: [], interrupt: null });
    show();
    await vi.waitFor(() => expect(api.getThreadStateAndInterrupt).toHaveBeenCalled());
    expect(api.deadRunReason).not.toHaveBeenCalled();
  });
});
