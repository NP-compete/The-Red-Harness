import type { AnswerNotesData } from '../components/AnswerNotes';
import type { Provenance } from '../components/MessageProvenance';

/** Everything the reader is told about an answer besides its text. */
export interface MessageExtras extends Provenance {
  answer_notes?: AnswerNotesData;
}

const CUT_OFF = new Set(['length', 'max_tokens', 'content_filter']);
const CARRIED = ['routed_tier', 'routed_by', 'fallback_from', 'cached'] as const;

/**
 * What is known about one answer, assembled from the message.
 *
 * The agent attaches this while a turn streams, but a conversation
 * loaded from history arrives with the same facts spread across the
 * reply metadata instead. Deriving them here is what keeps a reloaded
 * page saying the same thing the live one said.
 */
export function provenanceOf(message: Record<string, unknown>): MessageExtras | undefined {
  const given = message.provenance;
  if (given && typeof given === 'object' && Object.keys(given).length > 0) {
    return given as MessageExtras;
  }

  const meta = (message.response_metadata ?? {}) as Record<string, unknown>;
  const extra = (message.additional_kwargs ?? {}) as Record<string, unknown>;
  const found: MessageExtras = {};

  const model = meta.model_name ?? meta.model;
  if (typeof model === 'string' && model) found.model = model;

  const finish = meta.finish_reason;
  if (typeof finish === 'string' && finish) {
    found.finish_reason = finish;
    if (CUT_OFF.has(finish.toLowerCase())) found.truncated = true;
  }

  const scrubbed = extra.pii_scrubbed;
  if (typeof scrubbed === 'number' && scrubbed > 0) found.pii_scrubbed = scrubbed;

  const spending = extra.spend_warning;
  if (typeof spending === 'string' && spending) found.spend_warning = spending;

  for (const key of CARRIED) {
    const value = extra[key];
    if (value !== undefined && value !== null && value !== '' && value !== false) {
      found[key] = value as never;
    }
  }

  const notes = extra.answer_notes;
  if (worthSaying(notes)) found.answer_notes = notes as AnswerNotesData;

  return Object.keys(found).length > 0 ? found : undefined;
}

/**
 * Notes are shown only when something is wrong with the answer.
 *
 * A note on every turn saying the figures checked out teaches people
 * to stop reading the notes.
 */
function worthSaying(notes: unknown): boolean {
  if (!notes || typeof notes !== 'object') return false;
  const { stance, loop, claims, figures, coverage, budget, injection } =
    notes as Record<string, unknown>;

  if (stance !== undefined && stance !== 'plain') return true;
  if (loop) return true;
  // A tool a spent budget took away, and material written to be
  // obeyed rather than read. Either can be the only thing in the note
  // on a turn where everything else checked out.
  if (budget) return true;
  if (injection) return true;
  if (Array.isArray(claims) && claims.length > 0) return true;
  if (
    figures &&
    typeof figures === 'object' &&
    Array.isArray((figures as { unsupported?: unknown }).unsupported) &&
    (figures as { unsupported: unknown[] }).unsupported.length > 0
  ) {
    return true;
  }
  return Boolean(
    coverage &&
      typeof coverage === 'object' &&
      (coverage as { complete?: boolean }).complete === false,
  );
}
