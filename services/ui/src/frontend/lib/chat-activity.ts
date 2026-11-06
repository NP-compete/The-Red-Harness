import type { StreamingState } from '../redux/slices/chats';
import { authRequestsFromMessage } from './mcp-auth-marker';

/**
 * What a chat in the sidebar is doing right now.
 *
 * A delegated turn runs for minutes, and the only place that was
 * visible was the chat you happened to be looking at. Start one, open
 * another conversation, and the first became indistinguishable from a
 * finished one — including when it had stopped to ask a question and
 * was waiting on an answer that was never coming.
 *
 * `needs-input` outranks `running`: a turn paused on an approval is
 * technically still loading, but what the reader has to know is that
 * it is blocked on them.
 */
export type ChatActivity = 'needs-input' | 'running' | 'failed' | 'idle';

/** Just enough of a chat to judge how its last turn ended. */
export interface ChatForActivity {
  id: string;
  /**
   * What the agent last said about this conversation's run.
   *
   * The browser only watches the chat that is open. Without this, a
   * run paused on an approval in another conversation is filed beside
   * the ones that finished, and nobody goes back to it.
   */
  serverStatus?: string;
  messages?: Array<{ type?: string; role?: string; content?: unknown }>;
}

/** The last message the agent produced, or undefined. */
function lastAssistantMessage(chat: ChatForActivity | undefined) {
  const messages = chat?.messages;
  if (!messages?.length) return undefined;
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const m = messages[i];
    if (m.type === 'ai' || m.type === 'assistant' || m.role === 'assistant') return m;
  }
  return undefined;
}

export function chatActivity(
  state: StreamingState | undefined,
  chat?: ChatForActivity,
): ChatActivity {
  if (state?.pendingInterrupt) return 'needs-input';
  if (state?.isLoading || state?.isThinking) return 'running';
  // A turn that stopped because an integration is not connected is
  // finished, not answered — the reader has to go and connect it and
  // ask again. It used to pause on an interrupt, which put it here
  // via `pendingInterrupt`; now it ends cleanly, so without this it
  // files under "Completed" beside turns that actually answered.
  if (authRequestsFromMessage(lastAssistantMessage(chat)).length > 0) return 'needs-input';
  // Only consulted once the browser has nothing to say: the list is
  // fetched periodically, so a run that started since is newer news.
  if (chat?.serverStatus === 'interrupted') return 'needs-input';
  if (chat?.serverStatus === 'error' || chat?.serverStatus === 'failed') return 'failed';
  // The agent calls a thread busy while a run is in flight on it.
  if (chat?.serverStatus === 'busy') return 'running';
  return 'idle';
}

/** Activity for every chat that has one, keyed by chat id. */
export function activityByChat(
  streamingStates: Record<string, StreamingState>,
  chats: ChatForActivity[] = [],
): Record<string, ChatActivity> {
  const out: Record<string, ChatActivity> = {};
  const byId = new Map(chats.map((c) => [c.id, c]));
  // Union of both sources: a chat restored from history has no
  // streaming state at all, and its unanswered turn still counts.
  const ids = new Set([...Object.keys(streamingStates ?? {}), ...byId.keys()]);
  for (const chatId of ids) {
    const activity = chatActivity(streamingStates?.[chatId], byId.get(chatId));
    if (activity !== 'idle') out[chatId] = activity;
  }
  return out;
}
