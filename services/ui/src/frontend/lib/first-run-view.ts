export type FirstRunStep = 'connect_source' | 'ask_something' | 'invite_others';

export interface FirstRunCard {
  step: FirstRunStep;
  title: string;
  detail: string;
  action: string;
  dismissible: boolean;
}

export interface PresentedFirstRun {
  /** How many steps are left, for a headline that pluralises. */
  count: number;
  cards: FirstRunCard[];
  blocking: boolean;
}

// Catalogue keys, not words. This runs outside a component, where
// there is no translator to call, so a title written here would be
// English in every language.
const CARDS: Record<FirstRunStep, Omit<FirstRunCard, 'step' | 'dismissible'>> = {
  connect_source: {
    title: 'firstRun.connect_source',
    detail: 'firstRun.connect_sourceDetail',
    action: 'firstRun.connect_sourceAction',
  },
  ask_something: {
    title: 'firstRun.ask_something',
    detail: 'firstRun.ask_somethingDetail',
    action: 'firstRun.ask_somethingAction',
  },
  invite_others: {
    title: 'firstRun.invite_others',
    detail: 'firstRun.invite_othersDetail',
    action: 'firstRun.invite_othersAction',
  },
};

export function presentFirstRun(steps: FirstRunStep[]): PresentedFirstRun | null {
  if (steps.length === 0) {
    return null;
  }

  return {
    // A count, not a sentence: "thing" and "things" is an English
    // rule, and most languages do not divide at one.
    count: steps.length,
    cards: steps.map((step) => ({ step, ...CARDS[step], dismissible: true })),
    // Getting started is an offer, never something to clear before working.
    blocking: false,
  };
}
