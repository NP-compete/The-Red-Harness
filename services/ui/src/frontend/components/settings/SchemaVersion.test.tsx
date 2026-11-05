import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { SchemaVersion } from './SchemaVersion';
import * as api from '../../services/schema-version-api';

function answering(window: unknown) {
  return vi.spyOn(api, 'readSchemaWindow').mockResolvedValue(window as never);
}

const CURRENT = { current: 3, oldestSupported: 2, declared: 3, deprecated: false };

describe('SchemaVersion', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('says nothing while it is still asking', () => {
    vi.spyOn(api, 'readSchemaWindow').mockReturnValue(new Promise(() => {}) as never);
    const { container } = render(<SchemaVersion />);
    expect(container).toBeEmptyDOMElement();
  });

  it('shows the version the configuration declares', async () => {
    answering(CURRENT);
    render(<SchemaVersion />);
    await waitFor(() => expect(screen.getByText('3')).toBeInTheDocument());
  });

  it('shows the versions this build reads beside it', async () => {
    // Without the window, the declared version says nothing about
    // whether the next image will still start.
    answering(CURRENT);
    render(<SchemaVersion />);
    await waitFor(() => expect(screen.getByText(/2–3/)).toBeInTheDocument());
  });

  describe('a configuration on the old end of the window', () => {
    it('is marked', async () => {
      answering({ ...CURRENT, declared: 2, deprecated: true });
      render(<SchemaVersion />);
      await waitFor(() => expect(screen.getByRole('status')).toBeInTheDocument());
    });
  });

  describe('a configuration that declares nothing', () => {
    it('says it declares nothing rather than naming a version', async () => {
      answering({ ...CURRENT, declared: null, deprecated: true });
      render(<SchemaVersion />);
      await waitFor(() =>
        expect(screen.getByText(/not declared/i)).toBeInTheDocument(),
      );
    });
  });

  describe('an agent that could not say', () => {
    it('shows nothing at all', async () => {
      // An older build is not a deployment on version 0.
      answering(null);
      const { container } = render(<SchemaVersion />);
      await waitFor(() => expect(container).toBeEmptyDOMElement());
    });
  });
});
