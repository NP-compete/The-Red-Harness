import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ThreadTokenUsageLine } from './ThreadTokenUsageLine';

const api = vi.hoisted(() => ({ getThreadTokenUsage: vi.fn() }));
vi.mock('../services/token-usage-api', () => api);

const rates = vi.hoisted(() => ({ priceTokens: vi.fn() }));
vi.mock('../services/rates-api', () => rates);

beforeEach(() => {
  vi.clearAllMocks();
  rates.priceTokens.mockResolvedValue(null);
  api.getThreadTokenUsage.mockResolvedValue({
    used: 13500,
    inputTokens: 12300,
    outputTokens: 1200,
  });
});

describe('ThreadTokenUsageLine', () => {
  it('says what the conversation has used', async () => {
    render(<ThreadTokenUsageLine threadId="t1" />);
    expect(await screen.findByText(/13.5k tokens/)).toBeInTheDocument();
  });

  it('splits what went in from what came back', async () => {
    render(<ThreadTokenUsageLine threadId="t1" />);
    expect(await screen.findByText(/12.3k in · 1.2k out/)).toBeInTheDocument();
  });

  it('counts a small conversation exactly', async () => {
    api.getThreadTokenUsage.mockResolvedValue({ used: 940, inputTokens: 900, outputTokens: 40 });
    render(<ThreadTokenUsageLine threadId="t1" />);
    expect(await screen.findByText(/940 tokens/)).toBeInTheDocument();
  });

  it('shows nothing when tracking is off', async () => {
    api.getThreadTokenUsage.mockResolvedValue(null);
    const { container } = render(<ThreadTokenUsageLine threadId="t1" />);
    await vi.waitFor(() => expect(api.getThreadTokenUsage).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });

  it('shows nothing before the answer arrives', () => {
    const { container } = render(<ThreadTokenUsageLine threadId="t1" />);
    expect(container).toBeEmptyDOMElement();
  });

  const answer = (input: number, output: number, cacheRead = 0) => ({
    type: 'ai',
    usage_metadata: {
      input_tokens: input,
      output_tokens: output,
      total_tokens: input + output,
      input_token_details: { cache_read: cacheRead },
    },
  });

  it('counts the conversation itself when the agent keeps no record', async () => {
    api.getThreadTokenUsage.mockResolvedValue(null);
    render(<ThreadTokenUsageLine threadId="t1" messages={[answer(8930, 170)]} />);
    expect(await screen.findByText(/9.1k tokens/)).toBeInTheDocument();
  });

  it('prefers the record the agent kept over the turns on screen', async () => {
    render(<ThreadTokenUsageLine threadId="t1" messages={[answer(10, 5)]} />);
    expect(await screen.findByText(/13.5k tokens/)).toBeInTheDocument();
  });

  it('says how much of the input was read from cache', async () => {
    api.getThreadTokenUsage.mockResolvedValue(null);
    render(<ThreadTokenUsageLine threadId="t1" messages={[answer(1000, 100, 800)]} />);
    expect(await screen.findByText(/800 cached/)).toBeInTheDocument();
  });

  it('says nothing about cache when none was read', async () => {
    api.getThreadTokenUsage.mockResolvedValue(null);
    render(<ThreadTokenUsageLine threadId="t1" messages={[answer(1000, 100)]} />);
    expect(await screen.findByText(/1.1k tokens/)).toBeInTheDocument();
    expect(screen.queryByText(/cached/)).not.toBeInTheDocument();
  });

  it('says how many times the model was asked', async () => {
    render(<ThreadTokenUsageLine threadId="t1" messages={[answer(10, 5), answer(10, 5)]} />);
    expect(await screen.findByText(/2 model calls/)).toBeInTheDocument();
  });

  it('counts a single round in the singular', async () => {
    render(<ThreadTokenUsageLine threadId="t1" messages={[answer(10, 5)]} />);
    expect(await screen.findByText(/1 model call\b/)).toBeInTheDocument();
  });

  it('says how many tools those turns used', async () => {
    const withTools = {
      ...answer(10, 5),
      tool_calls: [{ name: 'search', args: {}, id: 'c1' }],
    };
    render(<ThreadTokenUsageLine threadId="t1" messages={[withTools]} />);
    expect(await screen.findByText(/1 tool call/)).toBeInTheDocument();
  });

  it('leaves tools out when none were used', async () => {
    render(<ThreadTokenUsageLine threadId="t1" messages={[answer(10, 5)]} />);
    expect(await screen.findByText(/1 model call/)).toBeInTheDocument();
    expect(screen.queryByText(/tool call/)).not.toBeInTheDocument();
  });

  it('can be read by someone not looking at the screen', async () => {
    api.getThreadTokenUsage.mockResolvedValue(null);
    render(<ThreadTokenUsageLine threadId="t1" messages={[answer(8930, 170)]} />);
    expect(await screen.findByRole('note')).toBeInTheDocument();
  });

  it('spells out what the compact line means', async () => {
    api.getThreadTokenUsage.mockResolvedValue(null);
    render(<ThreadTokenUsageLine threadId="t1" messages={[answer(8930, 170)]} />);
    const note = await screen.findByRole('note');
    expect(note).toHaveAccessibleName(/9100 tokens used/i);
    expect(note).toHaveAccessibleName(/8930 sent/i);
    expect(note).toHaveAccessibleName(/170 received/i);
  });

  it('spells out the effort too', async () => {
    api.getThreadTokenUsage.mockResolvedValue(null);
    render(<ThreadTokenUsageLine threadId="t1" messages={[answer(10, 5), answer(10, 5)]} />);
    expect(await screen.findByRole('note')).toHaveAccessibleName(/2 model calls/i);
  });
});

describe('what a conversation cost', () => {
  const costing = (cost: string | null) =>
    api.getThreadTokenUsage.mockResolvedValue({
      used: 150,
      inputTokens: 100,
      outputTokens: 50,
      cost,
      currency: 'USD',
    });

  it('says the money beside the tokens', async () => {
    costing('0.0009');
    render(<ThreadTokenUsageLine threadId="t1" />);
    expect(await screen.findByText(/\$0\.0009/)).toBeInTheDocument();
  });

  it('says nothing about money when nothing was priced', async () => {
    costing(null);
    render(<ThreadTokenUsageLine threadId="t1" />);
    await screen.findByText(/150 tokens/);
    expect(screen.queryByText(/\$/)).not.toBeInTheDocument();
  });

  it('does not read an unpriced conversation as free', async () => {
    costing(null);
    render(<ThreadTokenUsageLine threadId="t1" />);
    await screen.findByText(/150 tokens/);
    expect(screen.queryByText(/\$0\.00\b/)).not.toBeInTheDocument();
  });

  it('speaks the cost aloud too', async () => {
    costing('0.0009');
    render(<ThreadTokenUsageLine threadId="t1" />);
    const note = await screen.findByRole('note');
    expect(note.getAttribute('aria-label')).toMatch(/0\.0009/);
  });
});

describe('a conversation nothing kept a total for', () => {
  const message = (tokens: number) => ({
    type: 'ai',
    usage_metadata: { input_tokens: tokens, output_tokens: 1, total_tokens: tokens + 1 },
  });

  it('prices the turns on screen rather than showing no money at all', async () => {
    api.getThreadTokenUsage.mockResolvedValue(null);
    rates.priceTokens.mockResolvedValue({ cost: '0.0013', currency: 'USD' });
    render(<ThreadTokenUsageLine threadId="t1" messages={[message(8900)]} />);
    expect(await screen.findByText(/\$0\.0013/)).toBeInTheDocument();
  });

  it('says nothing about money when no price list priced it', async () => {
    api.getThreadTokenUsage.mockResolvedValue(null);
    rates.priceTokens.mockResolvedValue({ cost: null, currency: 'USD' });
    render(<ThreadTokenUsageLine threadId="t1" messages={[message(8900)]} />);
    await screen.findByText(/8.9k/);
    expect(screen.queryByText(/\$/)).not.toBeInTheDocument();
  });

  it('does not ask for a price when the agent kept the total itself', async () => {
    api.getThreadTokenUsage.mockResolvedValue({
      used: 150, inputTokens: 100, outputTokens: 50, cost: '0.0009', currency: 'USD',
    });
    render(<ThreadTokenUsageLine threadId="t1" messages={[message(100)]} />);
    await screen.findByText(/\$0\.0009/);
    expect(rates.priceTokens).not.toHaveBeenCalled();
  });
});
