export type Risk = 'low' | 'medium' | 'high';

export interface ApprovalRequest {
  tool: string;
  risk: Risk;
  reason: string;
  pending?: number;
  escalated?: boolean;
}

export type ChoiceKind = 'approve-once' | 'approve-run' | 'refuse';

export interface Choice {
  kind: ChoiceKind;
  label: string;
}

export interface PresentedApproval {
  title: string;
  reason: string;
  emphasis: Risk;
  choices: Choice[];
  note?: string;
}

const ESCALATION_NOTE =
  'This conversation has read content from an outside system, so changes are confirmed with you first.';

export function presentApproval(request: ApprovalRequest): PresentedApproval {
  const pending = request.pending ?? 1;

  const choices: Choice[] = [{ kind: 'approve-once', label: 'Yes' }];
  if (pending > 1) {
    choices.push({ kind: 'approve-run', label: `Yes to all ${pending}` });
  }
  choices.push({ kind: 'refuse', label: 'No' });

  return {
    title: `May I run ${request.tool}?`,
    reason: request.reason || 'This action changes data outside this conversation.',
    emphasis: request.risk,
    choices,
    note: request.escalated ? ESCALATION_NOTE : undefined,
  };
}
