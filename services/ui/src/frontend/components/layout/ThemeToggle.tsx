import { Switch } from '@patternfly/react-core';
import { MoonIcon, SunIcon } from '@patternfly/react-icons';
import { useAppDispatch, useAppSelector } from '../../redux/hooks';
import { selectTheme, toggleTheme } from '../../redux/slices/userSettings';
import { useTranslation } from 'react-i18next';

export function ThemeToggle() {
  const { t } = useTranslation();
  const dispatch = useAppDispatch();
  const theme = useAppSelector(selectTheme);
  const isDark = theme === 'dark';

  return (
    <div className="flex items-center gap-2">
      <SunIcon className={isDark ? 'text-muted-foreground' : 'text-yellow-500'} />
      <Switch
        id="theme-toggle"
        aria-label={t('appearance.toggleDarkMode')}
        isChecked={isDark}
        onChange={(_event, _checked) => {
          dispatch(toggleTheme());
        }}
        isReversed
      />
      <MoonIcon className={isDark ? 'text-blue-600 dark:text-blue-400' : 'text-muted-foreground'} />
    </div>
  );
}
