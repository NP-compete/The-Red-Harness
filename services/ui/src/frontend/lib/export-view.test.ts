import { describe, expect, it } from 'vitest';

import { presentExport } from '@/lib/export-view';

const request = {
  scope: 'thread' as const,
  format: 'json' as const,
  includeAttachments: false,
  containsSensitiveData: false,
  itemCount: 1,
  state: 'ready' as const,
  progress: 0,
  downloadUrl: null as string | null,
  expiresAt: null as string | null,
};

const now = new Date('2026-10-27T09:00:00Z');

describe('presentExport', () => {
  it('says what will be exported', () => {
    expect(presentExport(request, now).summary).toBe('1 conversation as JSON');
  });

  it('counts several items', () => {
    expect(presentExport({ ...request, itemCount: 12 }, now).summary).toBe(
      '12 conversations as JSON',
    );
  });

  it('names the format in a form people recognise', () => {
    expect(presentExport({ ...request, format: 'markdown' }, now).summary).toBe(
      '1 conversation as Markdown',
    );
  });

  it('warns when the export would carry sensitive data out', () => {
    const risky = { ...request, containsSensitiveData: true };
    expect(presentExport(risky, now).warning).toBe(
      'This export contains sensitive data that will leave the platform',
    );
  });

  it('does not warn about ordinary data', () => {
    expect(presentExport(request, now).warning).toBe('');
  });

  it('says attachments are included when they are', () => {
    expect(presentExport({ ...request, includeAttachments: true }, now).includes).toBe(
      'conversations and attachments',
    );
  });

  it('says attachments are left out when they are', () => {
    expect(presentExport(request, now).includes).toBe('conversations only');
  });

  it('can be started when it is ready', () => {
    expect(presentExport(request, now).canStart).toBe(true);
  });

  it('cannot be started while it is running', () => {
    const running = { ...request, state: 'running' as const, progress: 0.4 };
    expect(presentExport(running, now).canStart).toBe(false);
  });

  it('shows progress while it runs', () => {
    const running = { ...request, state: 'running' as const, progress: 0.4 };
    expect(presentExport(running, now).status).toBe('40% done');
  });

  it('offers the file once it is finished', () => {
    const done = {
      ...request,
      state: 'done' as const,
      progress: 1,
      downloadUrl: '/exports/abc',
      expiresAt: '2026-10-28T09:00:00Z',
    };
    expect(presentExport(done, now).downloadUrl).toBe('/exports/abc');
  });

  it('says how long the file will be available', () => {
    const done = {
      ...request,
      state: 'done' as const,
      progress: 1,
      downloadUrl: '/exports/abc',
      expiresAt: '2026-10-28T09:00:00Z',
    };
    expect(presentExport(done, now).status).toBe('Ready, available for 24 hours');
  });

  it('does not offer a file that has expired', () => {
    const stale = {
      ...request,
      state: 'done' as const,
      progress: 1,
      downloadUrl: '/exports/abc',
      expiresAt: '2026-10-26T09:00:00Z',
    };
    expect(presentExport(stale, now).downloadUrl).toBeNull();
  });

  it('says plainly when the file has expired', () => {
    const stale = {
      ...request,
      state: 'done' as const,
      progress: 1,
      downloadUrl: '/exports/abc',
      expiresAt: '2026-10-26T09:00:00Z',
    };
    expect(presentExport(stale, now).status).toBe('The file has expired');
  });

  it('lets an expired export be run again', () => {
    const stale = {
      ...request,
      state: 'done' as const,
      downloadUrl: '/exports/abc',
      expiresAt: '2026-10-26T09:00:00Z',
    };
    expect(presentExport(stale, now).canStart).toBe(true);
  });
});
