import type { Message } from '@langchain/langgraph-sdk';
import { describe, expect, it } from 'vitest';

import { exportAsMarkdown } from './export-chat';

const messages = [
  { id: '1', type: 'human', content: 'What is the travel limit?' },
  { id: '2', type: 'ai', content: '500 euros.' },
] as Message[];

const marking = {
  exportId: 'exp-123',
  organisation: 'Northwind',
  classification: 'internal',
  exportedAt: new Date('2026-03-01T12:00:00Z'),
};

describe('exportAsMarkdown with a marking', () => {
  it('still contains the conversation', () => {
    const md = exportAsMarkdown(messages, 'Chat', marking);
    expect(md).toContain('500 euros.');
  });

  it('records where the file came from', () => {
    const md = exportAsMarkdown(messages, 'Chat', marking);
    expect(md).toContain('Northwind');
  });

  it('records how the content is classified', () => {
    const md = exportAsMarkdown(messages, 'Chat', marking);
    expect(md).toContain('internal');
  });

  it('carries a reference the export can be traced by', () => {
    const md = exportAsMarkdown(messages, 'Chat', marking);
    expect(md).toContain('exp-123');
  });

  it('records the date it left', () => {
    const md = exportAsMarkdown(messages, 'Chat', marking);
    expect(md).toContain('2026-03-01');
  });

  it('puts the note at the end, not in the middle of the conversation', () => {
    const md = exportAsMarkdown(messages, 'Chat', marking);
    expect(md.indexOf('exp-123')).toBeGreaterThan(md.indexOf('500 euros.'));
  });

  it('never names the person who exported it in the file', () => {
    const md = exportAsMarkdown(messages, 'Chat', { ...marking, organisation: 'Northwind' });
    expect(md).not.toContain('@');
  });

  it('leaves a public export unmarked', () => {
    const md = exportAsMarkdown(messages, 'Chat', { ...marking, classification: 'public' });
    expect(md).not.toContain('exp-123');
  });

  it('leaves an unmarked export alone', () => {
    const md = exportAsMarkdown(messages, 'Chat');
    expect(md).not.toContain('Exported');
  });
});
