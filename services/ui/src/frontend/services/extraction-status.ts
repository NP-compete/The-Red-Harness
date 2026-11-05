import { buildAgentApiUrl } from '../lib/app-paths';
import { authenticatedFetch } from './authenticated-fetch';

export interface ExtractionStatus {
  engine: string;
  reachable: boolean;
  detail: string;
  fallback: boolean;
  handles: string[];
  maxBytes: number;
}

/**
 * What reads an attachment, and whether it can be reached.
 *
 * A misconfigured extractor is otherwise met at upload time, in
 * front of whoever attached the file, in a message about their file
 * rather than about the deployment.
 */
export async function getExtractionStatus(): Promise<ExtractionStatus | null> {
  try {
    const response = await authenticatedFetch(
      buildAgentApiUrl('/attachments/extraction'),
      { method: 'GET' },
    );
    if (!response.ok) return null;

    const body = (await response.json()) as {
      engine?: string;
      reachable?: boolean;
      detail?: string;
      fallback?: boolean;
      handles?: unknown;
      max_bytes?: number;
    };
    if (!body.engine) return null;

    return {
      engine: body.engine,
      reachable: body.reachable !== false,
      detail: body.detail ?? '',
      fallback: body.fallback === true,
      handles: Array.isArray(body.handles) ? body.handles.map(String) : [],
      maxBytes: typeof body.max_bytes === 'number' ? body.max_bytes : 0,
    };
  } catch {
    return null;
  }
}
