import { useTranslation } from 'react-i18next';
import { Globe } from 'lucide-react';

/**
 * Where an answer's words came from, when some came from outside.
 *
 * An answer built out of a ticket reads exactly like one built
 * out of what the agent knows. The reader can judge the ticket
 * — open it, know the team, perhaps have written it — but only
 * if they are told it is in there.
 *
 * Separate from the citations above, which name documents this
 * deployment keeps. This names a third party: material nobody
 * here wrote or reviewed, which is a different claim and
 * deserves different words.
 *
 * Absent when nothing matched. An empty strip reads as
 * "checked and found none", a different claim from "did not
 * need to look".
 */
export function FromOutside({ sources }: { sources: string[] | undefined }) {
  const { t } = useTranslation();
  if (!Array.isArray(sources) || sources.length === 0) return null;

  return (
    <p
      role="note"
      className="mt-2 flex items-center gap-1.5 text-xs text-muted-foreground"
    >
      <Globe className="h-3 w-3 shrink-0 opacity-70" aria-hidden="true" />
      {t('fromOutside.note', { sources: sources.join(', ') })}
    </p>
  );
}
