/**
 * An answer turned into something worth hearing.
 *
 * Markdown read out character by character is unlistenable: hashes
 * before a heading, the whole of a URL after its link text, and forty
 * lines of a shell script spelled out one flag at a time. What a
 * listener wants is the prose, in order, with the code announced
 * rather than recited.
 */

const CODE_SAID = 'a code block';
const RULE = /^(-{3,}|\*{3,}|_{3,})$/;
const TABLE_DIVIDER = /^:?-{2,}:?$/;

function cells(line: string): string[] {
  return line
    .split('|')
    .map((cell) => cell.trim())
    .filter((cell) => cell.length > 0);
}

function inline(text: string): string {
  return text
    .replace(/!?\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/__([^_]+)__/g, '$1')
    .replace(/\*([^*]+)\*/g, '$1')
    .replace(/(^|\s)_([^_]+)_(?=\s|$|[.,;:!?])/g, '$1$2')
    .replace(/\s+/g, ' ')
    .trim();
}

function stopped(text: string): string {
  return /[.!?:,;]$/.test(text) ? text : `${text}.`;
}

export function speakable(markdown: string): string {
  const said: string[] = [];
  let inFence = false;

  for (const raw of markdown.split('\n')) {
    if (/^\s*(```|~~~)/.test(raw)) {
      if (!inFence) said.push(CODE_SAID);
      inFence = !inFence;
      continue;
    }
    if (inFence) continue;

    let line = raw.trim();
    if (!line || RULE.test(line)) continue;

    if (line.startsWith('|')) {
      const parts = cells(line);
      if (parts.length === 0 || parts.every((part) => TABLE_DIVIDER.test(part))) continue;
      line = parts.join(', ');
    }

    line = line
      .replace(/^#{1,6}\s*/, '')
      .replace(/^>+\s*/, '')
      .replace(/^[-*+]\s+/, '')
      .replace(/^\d+[.)]\s+/, '');

    const spoken = inline(line);
    if (spoken) said.push(spoken);
  }

  // A message that is nothing but code has no prose to read, and
  // announcing the code on its own tells the listener nothing.
  if (said.every((part) => part === CODE_SAID)) return '';

  return said.map(stopped).join(' ');
}
