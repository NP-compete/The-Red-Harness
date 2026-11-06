import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { DebugToggle } from './DebugToggle';
import { renderWithProviders } from '../test-utils/render';

describe('DebugToggle', () => {
  it('says what it is rather than leaving an icon to guess at', () => {
    renderWithProviders(<DebugToggle />);
    expect(screen.getByText('Developer mode')).toBeInTheDocument();
  });

  it('is a control a screen reader can find by name', () => {
    renderWithProviders(<DebugToggle />);
    expect(screen.getByRole('button', { name: /developer mode/i })).toBeInTheDocument();
  });

  it('shows that it is off', () => {
    renderWithProviders(<DebugToggle />);
    expect(screen.getByRole('button', { name: /developer mode/i })).toHaveAttribute(
      'aria-pressed',
      'false',
    );
  });

  it('turns on when pressed', async () => {
    renderWithProviders(<DebugToggle />);
    await userEvent.click(screen.getByRole('button', { name: /developer mode/i }));
    expect(screen.getByRole('button', { name: /developer mode/i })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
  });

  it('starts on when the workspace has it on', () => {
    renderWithProviders(<DebugToggle />, {
      preloadedState: { userSettings: { debugMode: true } },
    });
    expect(screen.getByRole('button', { name: /developer mode/i })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
  });

  it('turns off again when pressed twice', async () => {
    renderWithProviders(<DebugToggle />);
    const toggle = () => screen.getByRole('button', { name: /developer mode/i });
    await userEvent.click(toggle());
    await userEvent.click(toggle());
    expect(toggle()).toHaveAttribute('aria-pressed', 'false');
  });
});
