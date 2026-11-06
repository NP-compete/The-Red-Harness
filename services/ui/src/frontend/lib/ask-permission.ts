/**
 * Whether to ask for notification permission now.
 *
 * Never on first load. A prompt before somebody has seen what the
 * product does is a prompt they refuse, and in most browsers a
 * refusal is permanent — one badly-timed ask costs the feature for
 * good. So it waits until they have started a run, which is the
 * moment the answer is obviously useful: that is the thing they are
 * about to walk away from.
 */
export function shouldAsk({
  supported,
  permission,
  startedARun,
  alreadyAsked,
}: {
  supported: boolean;
  permission: NotificationPermission;
  startedARun: boolean;
  alreadyAsked: boolean;
}): boolean {
  if (!supported) return false;
  // `granted` needs nothing and `denied` cannot be undone by asking
  // again — the browser will not even show it.
  if (permission !== 'default') return false;
  if (alreadyAsked) return false;
  return startedARun;
}
