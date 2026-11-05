import { describe, expect, it } from 'vitest';

import { presentForget } from '@/lib/forget-view';

const plan = {
  forgetting: ['units'],
  untouched: [] as string[],
  cannotUnsay: [] as string[],
  affectsOthers: [] as string[],
  foundNothing: false,
  needsConfirmation: false,
};

describe('presentForget', () => {
  it('says what it will forget', () => {
    expect(presentForget(plan).headline).toBe('Forgetting 1 thing');
  });

  it('counts several things', () => {
    expect(presentForget({ ...plan, forgetting: ['units', 'tone'] }).headline).toBe(
      'Forgetting 2 things',
    );
  });

  it('says plainly when it found nothing to forget', () => {
    const empty = { ...plan, forgetting: [], foundNothing: true };
    expect(presentForget(empty).headline).toBe('Nothing matching that is remembered');
  });

  it('warns that what was already sent cannot be taken back', () => {
    const sent = { ...plan, cannotUnsay: ['units'] };
    expect(presentForget(sent).caveat).toBe(
      'This stops future use — it cannot change messages already sent',
    );
  });

  it('adds no caveat when nothing has been sent', () => {
    expect(presentForget(plan).caveat).toBe('');
  });

  it('says when forgetting would reach other people', () => {
    const shared = { ...plan, affectsOthers: ['units'], needsConfirmation: true };
    expect(presentForget(shared).warning).toBe('1 of these is shared — it goes for everyone');
  });

  it('says when something could not be forgotten for you', () => {
    const theirs = { ...plan, forgetting: [], untouched: ['units'], foundNothing: true };
    expect(presentForget(theirs).warning).toBe('1 of these belongs to someone else and stays');
  });

  it('asks before forgetting on other people’s behalf', () => {
    const shared = { ...plan, affectsOthers: ['units'], needsConfirmation: true };
    expect(presentForget(shared).actions).toEqual(['Forget for everyone', 'Cancel']);
  });

  it('forgets your own memories without ceremony', () => {
    expect(presentForget(plan).actions).toEqual(['Forget', 'Cancel']);
  });

  it('offers nothing to do when there is nothing to forget', () => {
    const empty = { ...plan, forgetting: [], foundNothing: true };
    expect(presentForget(empty).actions).toEqual([]);
  });

  it('lists what is going so it can be checked first', () => {
    expect(presentForget({ ...plan, forgetting: ['units', 'tone'] }).items).toEqual([
      'units',
      'tone',
    ]);
  });
});
