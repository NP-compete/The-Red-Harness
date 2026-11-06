import { useEffect } from 'react';
import { useAppSelector } from '../redux/hooks';
import { selectTheme } from '../redux/slices/userSettings';

/**
 * Syncs the Redux theme state to DOM classes on <html>.
 * Applies both Tailwind's `.dark` and PatternFly's `.pf-v6-theme-dark`.
 *
 * Also mirrors the choice into a cookie. The theme lives in localStorage,
 * which the server cannot read, and the server now paints a pre-React boot
 * shell (see client.router.ts) that has to use the right palette. The
 * page's CSP forbids inline scripts, so nothing can read localStorage
 * before first paint; the cookie is the only channel that reaches the
 * server in time.
 */
export function useThemeSync(): void {
  const theme = useAppSelector(selectTheme);

  useEffect(() => {
    const html = document.documentElement;

    if (theme === 'dark') {
      html.classList.add('dark', 'pf-v6-theme-dark');
    } else {
      html.classList.remove('dark', 'pf-v6-theme-dark');
    }

    document.cookie = `ui_theme=${theme === 'light' ? 'light' : 'dark'}; path=/; max-age=31536000; samesite=lax`;
  }, [theme]);
}
