import { describe, it, expect } from 'vitest';
import { chatActivity, activityByChat } from './chat-activity';
import type { StreamingState } from '../redux/slices/chats';

const state = (over: Partial<StreamingState>): StreamingState =>
  ({ isLoading: false, isThinking: false, pendingInterrupt: null, ...over }) as StreamingState;

describe('chatActivity', () => {
  it('reports a streaming turn as running', () => {
    expect(chatActivity(state({ isLoading: true }))).toBe('running');
    expect(chatActivity(state({ isThinking: true }))).toBe('running');
  });

  it('puts a blocked turn ahead of a running one', () => {
    // A turn paused on an approval is still technically loading. What
    // the reader needs to know is that it is waiting on them.
    const blocked = state({ isLoading: true, pendingInterrupt: { value: 'x' } as never });
    expect(chatActivity(blocked)).toBe('needs-input');
  });

  it('treats a finished or unknown chat as idle', () => {
    expect(chatActivity(state({}))).toBe('idle');
    expect(chatActivity(undefined)).toBe('idle');
  });
});

describe('activityByChat', () => {
  it('lists only the chats that are doing something', () => {
    const result = activityByChat({
      a: state({ isLoading: true }),
      b: state({ pendingInterrupt: { value: 'x' } as never }),
      c: state({}),
    });

    expect(result).toEqual({ a: 'running', b: 'needs-input' });
  });

  it('survives an empty store', () => {
    expect(activityByChat({})).toEqual({});
    expect(activityByChat(undefined as never)).toEqual({});
  });
});

const askedToConnect = {
  id: 'c1',
  messages: [
    { type: 'human', content: 'how many open MRs?' },
    {
      type: 'ai',
      content: 'GitLab is not connected. Connect it in Settings → Components → MCP, then ask again.',
      additional_kwargs: { auth_required: [{ mcp_name: 'gitlab', reason: 'not_connected' }] },
    },
  ],
};

const answered = {
  id: 'c2',
  messages: [
    { type: 'human', content: 'hi' },
    { type: 'ai', content: 'Hello.' },
  ],
};

describe('a turn that stopped for an unconnected integration', () => {
  it('needs input, it did not complete', () => {
    // It used to pause on an interrupt, which landed here via
    // `pendingInterrupt`. The turn ends cleanly now, so without the
    // message check it files beside turns that actually answered.
    expect(chatActivity(state({}), askedToConnect)).toBe('needs-input');
  });

  it('is still needs-input with no streaming state at all', () => {
    // A chat restored from history has none, and its unanswered turn
    // is exactly the one the reader has forgotten about.
    expect(chatActivity(undefined, askedToConnect)).toBe('needs-input');
  });

  it('reads the marker when the model quoted it instead of stamping it', () => {
    const quoted = {
      id: 'c3',
      messages: [
        {
          type: 'ai',
          content: '[AUTH_REQUIRED mcp=dataverse reason=not_connected] not connected.',
        },
      ],
    };
    expect(chatActivity(state({}), quoted)).toBe('needs-input');
  });
});

describe('everything else is unchanged', () => {
  it('an answered turn is idle', () => {
    expect(chatActivity(state({}), answered)).toBe('idle');
  });

  it('a running turn is running', () => {
    expect(chatActivity(state({ isLoading: true }), answered)).toBe('running');
  });

  it('a running turn outranks an older unanswered one', () => {
    // Asked again after connecting: the new turn is what matters.
    expect(chatActivity(state({ isLoading: true }), askedToConnect)).toBe('running');
  });

  it('an interrupt still wins', () => {
    const s = state({ pendingInterrupt: { value: 'approve?' } as never });
    expect(chatActivity(s, answered)).toBe('needs-input');
  });
});

describe('activityByChat', () => {
  it('buckets a chat with no streaming state', () => {
    expect(activityByChat({}, [askedToConnect, answered])).toEqual({ c1: 'needs-input' });
  });

  it('omits idle chats so the sidebar falls back to Completed', () => {
    expect(activityByChat({ c2: state({}) }, [answered])).toEqual({});
  });
});

describe('a conversation the browser is not watching', () => {
  it('counts one paused on the server as needing you', () => {
    expect(chatActivity(undefined, { id: 'c1', serverStatus: 'interrupted' })).toBe(
      'needs-input',
    );
  });

  it('counts one whose run died as failed', () => {
    expect(chatActivity(undefined, { id: 'c1', serverStatus: 'error' })).toBe('failed');
  });

  it('counts a finished one as idle', () => {
    expect(chatActivity(undefined, { id: 'c1', serverStatus: 'success' })).toBe('idle');
  });

  it('says nothing new about one the server has no opinion on', () => {
    expect(chatActivity(undefined, { id: 'c1' })).toBe('idle');
  });

  it('lets what the browser can see outrank the server', () => {
    // The thread list is fetched once; a run that started since is
    // still recorded as whatever it was then.
    expect(
      chatActivity(state({ isLoading: true }), { id: 'c1', serverStatus: 'success' }),
    ).toBe('running');
  });

  it('carries the server status through the whole list', () => {
    const found = activityByChat({}, [
      { id: 'a', serverStatus: 'interrupted' },
      { id: 'b', serverStatus: 'error' },
    ]);
    expect(found).toEqual({ a: 'needs-input', b: 'failed' });
  });

  it('counts one the agent calls busy as running', () => {
    // The agent reports `busy` for a thread with a run in flight;
    // filing it as finished hides work that is still happening.
    expect(chatActivity(undefined, { id: 'c1', serverStatus: 'busy' })).toBe('running');
  });

  it('still counts an idle one as idle', () => {
    expect(chatActivity(undefined, { id: 'c1', serverStatus: 'idle' })).toBe('idle');
  });

  it('does not guess about a status it has never seen', () => {
    expect(chatActivity(undefined, { id: 'c1', serverStatus: 'quiescent' })).toBe('idle');
  });
});
