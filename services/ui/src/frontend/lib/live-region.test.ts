import { describe, expect, it } from 'vitest';

import { announce } from '@/lib/live-region';

const quiet = {
  streaming: true,
  charactersAdded: 40,
  sinceLastAnnouncementMs: 400,
  runFinished: false,
  needsApproval: false,
  failed: false,
  lastAnnounced: '',
};

describe('announce', () => {
  it('says nothing for a small amount of new text', () => {
    expect(announce(quiet)).toBeNull();
  });

  it('says nothing twice in quick succession', () => {
    const chatty = { ...quiet, charactersAdded: 500, sinceLastAnnouncementMs: 200 };
    expect(announce(chatty)).toBeNull();
  });

  it('announces once enough has arrived', () => {
    const lots = { ...quiet, charactersAdded: 500, sinceLastAnnouncementMs: 4000 };
    expect(announce(lots)?.message).toBe('Still writing');
  });

  it('announces a finished reply', () => {
    const done = { ...quiet, streaming: false, runFinished: true };
    expect(announce(done)?.message).toBe('Reply finished');
  });

  it('announces a finished reply even straight after another announcement', () => {
    // The end of a reply is the one thing a listener must not miss.
    const done = { ...quiet, streaming: false, runFinished: true, sinceLastAnnouncementMs: 10 };
    expect(announce(done)?.message).toBe('Reply finished');
  });

  it('announces when approval is needed', () => {
    const waiting = { ...quiet, needsApproval: true };
    expect(announce(waiting)?.message).toBe('Waiting for your approval');
  });

  it('announces a failure', () => {
    const broken = { ...quiet, streaming: false, failed: true };
    expect(announce(broken)?.message).toBe('Something went wrong');
  });

  it('interrupts for something needing a person', () => {
    const waiting = { ...quiet, needsApproval: true };
    expect(announce(waiting)?.assertive).toBe(true);
  });

  it('does not interrupt for ordinary progress', () => {
    const lots = { ...quiet, charactersAdded: 500, sinceLastAnnouncementMs: 4000 };
    expect(announce(lots)?.assertive).toBe(false);
  });

  it('interrupts for a failure', () => {
    const broken = { ...quiet, streaming: false, failed: true };
    expect(announce(broken)?.assertive).toBe(true);
  });

  it('never repeats the same announcement', () => {
    const repeat = {
      ...quiet,
      charactersAdded: 500,
      sinceLastAnnouncementMs: 4000,
      lastAnnounced: 'Still writing',
    };
    expect(announce(repeat)).toBeNull();
  });

  it('never reads the reply text aloud', () => {
    // The message area is read on demand; the live region only says what changed.
    const lots = { ...quiet, charactersAdded: 5000, sinceLastAnnouncementMs: 4000 };
    expect(announce(lots)?.message).toBe('Still writing');
  });

  it('a failure outranks needing approval', () => {
    const both = { ...quiet, failed: true, needsApproval: true };
    expect(announce(both)?.message).toBe('Something went wrong');
  });

  it('a finished reply outranks still writing', () => {
    const both = { ...quiet, runFinished: true, charactersAdded: 5000, sinceLastAnnouncementMs: 4000 };
    expect(announce(both)?.message).toBe('Reply finished');
  });
});

describe('after the reply has stopped arriving', () => {
  const settled = {
    streaming: false,
    charactersAdded: 900,
    sinceLastAnnouncementMs: 9000,
    runFinished: false,
    needsApproval: false,
    failed: false,
    lastAnnounced: '',
  };

  it('does not say writing is still going on', () => {
    // Completion is announced by another region. Saying "still
    // writing" after it means the reader hears the reply is
    // finished and then that it is not.
    expect(announce(settled)).toBeNull();
  });

  it('still says so while the reply is arriving', () => {
    expect(announce({ ...settled, streaming: true })?.message).toBe('Still writing');
  });

  it('still reports a failure once the stream has stopped', () => {
    expect(announce({ ...settled, failed: true })?.message).toBe('Something went wrong');
  });

  it('still reports an approval once the stream has stopped', () => {
    expect(announce({ ...settled, needsApproval: true })?.message).toBe(
      'Waiting for your approval',
    );
  });
});
