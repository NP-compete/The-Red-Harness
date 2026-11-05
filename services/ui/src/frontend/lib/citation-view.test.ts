import { describe, expect, it } from 'vitest';

import { describeCitations } from './citation-view';

const CITED = [
  { document_id: 'corpus:hr/leave.md', title: 'leave', scope: 'agent' },
  { document_id: 'user:1', title: 'My notes', scope: 'user' },
];

describe('describeCitations', () => {
  it('lists what was cited', () => {
    expect(describeCitations(CITED)).toHaveLength(2);
  });

  it('keeps the name a reader recognises', () => {
    expect(describeCitations(CITED)?.[0].title).toBe('leave');
  });

  it('keeps the identifier so the source can be opened', () => {
    expect(describeCitations(CITED)?.[0].documentId).toBe('corpus:hr/leave.md');
  });

  describe('where a citation came from', () => {
    it('marks the curated corpus as the agent’s', () => {
      // A curated policy and a file dropped in a chat deserve
      // different trust, and a title alone cannot show that.
      expect(describeCitations(CITED)?.[0].origin).toBe('agent');
    });

    it('marks a personal document as the reader’s own', () => {
      expect(describeCitations(CITED)?.[1].origin).toBe('user');
    });

    it('treats an origin it does not recognise as unknown', () => {
      // Rather than displaying a word from the agent verbatim
      // in an interface that has not been translated for it.
      const odd = [{ document_id: 'x', title: 'x', scope: 'something' }];
      expect(describeCitations(odd)?.[0].origin).toBe('unknown');
    });
  });

  describe('an answer that cited nothing', () => {
    it('reports nothing rather than an empty list', () => {
      // An empty citation strip reads as "checked and found
      // nothing", which is not what happened.
      expect(describeCitations([])).toBe(null);
    });

    it('treats a missing field the same way', () => {
      expect(describeCitations(undefined)).toBe(null);
    });
  });

  describe('something malformed', () => {
    it('drops an entry with no identifier', () => {
      const broken = [{ title: 'no id', scope: 'agent' } as never, ...CITED];
      expect(describeCitations(broken)).toHaveLength(2);
    });

    it('is not a list at all', () => {
      expect(describeCitations('nonsense' as never)).toBe(null);
    });
  });
});
