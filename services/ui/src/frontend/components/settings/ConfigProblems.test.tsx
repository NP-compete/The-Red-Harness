import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ConfigProblems } from './ConfigProblems';
import * as api from '../../services/config-problems-api';

function answering(report: unknown) {
  return vi.spyOn(api, 'readConfigProblems').mockResolvedValue(report as never);
}

const PROBLEM = {
  source: 'runtime/agent.yaml',
  detail: "'middleware' is set more than once (line 641, first at line 138)",
};

describe('ConfigProblems', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('says nothing while it is still asking', () => {
    vi.spyOn(api, 'readConfigProblems').mockReturnValue(new Promise(() => {}) as never);
    const { container } = render(<ConfigProblems />);
    expect(container).toBeEmptyDOMElement();
  });

  describe('a configuration that loaded cleanly', () => {
    it('is not worth a warning', async () => {
      // A banner on every healthy deployment is a banner people
      // stop seeing.
      answering({ clean: true, problems: [], unreadable: false });
      const { container } = render(<ConfigProblems />);
      await waitFor(() => expect(container).toBeEmptyDOMElement());
    });
  });

  describe('a configuration that loaded with problems', () => {
    it('says so', async () => {
      answering({ clean: false, problems: [PROBLEM], unreadable: false });
      render(<ConfigProblems />);
      expect(await screen.findByRole('alert')).toBeInTheDocument();
    });

    it('names the file', async () => {
      answering({ clean: false, problems: [PROBLEM], unreadable: false });
      render(<ConfigProblems />);
      expect(await screen.findByText(/runtime\/agent\.yaml/)).toBeInTheDocument();
    });

    it('says what was wrong, including where', async () => {
      // The line number is the whole value: "something is wrong
      // with your configuration" sends somebody reading all of it.
      answering({ clean: false, problems: [PROBLEM], unreadable: false });
      render(<ConfigProblems />);
      expect(await screen.findByText(/line 641/)).toBeInTheDocument();
    });

    it('says what it means, not only what was found', async () => {
      answering({ clean: false, problems: [PROBLEM], unreadable: false });
      render(<ConfigProblems />);
      expect(
        await screen.findByText(/not running the configuration that was written/i),
      ).toBeInTheDocument();
    });

    it('lists every one of them', async () => {
      answering({
        clean: false,
        problems: [PROBLEM, { source: 'runtime/pii.yaml', detail: 'duplicate key' }],
        unreadable: false,
      });
      render(<ConfigProblems />);
      expect(await screen.findByText(/runtime\/pii\.yaml/)).toBeInTheDocument();
    });
  });

  describe('an agent that cannot say', () => {
    it('does not accuse it of anything', async () => {
      // An older build, or one that refused. Neither is a broken
      // configuration, and claiming otherwise would be a fault
      // report nobody can act on.
      answering({ clean: true, problems: [], unreadable: true });
      const { container } = render(<ConfigProblems />);
      await waitFor(() => expect(container).toBeEmptyDOMElement());
    });
  });
});
