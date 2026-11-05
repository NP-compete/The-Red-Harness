import { buildAppPath } from '../lib/app-paths';

export interface ConfigProblem {
  source: string;
  detail: string;
}

export interface ConfigProblemReport {
  clean: boolean;
  problems: ConfigProblem[];
  /** The agent could not say — an older build, or it refused. */
  unreadable: boolean;
}

const QUIET: ConfigProblemReport = { clean: true, problems: [], unreadable: true };

/**
 * Whether the agent's configuration loaded without problems.
 *
 * A failure reports `unreadable` rather than inventing a verdict.
 * An older agent that has never heard of this question is not a
 * broken deployment, and saying it is would be a fault report
 * nobody can act on.
 */
export async function readConfigProblems(): Promise<ConfigProblemReport> {
  try {
    const response = await fetch(buildAppPath('/api/proxy/agent/admin/config/problems'), {
      credentials: 'include',
    });
    if (!response.ok) return QUIET;
    const body = (await response.json()) as Partial<ConfigProblemReport>;
    if (typeof body.clean !== 'boolean') return QUIET;
    return {
      clean: body.clean,
      problems: Array.isArray(body.problems) ? body.problems : [],
      unreadable: false,
    };
  } catch {
    return QUIET;
  }
}
