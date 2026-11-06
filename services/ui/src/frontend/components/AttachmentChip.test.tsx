import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { AttachmentChip } from './AttachmentChip';

const file = {
  filename: 'handbook.pdf',
  path: '/t1/handbook.pdf',
  bytes: 240_000,
  text_extracted: true,
  truncated: false,
};

describe('AttachmentChip', () => {
  it('names the file', () => {
    render(<AttachmentChip file={file} />);
    expect(screen.getByText('handbook.pdf')).toBeInTheDocument();
  });

  it('says how big it is in words a person reads', () => {
    render(<AttachmentChip file={file} />);
    expect(screen.getByText('240 kB')).toBeInTheDocument();
  });

  it('counts a large file in megabytes', () => {
    render(<AttachmentChip file={{ ...file, bytes: 2_400_000 }} />);
    expect(screen.getByText('2.4 MB')).toBeInTheDocument();
  });

  it('counts a tiny file in bytes', () => {
    render(<AttachmentChip file={{ ...file, bytes: 400 }} />);
    expect(screen.getByText('400 B')).toBeInTheDocument();
  });

  it('warns about a file that can run code', () => {
    render(<AttachmentChip file={{ ...file, filename: 'setup.exe' }} />);
    expect(
      screen.getByText('This kind of file can run code — open it with care'),
    ).toBeInTheDocument();
  });

  it('judges the file by its last extension, not a friendly earlier one', () => {
    render(<AttachmentChip file={{ ...file, filename: 'report.pdf.exe' }} />);
    expect(
      screen.getByText('This kind of file can run code — open it with care'),
    ).toBeInTheDocument();
  });

  it('adds no warning to an ordinary document', () => {
    render(<AttachmentChip file={file} />);
    expect(screen.queryByText(/can run code/)).not.toBeInTheDocument();
  });

  it('says when the agent could not read the file', () => {
    render(<AttachmentChip file={{ ...file, text_extracted: false }} />);
    expect(screen.getByText('(not readable)')).toBeInTheDocument();
  });

  it('says when only part of the file was read', () => {
    render(<AttachmentChip file={{ ...file, truncated: true }} />);
    expect(screen.getByText('(truncated)')).toBeInTheDocument();
  });

  it('says when a lesser parser had to stand in', () => {
    render(<AttachmentChip file={{ ...file, degraded: 'docling was unreachable' }} />);
    expect(screen.getByText('(basic parse)')).toBeInTheDocument();
  });

  it('keeps the reason the parser fell back, for whoever asks', () => {
    render(<AttachmentChip file={{ ...file, degraded: 'docling was unreachable' }} />);
    expect(screen.getByTitle('docling was unreachable')).toBeInTheDocument();
  });

  it('says nothing of the sort about a file read in full', () => {
    render(<AttachmentChip file={file} />);
    expect(screen.queryByText('(truncated)')).not.toBeInTheDocument();
  });
});
