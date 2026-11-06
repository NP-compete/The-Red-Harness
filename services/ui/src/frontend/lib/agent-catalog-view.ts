export interface CatalogAgent {
  name: string;
  summary: string;
  licensed: boolean;
  hasSeat: boolean;
  missingScopes: string[];
  deprecated: boolean;
  lastUsedAt: string | null;
}

export interface AgentCard {
  name: string;
  summary: string;
  usable: boolean;
  blockedBy: string;
  lastUsed: string;
  note: string;
  action: 'start' | 'request-access';
}

export interface PresentedCatalog {
  cards: AgentCard[];
  usableCount: number;
  emptyMessage: string;
}

const DAY = 86_400_000;

export function presentCatalog(agents: CatalogAgent[], now: Date): PresentedCatalog {
  const cards = [...agents]
    .map((agent) => {
      const blockedBy = blocked(agent);
      return {
        name: agent.name,
        summary: agent.summary,
        usable: blockedBy === '',
        blockedBy,
        lastUsed: agent.lastUsedAt ? ago(agent.lastUsedAt, now) : 'never used',
        note: agent.deprecated ? 'Being retired' : '',
        action: blockedBy === '' ? ('start' as const) : ('request-access' as const),
      };
    })
    .sort((a, b) => Number(b.usable) - Number(a.usable) || a.name.localeCompare(b.name));

  return {
    cards,
    usableCount: cards.filter((card) => card.usable).length,
    emptyMessage: cards.length === 0 ? 'No agents are available to you yet' : '',
  };
}

function blocked(agent: CatalogAgent): string {
  // Whoever can unblock it differs by reason, so only the first one is shown.
  if (!agent.licensed) return 'Your organisation is not licensed for this';
  if (!agent.hasSeat) return 'You need a seat on this team';
  if (agent.missingScopes.length > 0) {
    return `You need access to ${agent.missingScopes.join(', ')}`;
  }
  return '';
}

function ago(at: string, now: Date): string {
  const days = Math.round((now.getTime() - Date.parse(at)) / DAY);
  if (days < 1) return 'today';
  if (days === 1) return 'yesterday';
  return `${days} days ago`;
}
