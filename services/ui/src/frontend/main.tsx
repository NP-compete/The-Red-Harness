import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { Provider } from 'react-redux';
import { store } from './redux/store';
import App from './App';
import { getAppBasePath } from './lib/app-paths';
import { registerShellWorker } from './lib/register-sw';
import { getPwaConfig } from './services/config.service';
// Side-effect import: initialises i18next before the first render,
// so no component ever renders an untranslated first frame.
import './i18n';

// PatternFly's stylesheets are imported from global.css into a
// cascade layer — see the note there. Importing them here would put
// them outside every layer, where they beat all Tailwind utilities
// on specificity grounds that do not apply.

import './global.css';

type InjectedRecord = Record<string, unknown>;

function parseInjected(rootEl: HTMLElement): { user: InjectedRecord; app: InjectedRecord } {
  try {
    const userData = rootEl.dataset.user;
    const appData = rootEl.dataset.app;
    return {
      user: userData ? JSON.parse(decodeURIComponent(userData)) : {},
      app: appData ? JSON.parse(decodeURIComponent(appData)) : {},
    };
  } catch (e) {
    console.error('Failed to parse injected data:', e);
    return { user: {}, app: {} };
  }
}

function isSparseUser(user: InjectedRecord): boolean {
  return !user.preferred_username && !user.name && !user.email && !user.displayName && !user.sub;
}

async function loadSessionUser(injected: InjectedRecord): Promise<InjectedRecord | 'login'> {
  if (!isSparseUser(injected)) return injected;
  try {
    const res = await fetch('/api/me', {
      credentials: 'include',
      headers: { Accept: 'application/json' },
      redirect: 'manual',
    });
    if (res.status === 401) return 'login';
    const contentType = res.headers.get('content-type') || '';
    if (!res.ok || !contentType.includes('application/json')) return injected;
    const body = await res.json();
    return body && typeof body === 'object' ? (body as InjectedRecord) : injected;
  } catch {
    return injected;
  }
}

/**
 * Resolves once the main stylesheet is usable.
 *
 * The server loads it as `media="print"` so that it cannot block the first
 * paint of the server-rendered boot shell, which is styled with inline
 * attributes and needs nothing from it. That makes it possible — unlikely,
 * since this bundle is the larger download — for the JS to win the race, and
 * mounting then would replace a styled shell with an unstyled app. The 2 s
 * ceiling means a stylesheet that fails outright still yields a rendered app.
 */
function stylesheetReady(): Promise<void> {
  const link = document.querySelector<HTMLLinkElement>('link[data-main-css]');
  if (!link || link.sheet) return Promise.resolve();
  return new Promise((resolve) => {
    const done = () => resolve();
    link.addEventListener('load', done, { once: true });
    link.addEventListener('error', done, { once: true });
    setTimeout(done, 2000);
  });
}

async function boot() {
  const rootEl = document.getElementById('root')!;
  const injected = parseInjected(rootEl);
  (window as any).APP_DATA = injected.app;
  const sessionUser = await loadSessionUser(injected.user);
  if (sessionUser === 'login') {
    window.location.replace('/login');
    return;
  }
  (window as any).USER_DATA = sessionUser;
  await stylesheetReady();

  // After render, never before: a worker is an enhancement and
  // must not be between the reader and the first paint.
  void getPwaConfig().then((pwa) =>
    registerShellWorker({ enabled: pwa?.enabled === true }),
  );

  createRoot(rootEl).render(
    <StrictMode>
      <BrowserRouter basename={getAppBasePath()}>
        <Provider store={store}>
          <App />
        </Provider>
      </BrowserRouter>
    </StrictMode>
  );
}

void boot();
