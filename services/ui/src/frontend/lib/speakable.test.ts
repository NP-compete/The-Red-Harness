import { describe, expect, it } from 'vitest';

import { speakable } from './speakable';

describe('speakable', () => {
  it('keeps ordinary prose as it is', () => {
    expect(speakable('The deployment finished.')).toBe('The deployment finished.');
  });

  it('does not read punctuation that only marks emphasis', () => {
    expect(speakable('This is **important** and _urgent_.')).toBe(
      'This is important and urgent.',
    );
  });

  it('does not read the hashes of a heading', () => {
    expect(speakable('## Findings\n\nTwo of them.')).toBe('Findings. Two of them.');
  });

  it('says a list item is a list item rather than reading the bullet', () => {
    expect(speakable('- first\n- second')).toBe('first. second.');
  });

  it('reads the words of a link, not its address', () => {
    expect(speakable('See [the runbook](https://example.com/rb) for more.')).toBe(
      'See the runbook for more.',
    );
  });

  it('does not read a code block out loud', () => {
    const said = speakable('Run this:\n\n```sh\nrm -rf /tmp/x && echo done\n```\n\nThen stop.');
    expect(said).not.toContain('rm -rf');
  });

  it('says that a code block was there', () => {
    const said = speakable('Run this:\n\n```sh\nmake test\n```');
    expect(said).toMatch(/code/i);
  });

  it('reads short inline code as the words it is', () => {
    expect(speakable('Call `make test` first.')).toBe('Call make test first.');
  });

  it('reads a table row as a sentence, not as pipes', () => {
    const said = speakable('| Name | Age |\n| --- | --- |\n| Ada | 36 |');
    expect(said).not.toContain('|');
    expect(said).toContain('Ada');
  });

  it('drops the dashes that only draw a table', () => {
    expect(speakable('| a |\n| --- |\n| b |')).not.toContain('---');
  });

  it('collapses the blank lines between paragraphs', () => {
    expect(speakable('One.\n\n\n\nTwo.')).toBe('One. Two.');
  });

  it('has nothing to say about an empty message', () => {
    expect(speakable('')).toBe('');
  });

  it('has nothing to say about a message that is only a code block', () => {
    // Pronouncing "code block" alone is noise; there is no prose here.
    expect(speakable('```\nx = 1\n```')).toBe('');
  });

  it('does not read a horizontal rule', () => {
    expect(speakable('One.\n\n---\n\nTwo.')).toBe('One. Two.');
  });

  it('does not double the full stop a sentence already has', () => {
    expect(speakable('- Done.\n- Also done.')).toBe('Done. Also done.');
  });

  it('reads a numbered list without reading the markers twice', () => {
    expect(speakable('1. first\n2. second')).toBe('first. second.');
  });

  it('keeps a blockquote, which is still somebody talking', () => {
    expect(speakable('> it broke')).toBe('it broke.');
  });
});
