/**
 * Provenance the stream could not carry, taken from the saved turn.
 *
 * Some of what explains an answer is only known once the turn is
 * finished — how many personal details were held back from the
 * model, for one. The reply has already streamed by then, so
 * without this the note appeared only if the reader happened to
 * reload: they would read an answer produced from masked input,
 * with nothing on screen saying so.
 */
export function mergeProvenance<T extends Record<string, unknown>>(
  shown: T[],
  saved: Array<Record<string, unknown>>,
): T[] {
  const extra = new Map<string, Record<string, unknown>>();
  for (const message of saved) {
    const id = message.id;
    const kwargs = message.additional_kwargs;
    if (typeof id === 'string' && kwargs && typeof kwargs === 'object') {
      extra.set(id, kwargs as Record<string, unknown>);
    }
  }
  if (extra.size === 0) return shown;

  let changed = false;
  const merged = shown.map((message) => {
    const id = message.id;
    const found = typeof id === 'string' ? extra.get(id) : undefined;
    if (!found) return message;
    // What arrived live wins: it described the turn as it happened.
    const live = (message.additional_kwargs as Record<string, unknown>) ?? {};
    const both = { ...found, ...live };
    if (Object.keys(both).length === Object.keys(live).length) return message;
    changed = true;
    return { ...message, additional_kwargs: both };
  });
  return changed ? merged : shown;
}
