import { buildAgentApiUrl } from '../lib/app-paths';
import { authenticatedFetch } from './authenticated-fetch';

/**
 * Withdraw a question and everything that followed from it.
 *
 * Trimming the browser's own copy is not enough: the agent holds
 * the conversation, and the next read puts back every turn it was
 * never told had been withdrawn. Reports whether the agent agreed,
 * because an edit that goes ahead regardless leaves two versions of
 * the same question in the transcript.
 */
export async function withdrawFrom(
  threadId: string,
  messageIndex: number,
): Promise<boolean> {
  if (!threadId) return false;
  try {
    const response = await authenticatedFetch(
      buildAgentApiUrl(`/threads/${threadId}/truncate`),
      {
        method: 'POST',
        body: JSON.stringify({ message_index: messageIndex }),
      },
    );
    return response.ok;
  } catch {
    return false;
  }
}
