/**
 * Why the conversation list is empty, which is not always the same.
 *
 * A search that matches nothing used to fall through to "no
 * unassigned chats" — the message for a person who has none, shown
 * to a person who has plenty and simply searched for the wrong
 * word.
 */
export function emptyListReason({
  total,
  searching,
}: {
  total: number;
  searching: boolean;
}): 'noChatsYet' | 'noUnassignedChats' | 'noSearchMatches' {
  if (searching) return 'noSearchMatches';
  return total === 0 ? 'noChatsYet' : 'noUnassignedChats';
}
