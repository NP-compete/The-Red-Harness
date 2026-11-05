/**
 * Naming a specialist or a document in the middle of a sentence.
 *
 * `@` addresses one of the agent's specialists, `#` points at a file
 * it wrote. Both are shorthand for words the person would otherwise
 * have to get exactly right, and both only ever offer what they can
 * already see elsewhere in the interface — picking from this list
 * reaches nothing new.
 */

export type ReferenceKind = 'subagent' | 'document';

export interface Referenceable {
  name: string;
  /** One line, so a list of names is a list of choices. */
  about: string;
}

export interface Reference extends Referenceable {
  kind: ReferenceKind;
}

export interface ReferencePalette {
  open: boolean;
  /** What was asked for, whether or not anything matched. */
  kind?: ReferenceKind;
  matches: Reference[];
  emptyMessage?: string;
}

/**
 * The first sentence of a description, for a list of choices.
 *
 * A specialist's own account of itself is written for the model and
 * runs to a paragraph; printing it whole turns a list of names into
 * a wall of prose.
 */
function oneLine(about: string): string {
  const stop = about.search(/\.(\s|$)/);
  return stop === -1 ? about.trim() : about.slice(0, stop + 1).trim();
}

export interface Known {
  subagents: Referenceable[];
  documents: Referenceable[];
}

const CLOSED: ReferencePalette = { open: false, matches: [] };

// The reference being typed is the one at the end, and only when it
// starts a word: an email address and a colour both carry one of
// these characters without meaning anything by it.
const BEING_TYPED = /(?:^|\s)([@#])([^\s@#]*)$/;

export function openReferences(input: string, known: Known): ReferencePalette {
  const typing = BEING_TYPED.exec(input);
  if (!typing) return CLOSED;

  const [, marker, partial] = typing;
  const kind: ReferenceKind = marker === '@' ? 'subagent' : 'document';
  const from = kind === 'subagent' ? known.subagents : known.documents;

  const needle = partial.toLowerCase();
  const matches = from
    .filter((one) => one.name.toLowerCase().includes(needle))
    .map((one) => ({ ...one, about: oneLine(one.about), kind }));

  return {
    open: true,
    kind,
    matches,
    emptyMessage:
      matches.length === 0
        ? partial
          ? `Nothing here is called "${partial}"`
          : 'There is nothing to reference yet'
        : undefined,
  };
}

/** Finish the reference being typed, leaving the rest of the sentence. */
export function replaceReference(input: string, name: string): string {
  const typing = BEING_TYPED.exec(input);
  if (!typing) return input;
  return `${input.slice(0, typing.index + typing[0].indexOf(typing[1]))}${typing[1]}${name} `;
}
