/**
 * Which way of answering a conversation is using.
 *
 * Per thread, not per person. One conversation may be a quick
 * lookup and the next a long investigation, and carrying a
 * choice from the first into the second is how somebody ends up
 * paying for careful work on "what time is it".
 *
 * Whether the choice is worth offering at all is the agent's
 * call — it is the only thing that knows whether two profiles
 * would send different requests, and it answers with nothing
 * when they would not. What is decided here is what to do with
 * that answer.
 */

export interface ReasoningProfile {
  name: string;
  /** How hard the model is asked to think. Shown, not interpreted. */
  effort: string;
}

const HELD = 'template-ui-reasoning';

/** Whether to put the control on screen. */
export function offerIsWorthMaking(offered: ReasoningProfile[]): boolean {
  // One option is not a choice, and none is the agent saying the
  // options would all do the same thing.
  return Array.isArray(offered) && offered.length > 1;
}

function held(): Record<string, string> {
  try {
    const raw = localStorage.getItem(HELD);
    if (!raw) return {};
    const parsed: unknown = JSON.parse(raw);
    // An array parses but is not a map of threads to choices.
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return {};
    return parsed as Record<string, string>;
  } catch {
    // Unreadable storage costs somebody their choice, not their
    // conversation.
    return {};
  }
}

/**
 * What this thread chose, if the deployment still offers it.
 *
 * A name the agent no longer knows is ignored rather than sent:
 * a withdrawn profile would route nowhere, and the conversation
 * would quietly stop doing what its chooser still claims.
 *
 * Ignored, not deleted. A deployment reverting a change should
 * not have cost everybody the choice they made.
 */
export function chosenFor(threadId: string, offered: ReasoningProfile[]): string | null {
  if (!threadId) return null;
  const chosen = held()[threadId];
  if (!chosen) return null;
  const stillOffered = Array.isArray(offered) && offered.some((one) => one.name === chosen);
  return stillOffered ? chosen : null;
}

export function chooseFor(threadId: string, name: string): void {
  if (!threadId) return;
  try {
    localStorage.setItem(HELD, JSON.stringify({ ...held(), [threadId]: name }));
  } catch {
    // A full or blocked store loses the choice for this thread.
    // The conversation carries on at the agent's default.
  }
}

/** Drop a thread's choice, when the thread itself goes. */
export function forgetThread(threadId: string): void {
  try {
    const all = held();
    if (!(threadId in all)) return;
    delete all[threadId];
    localStorage.setItem(HELD, JSON.stringify(all));
  } catch {
    // As above.
  }
}
