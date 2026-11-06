import { Button } from '@patternfly/react-core';
import { Bug } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { useAppDispatch, useAppSelector } from '../redux/hooks';
import { selectDebugMode, setDebugMode } from '../redux/slices/userSettings';

export function DebugToggle() {
  const { t } = useTranslation();
  const dispatch = useAppDispatch();
  const debugMode = useAppSelector(selectDebugMode);

  return (
    <Button
      variant="plain"
      size="sm"
      // Named rather than left as an icon to guess at: a control
      // nobody can find is the same as one that is not there.
      className={`!px-2 !py-1.5 flex items-center gap-1.5 whitespace-nowrap ${
        debugMode ? 'text-yellow-500' : 'text-muted-foreground'
      }`}
      onClick={() => dispatch(setDebugMode(!debugMode))}
      aria-pressed={debugMode}
    >
      <span className="inline-flex items-center gap-1.5 whitespace-nowrap">
        <Bug className="w-4 h-4" />
        <span className="text-xs">{t('sidebar.developerMode')}</span>
      </span>
    </Button>
  );
}
