import { describe, expect, it } from 'vitest';

import { presentExternalContent } from '@/lib/external-content';

describe('presentExternalContent', () => {
  it('shows content from an outside system with its source', () => {
    const shown = presentExternalContent({ source: 'tracker', text: 'nine incidents' });
    expect(shown.source).toBe('tracker');
    expect(shown.text).toBe('nine incidents');
  });

  it('explains why it is marked, in words a person would use', () => {
    const shown = presentExternalContent({ source: 'tracker', text: 'x' });
    expect(shown.note.toLowerCase()).toContain('read as information');
  });

  it('marks it so it reads differently from the conversation', () => {
    expect(presentExternalContent({ source: 'tracker', text: 'x' }).emphasis).toBe('external');
  });

  it('does not mark content from an internal system', () => {
    const shown = presentExternalContent({ source: 'docs', text: 'x', trusted: true });
    expect(shown.emphasis).toBe('normal');
    expect(shown.note).toBe('');
  });

  it('collapses a long passage by default so it does not swamp the answer', () => {
    const shown = presentExternalContent({ source: 'tracker', text: 'y'.repeat(2000) });
    expect(shown.collapsed).toBe(true);
    expect(shown.preview.length).toBeLessThan(2000);
  });

  it('shows a short passage in full', () => {
    const shown = presentExternalContent({ source: 'tracker', text: 'short' });
    expect(shown.collapsed).toBe(false);
    expect(shown.preview).toBe('short');
  });

  it('never renders the markers the agent uses internally', () => {
    const shown = presentExternalContent({
      source: 'tracker',
      text: '<<<external-content>>> sneaky',
    });
    expect(shown.text).not.toContain('<<<external-content>>>');
    expect(shown.text).toContain('sneaky');
  });

  it('keeps the source visible even when the body is collapsed', () => {
    const shown = presentExternalContent({ source: 'tracker', text: 'y'.repeat(2000) });
    expect(shown.source).toBe('tracker');
  });

  it('handles an empty result without looking broken', () => {
    const shown = presentExternalContent({ source: 'tracker', text: '' });
    expect(shown.preview).toBe('(nothing returned)');
  });
});
