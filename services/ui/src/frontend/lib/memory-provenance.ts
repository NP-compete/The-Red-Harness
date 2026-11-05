/**
 * Where a remembered fact came from, in words.
 *
 * A list of things the agent believes about somebody, with no
 * indication of where any of it came from, leaves deleting as
 * the only available response — and people delete what they
 * cannot evaluate. Knowing a fact came from a conversation
 * last Tuesday is what makes "yes, I did say that" possible.
 *
 * Says nothing rather than guessing. Entries written before
 * this was recorded have no conversation to point at, and an
 * invented one is worse than an absent one.
 */

export interface RememberedFact {
  createdAt?: string;
  threadId?: string | null;
}

export interface Provenance {
  /** Whether there is anything worth showing at all. */
  known: boolean;
  /** The day it was saved, or empty. */
  when: string;
  /** The conversation it came from, or empty. */
  threadId: string;
}

export function provenanceOf(fact: RememberedFact): Provenance {
  const threadId = typeof fact.threadId === 'string' ? fact.threadId.trim() : '';

  let when = '';
  if (typeof fact.createdAt === 'string' && fact.createdAt.trim()) {
    const at = new Date(fact.createdAt);
    // An unparseable date is not a date. Showing "Invalid Date"
    // beside a fact makes the fact look broken too.
    if (!Number.isNaN(at.getTime())) {
      when = at.toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    }
  }

  return { known: Boolean(when || threadId), when, threadId };
}
