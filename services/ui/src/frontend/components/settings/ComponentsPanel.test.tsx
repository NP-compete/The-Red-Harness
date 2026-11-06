import { configureStore } from '@reduxjs/toolkit';
import { render, screen } from '@testing-library/react';
import { Provider } from 'react-redux';
import { describe, expect, it, vi } from 'vitest';

import configReducer from '../../redux/slices/config';
import userSettingsReducer from '../../redux/slices/userSettings';
import toastsReducer from '../../redux/slices/toasts';
import { ComponentsPanel } from './ComponentsPanel';

vi.mock('./McpServerList', () => ({ McpServerList: () => <div>server list</div> }));
vi.mock('./AlwaysAllowedTools', () => ({
  AlwaysAllowedTools: () => <div>tool approvals</div>,
}));
vi.mock('./OAuthConnections', () => ({
  OAuthConnections: () => <div>oauth connections</div>,
}));

function show() {
  const store = configureStore({
    reducer: {
      config: configReducer,
      userSettings: userSettingsReducer,
      toasts: toastsReducer,
    },
  });
  return render(
    <Provider store={store}>
      <ComponentsPanel />
    </Provider>,
  );
}

describe('ComponentsPanel', () => {
  it('lists the servers that can be connected', () => {
    show();
    expect(screen.getByText('server list')).toBeInTheDocument();
  });

  it('shows which tools may run unattended', () => {
    show();
    expect(screen.getByText('tool approvals')).toBeInTheDocument();
  });

  it('shows the connections this account has granted', () => {
    show();
    expect(screen.getByText('oauth connections')).toBeInTheDocument();
  });
});
