import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

const source = readFileSync(join(__dirname, '..', 'Sidebar.tsx'), 'utf-8');

/**
 * Every row in the list carries these, and they are read aloud.
 *
 * A screen reader in Spanish announcing "Rename chat:" on every
 * conversation is the least visible kind of untranslated string and
 * the most repeated.
 */
describe('the labels on a conversation row', () => {
  it('does not name the rename control in English in the source', () => {
    expect(source).not.toMatch(/aria-label=\{`Rename chat:/);
  });

  it('does not name the delete control in English in the source', () => {
    expect(source).not.toMatch(/aria-label=\{`Delete chat:/);
  });

  it('asks for them through the translator instead', () => {
    expect(source).toMatch(/t\('sidebar\.renameChat'/);
    expect(source).toMatch(/t\('sidebar\.deleteChatNamed'/);
  });
});

describe('controls above the conversation list', () => {
  it('asks the translator for the bulk-selection control', () => {
    expect(source).not.toMatch(/'Done' : 'Select'/);
    expect(source).toMatch(/t\('sidebar\.(doneSelecting|selectChats)'/);
  });
});

describe('the developer-mode toggle', () => {
  const toggle = readFileSync(join(__dirname, '..', 'DebugToggle.tsx'), 'utf-8');

  it('is named through the translator', () => {
    expect(toggle).not.toMatch(/>Developer mode</);
    expect(toggle).toMatch(/t\('settings\.tabs\.developers'|t\('sidebar\.developerMode'/);
  });
});
