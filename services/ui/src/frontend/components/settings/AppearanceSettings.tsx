import { useTranslation } from 'react-i18next';

import { useAppDispatch, useAppSelector } from '../../redux/hooks';
import {
  selectTheme,
  setTheme,
} from '../../redux/slices/userSettings';
import { Sun, Moon } from 'lucide-react';

type ThemeOption = 'light' | 'dark';

// Keys, not words: this list is built once at module load, where
// there is no translator to call.
const THEME_OPTIONS: { value: ThemeOption; labelKey: string; icon: typeof Sun; detailKey: string }[] = [
  { value: 'light', labelKey: 'appearance.light', icon: Sun, detailKey: 'appearance.lightDetail' },
  { value: 'dark', labelKey: 'appearance.dark', icon: Moon, detailKey: 'appearance.darkDetail' },
];

export function AppearanceSettings() {
  const { t } = useTranslation();
  const dispatch = useAppDispatch();
  const currentTheme = useAppSelector(selectTheme);

  return (
    <div className="space-y-6">
      <div>
        <h3 id="theme-group-label" className="text-sm font-medium text-foreground mb-1">{t('appearance.theme')}</h3>
        <p className="text-xs text-muted-foreground mb-4">
          {t('appearance.themeHelp', { agent: window.APP_DATA?.agentName || 'Agent' })}
        </p>
        <div
          role="radiogroup"
          aria-labelledby="theme-group-label"
          className="grid grid-cols-2 gap-3"
        >
          {THEME_OPTIONS.map((opt) => {
            const Icon = opt.icon;
            const isSelected = currentTheme === opt.value;
            return (
              <button
                key={opt.value}
                type="button"
                role="radio"
                aria-checked={isSelected}
                onClick={() => dispatch(setTheme(opt.value))}
                className={`flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all cursor-pointer ${
                  isSelected
                    ? 'border-primary bg-primary/5'
                    : 'border-border bg-card hover:border-primary/30 hover:bg-secondary/30'
                }`}
              >
                <Icon className={`w-6 h-6 ${isSelected ? 'text-primary' : 'text-muted-foreground'}`} aria-hidden="true" />
                <span className={`text-sm font-medium ${isSelected ? 'text-primary' : 'text-foreground'}`}>
                  {t(opt.labelKey)}
                </span>
                <span className="text-xs text-muted-foreground">{t(opt.detailKey)}</span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
