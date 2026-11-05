export interface AccessState {
  level: 'none' | 'read' | 'write';
  reason: string;
  viaLink: boolean;
  heldBy: string;
}

export interface PresentedAccess {
  headline: string;
  detail: string;
  canRead: boolean;
  canEdit: boolean;
  severity: 'info' | 'high';
  action: 'request-access' | 'ask-to-edit' | 'none';
}

export function presentAccess(access: AccessState): PresentedAccess | null {
  // Nothing to say when someone has everything they need.
  if (access.level === 'write') return null;

  if (access.level === 'none') {
    return {
      headline: 'You cannot open this conversation',
      detail: access.reason,
      canRead: false,
      canEdit: false,
      severity: 'high',
      action: 'request-access',
    };
  }

  if (access.viaLink) {
    return {
      headline: 'You are viewing this through a shared link',
      detail: 'A shared link only ever allows reading',
      canRead: true,
      canEdit: false,
      severity: 'info',
      // There is no one to ask: whoever shared the link chose this.
      action: 'none',
    };
  }

  return {
    headline: 'You can read this but not change it',
    detail: access.reason,
    canRead: true,
    canEdit: false,
    severity: 'info',
    action: access.heldBy ? 'ask-to-edit' : 'request-access',
  };
}
