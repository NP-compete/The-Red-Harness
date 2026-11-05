import { configureStore } from '@reduxjs/toolkit';
import { render, screen } from '@testing-library/react';
import { Provider } from 'react-redux';
import { describe, expect, it } from 'vitest';

import configReducer from '../../redux/slices/config';
import userSettingsReducer from '../../redux/slices/userSettings';
import { CapabilitiesSection } from './CapabilitiesSection';

const FEATURES = {
  debug_mode_default: false,
  auth_enabled: false,
  memory_enabled: true,
  mcp_apps_enabled: true,
  mcp_dcr_enabled: true,
};

function show(features: Partial<typeof FEATURES> | null, debugMode = false) {
  const store = configureStore({
    reducer: { config: configReducer, userSettings: userSettingsReducer },
    preloadedState: {
      config: {
        branding: null,
        features: features === null ? null : { ...FEATURES, ...features },
        content: null,
        loading: false,
        error: null,
      },
      userSettings: { debugMode } as never,
    } as never,
  });
  return render(
    <Provider store={store}>
      <CapabilitiesSection />
    </Provider>,
  );
}

describe('CapabilitiesSection', () => {
  it('says nothing before the settings have arrived', () => {
    const { container } = show(null);
    expect(container).toBeEmptyDOMElement();
  });

  it('lists a capability that is on', () => {
    show({});
    expect(screen.getByText('Memory')).toBeInTheDocument();
  });

  it('marks what is off', () => {
    show({ memory_enabled: false });
    const row = screen.getByText('Memory').closest('li');
    expect(row).toHaveTextContent('Off');
  });

  it('says who decided it', () => {
    show({ memory_enabled: false });
    expect(screen.getByText('Memory').closest('li')).toHaveTextContent(
      'set for this deployment',
    );
  });

  it('says when the choice is yours', () => {
    show({ debug_mode_default: true }, false);
    expect(screen.getByText('Debug detail').closest('li')).toHaveTextContent(
      'turned off by you',
    );
  });

  it('names what is holding a capability back', () => {
    show({ mcp_apps_enabled: false });
    expect(screen.getByText('App registration').closest('li')).toHaveTextContent(
      'needs Connected apps',
    );
  });

  it('does not claim a blocked capability is on', () => {
    show({ mcp_apps_enabled: false });
    expect(screen.getByText('App registration').closest('li')).toHaveTextContent('Off');
  });

  it('does not claim a capability is on when its switch is absent', () => {
    show({ mcp_dcr_enabled: undefined });
    expect(screen.getByText('App registration').closest('li')).toHaveTextContent('Off');
  });
});
