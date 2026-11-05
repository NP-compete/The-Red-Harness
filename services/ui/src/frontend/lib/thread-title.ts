import { compactionSummary } from './compaction-marker';
export const UNTITLED = 'New conversation';

// Every placeholder the app has used for a chat nobody has named.
// Code that asks "has this been titled yet?" must recognise all of
// them, or a chat sticks on whichever one it happened to get.
const PLACEHOLDERS = new Set(
  [UNTITLED, 'New Chat', 'Chat', 'Untitled chat', ''].map((name) => name.toLowerCase()),
);

/** Whether a chat is still waiting to be named after its question. */
export function isUnnamed(title: string | undefined): boolean {
  return PLACEHOLDERS.has((title ?? '').trim().toLowerCase());
}

const MAX_LENGTH = 48;
const MAX_PREVIEW = 80;

const POLITENESS =
  /^(?:(?:hi|hello|hey|please|kindly|can you|could you|would you|i'd like you to)[\s,]+)+/i;
const EMAIL = /[^\s@]+@[^\s@]+\.[^\s@]+/;
const TOKEN = /[A-Za-z0-9]+/g;

interface Message {
  type?: string;
  role?: string;
  content?: unknown;
}

/**
 * What to call a conversation in a list.
 *
 * Taken from the question that started it, so the name stops moving
 * the moment there is an answer — titling a chat with its latest
 * message renames it under the reader every turn.
 */
export function suggestTitle(messages: Message[]): string {
  const asked = messages.find(
    (message) =>
      (message?.type === 'human' || message?.role === 'user') &&
      // A compaction leaves a summary where the oldest turns were.
      // Naming the conversation after it renames it to words nobody
      // typed, and does so only once it has run long enough to be
      // worth finding again.
      compactionSummary(message) === null,
  );
  return titleFor(textOf(asked?.content));
}

/** The same, for the one place that has the prompt before the message. */
export function titleFor(prompt: string): string {
  const text = prompt.replace(/\s+/g, ' ').trim();

  // A title shows up in the chat list, in a rename box and in what a
  // screen reader announces, so anything that looks private never
  // becomes one.
  if (!text || looksPrivate(text)) {
    return UNTITLED;
  }

  const trimmed = text.replace(POLITENESS, '').trim() || text;
  return shorten(trimmed.charAt(0).toUpperCase() + trimmed.slice(1), MAX_LENGTH);
}

/**
 * The line of the question shown under a chat's name.
 *
 * Longer than a title and keeps the wording as written — but held
 * back by the same rule, because a preview sits directly beneath the
 * title that withheld it.
 */
export function previewFor(message: string): string {
  const text = message.replace(/\s+/g, ' ').trim();
  if (!text || looksPrivate(text)) return '';
  return shorten(text, MAX_PREVIEW);
}

function textOf(content: unknown): string {
  if (typeof content === 'string') return content;
  if (Array.isArray(content)) {
    return content
      .map((part) =>
        part && typeof part === 'object' && typeof (part as { text?: unknown }).text === 'string'
          ? (part as { text: string }).text
          : '',
      )
      .join(' ');
  }
  return '';
}

function looksPrivate(text: string): boolean {
  if (EMAIL.test(text)) return true;
  // Long, and mixing letters with digits: a key or an id, not a word.
  const words: string[] = text.match(TOKEN) ?? [];
  return words.some(
    (word) => word.length >= 16 && /\d/.test(word) && /[A-Za-z]/.test(word),
  );
}

function shorten(text: string, limit: number): string {
  if (text.length <= limit) return text;

  const kept: string[] = [];
  let length = 0;
  for (const word of text.split(' ')) {
    // One character is kept back for the ellipsis.
    if (length + word.length + (kept.length ? 1 : 0) > limit - 1) break;
    length += word.length + (kept.length ? 1 : 0);
    kept.push(word);
  }

  return kept.length ? `${kept.join(' ')}…` : `${text.slice(0, limit - 1)}…`;
}
