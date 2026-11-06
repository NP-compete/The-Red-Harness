import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it } from 'vitest';

import { RequirePrivilege } from './RequirePrivilege';
import { rememberAuthEnabled } from '../lib/role-utils';

function appData(data: Record<string, unknown> | undefined) {
  (window as unknown as { APP_DATA?: unknown }).APP_DATA = data;
}

afterEach(() => {
  appData(undefined);
  rememberAuthEnabled(undefined);
});

function show() {
  return render(
    <MemoryRouter initialEntries={['/secret']}>
      <Routes>
        <Route path="/" element={<p>home</p>} />
        <Route
          path="/secret"
          element={
            <RequirePrivilege>
              <p>the page</p>
            </RequirePrivilege>
          }
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe('RequirePrivilege', () => {
  it('lets an owner in', () => {
    appData({ userRole: 'owners' });
    show();
    expect(screen.getByText('the page')).toBeInTheDocument();
  });

  it('sends an ordinary user home', () => {
    appData({ userRole: 'users' });
    show();
    expect(screen.getByText('home')).toBeInTheDocument();
  });

  it('waits rather than deciding before the answer is in', () => {
    appData({});
    show();
    expect(screen.queryByText('home')).not.toBeInTheDocument();
  });

  it('does not show the page while it is still waiting', () => {
    appData({});
    show();
    expect(screen.queryByText('the page')).not.toBeInTheDocument();
  });

  it('lets the reader in once the settings say sign-in is off', () => {
    appData({});
    rememberAuthEnabled(false);
    show();
    expect(screen.getByText('the page')).toBeInTheDocument();
  });
});
