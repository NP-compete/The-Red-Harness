import i18n from '../i18n';
export type SkillScope = 'agent' | 'team' | 'user';
export type SkillAction = 'view' | 'edit';

export interface SkillSummary {
  name: string;
  scope: SkillScope;
  usedThisWeek: number;
  editable: boolean;
}

export interface SkillRow {
  name: string;
  appliesTo: string;
  usage: string;
  actions: SkillAction[];
}

export interface PresentedSkills {
  rows: SkillRow[];
  count: number;
  unused: string[];
  emptyMessage: string;
}

const APPLIES_TO: Record<SkillScope, string> = {
  agent: 'Everyone using this agent',
  team: 'Your team',
  user: 'Only you',
};

export function presentSkills(skills: SkillSummary[]): PresentedSkills {
  const rows = skills.map<SkillRow>((skill) => ({
    name: skill.name,
    appliesTo: APPLIES_TO[skill.scope],
    usage: describeUsage(skill.usedThisWeek),
    actions: skill.editable ? ['view', 'edit'] : ['view'],
  }));

  return {
    rows,
    count: rows.length,
    // Guidance nobody reaches for is guidance nobody is maintaining.
    unused: skills.filter((skill) => skill.usedThisWeek === 0).map((skill) => skill.name),
    emptyMessage: i18n.t('skills.noneWritten'),
  };
}

function describeUsage(count: number): string {
  if (count === 0) return 'not used this week';
  if (count === 1) return 'used once this week';
  return `used ${count} times this week`;
}
