import { useTranslation } from 'react-i18next';
import { AlertTriangle } from 'lucide-react';

export interface Provenance {
  model?: string;
  finish_reason?: string;
  truncated?: boolean;
  routed_tier?: string;
  routed_by?: string;
  fallback_from?: string;
  cached?: boolean;
  empty?: boolean;
  /**
   * How many personal details were replaced with stand-ins before the
   * model read the turn.
   *
   * The reply reads exactly as if they had been there, so without
   * this nothing says the model answered about something else. A
   * count only — the values are the thing being kept back.
   */
  pii_scrubbed?: number;
  /**
   * What the run has spent, once it has passed the threshold a
   * deployment set for saying so.
   *
   * The sentence comes from the agent because the figures and the
   * ceiling are its own. Shown as a warning rather than a note: a
   * run that is most of the way through its allowance is about to
   * stop, and that changes what the reader does next.
   */
  spend_warning?: string;
  /**
   * Integrations this turn could not reach.
   *
   * Carried structurally rather than left in the prose: the model
   * rewrites tool output in its own words, so a marker in the text
   * is not a channel the UI can rely on. Rendered by McpAuthPrompt,
   * not by this component.
   */
  auth_required?: Array<{
    mcp_name: string;
    reason: string;
    connect_url: string;
  }>;
}

/**
 * Why this answer looks the way it does.
 *
 * Which model produced it, whether routing picked a tier, whether a
 * fallback answered, whether it was cut short. All of that shaped
 * the reply and none of it was visible in the transcript, so the
 * reader had no way to weigh an answer differently from any other.
 *
 * Deliberately quiet: one small line, below the message, only when
 * there is something to say. The common case — one model, ordinary
 * stop — shows the model name and nothing else, because a badge per
 * turn announcing that everything is normal is noise that teaches
 * people to stop reading it.
 */
export function MessageProvenance({ provenance }: { provenance?: Provenance | null }) {
  const { t } = useTranslation();
  if (!provenance || Object.keys(provenance).length === 0) return null;

  const {
    model,
    truncated,
    routed_tier,
    routed_by,
    fallback_from,
    cached,
    empty,
    pii_scrubbed,
    spend_warning,
  } = provenance;

  // Ordered by how much it should change the reader's confidence.
  const warnings: string[] = [];
  if (spend_warning) warnings.push(spend_warning);
  if (truncated) warnings.push(t('provenance.truncated'));
  if (empty) warnings.push(t('provenance.empty'));
  if (fallback_from) {
    warnings.push(t('provenance.fallback', { from: fallback_from }));
  }

  const notes: string[] = [];
  if (routed_tier) {
    notes.push(
      routed_by
        ? t('provenance.routedBy', { tier: routed_tier, how: routed_by })
        : t('provenance.routed', { tier: routed_tier }),
    );
  }
  if (cached) notes.push(t('provenance.cached'));
  if (pii_scrubbed) {
    notes.push(t('provenance.scrubbed', { count: pii_scrubbed }));
  }

  if (!model && warnings.length === 0 && notes.length === 0) return null;

  return (
    <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-muted-foreground">
      {model && <code className="text-[11px]">{model}</code>}
      {notes.map((note) => (
        <span key={note}>{note}</span>
      ))}
      {warnings.map((warning) => (
        // Warnings carry an icon and a colour because they change
        // whether the answer can be trusted as complete; the notes
        // beside them do not.
        <span
          key={warning}
          className="inline-flex items-center gap-1 text-amber-600 dark:text-amber-500"
        >
          <AlertTriangle className="h-3 w-3" aria-hidden="true" />
          {warning}
        </span>
      ))}
    </div>
  );
}
