const KEY = 'agent.drafts';

/** Long enough to survive a weekend away from the machine. */
export const KEEP_FOR_DAYS = 7;

const KEEP_FOR_MS = KEEP_FOR_DAYS * 24 * 60 * 60 * 1000;

export interface Draft {
  text: string;
  savedAt: number;
  ageSeconds: number;
}

type Stored = Record<string, { text: string; savedAt: number }>;

function readAll(): Stored {
  try {
    const raw = localStorage.getItem(KEY);
    const parsed = raw ? JSON.parse(raw) : {};
    return parsed && typeof parsed === 'object' ? (parsed as Stored) : {};
  } catch {
    // Unreadable storage is the same as no draft, and is replaced on
    // the next save rather than left to fail every read.
    return {};
  }
}

function writeAll(drafts: Stored): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(drafts));
  } catch {
    // A draft that cannot be kept is not worth failing a keystroke over.
  }
}

export const draftStorage = {
  save(threadId: string, text: string): void {
    const drafts = readAll();
    if (text.trim()) {
      drafts[threadId] = { text, savedAt: Date.now() };
    } else {
      delete drafts[threadId];
    }
    writeAll(drafts);
  },

  load(threadId: string): Draft | null {
    const stored = readAll()[threadId];
    if (!stored || typeof stored.text !== 'string' || !stored.text.trim()) {
      return null;
    }

    const age = Date.now() - stored.savedAt;
    if (age > KEEP_FOR_MS) {
      return null;
    }

    return { text: stored.text, savedAt: stored.savedAt, ageSeconds: Math.floor(age / 1000) };
  },

  discard(threadId: string): void {
    const drafts = readAll();
    delete drafts[threadId];
    writeAll(drafts);
  },
};
