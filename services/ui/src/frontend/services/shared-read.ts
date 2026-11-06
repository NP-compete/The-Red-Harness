import { buildAgentApiUrl } from '../lib/app-paths';

export interface SharedMessage {
  type?: string;
  content?: unknown;
}

export type SharedConversation =
  | {
      state: 'ok';
      title: string;
      capturedAt: string | null;
      messages: SharedMessage[];
      attachmentNames: string[];
    }
  /** Revoked or expired — told apart, because the reader's next move differs. */
  | { state: 'gone'; reason: string }
  | { state: 'missing' }
  | { state: 'sign-in' }
  | { state: 'unavailable' };

export async function readShared(shareId: string): Promise<SharedConversation> {
  try {
    const response = await fetch(buildAgentApiUrl(`/shared/${shareId}`), {
      credentials: 'same-origin',
      signal: AbortSignal.timeout(10_000),
    });

    if (response.status === 410) {
      const body = (await response.json().catch(() => ({}))) as { detail?: string };
      return { state: 'gone', reason: body.detail ?? 'This link no longer works' };
    }
    if (response.status === 404) return { state: 'missing' };
    if (response.status === 401 || response.status === 403) return { state: 'sign-in' };
    if (!response.ok) return { state: 'unavailable' };

    const body = (await response.json()) as {
      title?: string;
      captured_at?: string | null;
      messages?: SharedMessage[];
      attachment_names?: string[];
    };

    return {
      state: 'ok',
      title: body.title ?? 'Shared conversation',
      capturedAt: body.captured_at ?? null,
      messages: body.messages ?? [],
      attachmentNames: body.attachment_names ?? [],
    };
  } catch {
    return { state: 'unavailable' };
  }
}
