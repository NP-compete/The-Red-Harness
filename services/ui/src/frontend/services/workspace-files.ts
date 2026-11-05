import { buildAgentApiUrl } from '../lib/app-paths';
import { authenticatedFetch } from './authenticated-fetch';

export interface WorkspaceFile {
  path: string;
  bytes: number;
  modified: string;
}

/**
 * Files the agent wrote for this person.
 *
 * A report it produces is kept where only the memories page ever
 * looked, and that page takes the one file it knows about — so until
 * now the agent could say it had written something and leave nowhere
 * to go and read it.
 */
export async function listWorkspaceFiles(): Promise<WorkspaceFile[]> {
  try {
    const response = await authenticatedFetch(buildAgentApiUrl('/workspace/files'), {
      method: 'GET',
    });
    if (!response.ok) return [];

    const body = (await response.json()) as { files?: unknown };
    if (!Array.isArray(body.files)) return [];

    return body.files
      .filter(
        (file): file is { path: string; bytes?: number; modified?: string } =>
          Boolean(file && typeof file === 'object' && (file as { path?: unknown }).path),
      )
      .map((file) => ({
        path: file.path,
        bytes: typeof file.bytes === 'number' ? file.bytes : 0,
        modified: file.modified ?? '',
      }));
  } catch {
    return [];
  }
}

/**
 * One file's contents, or `null` when there is nothing to show.
 *
 * A listing nobody can open is half an answer: the question behind
 * "the agent wrote a report" is what the report says.
 */
export async function readWorkspaceFile(path: string): Promise<string | null> {
  try {
    const response = await authenticatedFetch(
      buildAgentApiUrl(`/workspace/files/${encodeURIComponent(path.replace(/^\//, ''))}`),
      { method: 'GET' },
    );
    if (!response.ok) return null;

    const body = (await response.json()) as { content?: unknown };
    return typeof body.content === 'string' ? body.content : null;
  } catch {
    return null;
  }
}

/** Remove a file the agent wrote. True when it is gone. */
export async function deleteWorkspaceFile(path: string): Promise<boolean> {
  try {
    const response = await authenticatedFetch(
      buildAgentApiUrl(`/workspace/files/${encodeURIComponent(path.replace(/^\//, ''))}`),
      { method: 'DELETE' },
    );
    return response.ok;
  } catch {
    return false;
  }
}
