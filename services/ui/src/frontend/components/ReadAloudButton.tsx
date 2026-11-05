import { Square, Volume2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { useReadAloud } from '../hooks/useReadAloud';

export function ReadAloudButton({ text }: { text: string }) {
  const { t, i18n } = useTranslation();
  const { available, speaking, toggle } = useReadAloud(text, i18n.language);

  if (!available) return null;

  return (
    <button
      type="button"
      className="inline-flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted/80 hover:text-foreground"
      aria-label={speaking ? t('chat.stopReading') : t('chat.readAloud')}
      onClick={toggle}
    >
      {speaking ? (
        <Square className="h-3.5 w-3.5" />
      ) : (
        <Volume2 className="h-3.5 w-3.5" />
      )}
    </button>
  );
}
