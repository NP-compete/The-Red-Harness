/**
 * Why a particular call is being asked about.
 *
 * An approval card shows the tool's name, its arguments and two
 * buttons. For a tool whose policy always asks, that is enough —
 * the answer to "why am I being asked" is "you always are".
 *
 * It is not enough for a call that was going to be allowed and
 * was stopped because of something earlier in the run. The whole
 * value of stopping it is the sentence saying what: that the
 * agent read a ticket, and this write repeats a line from it.
 * Without it the card looks like every other one, and identical
 * cards are the ones people click through.
 */

interface ActionRequest {
  name?: unknown;
  description?: unknown;
}

export function reasonFor(value: unknown, toolName: string): string | null {
  if (typeof value !== 'object' || value === null) return null;

  const requests = (value as { action_requests?: unknown }).action_requests;
  if (!Array.isArray(requests)) return null;

  for (const entry of requests as ActionRequest[]) {
    if (entry?.name !== toolName) continue;
    const said = typeof entry.description === 'string' ? entry.description.trim() : '';
    // Nothing rather than an empty line. A card with a blank
    // space where an explanation goes reads as one that failed
    // to load.
    return said || null;
  }
  return null;
}
