import { configureStore } from '@reduxjs/toolkit';
import { render, screen } from '@testing-library/react';
import { Provider } from 'react-redux';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import configReducer from '../../redux/slices/config';
import toastsReducer from '../../redux/slices/toasts';
import { AdminPage } from '../AdminPage';

vi.mock('../../hooks/useRefreshableToken', () => ({
  useRefreshableToken: () => ({ token: 't' }),
}));

const BODY = {
  features: { memory_enabled: true, auth_enabled: false },
  overridable: ['memory_enabled'],
  canOverride: true,
  declared: [
    {
      key: 'memory_enabled',
      scope: 'deployment',
      effect: 'Lets the agent keep notes between conversations.',
      value: true,
      source: 'default',
      overridable: true,
    },
    {
      key: 'auth_enabled',
      scope: 'deployment',
      effect: 'Requires people to sign in.',
      value: false,
      source: 'environment',
      setBy: 'AUTH_ENABLED',
      overridable: false,
    },
  ],
  changes: [
    { key: 'memory_enabled', from: true, to: false, who: 'sam', when: '2026-10-27T18:00:00Z' },
  ],
};

function answers(body: unknown) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => body }),
  );
}

function show() {
  const store = configureStore({ reducer: { config: configReducer, toasts: toastsReducer } });
  return render(
    <Provider store={store}>
      <AdminPage embedded />
    </Provider>,
  );
}

beforeEach(() => {
  (window as unknown as { APP_DATA: unknown }).APP_DATA = { basePath: '/' };
  answers(BODY);
});
afterEach(() => vi.unstubAllGlobals());

describe('AdminPage', () => {
  it('offers a switch for a flag that can be changed here', async () => {
    show();
    expect(await screen.findByText('Memory')).toBeInTheDocument();
  });

  it('also reports a flag that cannot be changed here', async () => {
    // Showing only the changeable ones leaves an operator unable to
    // tell whether sign-in is on, or where it was decided.
    show();
    expect(await screen.findByText('auth_enabled')).toBeInTheDocument();
  });

  it('says where an unchangeable flag was decided', async () => {
    show();
    expect(await screen.findByText(/AUTH_ENABLED/)).toBeInTheDocument();
  });

  it('says what an unchangeable flag changes', async () => {
    show();
    expect(await screen.findByText('Requires people to sign in.')).toBeInTheDocument();
  });

  it('shows who changed what recently', async () => {
    show();
    expect(await screen.findByText(/sam/)).toBeInTheDocument();
  });

  it('says nothing about a trail that is empty', async () => {
    answers({ ...BODY, changes: [] });
    show();
    await screen.findByText('auth_enabled');
    expect(screen.queryByText(/recent changes/i)).not.toBeInTheDocument();
  });

  it('copes with a server that reports no provenance at all', async () => {
    answers({ features: BODY.features, overridable: BODY.overridable });
    show();
    expect(await screen.findByText('Memory')).toBeInTheDocument();
  });
});
