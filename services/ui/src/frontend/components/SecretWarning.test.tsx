import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { SecretWarning } from './SecretWarning';

describe('SecretWarning', () => {
  it('says nothing about an ordinary message', () => {
    const { container } = render(<SecretWarning text="what is the travel limit?" />);
    expect(container).toBeEmptyDOMElement();
  });

  it('says nothing about an empty box', () => {
    const { container } = render(<SecretWarning text="" />);
    expect(container).toBeEmptyDOMElement();
  });

  it('warns about a password', () => {
    render(<SecretWarning text="password = hunter2secret" />);
    expect(
      screen.getByText('This message looks like it contains a password'),
    ).toBeInTheDocument();
  });

  it('names an access token for what it is', () => {
    render(<SecretWarning text="bearer abcdef1234567890" />);
    expect(
      screen.getByText('This message looks like it contains an access token'),
    ).toBeInTheDocument();
  });

  it('counts several credentials rather than naming one', () => {
    render(<SecretWarning text={'bearer abcdef1234567890\napi_key: abcdef1234567890'} />);
    expect(
      screen.getByText('This message looks like it contains 2 credentials'),
    ).toBeInTheDocument();
  });

  it('says where to look', () => {
    render(<SecretWarning text={'hello\npassword = hunter2secret'} />);
    expect(screen.getByText(/line 2/)).toBeInTheDocument();
  });

  it('never puts the credential on screen', () => {
    render(<SecretWarning text="password = hunter2secret" />);
    expect(screen.queryByText(/hunter2secret/)).not.toBeInTheDocument();
  });

  it('warns rather than refusing', () => {
    render(<SecretWarning text="password = hunter2secret" />);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('announces itself to a screen reader', () => {
    render(<SecretWarning text="password = hunter2secret" />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });
});
