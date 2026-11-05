import { describe, expect, it } from 'vitest';

import { emptyListReason } from './empty-list-reason';

describe('emptyListReason', () => {
  it('says there are none yet when the person has never had one', () => {
    expect(emptyListReason({ total: 0, searching: false })).toBe('noChatsYet');
  });

  it('says none are unassigned when they all sit in projects', () => {
    expect(emptyListReason({ total: 5, searching: false })).toBe('noUnassignedChats');
  });

  it('says the search matched nothing when they are searching', () => {
    // Otherwise a search that misses reads as "you have no
    // conversations", which is the opposite of true.
    expect(emptyListReason({ total: 5, searching: true })).toBe('noSearchMatches');
  });

  it('still blames the search when they have none at all', () => {
    // They typed something; that is what they are asking about.
    expect(emptyListReason({ total: 0, searching: true })).toBe('noSearchMatches');
  });

  it('treats a blank search as not searching', () => {
    expect(emptyListReason({ total: 5, searching: false })).toBe('noUnassignedChats');
  });
});
