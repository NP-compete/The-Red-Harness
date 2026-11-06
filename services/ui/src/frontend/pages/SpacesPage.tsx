import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

import {
  createSpace,
  listSpaces,
  postMessage,
  react,
  readActiveRun,
  readPeople,
  readPins,
  readSpend,
  readTimeline,
  setAlwaysOn,
  setPin,
  streamTimeline,
  unreact,
  wouldAnswer,
  type ActiveRun,
  type People,
  type Space,
  type SpaceMessage,
  type SpaceSpend,
} from '../services/spaces-api';

const THUMB = '👍';
const POLL_MS = 3000;

/**
 * A room several people share with the agent (E33).
 *
 * **The timeline is resumed, not refetched.** Polling asks for
 * everything after the last sequence this screen holds, so a tab
 * left open for an hour costs the same as one left open for a
 * second, and messages cannot reorder under it — the order is the
 * database's sequence and this screen only appends.
 *
 * **Presence is shown before it is needed.** Somebody else's run
 * in progress is drawn at the top of the room, because two people
 * independently approving the same action is a double write
 * nobody intended and seeing it is the first defence.
 *
 * **Whether the agent will answer is shown before anybody sends.**
 * A channel where the agent silently ignores you is one people
 * stop using; the composer says `tagged`, `always_on` or
 * `not_addressed` as it is typed.
 *
 * **Spend is per person and per room.** Both, because either
 * alone is unusable — and the room is not a payer, which the
 * payload says in words rather than leaving to be inferred.
 */
export function SpacesPage() {
  const { t } = useTranslation();
  const [spaces, setSpaces] = useState<Space[] | null>(null);
  const [current, setCurrent] = useState<Space | null>(null);
  const [messages, setMessages] = useState<SpaceMessage[]>([]);
  const [pins, setPins] = useState<SpaceMessage[]>([]);
  const [running, setRunning] = useState<ActiveRun | null>(null);
  const [spend, setSpend] = useState<SpaceSpend | null>(null);
  const [draft, setDraft] = useState('');
  const [verdict, setVerdict] = useState('');
  const [note, setNote] = useState('');
  const [newName, setNewName] = useState('');
  const [newGroup, setNewGroup] = useState('');
  const [reopen, setReopen] = useState(0);
  const [people, setPeople] = useState<People | null>(null);
  const cursor = useRef(0);

  const load = useCallback(async () => {
    const found = await listSpaces();
    setSpaces(found);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const open = useCallback(async (space: Space) => {
    // A new room starts from nothing: keeping the previous room's
    // cursor would skip everything in this one below that sequence.
    cursor.current = 0;
    setCurrent(space);
    setMessages([]);
    setNote('');
    setVerdict('');
  }, []);

  /** Presence and pins, which are state rather than a sequence. */
  const refreshAround = useCallback(async () => {
    if (!current) return;
    setRunning(await readActiveRun(current.space_id));
    setPins((await readPins(current.space_id)) ?? []);
  }, [current]);

  /** The whole room again, without disturbing the stream's cursor. */
  const reread = useCallback(async () => {
    if (!current) return;
    const page = await readTimeline(current.space_id, 0);
    if (page) setMessages(page.messages);
    await refreshAround();
  }, [current, refreshAround]);

  useEffect(() => {
    if (!current) return;
    void refreshAround();
    const timer = setInterval(() => void refreshAround(), POLL_MS);
    return () => clearInterval(timer);
  }, [current, refreshAround]);

  // Messages arrive pushed, from the sequence this screen holds.
  // Reopening after `end` is ordinary rather than a recovery path:
  // a stream and a page ask for the same thing, so the cursor is
  // all the state a reconnect needs.
  useEffect(() => {
    if (!current) return;
    const close = streamTimeline(
      current.space_id,
      cursor.current,
      (message) => {
        cursor.current = Math.max(cursor.current, message.seq);
        setMessages((previous) =>
          // The same sequence twice is the same message — a
          // reopened stream can resend the frame it was cut off
          // during, and a room that shows it twice looks broken.
          previous.some((m) => m.seq === message.seq)
            ? previous
            : [...previous, message],
        );
      },
      () => setReopen((n) => n + 1),
    );
    return close;
  }, [current, reopen]);

  useEffect(() => {
    if (!current) return;
    void readSpend(current.space_id).then(setSpend);
    // Reread after each message: somebody who has just spoken is
    // somebody `@` should offer, and the agent assembles the list
    // from the timeline when the directory cannot answer.
    void readPeople(current.space_id).then(setPeople);
  }, [current, messages.length]);

  useEffect(() => {
    if (!current || !draft.trim()) {
      setVerdict('');
      return;
    }
    let live = true;
    const timer = setTimeout(async () => {
      const answer = await wouldAnswer(current.space_id, draft);
      if (live && answer) setVerdict(answer.reason);
    }, 400);
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [current, draft]);

  // The word being typed, when it is a mention. Derived rather
  // than tracked: a separate "are we mentioning" flag goes stale
  // the moment somebody edits the middle of a line.
  const mention = /(?:^|\s)@([\w.-]*)$/.exec(draft)?.[1];
  const candidates =
    mention === undefined || !people
      ? []
      : [people.agent, ...people.people.map((p) => p.handle)]
          .filter((handle, index, all) => all.indexOf(handle) === index)
          .filter((handle) => handle.toLowerCase().startsWith(mention.toLowerCase()))
          .slice(0, 6);

  const complete = useCallback(
    (handle: string) => {
      setDraft((text) => text.replace(/@[\w.-]*$/, `@${handle} `));
    },
    [],
  );

  const send = useCallback(async () => {
    if (!current || !draft.trim()) return;
    const sent = await postMessage(current.space_id, draft);
    if (!sent) {
      setNote(t('spaces.notSent'));
      return;
    }
    setDraft('');
    // Not appended here: the stream delivers it, and adding it
    // locally too is how a sender sees their own message twice.
  }, [current, draft, t]);

  const toggleReaction = useCallback(
    async (message: SpaceMessage) => {
      if (!current) return;
      const mine = (message.reactions[THUMB] ?? []).length > 0;
      if (mine) {
        await unreact(current.space_id, message.id, THUMB);
      } else {
        await react(current.space_id, message.id, THUMB);
      }
      // Reactions are not sequenced, so there is nothing to
      // resume from — the room is reread, and the stream's cursor
      // is left where it is.
      await reread();
    },
    [current, reread],
  );

  const togglePin = useCallback(
    async (message: SpaceMessage) => {
      if (!current) return;
      await setPin(current.space_id, message.id, !message.pinned);
      await reread();
    },
    [current, reread],
  );

  const toggleAlwaysOn = useCallback(async () => {
    if (!current) return;
    const next = !current.always_on;
    if (await setAlwaysOn(current.space_id, next)) {
      setCurrent({ ...current, always_on: next });
      await load();
    }
  }, [current, load]);

  const make = useCallback(async () => {
    if (!newName.trim() || !newGroup.trim()) return;
    const made = await createSpace(newName, newGroup);
    if (!made) {
      setNote(t('spaces.notCreated'));
      return;
    }
    setNewName('');
    setNewGroup('');
    await load();
    await open(made);
  }, [newName, newGroup, load, open, t]);

  return (
    <div className="flex h-full min-h-0 gap-4 p-4">
      <aside className="w-72 shrink-0 overflow-y-auto">
        <h1 className="mb-1 text-base font-semibold">{t('spaces.heading')}</h1>
        <p className="mb-3 text-xs text-muted-foreground">
          {t('spaces.membership')}
        </p>

        {spaces === null ? (
          <p className="text-sm text-muted-foreground">{t('spaces.notLoaded')}</p>
        ) : spaces.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t('spaces.none')}</p>
        ) : (
          <ul className="mb-4 space-y-1">
            {spaces.map((space) => (
              <li key={space.space_id}>
                <button
                  type="button"
                  onClick={() => void open(space)}
                  className={`w-full rounded px-2 py-1 text-left text-sm ${
                    current?.space_id === space.space_id
                      ? 'bg-secondary'
                      : 'hover:bg-secondary/50'
                  }`}
                >
                  <span className="block truncate">{space.name}</span>
                  <span className="block truncate font-mono text-[11px] text-muted-foreground">
                    {space.group_cn}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}

        <div className="space-y-1 border-t border-border pt-3">
          <input
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder={t('spaces.namePlaceholder')}
            aria-label={t('spaces.name')}
            className="w-full rounded border border-border bg-card px-2 py-1 text-sm"
          />
          <input
            value={newGroup}
            onChange={(e) => setNewGroup(e.target.value)}
            placeholder={t('spaces.groupPlaceholder')}
            aria-label={t('spaces.group')}
            className="w-full rounded border border-border bg-card px-2 py-1 text-sm"
          />
          <button
            type="button"
            onClick={() => void make()}
            className="w-full rounded border border-border px-2 py-1 text-sm"
          >
            {t('spaces.create')}
          </button>
          <p className="text-[11px] text-muted-foreground">
            {t('spaces.groupExplains')}
          </p>
        </div>
      </aside>

      {current === null ? (
        <section className="flex-1 text-sm text-muted-foreground">
          {t('spaces.pickOne')}
        </section>
      ) : (
        <section className="flex min-w-0 flex-1 flex-col">
          <header className="mb-2 flex items-center gap-3">
            <h2 className="text-base font-semibold">{current.name}</h2>
            <label className="flex items-center gap-1 text-xs">
              <input
                type="checkbox"
                checked={current.always_on}
                onChange={() => void toggleAlwaysOn()}
                aria-label={t('spaces.alwaysOn')}
              />
              {t('spaces.alwaysOn')}
            </label>
            <span className="text-xs text-muted-foreground">
              {t('spaces.alwaysOnExplains')}
            </span>
          </header>

          {running?.run_id && (
            <p className="mb-2 rounded border border-border bg-secondary/40 px-2 py-1 text-xs">
              {t('spaces.someoneRunning', { who: running.triggered_by })}
            </p>
          )}

          {pins.length > 0 && (
            <ul className="mb-2 space-y-0.5 text-xs">
              {pins.map((p) => (
                <li key={`pin-${p.id}`} className="truncate">
                  📌 {p.body}
                </li>
              ))}
            </ul>
          )}

          <ol className="mb-2 min-h-0 flex-1 space-y-2 overflow-y-auto">
            {messages.map((message) => (
              <li key={message.id} className="text-sm">
                <span className="font-medium">{message.author}</span>{' '}
                <span className="text-[11px] text-muted-foreground">
                  #{message.seq}
                </span>
                <p className="whitespace-pre-wrap">{message.body}</p>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <button
                    type="button"
                    onClick={() => void toggleReaction(message)}
                    aria-label={t('spaces.react')}
                  >
                    {THUMB} {(message.reactions[THUMB] ?? []).length || ''}
                  </button>
                  <button
                    type="button"
                    onClick={() => void togglePin(message)}
                    aria-label={t('spaces.pin')}
                  >
                    {message.pinned ? t('spaces.unpin') : t('spaces.pin')}
                  </button>
                </div>
              </li>
            ))}
          </ol>

          {candidates.length > 0 && (
            <ul className="mb-1 flex flex-wrap gap-1">
              {candidates.map((handle) => (
                <li key={handle}>
                  <button
                    type="button"
                    onClick={() => complete(handle)}
                    className="rounded border border-border px-2 py-0.5 text-xs"
                  >
                    @{handle}
                    {handle === people?.agent && (
                      <span className="ml-1 text-muted-foreground">
                        {t('spaces.theAgent')}
                      </span>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          )}
          {people && people.directory !== 'asked' && mention !== undefined && (
            <p className="mb-1 text-xs text-muted-foreground">
              {t('spaces.peoplePartial')}
            </p>
          )}

          {note && <p className="mb-1 text-xs text-destructive">{note}</p>}

          <div className="flex items-center gap-2">
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') void send();
              }}
              placeholder={t('spaces.sayPlaceholder')}
              aria-label={t('spaces.say')}
              className="flex-1 rounded border border-border bg-card px-2 py-1 text-sm"
            />
            <button
              type="button"
              onClick={() => void send()}
              className="rounded border border-border px-3 py-1 text-sm"
            >
              {t('spaces.send')}
            </button>
          </div>
          {verdict && (
            <p className="mt-1 text-xs text-muted-foreground">
              {t(`spaces.verdict.${verdict}`)}
            </p>
          )}

          {spend && (
            <div className="mt-3 border-t border-border pt-2 text-xs">
              <p>
                {t('spaces.spend', {
                  total: spend.total,
                  currency: spend.currency,
                  month: spend.month,
                })}
              </p>
              <ul className="text-muted-foreground">
                {spend.rows.map((row) => (
                  <li key={row.person}>
                    {row.person} — {row.amount} ({row.runs})
                  </li>
                ))}
              </ul>
              <p className="text-muted-foreground">{spend.billing}</p>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
