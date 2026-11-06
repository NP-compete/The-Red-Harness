import { useTranslation } from 'react-i18next';
import { useCallback, useState } from 'react';
import { Button } from '@patternfly/react-core';

import { removeDuplicateMemories } from '../../services/memory-dedupe';

/** Collapse memories that say the same thing twice. */
export function MemoryDedupe({ onChanged }: { onChanged: () => void }) {
  const { t } = useTranslation();
  const [busy, setBusy] = useState(false);
  const [said, setSaid] = useState('');

  const run = useCallback(async () => {
    setBusy(true);
    setSaid('');
    const result = await removeDuplicateMemories();
    setBusy(false);

    if (!result) {
      setSaid(t('memory.dedupeFailed'));
      return;
    }
    if (result.removed === 0) {
      setSaid(t('memory.noDuplicates'));
      return;
    }
    setSaid(
      t('counts.removedMemories', { count: result.removed, left: result.remaining }),
    );
    // Only when something actually went: reloading the list on every
    // press makes a no-op look like a change.
    onChanged();
  }, [onChanged]);

  return (
    <div className="flex items-center gap-3">
      <Button
        variant="link"
        size="sm"
        className="!text-xs !p-0"
        isDisabled={busy}
        onClick={() => void run()}
      >
        {t('memory.removeDuplicates')}</Button>
      {said && <span className="text-xs text-muted-foreground">{said}</span>}
    </div>
  );
}
