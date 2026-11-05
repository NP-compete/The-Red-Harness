import { describe, expect, it } from 'vitest';

import { provenanceOf } from './message-provenance';

describe('provenanceOf', () => {
  it('uses what the agent sent when it sent any', () => {
    const found = provenanceOf({ provenance: { model: 'given' }, response_metadata: { model_name: 'derived' } });
    expect(found?.model).toBe('given');
  });

  it('names the model from the reply metadata otherwise', () => {
    expect(provenanceOf({ response_metadata: { model_name: 'gemini-3.8-flash' } })?.model).toBe(
      'gemini-3.8-flash',
    );
  });

  it('reports an answer that was cut off', () => {
    const found = provenanceOf({ response_metadata: { finish_reason: 'length' } });
    expect(found?.truncated).toBe(true);
  });

  it('does not call an ordinary stop a truncation', () => {
    const found = provenanceOf({ response_metadata: { finish_reason: 'STOP' } });
    expect(found?.truncated).toBeUndefined();
  });

  it('carries how many personal details were held back', () => {
    expect(provenanceOf({ additional_kwargs: { pii_scrubbed: 4 } })?.pii_scrubbed).toBe(4);
  });

  it('ignores a count of none', () => {
    expect(provenanceOf({ additional_kwargs: { pii_scrubbed: 0 } })).toBeUndefined();
  });

  it('carries the notes when the answer rests on something shaky', () => {
    const notes = { stance: 'hedged' };
    expect(provenanceOf({ additional_kwargs: { answer_notes: notes } })?.answer_notes).toEqual(
      notes,
    );
  });

  it('leaves out notes that say nothing was wrong', () => {
    const notes = { stance: 'plain', figures: { checked: 3, unsupported: [] } };
    expect(provenanceOf({ additional_kwargs: { answer_notes: notes } })).toBeUndefined();
  });

  it('keeps notes that name an untraceable figure', () => {
    const notes = { stance: 'plain', figures: { checked: 2, unsupported: ['750'] } };
    expect(provenanceOf({ additional_kwargs: { answer_notes: notes } })?.answer_notes).toEqual(
      notes,
    );
  });

  it('keeps notes about a question only half answered', () => {
    const notes = { coverage: { complete: false, parts: ['when it is due'] } };
    expect(provenanceOf({ additional_kwargs: { answer_notes: notes } })?.answer_notes).toEqual(
      notes,
    );
  });

  it('keeps notes about a tool a spent budget took away', () => {
    // Otherwise the answer is quietly thinner with nothing to say why.
    const notes = { budget: { withheld: ['grep'], scope: 'block', limit: 3 } };
    expect(provenanceOf({ additional_kwargs: { answer_notes: notes } })?.answer_notes).toEqual(
      notes,
    );
  });

  it('keeps notes about material that tried to give instructions', () => {
    const notes = { injection: { signals: ['override'], evidence: ['ignore the above'] } };
    expect(provenanceOf({ additional_kwargs: { answer_notes: notes } })?.answer_notes).toEqual(
      notes,
    );
  });

  it('carries the routing the agent recorded', () => {
    const found = provenanceOf({ additional_kwargs: { routed_tier: 'fast', routed_by: 'rule' } });
    expect(found).toMatchObject({ routed_tier: 'fast', routed_by: 'rule' });
  });

  it('says nothing about an ordinary reply', () => {
    expect(provenanceOf({ response_metadata: { finish_reason: 'STOP' }, content: 'hi' })).toEqual({
      finish_reason: 'STOP',
    });
  });

  it('carries what the run was told about its spending', () => {
    const found = provenanceOf({
      additional_kwargs: { spend_warning: 'This run has spent 0.60 USD of its 1.00 USD limit.' },
    });
    expect(found?.spend_warning).toBe('This run has spent 0.60 USD of its 1.00 USD limit.');
  });

  it('says nothing about spending when the run was told nothing', () => {
    expect(provenanceOf({ additional_kwargs: { spend_warning: '' } })).toBeUndefined();
  });

  it('ignores a spending note that is not a sentence', () => {
    expect(provenanceOf({ additional_kwargs: { spend_warning: 42 } })).toBeUndefined();
  });

  it('says nothing at all when there is nothing to go on', () => {
    expect(provenanceOf({})).toBeUndefined();
  });
});
