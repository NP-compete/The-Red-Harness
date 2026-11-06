import i18n from '../i18n';
export type RefusalCode = 'no_authority' | 'policy_denied' | 'budget_exhausted';

export interface Refusal {
  code: RefusalCode;
  message: string;
  remedy: string;
  server?: string;
}

export type RefusalAction =
  | { kind: 'connect'; label: string; target: string }
  | { kind: 'new-conversation'; label: string };

export interface PresentedRefusal {
  title: string;
  detail: string;
  remedy: string;
  action?: RefusalAction;
}

const TITLES: Record<RefusalCode, string> = {
  no_authority: 'Not connected',
  policy_denied: 'Not allowed',
  budget_exhausted: 'Out of budget',
};

export function presentRefusal(refusal: Refusal): PresentedRefusal {
  const title = TITLES[refusal.code] ?? 'Could not continue';

  return {
    title,
    detail: refusal.message || refusal.remedy || title,
    remedy: refusal.remedy,
    action: actionFor(refusal),
  };
}

function actionFor(refusal: Refusal): RefusalAction | undefined {
  if (refusal.code === 'no_authority' && refusal.server) {
    return { kind: 'connect', label: i18n.t('refusal.connectServer', { server: refusal.server }), target: refusal.server };
  }
  if (refusal.code === 'budget_exhausted') {
    return { kind: 'new-conversation', label: i18n.t('refusal.startNewConversation') };
  }
  return undefined;
}
