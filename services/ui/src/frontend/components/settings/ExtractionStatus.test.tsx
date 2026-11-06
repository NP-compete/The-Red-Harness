import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ExtractionStatus } from './ExtractionStatus';

const api = vi.hoisted(() => ({ getExtractionStatus: vi.fn() }));
vi.mock('../../services/extraction-status', () => api);

const OK = {
  engine: 'builtin',
  reachable: true,
  detail: 'built-in parsers',
  fallback: true,
  handles: [],
  maxBytes: 20971520,
};

beforeEach(() => {
  vi.clearAllMocks();
  api.getExtractionStatus.mockResolvedValue(OK);
});

describe('ExtractionStatus', () => {
  it('names what reads attachments', async () => {
    render(<ExtractionStatus />);
    expect(await screen.findByText(/builtin/)).toBeInTheDocument();
  });

  it('says the largest file it will read', async () => {
    render(<ExtractionStatus />);
    expect(await screen.findByText(/20 MB/)).toBeInTheDocument();
  });

  it('warns when it cannot be reached', async () => {
    api.getExtractionStatus.mockResolvedValue({
      ...OK,
      reachable: false,
      detail: 'connection refused',
    });
    render(<ExtractionStatus />);
    expect(await screen.findByText(/cannot be reached/i)).toBeInTheDocument();
    expect(screen.getByText(/connection refused/)).toBeInTheDocument();
  });

  it('says what happens to a file it cannot read', async () => {
    render(<ExtractionStatus />);
    expect(await screen.findByText(/built-in parsers instead/i)).toBeInTheDocument();
  });

  it('warns when nothing takes over', async () => {
    api.getExtractionStatus.mockResolvedValue({ ...OK, fallback: false });
    render(<ExtractionStatus />);
    expect(await screen.findByText(/will not be read/i)).toBeInTheDocument();
  });

  it('lists the kinds it handles when it names any', async () => {
    api.getExtractionStatus.mockResolvedValue({
      ...OK,
      engine: 'external',
      handles: ['.pdf', '.docx'],
    });
    render(<ExtractionStatus />);
    expect(await screen.findByText(/\.pdf, \.docx/)).toBeInTheDocument();
  });

  it('says nothing when the agent will not say', async () => {
    api.getExtractionStatus.mockResolvedValue(null);
    const { container } = render(<ExtractionStatus />);
    await vi.waitFor(() => expect(api.getExtractionStatus).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });
});
