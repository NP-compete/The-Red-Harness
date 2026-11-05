export interface TeamEntitlement {
  team: string;
  agents: string[];
  seats: number;
  seatsTaken: string[];
  viewerId: string;
  adminIds: string[];
}

export interface PresentedEntitlement {
  seats: string;
  seatsLow: boolean;
  viewerHasSeat: boolean;
  agents: string[];
  note: string;
  action: 'request-seat' | 'none';
}

export function presentEntitlement(entitlement: TeamEntitlement): PresentedEntitlement {
  const free = Math.max(0, entitlement.seats - entitlement.seatsTaken.length);
  const hasSeat = entitlement.seatsTaken.includes(entitlement.viewerId);

  return {
    seats: free === 0 ? 'No seats free' : `${free} of ${entitlement.seats} seats free`,
    seatsLow: free <= 1,
    viewerHasSeat: hasSeat,
    agents: entitlement.agents,
    note: note(entitlement, hasSeat),
    action: !hasSeat && free > 0 ? 'request-seat' : 'none',
  };
}

function note(entitlement: TeamEntitlement, hasSeat: boolean): string {
  if (entitlement.agents.length === 0) return 'This team has no agents licensed yet';
  if (hasSeat) return '';
  if (entitlement.adminIds.length === 0) return 'No administrator is set for this team';
  return `Ask ${joinNames(entitlement.adminIds)} for a seat`;
}

function joinNames(names: string[]): string {
  if (names.length === 1) return names[0];
  return `${names.slice(0, -1).join(', ')} or ${names[names.length - 1]}`;
}
