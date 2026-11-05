import { describe, expect, it } from 'vitest';

import { presentAttachment } from '@/lib/attachment-view';

const file = {
  name: 'report.pdf',
  bytes: 240_000,
  scanned: true,
  safe: true,
  fromAgent: false,
};

describe('presentAttachment', () => {
  it('shows the file name', () => {
    expect(presentAttachment(file).name).toBe('report.pdf');
  });

  it('shows the size in units a person reads', () => {
    expect(presentAttachment(file).size).toBe('240 kB');
  });

  it('describes a document by what it is', () => {
    expect(presentAttachment(file).kind).toBe('document');
  });

  it('recognises an image', () => {
    expect(presentAttachment({ ...file, name: 'chart.png' }).kind).toBe('image');
  });

  it('recognises a spreadsheet', () => {
    expect(presentAttachment({ ...file, name: 'figures.xlsx' }).kind).toBe('spreadsheet');
  });

  it('treats anything unrecognised as just a file', () => {
    expect(presentAttachment({ ...file, name: 'thing.qqq' }).kind).toBe('file');
  });

  it('can preview a document in place', () => {
    expect(presentAttachment(file).canPreview).toBe(true);
  });

  it('never previews something executable', () => {
    const risky = { ...file, name: 'setup.exe' };
    expect(presentAttachment(risky).canPreview).toBe(false);
  });

  it('warns about something executable', () => {
    const risky = { ...file, name: 'setup.exe' };
    expect(presentAttachment(risky).warning).toBe('This kind of file can run code — open it with care');
  });

  it('treats a disguised extension as executable', () => {
    const risky = { ...file, name: 'invoice.pdf.exe' };
    expect(presentAttachment(risky).kind).toBe('program');
  });

  it('does not warn about an ordinary document', () => {
    expect(presentAttachment(file).warning).toBe('');
  });

  it('says plainly when a file has not been checked', () => {
    const unchecked = { ...file, scanned: false };
    expect(presentAttachment(unchecked).status).toBe('not checked yet');
  });

  it('says plainly when a file failed its check', () => {
    const bad = { ...file, safe: false };
    expect(presentAttachment(bad).status).toBe('failed its check');
  });

  it('refuses to download a file that failed its check', () => {
    const bad = { ...file, safe: false };
    expect(presentAttachment(bad).canDownload).toBe(false);
  });

  it('allows downloading a checked file', () => {
    expect(presentAttachment(file).canDownload).toBe(true);
  });

  it('marks a file the agent produced', () => {
    expect(presentAttachment({ ...file, fromAgent: true }).origin).toBe('made by the agent');
  });

  it('marks a file a person provided', () => {
    expect(presentAttachment(file).origin).toBe('you provided this');
  });
});
