import { lazy, Suspense, useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { readableOn } from './lib/readable-on';
import { AnnouncementBanner } from './components/AnnouncementBanner';
import { AppLayout } from './components/layout/AppLayout';
import { HomePage } from './pages/HomePage';
import { ErrorBoundary } from './components/ErrorBoundary';

// Everything past the landing route is split out. These screens pull in the
// chatbot, markdown and admin-table stacks, which is most of the bundle, and
// none of it is needed to paint /chat.
const ChatRoutePage = lazy(() => import('./pages/ChatPage').then(m => ({ default: m.ChatRoutePage })));
const ConsentPage = lazy(() => import('./pages/ConsentPage').then(m => ({ default: m.ConsentPage })));
const SharedPage = lazy(() => import('./pages/SharedPage').then(m => ({ default: m.SharedPage })));
const SettingsPage = lazy(() => import('./pages/SettingsPage').then(m => ({ default: m.SettingsPage })));
const AdminPage = lazy(() => import('./pages/AdminPage').then(m => ({ default: m.AdminPage })));
const ProjectChatPage = lazy(() => import('./pages/ProjectChatPage').then(m => ({ default: m.ProjectChatPage })));
const EvalDatasetPage = lazy(() => import('./pages/EvalDatasetPage').then(m => ({ default: m.EvalDatasetPage })));
const SpacesPage = lazy(() => import('./pages/SpacesPage').then(m => ({ default: m.SpacesPage })));
const SchedulePage = lazy(() => import('./pages/SchedulePage'));
const ProjectsPage = lazy(() => import('./pages/ProjectsPage'));
import { ToastNotifications } from './components/ToastNotifications';
import { rememberAgentRole, rememberAuthEnabled } from './lib/role-utils';
import { getWhoami } from './services/whoami';
import { RequirePrivilege } from './components/RequirePrivilege';
import { useThemeSync } from './hooks/useThemeSync';
import { loadConfig, setBranding, setFeatures } from './redux/slices/config';
import { setConfigDefaults } from './redux/slices/userSettings';
import type { RootState, AppDispatch } from './redux/store';
import i18n from './i18n';

export default function App() {
  const dispatch = useDispatch<AppDispatch>();
  const { branding, loading, error } = useSelector((state: RootState) => state.config);
  const theme = useSelector((state: RootState) => state.userSettings.theme);

  useThemeSync();

  // Load config at app init
  useEffect(() => {
    // Seed branding/features from server-injected HTML data
    const serverBranding = window.APP_DATA?.branding;
    const serverFeatures = window.APP_DATA?.features;
    if (serverBranding) {
      dispatch(setBranding(serverBranding));
    }
    if (serverFeatures) {
      dispatch(setFeatures(serverFeatures));
      dispatch(setConfigDefaults({ debug_mode_default: serverFeatures.debug_mode_default }));
    }

    dispatch(loadConfig()).then((result: any) => {
      if (result.meta.requestStatus === 'fulfilled' && result.payload?.features) {
        dispatch(setConfigDefaults({
          debug_mode_default: result.payload.features.debug_mode_default,
        }));
        // Read by the role check, which runs outside the store.
        rememberAuthEnabled(result.payload.features.auth_enabled);
      }
    });

    // The agent knows who is asking; the check above only guesses.
    void getWhoami().then((who) => rememberAgentRole(who?.role));
  }, [dispatch]);

  // Apply branding to DOM when config loads
  useEffect(() => {
    if (!branding) return;

    // Apply colors based on current theme
    const colors = theme === 'dark' ? branding.colors?.dark : branding.colors?.light;
    if (!colors) return;

    document.documentElement.style.setProperty('--primary', colors.primary);
    // A deployment picks its own brand colour; the label on top of it
    // has to be legible against whatever they picked, not against the
    // page.
    document.documentElement.style.setProperty(
      '--primary-foreground',
      readableOn(colors.primary),
    );
    document.documentElement.style.setProperty('--accent', colors.accent);
    document.documentElement.style.setProperty('--background', colors.background);
    document.documentElement.style.setProperty('--foreground', colors.foreground);

    // Update document title
    if (branding.title) {
      document.title = branding.title;
    }

    // Update favicon - use favicon_url if provided, otherwise fall back to logo_url
    const faviconUrl = branding.favicon_url || branding.logo_url;
    if (faviconUrl) {
      const link = document.querySelector("link[rel='icon']") as HTMLLinkElement;
      if (link) {
        link.href = faviconUrl;
      }
    }
  }, [branding, theme]);

  // Don't block render on config failure - fall back to defaults
  // Only show loading on initial mount, not on errors
  if (loading && !error && !branding) {
    return (
      <div
        role="status"
        aria-live="polite"
        aria-label={i18n.t('common.loadingApp')}
        style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}
      >
        {i18n.t('common.loadingConfig')}
      </div>
    );
  }

  // Log error but don't block render - config will fall back to defaults
  if (error) {
    console.warn('Config load failed, using defaults:', error);
  }

  return (
    <ErrorBoundary
      onError={(error, errorInfo) => {
        console.error('Top-level application error:', error, errorInfo);
      }}
    >
      <AnnouncementBanner />
      <Suspense fallback={null}>
      <Routes>
        <Route path="/consent" element={<ConsentPage />} />
        <Route path="/shared/:shareId" element={<SharedPage />} />
        <Route path="/*" element={
          <AppLayout>
            <Routes>
              <Route path="/" element={<Navigate to="/chat" replace />} />
              <Route path="/chat" element={<HomePage />} />
              <Route path="/chat/:threadId" element={<ChatRoutePage />} />
              <Route path="/project/:projectId" element={<ProjectChatPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              {/* Rooms, not a settings tab: a space is where work
                  happens, like /chat, and membership comes from the
                  directory rather than from anything set here. */}
              <Route path="/spaces" element={<SpacesPage />} />
              {/* What the agent will do without being asked again.
                  Beside /spaces rather than under /settings: a
                  schedule is work in flight, not a preference. */}
              <Route path="/scheduled" element={<SchedulePage />} />
              {/* The sidebar lists projects while you are reading a
                  conversation; this is the same set when choosing
                  one is the whole task. Same store, not a second
                  fetch. */}
              <Route path="/projects" element={<ProjectsPage />} />
              {/* Deployment-wide flags. Not under /settings because
                  Settings is per-user preference and these change
                  what everybody sees. */}
              <Route
                path="/admin"
                element={<RequirePrivilege><AdminPage /></RequirePrivilege>}
              />
              {/* Usage lives as a Settings tab now. A redirect
                  rather than a removal: this URL is in people's
                  history and in the sidebar of any tab they left
                  open. */}
              <Route
                path="/analytics"
                element={<Navigate to="/settings?tab=usage" replace />}
              />
              <Route
                path="/eval/dataset"
                element={<RequirePrivilege><EvalDatasetPage /></RequirePrivilege>}
              />
            </Routes>
          </AppLayout>
        } />
      </Routes>
      </Suspense>
      <ToastNotifications />
    </ErrorBoundary>
  );
}
