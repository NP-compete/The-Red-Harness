import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { Provider } from 'react-redux';
// ForkButton calls useNavigate, so the view needs a router in scope.
import { MemoryRouter } from 'react-router-dom';
import { configureStore } from '@reduxjs/toolkit';
import type { Message } from '@langchain/langgraph-sdk';
import { ChatMessagesView } from './ChatMessagesView';
import chatsReducer from '../redux/slices/chats';
import configReducer from '../redux/slices/config';
import personalizationReducer from '../redux/slices/personalization';
import toastsReducer from '../redux/slices/toasts';
import userSettingsReducer from '../redux/slices/userSettings';
import projectsReducer from '../redux/slices/projects';

// jsdom does not implement scrollIntoView
Element.prototype.scrollIntoView = vi.fn();

// ── Store factory ─────────────────────────────────────────────────────────────

function makeStore() {
  return configureStore({
    reducer: {
      chats: chatsReducer,
      config: configReducer,
      personalization: personalizationReducer,
      toasts: toastsReducer,
      userSettings: userSettingsReducer,
      projects: projectsReducer,
    },
  });
}

// ── Fixtures ──────────────────────────────────────────────────────────────────

const HUMAN_MESSAGE = {
  type: 'human',
  content: 'Hello agent',
  id: 'msg-human-1',
} as unknown as Message;

function makeBaseProps(overrides: Record<string, unknown> = {}) {
  return {
    messages: [HUMAN_MESSAGE],
    isLoading: false,
    pendingInterrupt: undefined as any,
    scrollAreaRef: React.createRef<HTMLDivElement>(),
    onSubmit: vi.fn(),
    onCancel: vi.fn(),
    liveActivityEvents: [] as any[],
    historicalActivities: {} as Record<string, any[]>,
    chatId: 'test-chat',
    traceId: null,
    ...overrides,
  };
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('ChatMessagesView — errorMessage prop', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders actual error text when errorMessage is provided', () => {
    const store = makeStore();
    render(
      <MemoryRouter>
        <Provider store={store}>
        <ChatMessagesView
          {...makeBaseProps({ errorMessage: 'Model configuration is invalid' })}
        />
        </Provider>
      </MemoryRouter>,
    );

    // showNoResponse has a 1500ms delay before rendering
    act(() => { vi.advanceTimersByTime(2000); });

    expect(screen.getByText('The agent encountered an error:')).toBeInTheDocument();
    expect(screen.getByText('Model configuration is invalid')).toBeInTheDocument();
  });

  it('shows generic fallback when errorMessage is not provided', () => {
    const store = makeStore();
    render(
      <MemoryRouter>
        <Provider store={store}>
        <ChatMessagesView {...makeBaseProps()} />
        </Provider>
      </MemoryRouter>,
    );

    act(() => { vi.advanceTimersByTime(2000); });

    expect(
      screen.getByText("The agent didn\u0027t respond. This could be a temporary issue."),
    ).toBeInTheDocument();
  });

  it('shows generic fallback when errorMessage is null', () => {
    const store = makeStore();
    render(
      <MemoryRouter>
        <Provider store={store}>
        <ChatMessagesView {...makeBaseProps({ errorMessage: null })} />
        </Provider>
      </MemoryRouter>,
    );

    act(() => { vi.advanceTimersByTime(2000); });

    expect(
      screen.getByText("The agent didn\u0027t respond. This could be a temporary issue."),
    ).toBeInTheDocument();
  });

  it('renders error when last message is AI (partial response before error)', () => {
    const store = makeStore();
    const AI_MESSAGE = {
      type: 'ai',
      content: 'Partial response...',
      id: 'msg-ai-1',
      tool_calls: [],
    } as unknown as Message;

    render(
      <MemoryRouter>
        <Provider store={store}>
        <ChatMessagesView
          {...makeBaseProps({
            messages: [HUMAN_MESSAGE, AI_MESSAGE],
            errorMessage: 'Model configuration is invalid',
          })}
        />
        </Provider>
      </MemoryRouter>,
    );

    // No delay needed — the standalone error block renders immediately
    expect(screen.getByText('The agent encountered an error:')).toBeInTheDocument();
    expect(screen.getByText('Model configuration is invalid')).toBeInTheDocument();
  });

  it('does not render standalone error block while loading', () => {
    const store = makeStore();
    const AI_MESSAGE = {
      type: 'ai',
      content: 'Partial response...',
      id: 'msg-ai-2',
      tool_calls: [],
    } as unknown as Message;

    render(
      <MemoryRouter>
        <Provider store={store}>
        <ChatMessagesView
          {...makeBaseProps({
            messages: [HUMAN_MESSAGE, AI_MESSAGE],
            isLoading: true,
            errorMessage: 'Some error',
          })}
        />
        </Provider>
      </MemoryRouter>,
    );

    expect(screen.queryByText('The agent encountered an error:')).not.toBeInTheDocument();
  });

  it('does not render error block while loading', () => {
    const store = makeStore();
    render(
      <MemoryRouter>
        <Provider store={store}>
        <ChatMessagesView
          {...makeBaseProps({ isLoading: true, errorMessage: 'Some error' })}
        />
        </Provider>
      </MemoryRouter>,
    );

    act(() => { vi.advanceTimersByTime(2000); });

    expect(screen.queryByText('The agent encountered an error:')).not.toBeInTheDocument();
    expect(screen.queryByText('Some error')).not.toBeInTheDocument();
  });
});

describe('actions row on delegation messages', () => {
  /**
   * A turn that delegates produces two assistant messages: one whose
   * only payload is `task` tool calls, and one with the answer. Both
   * used to get a full actions row, so a single turn showed two
   * "AI-generated" tags and offered a thumbs-up on a message that
   * said nothing but "I called two subagents".
   */
  const delegation = {
    id: 'ai-delegation',
    type: 'ai',
    content: '',
    tool_calls: [
      { name: 'task', id: 'c1', args: { subagent_type: 'investigator', description: 'Find MRs' } },
    ],
  } as unknown as Message;

  const answer = {
    id: 'ai-answer',
    type: 'ai',
    content: 'Here are your 20 open merge requests.',
  } as unknown as Message;

  const renderWith = (messages: Message[]) =>
    render(
      <MemoryRouter>
        <Provider store={makeStore()}>
          <ChatMessagesView {...makeBaseProps({ messages })} />
        </Provider>
      </MemoryRouter>,
    );

  it('marks the answer as AI-generated exactly once in a delegated turn', () => {
    renderWith([HUMAN_MESSAGE, delegation, answer]);
    // Exact text: the badge's own aria-label is "AI-generated
    // content", which a loose matcher also catches.
    expect(screen.getAllByText('AI-generated')).toHaveLength(1);
  });

  it('still marks a plain answer', () => {
    renderWith([HUMAN_MESSAGE, answer]);
    expect(screen.getAllByText('AI-generated')).toHaveLength(1);
  });
});

describe('ChatMessagesView — delegation intent', () => {
  it('renders the text the agent wrote above its subagent boxes', () => {
    const store = makeStore();
    const delegating = {
      type: 'ai',
      id: 'msg-ai-1',
      content: 'Checking GitLab with investigator for your open merge requests.',
      tool_calls: [
        { id: 'tc-1', name: 'task', args: { subagent_type: 'investigator', description: 'find MRs' } },
        { id: 'tc-2', name: 'task', args: { subagent_type: 'workspace', description: 'find issues' } },
      ],
    } as unknown as Message;

    render(
      <MemoryRouter>
        <Provider store={store}>
          <ChatMessagesView {...makeBaseProps({ messages: [HUMAN_MESSAGE, delegating] })} />
        </Provider>
      </MemoryRouter>,
    );

    const intent = screen.getByTestId('delegation-intent');
    expect(intent).toHaveTextContent('Checking GitLab with investigator');
  });

  it('renders no intent block when the agent delegated without saying anything', () => {
    const store = makeStore();
    const silent = {
      type: 'ai',
      id: 'msg-ai-2',
      content: '',
      tool_calls: [{ id: 'tc-3', name: 'task', args: { subagent_type: 'investigator' } }],
    } as unknown as Message;

    render(
      <MemoryRouter>
        <Provider store={store}>
          <ChatMessagesView {...makeBaseProps({ messages: [HUMAN_MESSAGE, silent] })} />
        </Provider>
      </MemoryRouter>,
    );

    expect(screen.queryByTestId('delegation-intent')).not.toBeInTheDocument();
  });
});

describe('ChatMessagesView — unbacked sentences', () => {
  const AI_MESSAGE = {
    type: 'ai',
    id: 'msg-ai-1',
    content: 'Rates were reviewed. The fee rose to 750.',
    provenance: {
      answer_notes: {
        claims: [{ text: 'The fee rose to 750.', supported: false, contradicted: false }],
      },
    },
  } as unknown as Message;

  it('marks the sentence inside the answer', () => {
    const store = makeStore();
    render(
      <MemoryRouter>
        <Provider store={store}>
          <ChatMessagesView {...makeBaseProps({ messages: [HUMAN_MESSAGE, AI_MESSAGE] })} />
        </Provider>
      </MemoryRouter>,
    );

    const marked = screen
      .getAllByText('The fee rose to 750.')
      .find((node) => node.tagName === 'MARK');
    expect(marked).toBeDefined();
  });

  it('leaves the answer unmarked when nothing was flagged', () => {
    const store = makeStore();
    const { container } = render(
      <MemoryRouter>
        <Provider store={store}>
          <ChatMessagesView
            {...makeBaseProps({
              messages: [HUMAN_MESSAGE, { ...AI_MESSAGE, provenance: undefined }],
            })}
          />
        </Provider>
      </MemoryRouter>,
    );

    expect(container.querySelector('mark')).toBeNull();
  });
});

describe('ChatMessagesView — stall notice', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  function renderWith(props: Record<string, unknown>) {
    const store = makeStore();
    return render(
      <MemoryRouter>
        <Provider store={store}>
          <ChatMessagesView {...makeBaseProps({ isLoading: true, ...props })} />
        </Provider>
      </MemoryRouter>,
    );
  }

  it('names the tool that is taking its time instead', () => {
    renderWith({
      toolCalls: [
        { id: '1', tool: 'curator', state: 'running', startedAt: 0, ms: 0, writes: false },
      ],
    });
    act(() => { vi.advanceTimersByTime(35000); });
    expect(screen.getByText(/curator is taking longer than expected/)).toBeInTheDocument();
    expect(screen.queryByText(/Nothing has happened/)).not.toBeInTheDocument();
  });

  it('goes back to saying nothing happened once the tool returns', () => {
    renderWith({
      toolCalls: [
        { id: '1', tool: 'curator', state: 'done', startedAt: 0, ms: 10, writes: false },
      ],
    });
    act(() => { vi.advanceTimersByTime(35000); });
    expect(screen.getByText(/Nothing has happened/)).toBeInTheDocument();
  });

  it('says nothing has happened once a run goes quiet', () => {
    renderWith({});
    act(() => { vi.advanceTimersByTime(35000); });
    expect(screen.getByText(/Nothing has happened/)).toBeInTheDocument();
  });

  it('stays quiet while a delegated step is working through its own steps', () => {
    const store = makeStore();
    const progress = (count: number) => ({
      sub: {
        ns: 'sub',
        steps: Array.from({ length: count }, (_, i) => ({ label: `step ${i}` })),
        startedAt: 0,
      },
    });
    const { rerender } = render(
      <MemoryRouter>
        <Provider store={store}>
          <ChatMessagesView
            {...makeBaseProps({ isLoading: true, subagentProgress: progress(1) })}
          />
        </Provider>
      </MemoryRouter>,
    );
    act(() => { vi.advanceTimersByTime(25000); });

    rerender(
      <MemoryRouter>
        <Provider store={makeStore()}>
          <ChatMessagesView
            {...makeBaseProps({ isLoading: true, subagentProgress: progress(2) })}
          />
        </Provider>
      </MemoryRouter>,
    );
    act(() => { vi.advanceTimersByTime(25000); });

    expect(screen.queryByText(/Nothing has happened/)).not.toBeInTheDocument();
  });

  it('stays quiet while a delegated step is still reporting', () => {
    const { rerender } = renderWith({ liveActivityEvents: [{ id: 'a1' }] });
    act(() => { vi.advanceTimersByTime(25000); });

    const store = makeStore();
    rerender(
      <MemoryRouter>
        <Provider store={store}>
          <ChatMessagesView
            {...makeBaseProps({
              isLoading: true,
              liveActivityEvents: [{ id: 'a1' }, { id: 'a2' }],
            })}
          />
        </Provider>
      </MemoryRouter>,
    );
    act(() => { vi.advanceTimersByTime(25000); });

    expect(screen.queryByText(/Nothing has happened/)).not.toBeInTheDocument();
  });
});

describe('ChatMessagesView — how long the answer took', () => {
  const AI = {
    type: 'ai',
    id: 'msg-ai-timing',
    content: 'Here is the answer.',
  } as unknown as Message;

  function show(timing: Record<string, number>) {
    const store = makeStore();
    return render(
      <MemoryRouter>
        <Provider store={store}>
          <ChatMessagesView
            {...makeBaseProps({
              messages: [HUMAN_MESSAGE, AI],
              lastResponseTiming: timing,
            })}
          />
        </Provider>
      </MemoryRouter>,
    );
  }

  it('can be read by someone not looking at the screen', () => {
    show({ totalDurationMs: 97900, timeToFirstTokenMs: 6245 });
    expect(screen.getByRole('note', { name: /took/i })).toBeInTheDocument();
  });

  it('says the wait in words rather than punctuation', () => {
    show({ totalDurationMs: 97900, timeToFirstTokenMs: 6245 });
    const note = screen.getByRole('note', { name: /took/i });
    expect(note).toHaveAccessibleName(/97.9 seconds/i);
    expect(note).toHaveAccessibleName(/6245 milliseconds/i);
  });

  it('leaves out the first token when it was never measured', () => {
    show({ totalDurationMs: 2000 });
    const note = screen.getByRole('note', { name: /took/i });
    expect(note).not.toHaveAccessibleName(/first/i);
  });
});


describe('ChatMessagesView — where a conversation was shortened', () => {
  const SUMMARY = {
    type: 'human',
    content: 'Here is a summary of the conversation to date:\n\nThey asked about the fee.',
    id: 'msg-summary',
  } as unknown as Message;

  const show = (messages: Message[]) =>
    render(
      <MemoryRouter>
        <Provider store={makeStore()}>
          <ChatMessagesView {...makeBaseProps({ messages })} />
        </Provider>
      </MemoryRouter>,
    );

  it('marks the point the earlier turns were summarised away', () => {
    show([SUMMARY]);
    expect(screen.getByText(/earlier turns were summarised/i)).toBeInTheDocument();
  });

  it('does not show the summary as something the person said', () => {
    show([SUMMARY]);
    expect(
      screen.queryByText(/Here is a summary of the conversation to date/i),
    ).not.toBeInTheDocument();
  });

  it('leaves an ordinary question alone', () => {
    show([HUMAN_MESSAGE]);
    expect(screen.getByText('Hello agent')).toBeInTheDocument();
    expect(screen.queryByText(/earlier turns were summarised/i)).not.toBeInTheDocument();
  });
});
