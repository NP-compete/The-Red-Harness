import { buildAppPath } from '../lib/app-paths';

export interface DeletionPreview {
  subject: string;
  delete: Record<string, string[]>;
  kept: Record<string, string[]>;
  retained: Record<string, string[]>;
  counts: Record<string, number>;
  notes: string[];
  /** Stores this action does not reach, and where to go instead. */
  not_included?: Record<string, string>;
}

export interface DeletionResult {
  counts: Record<string, number>;
  failed: Record<string, string>;
  not_included?: Record<string, string>;
}

/**
 * What removing everything would take with it.
 *
 * `null` when the agent cannot answer — an older one that has
 * never been asked is not a person with no data, and offering
 * a delete button on that basis would be a button that does
 * nothing somebody is relying on.
 */
export async function previewDeletion(): Promise<DeletionPreview | null> {
  try {
    const response = await fetch(buildAppPath('/api/proxy/agent/me/deletion-preview'), {
      credentials: 'include',
    });
    if (!response.ok) return null;
    const body = (await response.json()) as Partial<DeletionPreview>;
    return body.delete ? (body as DeletionPreview) : null;
  } catch {
    return null;
  }
}

export async function deleteMyData(): Promise<DeletionResult | null> {
  try {
    const response = await fetch(buildAppPath('/api/proxy/agent/me/data'), {
      method: 'DELETE',
      credentials: 'include',
    });
    if (!response.ok) return null;
    return (await response.json()) as DeletionResult;
  } catch {
    return null;
  }
}

/** Where a copy is downloaded from. A link, so the browser saves it. */
export function exportHref(): string {
  return buildAppPath('/api/proxy/agent/me/export');
}
