/**
 * Spotting the stand-in left behind when a thread is compacted.
 *
 * A long conversation is kept workable by summarising its oldest
 * turns and dropping them. What is left in their place arrives as
 * though the person had typed it, so without this the transcript
 * shows words they never said and loses the ones they did — which
 * from the outside is indistinguishable from the agent forgetting.
 */

const OPENING = /^\s*here is a summary of the conversation to date:\s*/i;

function text(content: unknown): string {
  if (typeof content === 'string') return content;
  if (Array.isArray(content)) {
    return content
      .map((part) =>
        typeof part === 'string'
          ? part
          : typeof (part as { text?: unknown })?.text === 'string'
            ? ((part as { text: string }).text)
            : '',
      )
      .join('');
  }
  return '';
}

/**
 * What a compaction summarised, or `null` for an ordinary message.
 *
 * An empty string is a summary with nothing in it, which is still a
 * compaction and still worth marking.
 */
export function compactionSummary(message: unknown): string | null {
  if (!message || typeof message !== 'object') return null;
  const { type, content } = message as { type?: unknown; content?: unknown };
  if (type !== 'human') return null;

  const body = text(content);
  if (!OPENING.test(body)) return null;
  return body.replace(OPENING, '').trim();
}
