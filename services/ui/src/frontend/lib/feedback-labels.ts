export type Direction = 'up' | 'down';

/**
 * Which string names a rating control, given what has been rated.
 *
 * A catalogue key rather than the words: this runs outside a
 * component, where there is no translator to call, and a label
 * written here would be English in every language.
 *
 * A rating is recorded once. Once it is, both controls are closed —
 * and leaving "Rate response as not helpful" on the dead one
 * promises an action that cannot happen. Saying what was recorded
 * instead explains the state rather than inviting a click into it.
 */
export function feedbackLabel(
  button: Direction,
  recorded: Direction | null,
): string {
  if (recorded === null) {
    return button === 'up' ? 'rating.rateHelpful' : 'rating.rateNotHelpful';
  }
  if (recorded === button) {
    return recorded === 'up' ? 'rating.ratedHelpful' : 'rating.ratedUnhelpful';
  }
  return 'rating.alreadyRated';
}

/**
 * Which string names the fork control, given what it is doing.
 *
 * Its tooltip already changed on failure and its accessible name
 * did not, so whether the last attempt worked was information only
 * available to people who could see the tooltip.
 */
export function forkLabel({
  busy,
  failed,
  asking = false,
}: {
  busy: boolean;
  failed: boolean;
  /** Waiting for the second click, the one that actually forks. */
  asking?: boolean;
}): string {
  if (busy) return 'rating.forkInProgress';
  if (asking) return 'rating.forkConfirm';
  if (failed) return 'rating.forkFailed';
  return 'rating.fork';
}
