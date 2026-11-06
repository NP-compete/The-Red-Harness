import { buildAgentApiUrl } from '../lib/app-paths';
import { authenticatedFetch } from './authenticated-fetch';
import type { Risk } from '../lib/approval';

export type Decision = 'allow' | 'ask' | 'refuse';

export interface ApprovalRule {
  tools: string[];
  decision: Decision;
  risk: Risk;
  reason: string;
}

export interface WorkspaceRule {
  operations: string[];
  paths: string[];
  allowed: boolean;
}

export interface ApprovalPolicy {
  enabled: boolean;
  otherwise: Decision;
  rules: ApprovalRule[];
  /** Where the agent may read and write, and where it may not. */
  workspace: WorkspaceRule[];
  /** False when nothing it does reaches outside the conversation. */
  live: boolean;
}

/**
 * What this deployment lets the agent do without asking.
 *
 * The approvals a person grants sit on top of this, and until now
 * only their half was visible — so "why did it just ask me about
 * that?" and "why did it *not* ask me about that?" had no answer
 * anywhere in the product.
 */
export async function getApprovalPolicy(): Promise<ApprovalPolicy | null> {
  try {
    const response = await authenticatedFetch(buildAgentApiUrl('/permissions'), {
      method: 'GET',
    });
    if (!response.ok) return null;

    const body = (await response.json()) as {
      approval?: {
        enabled?: boolean;
        default_decision?: string;
        policies?: unknown[];
      };
      filesystem?: { rules?: unknown[] };
      dry_run?: boolean;
    };
    const approval = body.approval;
    if (!approval) return null;

    const rules = (approval.policies ?? [])
      .filter(
        (rule): rule is { tools: string[]; decision?: string; risk?: string; reason?: string } =>
          Boolean(
            rule &&
              typeof rule === 'object' &&
              Array.isArray((rule as { tools?: unknown }).tools) &&
              (rule as { tools: unknown[] }).tools.length > 0,
          ),
      )
      .map((rule) => ({
        tools: rule.tools.map(String),
        decision: asDecision(rule.decision),
        risk: asRisk(rule.risk),
        reason: rule.reason ?? '',
      }));

    const workspace = (body.filesystem?.rules ?? [])
      .filter(
        (rule): rule is { operations?: unknown[]; paths: unknown[]; mode?: string } =>
          Boolean(
            rule &&
              typeof rule === 'object' &&
              Array.isArray((rule as { paths?: unknown }).paths) &&
              (rule as { paths: unknown[] }).paths.length > 0,
          ),
      )
      .map((rule) => ({
        operations: (rule.operations ?? []).map(String),
        paths: rule.paths.map(String),
        allowed: rule.mode !== 'deny',
      }));

    return {
      enabled: approval.enabled !== false,
      otherwise: asDecision(approval.default_decision),
      rules,
      workspace,
      live: body.dry_run !== true,
    };
  } catch {
    return null;
  }
}

function asDecision(value: unknown): Decision {
  return value === 'allow' || value === 'refuse' ? value : 'ask';
}

function asRisk(value: unknown): Risk {
  return value === 'high' || value === 'medium' ? value : 'low';
}
