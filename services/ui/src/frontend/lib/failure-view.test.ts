import { describe, expect, it } from 'vitest';

import { presentFailure } from '@/lib/failure-view';

const failure = {
  message: 'The mail step could not be completed.',
  detail: '',
  reference: 'a1b2c3d4e5f6',
  retryable: false,
};

describe('presentFailure', () => {
  it('shows the message it was given', () => {
    expect(presentFailure(failure, { isOperator: false }).message).toBe(
      'The mail step could not be completed.',
    );
  });

  it('shows the reference so it can be quoted', () => {
    expect(presentFailure(failure, { isOperator: false }).reference).toBe('a1b2c3d4e5f6');
  });

  it('tells the person what the reference is for', () => {
    expect(presentFailure(failure, { isOperator: false }).referenceNote.toLowerCase()).toContain(
      'quote',
    );
  });

  it('offers a retry when the failure may clear', () => {
    expect(presentFailure({ ...failure, retryable: true }, { isOperator: false }).action).toBe(
      'retry',
    );
  });

  it('offers to report rather than retry when it will not clear', () => {
    expect(presentFailure(failure, { isOperator: false }).action).toBe('report');
  });

  it('hides the technical detail from an ordinary reader', () => {
    const withDetail = { ...failure, detail: 'File "/opt/app/mail.py", line 88' };
    expect(presentFailure(withDetail, { isOperator: false }).detail).toBe('');
  });

  it('shows the technical detail to an operator', () => {
    const withDetail = { ...failure, detail: 'File "/opt/app/mail.py", line 88' };
    expect(presentFailure(withDetail, { isOperator: true }).detail).toBe(
      'File "/opt/app/mail.py", line 88',
    );
  });

  it('keeps the detail collapsed until it is asked for', () => {
    const withDetail = { ...failure, detail: 'File "/opt/app/mail.py", line 88' };
    expect(presentFailure(withDetail, { isOperator: true }).detailOpen).toBe(false);
  });

  it('does not offer to expand detail that is not there', () => {
    expect(presentFailure(failure, { isOperator: true }).hasDetail).toBe(false);
  });

  it('offers to expand detail that is there', () => {
    const withDetail = { ...failure, detail: 'something technical' };
    expect(presentFailure(withDetail, { isOperator: true }).hasDetail).toBe(true);
  });

  it('never claims the run succeeded', () => {
    expect(presentFailure(failure, { isOperator: false }).succeeded).toBe(false);
  });

  it('does not show a blank message when none was given', () => {
    const blank = { ...failure, message: '' };
    expect(presentFailure(blank, { isOperator: false }).message).toBe(
      'Something went wrong while running this step.',
    );
  });
});
