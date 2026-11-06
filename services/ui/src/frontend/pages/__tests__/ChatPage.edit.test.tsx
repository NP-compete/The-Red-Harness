import { configureStore } from '@reduxjs/toolkit';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
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
  withdrawFrom: vi.fn(),
  submit: vi.fn(),
}));

vi.mock('../../services/agent-rest', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  getThreadStateAndInterrupt: api.getThreadStateAndInterrupt,
}));
vi.mock('../../services/run-status', () => ({
  deadRunReason: api.deadRunReason,
  runStillGoing: vi.fn().mockResolvedValue(false),
}));
vi.mock('../../services/thread-truncate', () => ({ withdrawFrom: api.withdrawFrom }));
vi.mock('../../services/feedback-api', () => ({
  getThreadFeedback: vi.fn().mockResolvedValue({}),
}));
vi.mock('../../services/newChatTracker', () => ({
  isClientCreatedChat: () => false,
  markChatAsClientCreated: vi.fn(),
  clearClientCreatedChat: vi.fn(),
}));

const MESSAGES = [
  { type: 'human', content: 'Say APPLE', id: 'm1' },
  { type: 'ai', content: 'APPLE', id: 'm2' },
];

vi.mock('../../hooks/useStreamingAPI', () => ({
  MAX_RETRIES: 5,
  useStreamingAPI: () => ({
    messages: MESSAGES,
    streamEvents: [],
    isLoading: false,
    pendingInterrupt: null,
    submit: api.submit,
    cancel: vi.fn(),
    stop: vi.fn(),
    setMessages: vi.fn(),
  }),
}));

let store: ReturnType<typeof makeStore>;

function makeStore() {
  return configureStore({
    preloadedState: {
      chats: {
        ...chatsReducer(undefined, { type: '@@init' }),
        isLoadingThreads: false,
        chats: [
          {
            id: THREAD,
            title: 'Say APPLE',
            preview: '',
            timestamp: new Date().toISOString(),
            messages: MESSAGES,
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
}

function show() {
  store = makeStore();
  return render(
    <Provider store={store}>
      <MemoryRouter initialEntries={[`/chat/${THREAD}`]}>
        <ChatPage threadId={THREAD} />
      </MemoryRouter>
    </Provider>,
  );
}

async function editFirstMessage(to: string) {
  fireEvent.click(await screen.findByRole('button', { name: /edit message/i }));
  const box = await screen.findByRole('textbox', { name: /edit/i });
  fireEvent.change(box, { target: { value: to } });
  fireEvent.click(screen.getByRole("button", { name: /save edited message/i }));
}

beforeEach(() => {
  vi.clearAllMocks();
  api.getThreadStateAndInterrupt.mockResolvedValue({ messages: MESSAGES, interrupt: null });
  api.deadRunReason.mockResolvedValue(null);
  api.withdrawFrom.mockResolvedValue(true);
});

describe('editing a question', () => {
  it('withdraws the question being replaced, and the answer it got', async () => {
    show();
    await editFirstMessage('Say BANANA');
    await waitFor(() => expect(api.withdrawFrom).toHaveBeenCalledWith(THREAD, 0));
  });

  it('asks the new question once the old one is gone', async () => {
    show();
    await editFirstMessage('Say BANANA');
    await waitFor(() => expect(api.submit).toHaveBeenCalled());
  });

  it('does not ask again when the old turns could not be withdrawn', async () => {
    // Otherwise the conversation ends up holding both versions.
    api.withdrawFrom.mockResolvedValue(false);
    show();
    await editFirstMessage('Say BANANA');
    await waitFor(() => expect(api.withdrawFrom).toHaveBeenCalled());
    expect(api.submit).not.toHaveBeenCalled();
  });

  it('says so when the edit could not be made', async () => {
    // Raised as a toast, which this page does not render itself.
    api.withdrawFrom.mockResolvedValue(false);
    show();
    await editFirstMessage('Say BANANA');
    await waitFor(() =>
      expect(store.getState().toasts.toasts.length).toBeGreaterThan(0),
    );
  });
});
