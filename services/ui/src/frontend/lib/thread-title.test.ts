import { describe, expect, it } from 'vitest';

import {
  isUnnamed,
  previewFor,
  suggestTitle,
  titleFor,
  UNTITLED,
} from './thread-title';

const human = (content: string) => ({ type: 'human', content });
const ai = (content: string) => ({ type: 'ai', content });

describe('suggestTitle', () => {
  it('names a conversation after what was asked', () => {
    expect(suggestTitle([human('What is the travel limit?')])).toBe(
      'What is the travel limit?',
    );
  });

  it('keeps the name when the answer arrives', () => {
    expect(suggestTitle([human('What is the travel limit?'), ai('It is 500 euros.')])).toBe(
      'What is the travel limit?',
    );
  });

  it('keeps the name when the conversation goes on', () => {
    const chat = [human('What is the travel limit?'), ai('500 euros.'), human('And hotels?')];
    expect(suggestTitle(chat)).toBe('What is the travel limit?');
  });

  it('drops the politeness nobody scans a list by', () => {
    expect(suggestTitle([human('Can you please tell me the travel limit?')])).toBe(
      'Tell me the travel limit?',
    );
  });

  it('shortens a long question on a word boundary', () => {
    const asked = 'What is the travel limit for employees who are flying to another country';
    const title = suggestTitle([human(asked)]);
    expect(title.length).toBeLessThanOrEqual(48);
    expect(title.endsWith('…')).toBe(true);
    expect(title).not.toMatch(/\s…$/);
  });

  it('withholds a question carrying an email address', () => {
    expect(suggestTitle([human('Who manages sodutta@redhat.com?')])).toBe(UNTITLED);
  });

  it('withholds a question carrying something that looks like a key', () => {
    expect(suggestTitle([human('Is sk7f3kd92mfkd0192x valid?')])).toBe(UNTITLED);
  });

  it('is not fooled into withholding an ordinary long word', () => {
    expect(suggestTitle([human('Explain internationalisation to me')])).toBe(
      'Explain internationalisation to me',
    );
  });

  it('has a name for a conversation with nothing in it', () => {
    expect(suggestTitle([])).toBe(UNTITLED);
  });

  it('has a name for a conversation nobody has spoken in', () => {
    expect(suggestTitle([ai('Hello.')])).toBe(UNTITLED);
  });

  it('collapses the whitespace of a pasted question', () => {
    expect(suggestTitle([human('What is\n  the   limit?')])).toBe('What is the limit?');
  });

  it('reads the text out of a structured message', () => {
    const message = { type: 'human', content: [{ type: 'text', text: 'What is the limit?' }] };
    expect(suggestTitle([message])).toBe('What is the limit?');
  });
});

describe('titleFor', () => {
  it('names a conversation after the prompt that opened it', () => {
    expect(titleFor('What is the travel limit?')).toBe('What is the travel limit?');
  });

  it('drops the politeness here too', () => {
    expect(titleFor('Please can you tell me the travel limit?')).toBe(
      'Tell me the travel limit?',
    );
  });

  it('never cuts a word in half', () => {
    const title = titleFor('What is the travel limit for contractors working abroad');
    expect(title.endsWith('…')).toBe(true);
    expect(title.replace('…', '').endsWith(' ')).toBe(false);
    expect(title).not.toContain('contracto…');
  });

  it('withholds a prompt carrying an email address', () => {
    expect(titleFor('Who manages sodutta@redhat.com?')).toBe(UNTITLED);
  });

  it('has a name for an empty prompt', () => {
    expect(titleFor('')).toBe(UNTITLED);
  });
});

describe('isUnnamed', () => {
  it('knows the placeholder this module hands out', () => {
    expect(isUnnamed(UNTITLED)).toBe(true);
  });

  it('knows the placeholders the app used before it', () => {
    expect(isUnnamed('New Chat')).toBe(true);
    expect(isUnnamed('Chat')).toBe(true);
    expect(isUnnamed('Untitled chat')).toBe(true);
  });

  it('ignores the casing of those', () => {
    expect(isUnnamed('new chat')).toBe(true);
  });

  it('treats an empty title as unnamed', () => {
    expect(isUnnamed('')).toBe(true);
    expect(isUnnamed(undefined)).toBe(true);
  });

  it('leaves a real name alone', () => {
    expect(isUnnamed('What is the travel limit?')).toBe(false);
  });
});

describe('previewFor', () => {
  it('shows enough of the question to recognise the chat by', () => {
    expect(previewFor('What is the travel limit for contractors?')).toBe(
      'What is the travel limit for contractors?',
    );
  });

  it('keeps the politeness, unlike a title', () => {
    // A preview is the message, not a label; trimming it twice over
    // would make two different renderings of the same sentence.
    expect(previewFor('Please tell me the limit')).toBe('Please tell me the limit');
  });

  it('cuts a long question on a word boundary', () => {
    const long =
      'What is the travel limit for contractors who are flying abroad next quarter and claiming hotels?';
    const preview = previewFor(long);
    expect(preview.endsWith('…')).toBe(true);
    expect(preview.length).toBeLessThanOrEqual(81);
  });

  it('shows nothing rather than publish an address', () => {
    expect(previewFor('Who manages sodutta@redhat.com?')).toBe('');
  });

  it('shows nothing rather than publish a key', () => {
    expect(previewFor('Is sk7f3kd92mfkd0192x valid?')).toBe('');
  });

  it('has nothing to show for an empty message', () => {
    expect(previewFor('')).toBe('');
  });
});


describe('a conversation that has been shortened', () => {
  const summary = {
    type: 'human',
    content: 'Here is a summary of the conversation to date:\n\nThey asked about the fee.',
  } as unknown as Message;

  it('is not named after the summary standing in for its oldest turns', () => {
    const asked = { type: 'human', content: 'What is the onboarding fee?' } as unknown as Message;
    expect(suggestTitle([summary, asked])).toBe('What is the onboarding fee?');
  });

  it('stays unnamed rather than taking the summary as its name', () => {
    expect(isUnnamed(suggestTitle([summary]))).toBe(true);
  });
});
