import { buildAgentApiUrl } from '../lib/app-paths';
import { authenticatedFetch } from './authenticated-fetch';

export interface TagCount {
  tag: string;
  threads: number;
}

/** The tags on one conversation, or none if they cannot be read. */
export async function getThreadTags(threadId: string): Promise<string[]> {
  try {
    const response = await authenticatedFetch(
      buildAgentApiUrl(`/threads/${threadId}/tags`),
      { method: 'GET' },
    );
    if (!response.ok) return [];
    return ((await response.json()) as { tags?: string[] }).tags ?? [];
  } catch {
    return [];
  }
}

/**
 * Replace a conversation's tags.
 *
 * Returns what the agent settled on rather than what was sent: it
 * lowercases, trims and sorts, and echoing the input would show a tag
 * that is not the one stored. `null` means the set was refused.
 */
export async function setThreadTags(
  threadId: string,
  tags: string[],
): Promise<string[] | null> {
  try {
    const response = await authenticatedFetch(
      buildAgentApiUrl(`/threads/${threadId}/tags`),
      {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tags }),
      },
    );
    if (!response.ok) return null;
    return ((await response.json()) as { tags?: string[] }).tags ?? [];
  } catch {
    return null;
  }
}

/** Every tag this account has used, with how many conversations carry it. */
export async function listTags(): Promise<TagCount[]> {
  try {
    const response = await authenticatedFetch(buildAgentApiUrl('/tags'), {
      method: 'GET',
    });
    if (!response.ok) return [];
    return ((await response.json()) as { tags?: TagCount[] }).tags ?? [];
  } catch {
    return [];
  }
}

export interface TaggedThread {
  id: string;
  title: string;
  tags: string[];
  updatedAt: string | null;
}

/** The conversations carrying a tag, newest first as the agent orders them. */
export async function threadsWithTag(tag: string): Promise<TaggedThread[]> {
  try {
    const response = await authenticatedFetch(
      // Tags may contain spaces, so the path segment is escaped.
      buildAgentApiUrl(`/tags/${encodeURIComponent(tag)}/threads`),
      { method: 'GET' },
    );
    if (!response.ok) return [];
    const body = (await response.json()) as {
      threads?: { thread_id?: string; title?: string; tags?: string[]; updated_at?: string | null }[];
    };
    return (body.threads ?? [])
      .filter((row) => row.thread_id)
      .map((row) => ({
        id: row.thread_id as string,
        title: row.title ?? 'Untitled conversation',
        tags: row.tags ?? [],
        updatedAt: row.updated_at ?? null,
      }));
  } catch {
    return [];
  }
}
