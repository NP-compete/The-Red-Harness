import { buildAppPath } from '../lib/app-paths';

/**
 * Rooms several people share with the agent (E33).
 *
 * Everything here goes through the agent's own surface, so the
 * rules that matter are enforced where they are decided rather
 * than here: membership is a directory group asked on every
 * request, one run at a time per room, and approval bound to
 * whoever started the run. A screen cannot grant itself any of
 * that by calling a different endpoint.
 *
 * `null` on anything other than a clean answer, as the other
 * services here do. An empty room and a room that failed to load
 * are different facts, and drawing the second as the first is how
 * somebody concludes a conversation was lost.
 */

export interface Space {
  space_id: string;
  name: string;
  group_cn: string;
  created_by: string;
  created_at: string | null;
  always_on: boolean;
}

export interface SpaceMessage {
  seq: number;
  id: string;
  space_id: string;
  author: string;
  body: string;
  reply_to: string | null;
  pinned: boolean;
  pinned_by: string | null;
  created_at: string;
  reactions: Record<string, string[]>;
}

export interface Timeline {
  messages: SpaceMessage[];
  /** The cursor to resume from. A sequence, never a clock. */
  next_seq: number;
}

export interface ActiveRun {
  run_id: string | null;
  triggered_by: string | null;
  at: string | null;
}

export interface SpendRow {
  person: string;
  amount: string;
  runs: number;
}

export interface SpaceSpend {
  space_id: string;
  month: string;
  currency: string;
  rate_card_version: string;
  rows: SpendRow[];
  total: string;
  billing: string;
}

export interface Addressing {
  addressed: boolean;
  reason: string;
  handle: string;
}

async function ask<T>(path: string, init?: RequestInit): Promise<T | null> {
  try {
    const response = await fetch(buildAppPath(`/api/proxy/agent/${path}`), {
      credentials: 'include',
      ...init,
      headers: init?.body ? { 'Content-Type': 'application/json' } : undefined,
    });
    if (!response.ok) return null;
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

export async function listSpaces(): Promise<Space[] | null> {
  const body = await ask<{ spaces: Space[] }>('spaces');
  return Array.isArray(body?.spaces) ? body.spaces : null;
}

export async function createSpace(
  name: string,
  groupCn: string,
): Promise<Space | null> {
  return ask<Space>('spaces', {
    method: 'POST',
    body: JSON.stringify({ name, group_cn: groupCn }),
  });
}

export async function readTimeline(
  spaceId: string,
  afterSeq = 0,
): Promise<Timeline | null> {
  const body = await ask<Timeline>(
    `spaces/${encodeURIComponent(spaceId)}/messages?after_seq=${afterSeq}`,
  );
  return Array.isArray(body?.messages) ? body : null;
}

export async function postMessage(
  spaceId: string,
  text: string,
  replyTo?: string,
): Promise<SpaceMessage | null> {
  return ask<SpaceMessage>(`spaces/${encodeURIComponent(spaceId)}/messages`, {
    method: 'POST',
    body: JSON.stringify({ body: text, reply_to: replyTo ?? null }),
  });
}

export async function react(
  spaceId: string,
  messageId: string,
  emoji: string,
): Promise<boolean> {
  const done = await ask(
    `spaces/${encodeURIComponent(spaceId)}/messages/${messageId}/reactions`,
    { method: 'POST', body: JSON.stringify({ emoji }) },
  );
  return done !== null;
}

export async function unreact(
  spaceId: string,
  messageId: string,
  emoji: string,
): Promise<boolean> {
  const done = await ask(
    `spaces/${encodeURIComponent(spaceId)}/messages/${messageId}` +
      `/reactions/${encodeURIComponent(emoji)}`,
    { method: 'DELETE' },
  );
  return done !== null;
}

export async function setPin(
  spaceId: string,
  messageId: string,
  pinned: boolean,
): Promise<boolean> {
  const done = await ask(
    `spaces/${encodeURIComponent(spaceId)}/messages/${messageId}/pin`,
    { method: 'POST', body: JSON.stringify({ pinned }) },
  );
  return done !== null;
}

export async function readPins(spaceId: string): Promise<SpaceMessage[] | null> {
  const body = await ask<{ pins: SpaceMessage[] }>(
    `spaces/${encodeURIComponent(spaceId)}/pins`,
  );
  return Array.isArray(body?.pins) ? body.pins : null;
}

export async function readActiveRun(spaceId: string): Promise<ActiveRun | null> {
  return ask<ActiveRun>(`spaces/${encodeURIComponent(spaceId)}/run`);
}

export async function setAlwaysOn(
  spaceId: string,
  alwaysOn: boolean,
): Promise<boolean> {
  const done = await ask(`spaces/${encodeURIComponent(spaceId)}`, {
    method: 'PATCH',
    body: JSON.stringify({ always_on: alwaysOn }),
  });
  return done !== null;
}

export async function wouldAnswer(
  spaceId: string,
  text: string,
): Promise<Addressing | null> {
  return ask<Addressing>(`spaces/${encodeURIComponent(spaceId)}/addressed`, {
    method: 'POST',
    body: JSON.stringify({ text }),
  });
}

/**
 * The room, pushed (E33-T2).
 *
 * The same contract as reading a page: everything after a
 * sequence the caller already holds. Reconnecting is therefore
 * the ordinary case and not a recovery path — on `end`, or on an
 * error, the caller reopens with the cursor it has and loses
 * nothing.
 *
 * Returns the close function. Callers must call it: an
 * `EventSource` left open reconnects for ever, including after
 * the component that made it is gone.
 */
export function streamTimeline(
  spaceId: string,
  afterSeq: number,
  onMessage: (message: SpaceMessage) => void,
  onEnd?: () => void,
): () => void {
  const source = new EventSource(
    buildAppPath(
      `/api/spaces/${encodeURIComponent(spaceId)}/stream?after_seq=${afterSeq}`,
    ),
    { withCredentials: true },
  );
  source.addEventListener('message', (event) => {
    try {
      onMessage(JSON.parse((event as MessageEvent).data) as SpaceMessage);
    } catch {
      // One unreadable frame is not a reason to tear down a room.
    }
  });
  source.addEventListener('end', () => {
    source.close();
    onEnd?.();
  });
  return () => source.close();
}

export interface Person {
  handle: string;
  /** `directory` or `spoke_here` — where the name came from. */
  source: string;
}

export interface People {
  people: Person[];
  agent: string;
  directory: string;
}

/**
 * Who `@` may address in this room (E41-T3).
 *
 * Assembled by the agent per request from the directory and the
 * room's own timeline, never a stored roster — so the list can be
 * shorter than the room when the directory cannot answer, which is
 * why `directory` comes back with it.
 */
export async function readPeople(spaceId: string): Promise<People | null> {
  const body = await ask<People>(`spaces/${encodeURIComponent(spaceId)}/people`);
  return Array.isArray(body?.people) ? body : null;
}

export async function readSpend(
  spaceId: string,
  month = '',
): Promise<SpaceSpend | null> {
  const query = month ? `?month=${encodeURIComponent(month)}` : '';
  const body = await ask<SpaceSpend>(
    `spaces/${encodeURIComponent(spaceId)}/spend${query}`,
  );
  return Array.isArray(body?.rows) ? body : null;
}
