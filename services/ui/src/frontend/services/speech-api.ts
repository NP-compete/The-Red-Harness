import { buildAgentApiUrl } from '../lib/app-paths';
import { authenticatedFetch } from './authenticated-fetch';

const NO_ANSWER = 'That recording could not be turned into text. Try again, or type it.';

/**
 * Whether this deployment will turn speech into text.
 *
 * Asked rather than assumed: the browser has recognition of its own
 * and using it would send a voice somewhere nobody agreed to, so the
 * control only appears when the agent says it can do the work here.
 */
export async function dictationOffered(): Promise<boolean> {
  try {
    const response = await authenticatedFetch(buildAgentApiUrl('/speech'), {
      method: 'GET',
    });
    if (!response.ok) return false;
    const body = (await response.json()) as { dictation?: boolean };
    return body.dictation === true;
  } catch {
    return false;
  }
}

export interface Dictated {
  text: string;
  /** Why there is no text, when there should have been. */
  problem?: string;
}

/** Turn a recording into text for the person to read before sending. */
export async function transcribeDictation(recording: Blob): Promise<Dictated> {
  const form = new FormData();
  form.append('audio', recording, 'dictation.webm');

  try {
    const response = await authenticatedFetch(buildAgentApiUrl('/speech/transcribe'), {
      method: 'POST',
      body: form,
    });
    const body = (await response.json().catch(() => ({}))) as {
      text?: string;
      detail?: string;
    };
    if (!response.ok) {
      return { text: '', problem: body.detail || NO_ANSWER };
    }
    return { text: body.text ?? '' };
  } catch {
    return { text: '', problem: NO_ANSWER };
  }
}
