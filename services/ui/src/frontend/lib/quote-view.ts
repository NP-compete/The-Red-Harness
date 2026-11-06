export interface QuoteState {
  source: string;
  text: string;
  offset: number;
  shortened: boolean;
}

export interface PresentedQuote {
  text: string;
  source: string;
  note: string;
  jumpTo: number;
}

export function presentQuote(quote: QuoteState | null): PresentedQuote | null {
  if (!quote) {
    return null;
  }

  return {
    // Ellipses keep a cut quote from reading as the whole sentence.
    text: quote.shortened ? `…${quote.text}…` : quote.text,
    source: quote.source,
    note: quote.shortened ? 'Shortened from the original' : '',
    jumpTo: quote.offset,
  };
}
