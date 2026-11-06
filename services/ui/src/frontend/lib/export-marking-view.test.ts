import { describe, expect, it } from 'vitest';

import { presentMarking } from '@/lib/export-marking-view';

const marked = {
  marked: true,
  placement: 'footer' as const,
  exportId: 'a1b2c3d4e5f6',
  format: 'markdown',
  classification: 'internal',
};

describe('presentMarking', () => {
  it('says the file carries a mark', () => {
    expect(presentMarking(marked).headline).toBe('This file is marked');
  });

  it('explains what the mark is for', () => {
    expect(presentMarking(marked).detail).toBe(
      'A note at the end records where this came from',
    );
  });

  it('shows the reference so it can be quoted', () => {
    expect(presentMarking(marked).reference).toBe('a1b2c3d4e5f6');
  });

  it('says plainly when a format could not be marked', () => {
    const plain = { ...marked, marked: false, placement: 'none' as const, format: 'json' };
    expect(presentMarking(plain).headline).toBe('This file carries no mark');
  });

  it('explains that the export is still recorded', () => {
    const plain = { ...marked, marked: false, placement: 'none' as const, format: 'json' };
    expect(presentMarking(plain).detail).toBe('The export is still recorded against your account');
  });

  it('still shows the reference for an unmarked format', () => {
    const plain = { ...marked, marked: false, placement: 'none' as const, format: 'json' };
    expect(presentMarking(plain).reference).toBe('a1b2c3d4e5f6');
  });

  it('warns before exporting something confidential', () => {
    const sensitive = { ...marked, classification: 'confidential' };
    expect(presentMarking(sensitive).warning).toBe(
      'This is confidential — do not share it outside your organisation',
    );
  });

  it('does not warn about internal material', () => {
    expect(presentMarking(marked).warning).toBe('');
  });

  it('treats a confidential export as worth a second look', () => {
    const sensitive = { ...marked, classification: 'confidential' };
    expect(presentMarking(sensitive).severity).toBe('medium');
  });

  it('treats an ordinary export as routine', () => {
    expect(presentMarking(marked).severity).toBe('info');
  });

  it('never claims an unmarked file is traceable from its contents', () => {
    const plain = { ...marked, marked: false, placement: 'none' as const, format: 'json' };
    expect(presentMarking(plain).traceableFromFile).toBe(false);
  });

  it('says a marked file is traceable from its contents', () => {
    expect(presentMarking(marked).traceableFromFile).toBe(true);
  });

  it('never shows who exported it', () => {
    // The person is in the record, not on the face of the dialog.
    expect(JSON.stringify(presentMarking(marked))).not.toContain('ana');
  });
});
