import { buildAppPath } from '../lib/app-paths';
import type { LibraryReport } from '../lib/document-view';

/**
 * A person's own documents in the retrieval library.
 *
 * Not the same thing as the shared volume behind `/documents`,
 * which is one capacity for the whole deployment, writable only
 * by a privileged role, and read by the agent through its
 * filesystem tools. These are personal, quota'd per person, and
 * reached by scope-aware retrieval.
 */
const BASE = '/api/proxy/agent/knowledge/documents';
const REWRITE = '/api/proxy/agent/knowledge/rewrite';

export interface Rewritten {
  ok: boolean;
  text: string;
  reason: string;
}

/**
 * Ask for one selected passage to be rewritten.
 *
 * Stores nothing. A reply that is not usable comes back as
 * `ok: false` with something to show, never as empty text the
 * caller might write over the passage somebody highlighted.
 */
export async function rewriteSelection(
  selection: string,
  instruction: string,
): Promise<Rewritten> {
  try {
    const response = await fetch(buildAppPath(REWRITE), {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ selection, instruction }),
    });
    if (!response.ok) {
      return { ok: false, text: '', reason: 'Your text is unchanged.' };
    }
    const body = (await response.json()) as Partial<Rewritten>;
    return {
      ok: body.ok === true && !!body.text,
      text: body.text ?? '',
      reason: body.reason ?? '',
    };
  } catch {
    return { ok: false, text: '', reason: 'Your text is unchanged.' };
  }
}

/**
 * `null` when the deployment does not keep personal documents.
 * The agent answers 404 for that, because it is the absence of
 * a page rather than a refusal.
 */
export async function readLibrary(): Promise<LibraryReport | null> {
  try {
    const response = await fetch(buildAppPath(BASE), { credentials: 'include' });
    if (!response.ok) return null;
    const body = (await response.json()) as Partial<LibraryReport>;
    return Array.isArray(body.documents) ? (body as LibraryReport) : null;
  } catch {
    return null;
  }
}

export async function addToLibrary(
  title: string,
  text: string,
): Promise<{ ok: true } | { ok: false; detail: string | null }> {
  try {
    const response = await fetch(buildAppPath(BASE), {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, text }),
    });
    if (response.ok) return { ok: true };
    const body = (await response.json().catch(() => ({}))) as { detail?: string };
    // The agent's own words: it knows how much room is left,
    // and a generic failure here sends somebody guessing.
    return { ok: false, detail: body.detail ?? 'Could not save that document.' };
  } catch {
    return { ok: false, detail: 'Could not reach the agent.' };
  }
}

export interface StoredDocument {
  id: string;
  title: string;
  text: string;
  editable: boolean;
}

export async function readDocument(id: string): Promise<StoredDocument | null> {
  try {
    const response = await fetch(`${buildAppPath(BASE)}/${encodeURIComponent(id)}`, {
      credentials: 'include',
    });
    if (!response.ok) return null;
    return (await response.json()) as StoredDocument;
  } catch {
    // Nothing to edit is better than an editor full of
    // nothing, which looks like a note that lost its text.
    return null;
  }
}

export async function editInLibrary(
  id: string,
  title: string,
  text: string,
): Promise<{ ok: true } | { ok: false; detail: string | null }> {
  try {
    const response = await fetch(`${buildAppPath(BASE)}/${encodeURIComponent(id)}`, {
      method: 'PUT',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, text }),
    });
    if (response.ok) return { ok: true };
    const body = (await response.json().catch(() => ({}))) as { detail?: string };
    // The agent's own words. It knows how much room is left and
    // whose note this is; a generic failure here sends somebody
    // guessing at which of those went wrong.
    return { ok: false, detail: body.detail ?? 'Could not save that change.' };
  } catch {
    return { ok: false, detail: 'Could not reach the agent.' };
  }
}

export async function removeFromLibrary(id: string): Promise<boolean> {
  try {
    const response = await fetch(`${buildAppPath(BASE)}/${encodeURIComponent(id)}`, {
      method: 'DELETE',
      credentials: 'include',
    });
    return response.ok;
  } catch {
    return false;
  }
}
