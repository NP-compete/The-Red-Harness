import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { RateLimitNotice } from './RateLimitNotice';

describe('RateLimitNotice', () => {
  it('says nothing while requests are getting through', () => {
    const { container } = render(<RateLimitNotice isRateLimited={false} retryAfterSeconds={0} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('says plainly when there have been too many', () => {
    render(<RateLimitNotice isRateLimited retryAfterSeconds={30} />);
    expect(screen.getByText('Too many requests')).toBeInTheDocument();
  });

  it('says how long to wait', () => {
    render(<RateLimitNotice isRateLimited retryAfterSeconds={30} />);
    expect(screen.getByText('Try again in 30 seconds')).toBeInTheDocument();
  });

  it('counts a single second properly', () => {
    render(<RateLimitNotice isRateLimited retryAfterSeconds={1} />);
    expect(screen.getByText('Try again in 1 second')).toBeInTheDocument();
  });

  it('never tells anyone to try again in no time at all', () => {
    // A countdown that reaches zero before the limit lifts invites a
    // retry that fails again.
    render(<RateLimitNotice isRateLimited retryAfterSeconds={0} />);
    expect(screen.getByText('Try again in 1 second')).toBeInTheDocument();
  });

  it('rounds a part second up rather than down', () => {
    render(<RateLimitNotice isRateLimited retryAfterSeconds={2.3} />);
    expect(screen.getByText('Try again in 3 seconds')).toBeInTheDocument();
  });

  it('announces itself to a screen reader', () => {
    render(<RateLimitNotice isRateLimited retryAfterSeconds={5} />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });
});
