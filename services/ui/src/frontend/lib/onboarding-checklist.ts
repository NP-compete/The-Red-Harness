export interface SetupState {
  hasSeat: boolean;
  hasAgent: boolean;
  connectedServers: number;
  budgetSet: boolean;
  approverSet: boolean;
  firstRunDone: boolean;
  isAdmin: boolean;
}

export interface ChecklistStep {
  id: string;
  title: string;
  doneBy: string;
  href: string;
  blocked: boolean;
}

export interface PresentedChecklist {
  remaining: ChecklistStep[];
  progress: string;
  complete: boolean;
}

const ADMIN = 'an administrator';
const YOU = 'you';

export function presentChecklist(setup: SetupState): PresentedChecklist {
  const steps = [
    {
      id: 'seat',
      title: 'Get a seat on a team',
      done: setup.hasSeat,
      adminOnly: false,
      doneBy: ADMIN,
      href: '/settings/teams',
      needs: [],
    },
    {
      id: 'agent',
      title: 'Have an agent licensed',
      done: setup.hasAgent,
      adminOnly: false,
      doneBy: ADMIN,
      href: '/settings/agents',
      needs: ['seat'],
    },
    {
      id: 'connect',
      title: 'Connect a server',
      done: setup.connectedServers > 0,
      adminOnly: false,
      doneBy: YOU,
      href: '/settings/components/mcp',
      needs: ['seat'],
    },
    {
      id: 'budget',
      title: 'Set a spending limit',
      done: setup.budgetSet,
      adminOnly: true,
      doneBy: ADMIN,
      href: '/settings/budget',
      needs: [],
    },
    {
      id: 'approver',
      title: 'Name who approves risky steps',
      done: setup.approverSet,
      adminOnly: true,
      doneBy: ADMIN,
      href: '/settings/approvals',
      needs: [],
    },
    {
      id: 'first-run',
      title: 'Run something',
      done: setup.firstRunDone,
      adminOnly: false,
      doneBy: YOU,
      href: '/',
      needs: ['seat', 'agent'],
    },
  ];

  // An unfinished step nobody here can act on is noise, not a checklist item.
  const applicable = steps.filter((step) => step.done || !step.adminOnly || setup.isAdmin);
  const done = applicable.filter((step) => step.done);
  const doneIds = new Set(done.map((step) => step.id));

  const remaining = applicable
    .filter((step) => !step.done)
    .map(({ id, title, doneBy, href, needs }) => ({
      id,
      title,
      doneBy,
      href,
      blocked: needs.some((need) => !doneIds.has(need)),
    }));

  return {
    remaining,
    progress: `${done.length} of ${applicable.length} done`,
    complete: remaining.length === 0,
  };
}
