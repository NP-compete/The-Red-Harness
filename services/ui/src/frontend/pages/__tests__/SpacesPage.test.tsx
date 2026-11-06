import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { SpacesPage } from '../SpacesPage';

/**
 * E33 in the product.
 *
 * Two of these are about what the screen must *not* do. A room
 * that failed to load drawn as a room with nothing in it tells
 * somebody their conversation is gone; and a timeline refetched
 * from zero on every poll reorders under anyone whose page is
 * slower than the interval — which is the one thing E33-T2 says
 * must not happen. The second is asserted on the request the
 * screen makes, because a reordering only shows up under a race
 * a test will not reliably lose.
 */

const SPACE = {
  space_id: 's-1',
  name: 'Billing migration',
  group_cn: 'cn=billing',
  created_by: 'ada',
  created_at: null,
  always_on: false,
};

const MESSAGE = {
  seq: 7,
  id: 'm-1',
  space_id: 's-1',
  author: 'ada',
  body: 'the invoice job failed',
  reply_to: null,
  pinned: false,
  pinned_by: null,
  created_at: '2026-10-30T00:00:00Z',
  reactions: {},
};


/** A stand-in for the browser's EventSource, which jsdom has not. */
class FakeStream {
  static made: FakeStream[] = [];
  listeners: Record<string, ((event: unknown) => void)[]> = {};
  closed = false;
  constructor(public url: string) {
    FakeStream.made.push(this);
  }
  addEventListener(name: string, fn: (event: unknown) => void) {
    (this.listeners[name] ??= []).push(fn);
  }
  close() {
    this.closed = true;
  }
  push(message: unknown) {
    act(() => {
      for (const fn of this.listeners.message ?? []) {
        fn({ data: JSON.stringify(message) });
      }
    });
  }
  end() {
    act(() => {
      for (const fn of this.listeners.end ?? []) fn({});
    });
  }
}

const streams = FakeStream.made;

const asked: string[] = [];

function serve(route: (path: string) => unknown | undefined) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      asked.push(url);
      const body = route(url);
      if (body === undefined) return { ok: false, status: 404, json: async () => ({}) };
      return { ok: true, status: 200, json: async () => body };
    }),
  );
}

function routes(path: string) {
  if (path.endsWith('/agent/spaces')) return { spaces: [SPACE] };
  if (path.includes('/messages?after_seq=0')) {
    return { messages: [MESSAGE], next_seq: 7 };
  }
  if (path.includes('/messages?after_seq=')) return { messages: [], next_seq: 7 };
  if (path.endsWith('/run')) return { run_id: null, triggered_by: null, at: null };
  if (path.endsWith('/pins')) return { pins: [] };
  if (path.includes('/spend')) {
    return {
      space_id: 's-1',
      month: '2026-10',
      currency: 'USD',
      rate_card_version: 'v1',
      rows: [{ person: 'ada', amount: '1.10', runs: 1 }],
      total: '1.10',
      billing: 'a space is a place, not a payer',
    };
  }
  return undefined;
}

describe('SpacesPage', () => {
  beforeEach(() => {
    asked.length = 0;
    streams.length = 0;
    vi.useRealTimers();
    vi.stubGlobal('EventSource', FakeStream);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('lists the rooms this person is in, with the group that decides it', async () => {
    serve(routes);
    render(<SpacesPage />);
    expect(await screen.findByText('Billing migration')).toBeInTheDocument();
    expect(screen.getByText('cn=billing')).toBeInTheDocument();
  });

  it('says a room that failed to load is not a room with nothing in it', async () => {
    serve(() => undefined);
    render(<SpacesPage />);
    expect(
      await screen.findByText(/not the same as having none/i),
    ).toBeInTheDocument();
  });

  it('opens a stream from the sequence it holds, rather than refetching', async () => {
    serve(routes);
    render(<SpacesPage />);
    await userEvent.click(await screen.findByText('Billing migration'));

    await waitFor(() => expect(streams.length).toBe(1));
    expect(streams[0].url).toContain('/api/spaces/s-1/stream?after_seq=0');

    streams[0].push(MESSAGE);
    expect(await screen.findByText('the invoice job failed')).toBeInTheDocument();
  });

  it('shows a message resent after a reconnect once, not twice', async () => {
    serve(routes);
    render(<SpacesPage />);
    await userEvent.click(await screen.findByText('Billing migration'));
    await waitFor(() => expect(streams.length).toBe(1));

    streams[0].push(MESSAGE);
    await screen.findByText('the invoice job failed');
    streams[0].push(MESSAGE);

    await waitFor(() =>
      expect(screen.getAllByText('the invoice job failed')).toHaveLength(1),
    );
  });

  it('reopens from the cursor when the agent ends the stream', async () => {
    serve(routes);
    render(<SpacesPage />);
    await userEvent.click(await screen.findByText('Billing migration'));
    await waitFor(() => expect(streams.length).toBe(1));

    streams[0].push(MESSAGE);
    await screen.findByText('the invoice job failed');
    streams[0].end();

    await waitFor(() => expect(streams.length).toBe(2));
    // Not from zero: the room would arrive again behind what is
    // already on screen.
    expect(streams[1].url).toContain('after_seq=7');
  });

  it('shows the room spend per person, and says the room is not a payer', async () => {
    serve(routes);
    render(<SpacesPage />);
    await userEvent.click(await screen.findByText('Billing migration'));
    expect(await screen.findByText(/1.10 USD in this room/)).toBeInTheDocument();
    expect(screen.getByText(/not a payer/)).toBeInTheDocument();
  });

  it('shows who is mid-run, so two people do not act at once', async () => {
    serve((path) =>
      path.endsWith('/run')
        ? { run_id: 'r-1', triggered_by: 'bo', at: null }
        : routes(path),
    );
    render(<SpacesPage />);
    await userEvent.click(await screen.findByText('Billing migration'));
    expect(await screen.findByText(/bo has a run going here/)).toBeInTheDocument();
  });
});

describe('SpacesPage mentions (E41-T3)', () => {
  beforeEach(() => {
    asked.length = 0;
    streams.length = 0;
    vi.stubGlobal('EventSource', FakeStream);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  function withPeople(path: string) {
    if (path.endsWith('/people')) {
      return {
        people: [
          { handle: 'ada', source: 'directory' },
          { handle: 'bo', source: 'spoke_here' },
        ],
        agent: 'orchestrator',
        directory: 'asked',
      };
    }
    return routes(path);
  }

  async function openRoomAndType(text: string, route = withPeople) {
    serve(route);
    render(<SpacesPage />);
    await userEvent.click(await screen.findByText('Billing migration'));
    await userEvent.type(await screen.findByLabelText('Message'), text);
  }

  it('offers the room and the agent once an @ is typed', async () => {
    await openRoomAndType('@');
    expect(await screen.findByText(/@orchestrator/)).toBeInTheDocument();
    expect(screen.getByText('@ada')).toBeInTheDocument();
    expect(screen.getByText('@bo')).toBeInTheDocument();
  });

  it('offers nobody until somebody types an @', async () => {
    await openRoomAndType('hello');
    expect(screen.queryByText('@ada')).not.toBeInTheDocument();
  });

  it('narrows as the handle is typed', async () => {
    await openRoomAndType('@a');
    expect(await screen.findByText('@ada')).toBeInTheDocument();
    expect(screen.queryByText('@bo')).not.toBeInTheDocument();
  });

  it('says when the list may be shorter than the room', async () => {
    /** A picker listing two of eight looks like a complete list. */
    await openRoomAndType('@', (path) =>
      path.endsWith('/people')
        ? { people: [{ handle: 'bo', source: 'spoke_here' }], agent: 'a', directory: 'not configured' }
        : routes(path),
    );
    expect(await screen.findByText(/may be shorter than the room/)).toBeInTheDocument();
  });
});
